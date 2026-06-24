import subprocess, os
vp = "/kaggle/working/venv/bin/python"
env = dict(os.environ); env["UV_LINK_MODE"]="copy"
# убираем sageattention v1, который заехал при тесте, и исходники
subprocess.run(["uv","pip","uninstall","--python",vp,"sageattention"],capture_output=True,text=True,env=env)
subprocess.run(["rm","-rf","/kaggle/working/_sagesrc"])
chk = subprocess.run([vp,"-c","import importlib.util as u;print('sageattention installed:', u.find_spec('sageattention') is not None)"],capture_output=True,text=True)
print(chk.stdout.strip())
print("_sagesrc exists:", os.path.exists("/kaggle/working/_sagesrc"))
