# test_rec.py — 已知 start(path, WAV) 可用，验证实际录音 + 回放

import audio
import utime
import uos

TMP = "/usr/test_rec.wav"

# 删掉旧文件
try:
    uos.remove(TMP)
except Exception:
    pass

print("=== Record 5 seconds — speak NOW! ===")
r = audio.Record(0)

# 增益拉满（试试看，参数可能是 0-10 或 0-100）
try:
    print("gain before =", r.gain_get())
except Exception as e:
    print("gain_get err:", e)
try:
    r.gain_set(10)
    print("gain set to 10")
except Exception as e:
    print("gain_set 10 err:", e)
    try:
        r.gain_set(100)
        print("gain set to 100")
    except Exception as e2:
        print("gain_set 100 err:", e2)

rc = r.start(TMP, audio.Record.WAV)
print("start rc =", rc)

for i in range(5):
    utime.sleep(1)
    busy = r.isBusy() if hasattr(r, "isBusy") else "?"
    try:
        used = r.ring_buf_used()
    except Exception:
        used = "?"
    print("  t=%ds busy=%s used=%s" % (i + 1, busy, used))

print("Calling stop...")
try:
    r.stop()
except Exception as e:
    print("stop err:", e)

# 等一下让文件落盘
utime.sleep(1)

# 查文件大小
try:
    st = uos.stat(TMP)
    print("file size =", st[6], "bytes")
except Exception as e:
    print("stat err:", e)

# getSize / getFilePath
try:
    print("getSize() =", r.getSize())
except Exception as e:
    print("getSize err:", e)
try:
    print("getFilePath() =", r.getFilePath())
except Exception as e:
    print("getFilePath err:", e)

# 直接 dump 头部字节验证 WAV header
try:
    f = open(TMP, "rb")
    head = f.read(64)
    f.close()
    print("first 64 bytes hex =", "".join("%02x" % b for b in head))
    print("first 4 ascii    =", head[:4])
    print("bytes 8-12 ascii =", head[8:12])
except Exception as e:
    print("read head err:", e)

# 回放
print("\n=== Playback ===")
try:
    from machine import Pin
    pa = Pin(Pin.GPIO33, Pin.OUT, Pin.PULL_DISABLE, 0)
    pa.write(1)
except Exception as e:
    print("PA err:", e)
    pa = None

a = audio.Audio(0)
a.setVolume(10)
rc = a.play(2, 1, TMP)
print("play rc =", rc)
utime.sleep(6)
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
