import subprocess, os
vp = "/kaggle/working/venv/bin/python"
env=dict(os.environ); env["UV_LINK_MODE"]="copy"
subprocess.run(["uv","pip","uninstall","--python",vp,"sageattention"],capture_output=True,text=True,env=env)
chk=subprocess.run([vp,"-c","import importlib.util as u;print('sageattention removed:', u.find_spec('sageattention') is None)"],capture_output=True,text=True)
print(chk.stdout.strip())
