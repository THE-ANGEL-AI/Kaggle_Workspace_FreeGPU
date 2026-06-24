L = globals().get('_L')
print("жму Перезапустить...")
L._on_restart_click(None)
print("после клика: starting:", L._starting, "restart_disabled:", L.restart_btn.disabled, "stopped:", L.stopped, "url(сброшен):", L.public_url)
