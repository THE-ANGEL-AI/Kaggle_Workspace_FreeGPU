import subprocess, sys
print("PY:", sys.version)
print(subprocess.run(["nvidia-smi","--query-gpu=index,name,memory.total,driver_version","--format=csv"],capture_output=True,text=True).stdout)
import os
print("cwd:", os.getcwd())
print("working contents:", os.listdir("/kaggle/working"))
