L = globals().get('_L')
full = "".join(o.get("text","") for o in L.log.outputs)
import re
keys = ["cu130","optimized CUDA","pytorch version","Device:","Total VRAM","Using pytorch attention","xformers","WARNING","comfyui_version","ComfyUI version","MultiGPU"]
for line in full.splitlines():
    if any(k in line for k in keys):
        print(line)
print("URL:", L.public_url, "| status:", L.status.value[:80])
