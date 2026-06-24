import sys
print("kernel python:", sys.version.split()[0])
try:
    import ipywidgets; print("ipywidgets:", ipywidgets.__version__)
except Exception as e:
    print("ipywidgets MISSING:", e)
import importlib, start
importlib.reload(start)
print("start.py imported OK; class:", start.ComfyLauncher.__name__)
