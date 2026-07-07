# test_rec2.py — 调增益、试别的录音 API、看实际能录多久

import audio
import utime
import uos

TMP = "/usr/test_rec.wav"

# ---- 1. 增益 ----
print("=== Gain probing ===")
r = audio.Record(0)
print("gain_get() =", r.gain_get())

# 2参签名 (channel, value)
for ch in (0, 1):
    for val in (5, 10, 20, 30):
        try:
            r.gain_set(ch, val)
            print("gain_set(%d, %d) OK -> get=%s" % (ch, val, r.gain_get()))
        except Exception as e:
            print("gain_set(%d, %d) err: %s" % (ch, val, e))

print("gain final =", r.gain_get())

# ---- 2. 拉满增益再录 ----
try:
    uos.remove(TMP)
except Exception:
    pass

print("\n=== Record with gain — speak loudly NOW for 6 seconds ===")
r2 = audio.Record(0)
try:
    r2.gain_set(0, 30)
    r2.gain_set(1, 30)
except Exception as e:
    print("gain set err:", e)

rc = r2.start(TMP, audio.Record.WAV)
print("start rc =", rc)

prev_size = 0
for i in range(7):
    utime.sleep(1)
    try:
        sz = uos.stat(TMP)[6]
    except Exception:
        sz = -1
    busy = r2.isBusy() if hasattr(r2, "isBusy") else "?"
    delta = sz - prev_size if sz >= 0 and prev_size >= 0 else 0
    prev_size = sz
    print("  t=%ds size=%d (+%d) busy=%s" % (i + 1, sz, delta, busy))

print("Calling stop...")
try:
    r2.stop()
except Exception as e:
    print("stop err:", e)

utime.sleep(1)
try:
    final_sz = uos.stat(TMP)[6]
    print("FINAL file size =", final_sz, "bytes")
except Exception as e:
    print("stat err:", e)

# ---- 3. 试 stream_start：看看是不是它能录更长 ----
print("\n=== stream_start probing (attrs only, no actual run) ===")
print("stream_start type:", type(r2.stream_start))

# ---- 4. 回放 ----
print("\n=== Playback (PA on) ===")
try:
    from machine import Pin
    pa = Pin(Pin.GPIO33, Pin.OUT, Pin.PULL_DISABLE, 0)
    pa.write(1)
except Exception as e:
    print("PA err:", e)
    pa = None

a = audio.Audio(0)
a.setVolume(11)   # max
print("audio volume set to 11")
rc = a.play(2, 1, TMP)
print("play rc =", rc)

# 估算时长：fileSize / (8000 * 2)
try:
    sz = uos.stat(TMP)[6]
    dur = (sz - 44) / 16000.0
    print("estimated dur =", dur, "s")
    utime.sleep(int(dur) + 2)
except Exception:
    utime.sleep(8)

try:
    a.stop()
except Exception:
    pass
if pa:
    try:
        pa.write(0)
    except Exception:
        pass

print("=== DONE ===")
