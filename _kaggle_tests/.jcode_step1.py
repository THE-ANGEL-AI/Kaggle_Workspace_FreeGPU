import subprocess
r = subprocess.run(["python","instal_comfyui.py"], cwd="/kaggle/working",
                   capture_output=True, text=True)
print(r.stdout[-12000:])
print("STDERR_TAIL:\n", r.stderr[-4000:])
print("RETURN CODE:", r.returncode)
