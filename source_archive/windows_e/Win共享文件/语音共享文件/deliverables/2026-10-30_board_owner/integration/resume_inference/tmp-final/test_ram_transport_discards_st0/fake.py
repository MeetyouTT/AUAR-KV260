import sys,json
for line in sys.stdin:
 r=json.loads(line)
 print("PRIVATE",file=sys.stderr,flush=True)
 print("RESULT "+json.dumps({"ok":True,"request_id":r["request_id"],"result":{"ready":True}}),flush=True)
