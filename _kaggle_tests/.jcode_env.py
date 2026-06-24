import subprocess, sys, os
print("=== nvidia-smi ===")
print(subprocess.run(["nvidia-smi","--query-gpu=name,driver_version,memory.total","--format=csv"],
                     capture_output=True, text=True).stdout)
print("=== python (system) ===", sys.version.split()[0])
print("=== cwd ===", os.getcwd())
print("=== /kaggle/working listing ===")
print(subprocess.run(["ls","-la","/kaggle/working"], capture_output=True, text=True).stdout)
print("=== uv? ===")
print(subprocess.run(["bash","-lc","which uv && uv --version || echo NO_UV"], capture_output=True, text=True).stdout)
