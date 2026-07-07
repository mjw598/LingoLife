# test_rec_long.py - watch file size grow during a long WAV recording
#
# Goal: see whether r.start(path, WAV) actually keeps writing past 1.66s
# or whether the firmware caps it. We sample size every 500ms for 10s.

import audio
import utime
import uos

OUT = "/usr/probe_long.wav"

try: uos.remove(OUT)
except: pass

r = audio.Record(0)

print("=== long-record test ===")
print("calling r.start(%r, WAV) ..." % OUT)
rc = r.start(OUT, r.WAV)
print("start ->", rc)
if rc not in (0, None):
    print("start failed; abort")
else:
    t0 = utime.ticks_ms()
    last_sz = -1
    same_count = 0
    for i in range(20):
        utime.sleep_ms(500)
        try:
            sz = uos.stat(OUT)[6]
        except:
            sz = -1
        try:
            busy = r.isBusy()
        except:
            busy = "?"
        elapsed = utime.ticks_diff(utime.ticks_ms(), t0)
        delta = sz - last_sz if last_sz >= 0 else sz
        print("t=%5d ms  size=%-7d  delta=%-6d  busy=%s" % (elapsed, sz, delta, busy))
        if sz == last_sz:
            same_count += 1
        else:
            same_count = 0
        last_sz = sz
        if same_count >= 4:
            print("size stuck for 2s; firmware stopped writing")
            break
    print("calling r.stop() ...")
    try:
        rv = r.stop()
        print("stop ->", rv)
    except Exception as e:
        print("stop err:", e)
    utime.sleep_ms(500)
    try:
        final_sz = uos.stat(OUT)[6]
        print("final file size:", final_sz)
    except Exception as e:
        print("stat err:", e)
print("=== DONE ===")
