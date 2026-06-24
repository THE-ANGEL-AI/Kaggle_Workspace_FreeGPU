import importlib, start
importlib.reload(start)
_L = start.ComfyLauncher()
globals()['_L'] = _L
_L.launch()
print("launch() вернулся. buttons:", [b.description for b in _L.panel.children[1].children if hasattr(b,'description')])
