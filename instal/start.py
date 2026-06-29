#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
start.py
================================================================
ЕДИНСТВЕННАЯ ТОЧКА ВХОДА для запуска ComfyUI на Kaggle.

Всё в одном: %run instal/start.py
  * сам проверяет, чего не хватает
  * сам доустанавливает ComfyUI / torch / кастомные ноды / модели
  * сам запускает ComfyUI + Cloudflare-туннель + SageAttention + keep-alive

Никаких ручных шагов. Одна ячейка — полный пайплайн.

Архитектура (все модули в instal/):
  * start.py           — тонкий вход (только setup_env + передача лаунчеру)
  * kaggle_env.py      — пути, venv, uv (единый источник правды)
  * launcher.py        — ComfyLauncher (проверки, доустановка, жизненный цикл)
  * logging_ui.py      — LogManager (UI + троттлинг лога)
  * sage_installer.py  — SageAttention-SM75 (Turing T4)
================================================================
"""

import importlib
import os
import shutil
import sys

# ----------------------------------------------------------------------
# 0. Сброс stale-кэша модулей и .pyc
# ----------------------------------------------------------------------
try:
    _KE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _KE_DIR = "/kaggle/working/instal"
sys.path.insert(0, _KE_DIR)

# После git pull в той же сессии Jupyter старые .py файлы обновлены,
# но sys.modules хранит закешированные старые модули.
# Выкидываем все instal-модули — Python перечитает свежие .py.
for _mod_name in list(sys.modules.keys()):
    if _mod_name in (
        "kaggle_env", "logging_ui", "launcher", "sage_installer",
        "instal_comfyui", "instal_castom_node",
    ):
        del sys.modules[_mod_name]

# Чистим все __pycache__ в instal/ рекурсивно — stale .pyc переживает
# git pull, и Python может не перекомпилировать, если timestamp совпал.
for _root, _dirs, _files in os.walk(_KE_DIR):
    if "__pycache__" in _dirs:
        shutil.rmtree(os.path.join(_root, "__pycache__"), ignore_errors=True)
        _dirs.remove("__pycache__")  # не лезем внутрь удалённого

# Инвалидируем кэш importlib finder'ов — чтобы они перечитали файлы
# с диска, а не вернули stale spec из внутреннего кэша.
importlib.invalidate_caches()

import kaggle_env as ke

# Ставим UV_* env-переменные и добавляем /kaggle/working/bin в PATH.
# Без этого `uv pip install` падает после рестарта сессии Kaggle.
ke.setup_env()


# ----------------------------------------------------------------------
# 2. Запуск — вся тяжёлая работа в launcher.py
# ----------------------------------------------------------------------
def launch():
    """Передаёт управление ComfyLauncher'у. Тот сам доустановит всё
    необходимое (ComfyUI, torch, ноды) и запустит сервис."""
    os.chdir(ke.HOME_DIR)

    from launcher import ComfyLauncher
    return ComfyLauncher().launch()


# При `%run start.py` запускаемся автоматически.
if __name__ == "__main__":
    launch()
