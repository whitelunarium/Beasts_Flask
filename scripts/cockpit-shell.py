"""
Open a Cockpit shell channel and run a command. Cockpit protocol:
  - WS to wss://host/cockpit/socket?... with cookie + csrf
  - Send control frames as JSON
  - Send 'open' to request a 'stream' channel running '/bin/bash'
  - Send 'done' to signal end of input
  - Receive output frames; close when channel closes
"""
import sys, json, ssl, websocket, time, base64

HOST   = "cockpit.stu.opencodingsociety.com"
COOKIE = sys.argv[1]
CSRF   = sys.argv[2]
COMMAND = sys.argv[3] if len(sys.argv) > 3 else "whoami && hostname && pwd && ls ~ | head -5"

WS_URL = f"wss://{HOST}/cockpit/socket"

# Cockpit handshake: open a 'stream' channel
INIT = {
    "command": "init",
    "version": 1,
    "host": "localhost",
}
OPEN = {
    "command": "open",
    "channel": "1",
    "payload": "stream",
    "spawn": ["/bin/bash", "-c", COMMAND],
    "host": "localhost",
    "err": "out",
}

cookie_header = f"cockpit={COOKIE}"
ws = websocket.create_connection(
    WS_URL,
    sslopt={"cert_reqs": ssl.CERT_REQUIRED},
    cookie=cookie_header,
    header=[f"X-CSRF-Token: {CSRF}", "Origin: https://" + HOST],
    timeout=30,
)

def send_control(msg):
    # Control frames are JSON prefixed with a null channel id (empty channel)
    payload = "\n" + json.dumps(msg)
    ws.send(payload)

def send_data(channel_id, data):
    payload = channel_id + "\n" + data
    ws.send(payload)

# 1. Init handshake
send_control(INIT)

# 2. Open stream channel running our command
send_control(OPEN)

# 3. Receive output until channel closes
out = []
deadline = time.time() + 60
while time.time() < deadline:
    try:
        msg = ws.recv()
    except Exception as e:
        print(f"WS recv error: {e}", file=sys.stderr)
        break
    if not msg:
        continue
    # First byte segment is the channel id (or empty for control)
    nl = msg.find("\n")
    if nl == -1:
        continue
    channel = msg[:nl]
    body = msg[nl+1:]
    if channel == "":
        # Control frame
        try:
            ctrl = json.loads(body)
        except Exception:
            continue
        if ctrl.get("command") == "close" and ctrl.get("channel") == "1":
            print(f"--- channel closed (problem={ctrl.get('problem')}) ---", file=sys.stderr)
            break
        if ctrl.get("command") == "ready":
            pass
    else:
        out.append(body)

ws.close()
sys.stdout.write("".join(out))
