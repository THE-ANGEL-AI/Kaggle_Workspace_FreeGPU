#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
instal_comfyui.py
=================================================================
ШАГ 1 из 3. Устанавливает ComfyUI и ноду ComfyUI-Manager.

Что здесь сделано для СКОРОСТИ и против КОНФЛИКТОВ:
  * venv создаётся через `uv` вместо `virtualenv` — установка пакетов
    в разы быстрее (uv ставит torch и зависимости параллельно).
  * Python 3.12 — стабильные колёса (wheels) для torch cu130, быстрый
    интерпретатор. Берётся управляемый uv-ом CPython (не зависим от
    того, что окажется в образе Kaggle).
  * torch собран под CUDA 13.0 (cu130) — драйвер Kaggle (580.x) его держит,
    и ComfyUI 0.24 включает на нём оптимизированные CUDA-операции (на cu128
    был warning и более медленный путь). Проверено на 2× T4.
  * xformers НЕ ставим: последние сборки xformers не содержат ядер для
    Turing (T4, compute 7.5) и только тормозят. Быстрое внимание на T4
    даёт нативный PyTorch SDPA — он включается флагом в start.py.
  * SageAttention СОЗНАТЕЛЬНО НЕ ставим — он несовместим с Turing (T4, sm_75).
    Проверено на железе (июнь 2026):
      - v2.2+ из исходников отказывается собираться: setup.py пропускает обе
        карты ("skipping GPU with compute capability 7.5") и падает с
        "RuntimeError: No target compute capabilities";
      - v1.0.6 (Triton, PyPI) ставится, но падает при запуске ядра на sm_75
        ("RuntimeError: PassManager::run failed").
    SageAttention требует Ampere (sm_80) или новее. На T4 быстрое внимание =
    PyTorch SDPA (флаг --use-pytorch-cross-attention в start.py). Если когда-то
    перейдёшь на sm_80+ GPU — Sage можно будет добавить отдельным шагом.
  * НЕ ставим tensorflow и старые diffusers/transformers — они тянут
    свои версии CUDA/численных библиотек и конфликтуют. Современные
    версии приедут вместе с requirements кастомных нод (шаг 2).

Запуск (в блокноте):  !python instal/instal_comfyui.py

Скрипт ИДЕМПОТЕНТЕН: каждый шаг сначала проверяет, не сделан ли он уже
(uv установлен? venv цел? torch с CUDA на месте? репозитории склонированы?),
и пропускает лишнюю работу. Можно безопасно перезапускать.
=================================================================
"""

import os
import shutil
import subprocess
import sys

# На Kaggle кэш uv и venv на разных ФС — hardlink не работает, uv ругается.
# copy-режим убирает предупреждение и лишние попытки слинковать.
os.environ.setdefault("UV_LINK_MODE", "copy")
# uv не должен задавать интерактивных вопросов (в блокноте отвечать некому).
os.environ.setdefault("UV_NO_PROMPT", "1")

# ----------------------------------------------------------------------
# Пути и параметры. Меняй здесь, если нужно другое окружение.
# ----------------------------------------------------------------------
HOME_DIR     = "/kaggle/working"
VENV_DIR     = f"{HOME_DIR}/venv"
VENV_PYTHON  = f"{VENV_DIR}/bin/python"
COMFY_DIR    = f"{HOME_DIR}/ComfyUI"

# Управляемый uv-ом CPython кладём в /kaggle/working (переживает рестарт сессии),
# а НЕ в ~/.local (НЕ переживает). Иначе симлинк venv/bin/python после каждого
# рестарта становится битым → torch приходится ставить заново каждый раз.
# Теперь и venv, и его базовый python персистентны — venv выживает между сессиями.
os.environ.setdefault("UV_PYTHON_INSTALL_DIR", f"{HOME_DIR}/uv-python")

PYTHON_VERSION = "3.12"                                  # версия интерпретатора в venv
# CUDA 13.0: драйвер Kaggle (580.x) его поддерживает, а ComfyUI 0.24 на cu130
# включает оптимизированные CUDA-операции (на cu128 был warning и медленный путь).
# Проверено на 2× T4: оба GPU работают, предупреждение исчезает.
# Если понадобится откат на 12.8 — поставь cu128.
TORCH_INDEX    = "https://download.pytorch.org/whl/cu130"  # CUDA 13.0 (оптимизированный путь ComfyUI)

COMFYUI_REPO = "https://github.com/Comfy-Org/ComfyUI.git"
MANAGER_REPO = "https://github.com/ltdrdata/ComfyUI-Manager.git"


# ----------------------------------------------------------------------
# Маленькие помощники: единый стиль вывода и запуск команд.
# ----------------------------------------------------------------------
def log(msg):      print(f"\n\033[92m✅ {msg}\033[0m", flush=True)
def warn(msg):     print(f"\n\033[93m⚠️  {msg}\033[0m", flush=True)
def step(msg):     print(f"\n\033[96m=== {msg} ===\033[0m", flush=True)


def run(cmd, check=True, **kwargs):
    """Печатает и выполняет команду. По умолчанию падает при ошибке."""
    if isinstance(cmd, str):
        printable = cmd
        kwargs.setdefault("shell", True)
    else:
        printable = " ".join(cmd)
    print(f"$ {printable}", flush=True)
    return subprocess.run(cmd, check=check, **kwargs)


def uv_pip_install(*packages, extra_args=None):
    """uv pip install в наш venv (быстрее обычного pip)."""
    cmd = ["uv", "pip", "install", "--python", VENV_PYTHON]
    if extra_args:
        cmd += list(extra_args)
    cmd += list(packages)
    run(cmd)


def venv_python_ok():
    """venv считается рабочим, только если его python РЕАЛЬНО запускается.

    На Kaggle папка /kaggle/working/venv переживает рестарт сессии, а вот
    управляемый uv-ом CPython, на который ссылается venv/bin/python, лежит
    в кэше (~/.local, ~/.cache) и НЕ переживает. Симлинк становится битым:
    os.path.exists по нему вернёт False, но даже если файл на месте — он
    может не запускаться. Поэтому проверяем именно запуском.
    """
    if not os.path.exists(VENV_PYTHON):
        return False
    try:
        subprocess.run([VENV_PYTHON, "-c", "pass"],
                       check=True, capture_output=True, timeout=30)
        return True
    except (subprocess.SubprocessError, OSError):
        return False


def torch_cuda_ok():
    """torch уже стоит в venv и видит CUDA? Тогда переустановка не нужна."""
    if not venv_python_ok():
        return False
    try:
        subprocess.run(
            [VENV_PYTHON, "-c", "import torch; assert torch.cuda.is_available()"],
            check=True, capture_output=True, timeout=120)
        return True
    except (subprocess.SubprocessError, OSError):
        return False


# ----------------------------------------------------------------------
# 1. Системные пакеты (ffmpeg для нод с видео/превью).
# ----------------------------------------------------------------------
def install_system_packages():
    step("Системные пакеты (ffmpeg)")
    if shutil.which("ffmpeg"):
        log("ffmpeg уже установлен (пропуск apt)")
        return
    run("apt-get update -qq", check=False)
    run("apt-get install -y -qq ffmpeg", check=False)


# ----------------------------------------------------------------------
# 2. Ставим uv (если ещё нет) и создаём venv нужной версии Python.
# ----------------------------------------------------------------------
def ensure_uv():
    """Ставим uv, только если его ещё нет. Без лишних переустановок."""
    if shutil.which("uv"):
        log("uv уже установлен (пропуск)")
        return

    step("Установка uv")
    # На свежих образах системный python «externally managed» (PEP 668) и
    # pip без флага падает. Сначала пробуем обычно, при ошибке — с флагом.
    base = [sys.executable, "-m", "pip", "install", "-q", "-U", "uv"]
    if run(base, check=False).returncode != 0:
        warn("pip отказал (externally-managed?), пробую --break-system-packages")
        run(base + ["--break-system-packages"], check=False)

    if not shutil.which("uv"):
        # uv мог встать в каталог, которого нет в PATH (~/.local/bin).
        local_bin = os.path.expanduser("~/.local/bin")
        if os.path.exists(os.path.join(local_bin, "uv")):
            os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")
    if not shutil.which("uv"):
        raise RuntimeError("Не удалось установить uv — проверь лог выше")
    log("uv установлен")


def setup_uv_venv():
    ensure_uv()

    step("Создание venv")
    if venv_python_ok():
        log(f"venv уже существует и рабочий: {VENV_DIR} (пересоздание пропущено)")
        return

    if os.path.exists(VENV_DIR):
        # Папка есть, но python не запускается (битый симлинк после рестарта
        # сессии). Создаём заново поверх с --clear, без интерактивных вопросов.
        warn(f"venv найден, но нерабочий — пересоздаю: {VENV_DIR}")

    # --seed кладёт pip/setuptools внутрь venv — некоторым нодам это нужно.
    # --clear молча перезаписывает существующую папку (без вопроса «очистить?»).
    run(["uv", "venv", VENV_DIR, "--python", PYTHON_VERSION, "--seed", "--clear"])
    log(f"venv создан на Python {PYTHON_VERSION}: {VENV_DIR}")


# ----------------------------------------------------------------------
# 3. PyTorch под CUDA 13.0 (главное для скорости генерации).
# ----------------------------------------------------------------------
def install_torch():
    step("PyTorch для CUDA 13.0 (cu130)")
    if torch_cuda_ok():
        log("torch с рабочей CUDA уже установлен (переустановка пропущена)")
    else:
        uv_pip_install(
            "torch", "torchvision", "torchaudio",
            extra_args=["--index-url", TORCH_INDEX],
        )

    # Проверяем, что torch видит CUDA — сразу ловим проблему, не на запуске.
    run([VENV_PYTHON, "-c",
         "import torch; "
         "print('Torch:', torch.__version__); "
         "print('CUDA build:', torch.version.cuda); "
         "print('CUDA available:', torch.cuda.is_available()); "
         "print('GPU count:', torch.cuda.device_count())"],
        check=False)


# ----------------------------------------------------------------------
# 4. ComfyUI: клон + его зависимости.
# ----------------------------------------------------------------------
def install_comfyui():
    step("ComfyUI")
    if not os.path.exists(COMFY_DIR):
        run(["git", "clone", COMFYUI_REPO, COMFY_DIR])
    else:
        run(["git", "-C", COMFY_DIR, "pull"], check=False)

    uv_pip_install("-r", f"{COMFY_DIR}/requirements.txt")
    log("ComfyUI и его зависимости установлены")


# ----------------------------------------------------------------------
# 5. ComfyUI-Manager (менеджер нод — ставится здесь по ТЗ).
# ----------------------------------------------------------------------
def install_manager():
    step("Нода ComfyUI-Manager")
    manager_dir = f"{COMFY_DIR}/custom_nodes/ComfyUI-Manager"
    if not os.path.exists(manager_dir):
        run(["git", "clone", MANAGER_REPO, manager_dir])
    else:
        run(["git", "-C", manager_dir, "pull"], check=False)

    req = f"{manager_dir}/requirements.txt"
    if os.path.exists(req):
        uv_pip_install("-r", req)
    log("ComfyUI-Manager установлен")


# ----------------------------------------------------------------------
# 6. Небольшой набор общих пакетов, полезных большинству нод.
#    (Современные версии, без старых пинов — чтобы не было конфликтов.)
# ----------------------------------------------------------------------
def install_common_extras():
    step("Общие вспомогательные пакеты")
    uv_pip_install(
        "nvidia-ml-py",   # мониторинг GPU (Crystools)
        "einops",
        "omegaconf",
        "timm",
        "mediapy",
        "loguru",
        "imageio[ffmpeg]", "opencv-python", "ffmpeg-python",
    )
    log("Вспомогательные пакеты установлены")


def main():
    step("ШАГ 1: установка ComfyUI и Manager (uv + torch cu130)")
    os.chdir(HOME_DIR)

    install_system_packages()
    setup_uv_venv()
    install_torch()
    install_comfyui()
    install_manager()
    install_common_extras()

    log("ГОТОВО. ComfyUI установлен. Теперь запусти: !python instal/instal_castom_node.py")


if __name__ == "__main__":
    main()
