L = globals().get('_L')
print("starting:", L._starting, "| restart_disabled:", L.restart_btn.disabled)
print("URL#1:", L.public_url, "| status:", L.status.value[:90])
globals()['_url1'] = L.public_url
