import subprocess
r = subprocess.run(["python","instal_castom_node.py"], cwd="/kaggle/working",
                   capture_output=True, text=True)
print(r.stdout[-10000:])
print("STDERR_TAIL:\n", r.stderr[-3000:])
print("RC:", r.returncode)
