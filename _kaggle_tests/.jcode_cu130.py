import subprocess, os
env = dict(os.environ); env["UV_LINK_MODE"]="copy"
vp = "/kaggle/working/venv/bin/python"
r = subprocess.run(
    ["uv","pip","install","--python",vp,"--reinstall",
     "torch","torchvision","torchaudio",
     "--index-url","https://download.pytorch.org/whl/cu130"],
    capture_output=True, text=True, env=env, cwd="/kaggle/working")
print(r.stdout[-3000:])
print("ERR:", r.stderr[-3000:])
print("RC:", r.returncode)
rr = subprocess.run([vp,"-c","import torch;print('torch',torch.__version__,'cuda',torch.version.cuda,'avail',torch.cuda.is_available(),'gpus',torch.cuda.device_count())"],capture_output=True,text=True)
print("VERIFY:", rr.stdout.strip(), "|", rr.stderr.strip()[-300:])
