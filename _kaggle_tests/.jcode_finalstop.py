import socket, time
L = globals().get('_L')
L._on_stop_click(None)
time.sleep(3)
def port_up():
    try:
        with socket.create_connection(("127.0.0.1",8188),timeout=2): return True
    except OSError: return False
print("после стопа: comfy rc:", L.comfy_proc.poll(), "tunnel rc:", L.tunnel_proc.poll(), "порт up:", port_up())
print("status:", L.status.value[:120])
