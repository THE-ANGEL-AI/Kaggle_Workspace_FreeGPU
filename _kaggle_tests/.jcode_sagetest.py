import subprocess, os
vp = "/kaggle/working/venv/bin/python"
# 1) что говорит torch про вычислительные возможности карт
r = subprocess.run([vp,"-c",
  "import torch;"
  "print('torch',torch.__version__);"
  "print('caps',[torch.cuda.get_device_capability(i) for i in range(torch.cuda.device_count())])"],
  capture_output=True,text=True)
print("=== GPU caps ===")
print(r.stdout, r.stderr[-300:])

# 2) пробуем поставить SageAttention (свежий) в venv — смотрим, компилируется ли на sm_75
print("=== попытка установки SageAttention ===")
env = dict(os.environ); env["UV_LINK_MODE"]="copy"
r2 = subprocess.run(
  ["uv","pip","install","--python",vp,"--no-build-isolation","sageattention"],
  capture_output=True,text=True,env=env,cwd="/kaggle/working")
out = (r2.stdout + "\n" + r2.stderr)
print(out[-4000:])
print("RC:", r2.returncode)
