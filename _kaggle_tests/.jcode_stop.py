import socket, time
L = globals().get('_L')
print("ДО: comfy alive(None=да):", L.comfy_proc.poll(), "tunnel:", L.tunnel_proc.poll())
L._on_stop_click(None)      # имитируем нажатие кнопки «Остановить»
time.sleep(3)
def port_up():
    try:
        with socket.create_connection(("127.0.0.1",8188),timeout=2): return True
    except OSError: return False
print("ПОСЛЕ: comfy rc:", L.comfy_proc.poll(), "tunnel rc:", L.tunnel_proc.poll())
print("порт 8188 up:", port_up())
print("stopped flag:", L.stopped, "| stop_btn.disabled:", L.stop_btn.disabled)
print("status:", L.status.value[:140])
