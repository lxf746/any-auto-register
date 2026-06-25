"""StreamSendMessage + LoadSession streaming test using saved tokens."""
import sys, os, json, time, cbor2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from curl_cffi import requests as cffi
from platforms.kiro.event_stream import iter_aws_event_stream
from platforms.kiro.replay import KiroSession

saved = KiroSession()
if not saved.load():
    print("No saved tokens. Run a full registration first.")
    sys.exit(1)

access_token = saved.access_token
session_token = saved.session_token
csrf_token = saved.csrf_token
user_id = saved.user_id

s = cffi.Session(impersonate="chrome124")
base = "https://app.kiro.dev/service/KiroWebPortalService/operation/"

def cbor_headers():
    h = {"Accept": "application/cbor", "Content-Type": "application/cbor",
         "smithy-protocol": "rpc-v2-cbor", "Origin": "https://app.kiro.dev",
         "Referer": "https://app.kiro.dev/", "Authorization": f"Bearer {access_token}"}
    if csrf_token:
        h["x-csrf-token"] = csrf_token
    return h

cookies = {"SessionToken": session_token, "AccessToken": access_token, "UserId": user_id, "Idp": "BuilderId"}

# Resolve space + session
if saved.space_id:
    space_id = saved.space_id
    session_id = saved.session_id or space_id
else:
    r = s.post(base + "ListSpaces", headers=cbor_headers(), cookies=cookies,
               data=cbor2.dumps({"origin": "KIRO_IDE"}), timeout=15)
    spaces = cbor2.loads(r.content).get("spaces", [])
    if not spaces:
        r = s.post(base + "CreateSpace", headers=cbor_headers(), cookies=cookies,
                   data=cbor2.dumps({"origin": "KIRO_IDE", "name": f"stream-test-{int(time.time())}"}), timeout=15)
        space_id = cbor2.loads(r.content).get("spaceId", "")
        session_id = space_id
    else:
        space_id = spaces[0]["spaceId"]
        session_id = (spaces[0].get("sessionIds") or [space_id])[0]

print(f"Space: {space_id}  Session: {session_id}")

def stream_and_dump(op, body, label, timeout=60):
    r = s.post(base + op, headers=cbor_headers(), cookies=cookies,
               data=cbor2.dumps(body), stream=True, timeout=timeout)
    chunks = []
    for chunk in r.iter_content(chunk_size=4096):
        if chunk:
            chunks.append(chunk)
    raw = b"".join(chunks)
    messages = list(iter_aws_event_stream(raw))
    print(f"\n=== {label}: {len(messages)} events ===")
    full_text = ""
    for headers, payload in messages:
        etype = headers.get(":event-type", "?")
        if etype == "initial-response":
            print(f"  initial-response: OK")
        elif etype == "event":
            ev = cbor2.loads(payload)
            ev_type = ev.get("eventType", "?")
            pw = ev.get("payload", "")
            if ev_type == "agent_message_chunk":
                chunk = json.loads(pw) if isinstance(pw, str) else pw
                text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
                full_text += text
            elif ev_type in ("tool_call", "tool_call_update", "done", "session_info_update"):
                pass
            elif ev_type == "error":
                print(f"  ERROR: {pw[:200]}")
            else:
                print(f"  {ev_type}: {str(pw)[:100]}")
        else:
            print(f"  {etype}")
    if full_text:
        print(f"\n  Assistant text ({len(full_text)} chars):")
        for line in full_text.strip().split("\n"):
            print(f"    {line}")
    return full_text

# StreamSendMessage
stream_and_dump("StreamSendMessage", {
    "spaceId": space_id, "sessionId": session_id,
    "contentBlocks": [{"text": {"text": "Write a Python hello world function, return ONLY the code, no explanation"}}],
    "csrfToken": csrf_token, "modelId": "auto",
}, "StreamSendMessage", timeout=60)

# LoadSession
stream_and_dump("LoadSession", {
    "spaceId": space_id, "sessionId": session_id, "csrfToken": csrf_token,
}, "LoadSession", timeout=30)

print("\nDone")
