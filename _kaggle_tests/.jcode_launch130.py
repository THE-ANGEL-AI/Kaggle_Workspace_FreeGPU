import importlib, start
importlib.reload(start)
_L = start.ComfyLauncher()
globals()['_L'] = _L
_L.launch()
print("launch ок")
