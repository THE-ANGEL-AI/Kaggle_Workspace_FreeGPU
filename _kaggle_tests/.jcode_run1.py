import subprocess, sys, time
t0 = time.time()
p = subprocess.Popen([sys.executable, "/kaggle/working/instal/instal_comfyui.py"],
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
for line in iter(p.stdout.readline, ""):
    sys.stdout.write(line); sys.stdout.flush()
p.wait()
print(f"\n[RUNNER] instal_comfyui.py exit={p.returncode} elapsed={time.time()-t0:.0f}s")
