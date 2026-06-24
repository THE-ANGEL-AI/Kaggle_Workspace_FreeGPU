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
        "import sys, runpy, llama_cpp\n"
        "_orig = llama_cpp.Llama.__init__\n"
        "def _init(self, *a, **k):\n"
        "    k.setdefault('swa_full', False)\n"
        "    return _orig(self, *a, **k)\n"
        "llama_cpp.Llama.__init__ = _init\n"
        "runpy.run_module('llama_cpp.server', run_name='__main__')\n"
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
    m = re.search(r"https://[^\s]+trycloudflare\.com", line)
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

print("\n" + "=" * 64)
if public and ready():
    print("✅ ГОТОВО. Публичный URL:", public)
    print("\nOpen Code / OpenAI-клиент:")
    print("  Base URL :", public + "/v1")
    print("  API key  : sk-local  (любой непустой)")
    print("  Model    :", MODEL_PATH)
else:
    print("⚠️  URL:", public, "| сервер готов:", ready(), "— проверь", LOG)
print("=" * 64)
