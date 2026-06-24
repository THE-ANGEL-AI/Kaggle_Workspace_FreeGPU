import subprocess, os
vp = "/kaggle/working/venv/bin/python"
# клонируем исходники SageAttention 2.x
subprocess.run(["rm","-rf","/kaggle/working/_sagesrc"])
subprocess.run(["git","clone","--depth","1","https://github.com/thu-ml/SageAttention.git","/kaggle/working/_sagesrc"],
               capture_output=True,text=True)
# версия из исходников
ver = subprocess.run(["grep","-rE","version",'/kaggle/working/_sagesrc/setup.py'],capture_output=True,text=True).stdout
print("setup.py version line:", ver.strip()[:200])
# пробуем собрать — смотрим на проверку архитектуры sm_75
env = dict(os.environ)
env["CUDA_HOME"]="/usr/local/cuda"
r = subprocess.run([vp,"setup.py","build_ext","--inplace"],
                   capture_output=True,text=True,cwd="/kaggle/working/_sagesrc",env=env)
out = (r.stdout + "\n" + r.stderr)
print("=== вывод сборки (хвост) ===")
print(out[-3500:])
print("RC:", r.returncode)
