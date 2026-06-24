#!/usr/bin/env python3
"""Remote Kaggle Jupyter-proxy driver.

Usage:
  python _kaggle_driver.py exec  "<python code>"        # run code in (cached) kernel
  python _kaggle_driver.py exec  - < file.py            # run code from stdin
  python _kaggle_driver.py newk                         # force a new kernel
  python _kaggle_driver.py put   <remote_path> < file   # upload text file
  python _kaggle_driver.py get   <remote_path>          # download text file

Base URL read from .jbase, kernel id cached in .jkid.
"""
import sys, os, json, time, uuid, datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import requests
import websocket  # websocket-client

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = open(os.path.join(HERE, ".jbase")).read().strip()
KIDF = os.path.join(HERE, ".jkid")
WSBASE = "wss://" + BASE.split("://", 1)[1]


def _xsrf(sess):
    r = sess.get(BASE + "/api/contents", timeout=30)
    return sess.cookies.get("_xsrf", "")


def new_kernel(sess):
    tok = _xsrf(sess)
    r = sess.post(BASE + "/api/kernels",
                  headers={"X-XSRFToken": tok},
                  data=json.dumps({"name": "python3"}), timeout=60)
    r.raise_for_status()
    kid = r.json()["id"]
    open(KIDF, "w").write(kid)
    return kid


def get_kernel(sess, force=False):
    if not force and os.path.exists(KIDF):
        kid = open(KIDF).read().strip()
        # validate
        r = sess.get(BASE + "/api/kernels/" + kid, timeout=30)
        if r.status_code == 200:
            return kid
    return new_kernel(sess)


def _msg(code):
    mid = uuid.uuid4().hex
    return mid, json.dumps({
        "header": {"msg_id": mid, "username": "u", "session": uuid.uuid4().hex,
                   "msg_type": "execute_request", "version": "5.3",
                   "date": datetime.datetime.utcnow().isoformat() + "Z"},
        "parent_header": {}, "metadata": {},
        "content": {"code": code, "silent": False, "store_history": True,
                    "user_expressions": {}, "allow_stdin": False,
                    "stop_on_error": True},
        "channel": "shell",
    })


def execute(sess, kid, code, idle_timeout=600):
    ws_url = WSBASE + "/api/kernels/" + kid + "/channels"
    cookie = "; ".join(f"{c.name}={c.value}" for c in sess.cookies)
    ws = websocket.create_connection(
        ws_url, header=[f"Cookie: {cookie}"], timeout=idle_timeout,
        max_size=None)
    mid, frame = _msg(code)
    ws.send(frame)
    got_idle = False
    got_reply = False
    last = time.time()
    try:
        while True:
            try:
                raw = ws.recv()
            except websocket.WebSocketTimeoutException:
                print(f"\n[driver] recv timeout after {idle_timeout}s", flush=True)
                break
            if not raw:
                continue
            m = json.loads(raw)
            parent = m.get("parent_header", {}).get("msg_id")
            if parent != mid:
                continue
            mt = m.get("msg_type")
            c = m.get("content", {})
            if mt == "stream":
                sys.stdout.write(c.get("text", ""))
                sys.stdout.flush()
            elif mt in ("execute_result", "display_data"):
                data = c.get("data", {}).get("text/plain", "")
                if data:
                    print(data, flush=True)
            elif mt == "error":
                print("\n".join(c.get("traceback", [])), flush=True)
            elif mt == "execute_reply":
                got_reply = True
            elif mt == "status":
                if c.get("execution_state") == "idle":
                    got_idle = True
            if got_idle and got_reply:
                break
    finally:
        ws.close()


def put_file(sess, path, content):
    tok = _xsrf(sess)
    r = sess.put(BASE + "/api/contents/" + path,
                 headers={"X-XSRFToken": tok},
                 data=json.dumps({"type": "file", "format": "text",
                                  "content": content}), timeout=120)
    r.raise_for_status()
    print("put ok:", path)


def get_file(sess, path):
    r = sess.get(BASE + "/api/contents/" + path + "?content=1", timeout=120)
    r.raise_for_status()
    print(r.json().get("content", ""))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "exec"
    sess = requests.Session()
    if cmd == "newk":
        print(new_kernel(sess)); return
    if cmd == "put":
        path = sys.argv[2]
        content = sys.stdin.read()
        put_file(sess, path, content); return
    if cmd == "get":
        get_file(sess, sys.argv[2]); return
    if cmd == "exec":
        arg = sys.argv[2] if len(sys.argv) > 2 else "-"
        code = sys.stdin.read() if arg == "-" else arg
        to = int(sys.argv[3]) if len(sys.argv) > 3 else 600
        kid = get_kernel(sess)
        execute(sess, kid, code, idle_timeout=to)
        return
    print("unknown cmd:", cmd)


if __name__ == "__main__":
    main()
