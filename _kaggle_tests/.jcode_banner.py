L = globals().get('_L')
outs = L.log.outputs
full = "".join(o.get("text","") for o in outs)
import re
for line in full.splitlines():
    if any(k in line for k in ["Device:","VRAM","cross attention","CUDA","Total VRAM","pytorch","Using ","ComfyUI version","Set vram","xformers"]):
        print(line)
print("=== локальная проверка API ===")
import urllib.request, json
try:
    d = json.load(urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=10))
    print("devices:", [ (x.get('name'), x.get('type')) for x in d.get('devices',[]) ])
    print("comfyui_version:", d.get('system',{}).get('comfyui_version'))
except Exception as e:
    print("api err:", e)
