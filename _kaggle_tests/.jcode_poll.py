import socket, time
L = globals().get('_L')
if L is None:
    print("нет _L"); raise SystemExit
def port_up():
    try:
        with socket.create_connection(("127.0.0.1",8188),timeout=2): return True
    except OSError: return False
print("status html:", L.status.value[:120])
print("comfy_proc alive:", L.comfy_proc.poll() if L.comfy_proc else "none")
print("tunnel_proc alive:", L.tunnel_proc.poll() if L.tunnel_proc else "none")
print("port 8188 up:", port_up())
print("public_url:", L.public_url)
# последние строки лога из виджета
outs = L.log.outputs
tail = "".join(o.get("text","") for o in outs)[-1500:]
print("---LOG TAIL---")
print(tail)
