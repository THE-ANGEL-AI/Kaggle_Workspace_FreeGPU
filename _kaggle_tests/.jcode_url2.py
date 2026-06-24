import socket
L = globals().get('_L')
def port_up():
    try:
        with socket.create_connection(("127.0.0.1",8188),timeout=2): return True
    except OSError: return False
print("URL#1 было:", globals().get('_url1'))
print("URL#2 стало:", L.public_url)
print("различаются:", globals().get('_url1') != L.public_url)
print("порт up:", port_up(), "| comfy alive(None=да):", L.comfy_proc.poll())
print("status:", L.status.value[:90])
