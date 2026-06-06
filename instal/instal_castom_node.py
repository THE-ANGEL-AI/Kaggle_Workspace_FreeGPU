#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
instal_castom_node.py
=================================================================
ШАГ 2 из 3. Ставит кастомные ноды и делает символьные ссылки на
модели (как в исходном блокноте, но без конфликтов).

Главное изменение против тормозов на мульти-GPU:
  * Вместо хака ComfyBootlegOffload.py ставится официальная нода
    ComfyUI-MultiGPU (DisTorch2). Старый гист и DisTorch2 оба патчат
    выгрузку слоёв и КОНФЛИКТУЮТ между собой — отсюда долгая генерация
    на двух T4. Оставляем только ComfyUI-MultiGPU.

Список нод и список ссылок на модели вынесены наверх — правь их там,
ты добавляешь модели и ноды вручную.

Запуск (в блокноте):  !python instal/instal_castom_node.py

Перед работой скрипт проверяет, что ШАГ 1 выполнен (есть uv, рабочий venv
и папка ComfyUI/custom_nodes). Если нет — выходит с понятной подсказкой.
=================================================================
"""

import os
import shutil
import subprocess

# На Kaggle кэш uv и venv на разных ФС — copy-режим убирает warning про hardlink.
os.environ.setdefault("UV_LINK_MODE", "copy")
# uv не должен задавать интерактивных вопросов (в блокноте отвечать некому).
os.environ.setdefault("UV_NO_PROMPT", "1")

# ----------------------------------------------------------------------
# Пути
# ----------------------------------------------------------------------
HOME_DIR    = "/kaggle/working"
VENV_PYTHON = f"{HOME_DIR}/venv/bin/python"
COMFY_DIR   = f"{HOME_DIR}/ComfyUI"
NODES_DIR   = f"{COMFY_DIR}/custom_nodes"

# ----------------------------------------------------------------------
# СПИСОК КАСТОМНЫХ НОД  (name -> git-репозиторий).
# Добавляй/убирай ноды прямо здесь.
# ----------------------------------------------------------------------
CUSTOM_NODES = {
    "ComfyUI-Crystools":  "https://github.com/crystian/ComfyUI-Crystools.git",
    "ComfyUI-GGUF":       "https://github.com/city96/ComfyUI-GGUF.git",
    "ComfyUI-Logic":      "https://github.com/theUpsider/ComfyUI-Logic.git",
    "comfy-image-saver":  "https://github.com/giriss/comfy-image-saver.git",
    "ComfyUI-QwenVL":     "https://github.com/1038lab/ComfyUI-QwenVL.git",
    # Официальная мульти-GPU нода (DisTorch2). Заменяет ComfyBootlegOffload.py.
    "ComfyUI-MultiGPU":   "https://github.com/pollockjj/ComfyUI-MultiGPU.git",
}

# ----------------------------------------------------------------------
# СИМВОЛЬНЫЕ ССЫЛКИ НА МОДЕЛИ  (источник в /kaggle/input -> папка ComfyUI).
# Это твой раздел: меняй пути под свои датасеты/модели.
# ----------------------------------------------------------------------
SYMLINKS = [
    # (источник, назначение)
    ("/kaggle/input/datasets/theangel/flux2-dev32b/flux2-dev-Q4_0.gguf",
     f"{COMFY_DIR}/models/diffusion_models/flux2-dev-Q4_0.gguf"),

    ("/kaggle/input/datasets/theangel/flux2-dev32b/mistral_3_small_flux2_fp8.safetensors",
     f"{COMFY_DIR}/models/text_encoders/mistral_3_small_flux2_fp8.safetensors"),

    ("/kaggle/input/datasets/theangel/flux2-dev32b/flux2-vae.safetensors",
     f"{COMFY_DIR}/models/vae/flux2-vae.safetensors"),
]


# ----------------------------------------------------------------------
# Помощники
# ----------------------------------------------------------------------
def log(msg):   print(f"\n\033[92m✅ {msg}\033[0m", flush=True)
def warn(msg):  print(f"\n\033[93m⚠️  {msg}\033[0m", flush=True)
def step(msg):  print(f"\n\033[96m=== {msg} ===\033[0m", flush=True)


def run(cmd, check=True, **kwargs):
    printable = cmd if isinstance(cmd, str) else " ".join(cmd)
    print(f"$ {printable}", flush=True)
    return subprocess.run(cmd, check=check, **kwargs)


def uv_pip_install_req(req_path):
    """Ставит requirements ноды в наш venv через uv."""
    run(["uv", "pip", "install", "--python", VENV_PYTHON, "-r", req_path], check=False)


def venv_python_ok():
    """venv цел только если его python реально запускается (см. instal_comfyui.py)."""
    if not os.path.exists(VENV_PYTHON):
        return False
    try:
        subprocess.run([VENV_PYTHON, "-c", "pass"],
                       check=True, capture_output=True, timeout=30)
        return True
    except (subprocess.SubprocessError, OSError):
        return False


def check_prerequisites():
    """Проверяем, что ШАГ 1 выполнен: есть uv, рабочий venv и custom_nodes."""
    step("Проверка окружения (результат ШАГА 1)")
    if not shutil.which("uv"):
        raise RuntimeError(
            "uv не найден. Сначала запусти: !python instal/instal_comfyui.py"
        )
    if not venv_python_ok():
        raise RuntimeError(
            "venv не найден или нерабочий (битый после рестарта сессии). "
            "Перезапусти: !python instal/instal_comfyui.py"
        )
    if not os.path.exists(NODES_DIR):
        raise RuntimeError(
            f"Не найдена папка {NODES_DIR}. "
            "Сначала запусти: !python instal/instal_comfyui.py"
        )
    log("Окружение готово: uv, venv и ComfyUI на месте")


# ----------------------------------------------------------------------
# Установка одной ноды: clone (или pull) + её requirements.
# ----------------------------------------------------------------------
def install_node(name, repo):
    target = os.path.join(NODES_DIR, name)
    if not os.path.exists(target):
        run(["git", "clone", repo, target])
    else:
        run(["git", "-C", target, "pull"], check=False)

    req = os.path.join(target, "requirements.txt")
    if os.path.exists(req):
        uv_pip_install_req(req)
    log(f"Нода готова: {name}")


# ----------------------------------------------------------------------
# Создание символьной ссылки на модель (идемпотентно).
# ----------------------------------------------------------------------
def make_symlink(src, dst):
    if not os.path.exists(src):
        warn(f"Источник не найден, пропуск: {src}")
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.islink(dst) or os.path.exists(dst):
        os.remove(dst)            # пересоздаём, чтобы ссылка всегда была актуальной
    os.symlink(src, dst)
    log(f"Ссылка: {os.path.basename(dst)}")


def main():
    step("ШАГ 2: кастомные ноды + ссылки на модели")

    check_prerequisites()

    step("Установка кастомных нод")
    for name, repo in CUSTOM_NODES.items():
        install_node(name, repo)

    step("Символьные ссылки на модели")
    for src, dst in SYMLINKS:
        make_symlink(src, dst)

    log("ГОТОВО. Ноды и модели на месте. Теперь запусти: %run instal/start.py")


if __name__ == "__main__":
    main()
