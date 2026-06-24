# -*- coding: utf-8 -*-
"""Builds gemma_kaggle_server.ipynb (local helper, not part of the runtime)."""
import json, os

md_intro = """\
# Gemma 4 (Q8_0) — OpenAI-сервер на Kaggle (2× T4) + публичный URL

Поднимает **llama-cpp-python** с CUDA на двух Tesla T4, OpenAI-совместимый сервер
и **Cloudflare-туннель** → публичный URL для подключения в **Open Code** / любой
OpenAI-клиент.

**Подключение в Open Code:**
- Base URL: `<публичный_url>/v1`
- API key: любой непустой (напр. `sk-local`)
- Model: `/kaggle/working/models/gemma4-v2-Q8_0.gguf`

Проверено на железе (2× T4, драйвер 580.x, CUDA 12.8, Python 3.12):
обе карты грузятся через `tensor_split`, ответ ~0.6 c.
"""

setup = '''\
# ── 1. УСТАНОВКА И ЗАГРУЗКА ────────────────────────────────────────────────
import os, subprocess, sys

MODEL_DIR  = "/kaggle/working/models"
MODEL_PATH = f"{MODEL_DIR}/gemma4-v2-Q8_0.gguf"
REPO_ID    = "yuxinlu1/gemma-4-12B-agentic-fable5-composer2.5-v2-3.5x-tau2-GGUF"
HOME       = os.path.expanduser("~")
CF_BIN     = f"{HOME}/cloudflared"
os.makedirs(MODEL_DIR, exist_ok=True)

# llama-cpp-python с CUDA: готовый wheel из индекса abetlen (cu124 работает на
# драйвере cu128). [server] добавляет OpenAI-совместимый сервер.
# Прим.: wheel deepbeepmeep llamacpp_gguf_cuda — cp311, НЕ ставится на Python 3.12
# образа Kaggle, и не нужен: этот wheel уже даёт полный GPU-offload на обе T4.
try:
    import llama_cpp  # noqa: F401
    print("[*] llama-cpp-python уже установлен:", llama_cpp.__version__)
except ImportError:
    print("[*] Ставлю llama-cpp-python[server] (CUDA wheel)...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--prefer-binary",
                    "llama-cpp-python[server]",
                    "--extra-index-url",
                    "https://abetlen.github.io/llama-cpp-python/whl/cu124"], check=True)

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "huggingface_hub"], check=False)

# cloudflared: качаем бинарь напрямую (надёжнее, чем pip-пакет), +x обязателен.
if not os.path.exists(CF_BIN) or os.path.getsize(CF_BIN) < 5_000_000:
    print("[*] Скачиваю cloudflared...")
    subprocess.run(["wget", "-q",
        "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
        "-O", CF_BIN], check=True)
os.chmod(CF_BIN, 0o755)
print("[*] cloudflared готов")

# Модель (~12.7 ГБ) — качаем только если её ещё нет.
if not os.path.exists(MODEL_PATH):
    print("[*] Скачиваю модель (~12.7 ГБ)...")
    from huggingface_hub import hf_hub_download
    hf_hub_download(repo_id=REPO_ID, filename="gemma4-v2-Q8_0.gguf",
                    local_dir=MODEL_DIR)
print("[*] МОДЕЛЬ:", MODEL_PATH,
      f"({os.path.getsize(MODEL_PATH)/1e9:.1f} ГБ)" if os.path.exists(MODEL_PATH) else "(нет)")
'''

launch = '''\
# ── 2. ЗАПУСК СЕРВЕРА + ТУННЕЛЯ ────────────────────────────────────────────
import os, re, time, json, signal, subprocess, urllib.request

PORT       = 8080
MODEL_PATH = "/kaggle/working/models/gemma4-v2-Q8_0.gguf"
CF_BIN     = os.path.expanduser("~/cloudflared")
LOG        = "/kaggle/working/server.log"

# Идемпотентность: гасим прошлые процессы перед повторным запуском.
subprocess.run("pkill -f gemma_server.py; pkill -f llama_cpp.server; pkill -f cloudflared", shell=True)
time.sleep(2)

# Лаунчер-обёртка: llama_cpp.server НЕ умеет swa_full через CLI, а для Gemma на
# 256k он обязателен — иначе SWA-слои аллоцируют KV на полный контекст (~90 ГБ, OOM).
# swa_full=False → эффективный KV-кэш (sliding window 1024), flash_attn убирает
# паддинг V-кэша и огромный буфер внимания. Итог: ~20 ГБ из 30 на 256k.
LAUNCHER = "/kaggle/working/gemma_server.py"
with open(LAUNCHER, "w") as f:
    f.write(
        "import sys, runpy, llama_cpp\\n"
        "_orig = llama_cpp.Llama.__init__\\n"
        "def _init(self, *a, **k):\\n"
        "    k.setdefault('swa_full', False)\\n"
        "    return _orig(self, *a, **k)\\n"
        "llama_cpp.Llama.__init__ = _init\\n"
        "runpy.run_module('llama_cpp.server', run_name='__main__')\\n"
    )

# Сервер: оба T4 через tensor_split, все слои на GPU, полное окно 256k.
server = subprocess.Popen([
    "python", LAUNCHER,
    "--model", MODEL_PATH,
    "--host", "0.0.0.0", "--port", str(PORT),
    "--n_gpu_layers", "999",
    "--tensor_split", "0.5", "0.5",
    "--n_ctx", "262144",       # полное окно 256k
    "--n_batch", "256",
    "--n_ubatch", "128",       # КРИТ: маленькая порция prompt-eval → не падаем на больших промптах (opencode шлёт 30k+ токенов)
    "--flash_attn", "true",    # обязателен для 256k: маленький буфер внимания + V-кэш без паддинга
    "--use_mlock", "false",    # КРИТИЧНО: дефолт сервера True лочит 12.7 ГБ в RAM → OOM. Off = веса стримятся в VRAM
    "--use_mmap", "true",      # mmap: страницы файла → GPU, RAM почти не тратится
], stdout=open(LOG, "w"), stderr=subprocess.STDOUT)
print("[*] server PID:", server.pid, "(лог:", LOG + ")")

# Туннель Cloudflare.
tun = subprocess.Popen(
    [CF_BIN, "tunnel", "--no-autoupdate", "--protocol", "http2",
     "--url", f"http://127.0.0.1:{PORT}"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

public = None
t0 = time.time()
while time.time() - t0 < 90:
    line = tun.stdout.readline()
    if not line:
        if tun.poll() is not None:
            break
        continue
    m = re.search(r"https://[^\\s]+trycloudflare\\.com", line)
    if m:
        public = m.group(0)
        break

# Ждём прогрузку модели (≈20–60 c для Q8 на 2× T4).
def ready():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/v1/models", timeout=3).read()
        return True
    except Exception:
        return False

print("[*] Жду прогрузку модели...")
t0 = time.time()
while time.time() - t0 < 240 and not ready():
    if server.poll() is not None:
        raise RuntimeError("Сервер упал — смотри " + LOG)
    time.sleep(5)

print("\\n" + "=" * 64)
if public and ready():
    print("✅ ГОТОВО. Публичный URL:", public)
    print("\\nOpen Code / OpenAI-клиент:")
    print("  Base URL :", public + "/v1")
    print("  API key  : sk-local  (любой непустой)")
    print("  Model    :", MODEL_PATH)
else:
    print("⚠️  URL:", public, "| сервер готов:", ready(), "— проверь", LOG)
print("=" * 64)
'''

test = '''\
# ── 3. (опц.) ПРОВЕРКА ─────────────────────────────────────────────────────
import json, time, urllib.request

URL = f"http://127.0.0.1:8080/v1/chat/completions"
body = json.dumps({"model": "gemma",
    "messages": [{"role": "user", "content": "Привет! Ответь одним словом."}],
    "max_tokens": 32, "temperature": 0.7}).encode()
req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
t = time.time()
r = json.loads(urllib.request.urlopen(req, timeout=120).read())
print("Ответ:", r["choices"][0]["message"]["content"].strip())
print("Латентность:", round(time.time() - t, 2), "c |", r.get("usage"))
'''

stop = '''\
# ── 4. (опц.) ОСТАНОВКА ────────────────────────────────────────────────────
import subprocess
subprocess.run("pkill -f llama_cpp.server; pkill -f cloudflared", shell=True)
print("Сервер и туннель остановлены.")
'''

def code(src):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": src}

nb = {
    "cells": [
        {"cell_type": "markdown", "metadata": {}, "source": md_intro},
        code(setup), code(launch), code(test), code(stop),
    ],
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    },
    "nbformat": 4, "nbformat_minor": 5,
}

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gemma_kaggle_server.ipynb")
with open(out, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("wrote", out)
