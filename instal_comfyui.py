#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
instal_comfyui.py
=================================================================
ШАГ 1 из 3. Устанавливает ComfyUI и ноду ComfyUI-Manager.

Что здесь сделано для СКОРОСТИ и против КОНФЛИКТОВ:
  * venv создаётся через `uv` вместо `virtualenv` — установка пакетов
    в разы быстрее (uv ставит torch и зависимости параллельно).
  * Python 3.12 — стабильные колёса (wheels) для torch cu128, быстрый
    интерпретатор. Берётся управляемый uv-ом CPython (не зависим от
    того, что окажется в образе Kaggle).
  * torch собран под CUDA 12.8 (cu128, стабильный канал) — подходит к
    драйверу Kaggle и к картам T4.
  * xformers НЕ ставим: последние сборки xformers не содержат ядер для
    Turing (T4, compute 7.5) и только тормозят. Быстрое внимание на T4
    даёт нативный PyTorch SDPA — он включается флагом в start.py.
  * НЕ ставим tensorflow и старые diffusers/transformers — они тянут
    свои версии CUDA/численных библиотек и конфликтуют. Современные
    версии приедут вместе с requirements кастомных нод (шаг 2).

Запуск (в блокноте):  !python instal_comfyui.py
=================================================================
"""

import os
import subprocess
import sys

# На Kaggle кэш uv и venv на разных ФС — hardlink не работает, uv ругается.
# copy-режим убирает предупреждение и лишние попытки слинковать.
os.environ.setdefault("UV_LINK_MODE", "copy")

# ----------------------------------------------------------------------
# Пути и параметры. Меняй здесь, если нужно другое окружение.
# ----------------------------------------------------------------------
HOME_DIR     = "/kaggle/working"
VENV_DIR     = f"{HOME_DIR}/venv"
VENV_PYTHON  = f"{VENV_DIR}/bin/python"
COMFY_DIR    = f"{HOME_DIR}/ComfyUI"

PYTHON_VERSION = "3.12"                                  # версия интерпретатора в venv
TORCH_INDEX    = "https://download.pytorch.org/whl/cu128"  # стабильный канал CUDA 12.8

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


# ----------------------------------------------------------------------
# 1. Системные пакеты (ffmpeg для нод с видео/превью).
# ----------------------------------------------------------------------
def install_system_packages():
    step("Системные пакеты (ffmpeg)")
    run("apt-get update -qq", check=False)
    run("apt-get install -y -qq ffmpeg", check=False)


# ----------------------------------------------------------------------
# 2. Ставим uv и создаём venv нужной версии Python.
# ----------------------------------------------------------------------
def setup_uv_venv():
    step("Установка uv и создание venv")
    run([sys.executable, "-m", "pip", "install", "-q", "-U", "uv"])

    if os.path.exists(VENV_PYTHON):
        log(f"venv уже существует: {VENV_DIR} (пересоздание пропущено)")
        return

    # --seed кладёт pip/setuptools внутрь venv — некоторым нодам это нужно.
    run(["uv", "venv", VENV_DIR, "--python", PYTHON_VERSION, "--seed"])
    log(f"venv создан на Python {PYTHON_VERSION}: {VENV_DIR}")


# ----------------------------------------------------------------------
# 3. PyTorch под CUDA 12.8 (главное для скорости генерации).
# ----------------------------------------------------------------------
def install_torch():
    step("PyTorch для CUDA 12.8 (cu128)")
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
    step("ШАГ 1: установка ComfyUI и Manager (uv + torch cu128)")
    os.chdir(HOME_DIR)

    install_system_packages()
    setup_uv_venv()
    install_torch()
    install_comfyui()
    install_manager()
    install_common_extras()

    log("ГОТОВО. ComfyUI установлен. Теперь запусти: !python instal_castom_node.py")


if __name__ == "__main__":
    main()
