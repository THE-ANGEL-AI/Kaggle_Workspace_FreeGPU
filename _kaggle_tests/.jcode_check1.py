import os, subprocess
vp = "/kaggle/working/venv/bin/python"
print("venv python exists:", os.path.exists(vp))
print("ComfyUI exists:", os.path.exists("/kaggle/working/ComfyUI/main.py"))
print("Manager exists:", os.path.exists("/kaggle/working/ComfyUI/custom_nodes/ComfyUI-Manager"))
if os.path.exists(vp):
    r = subprocess.run([vp,"-c","import torch;print('torch',torch.__version__,'cuda',torch.version.cuda,'avail',torch.cuda.is_available(),'gpus',torch.cuda.device_count())"],capture_output=True,text=True)
    print("TORCH:", r.stdout.strip(), r.stderr.strip()[-500:])
print("working:", sorted(os.listdir("/kaggle/working")))
