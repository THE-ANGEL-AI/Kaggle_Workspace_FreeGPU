import subprocess, sys, time, socket, os, importlib.util

HOME="/kaggle/working"; VENV=f"{HOME}/venv/bin/python"; COMFY=f"{HOME}/ComfyUI"; PORT=8188

# --- A. Проверяем логику start.py без реального запуска -----------------
print("=== A. Проверка логики start.py ===")
spec = importlib.util.spec_from_file_location("startmod", f"{HOME}/instal/start.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print("INSTALLER путь:", m.INSTALLER, "| существует:", os.path.exists(m.INSTALLER))
lau = m.ComfyLauncher()                      # создаём, UI-виджеты строятся вхолостую
print("_venv_python_ok():", lau._venv_python_ok())   # должно быть True

# --- B. Реальный запуск ComfyUI venv-питоном (как в start.py) ----------
print("\n=== B. Реальный запуск ComfyUI (флаги из start.py) ===")
cmd=[VENV,"main.py","--listen","0.0.0.0","--port",str(PORT),
     "--enable-cors-header","*","--disable-auto-launch",
     "--use-pytorch-cross-attention","--preview-method","auto"]
p=subprocess.Popen(cmd,cwd=COMFY,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
t0=time.time(); started=False
import threading
def reader():
    for line in iter(p.stdout.readline,""):
        sys.stdout.write(line); sys.stdout.flush()
th=threading.Thread(target=reader,daemon=True); th.start()
while time.time()-t0<200:
    if p.poll() is not None:
        print(f"[TEST] ComfyUI ВЫШЕЛ преждевременно code={p.returncode}"); break
    try:
        with socket.create_connection(("127.0.0.1",PORT),timeout=2):
            started=True; break
    except OSError:
        time.sleep(2)
print(f"\n[TEST] порт {PORT} слушается: {started} (за {time.time()-t0:.0f}s)")
# гасим
p.terminate()
try: p.wait(timeout=10)
except subprocess.TimeoutExpired: p.kill()
print(f"[TEST] ComfyUI остановлен. ИТОГ: {'OK' if started else 'FAIL'}")
