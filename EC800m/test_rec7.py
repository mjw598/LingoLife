# test_rec7.py — fmt=4(AMR-NB), sr=8000, time=0 持续录音

import audio
import utime
import uos

TMP = "/usr/test_rec.amr"

try:
    uos.remove(TMP)
except Exception:
    pass

print("=== stream_start AMR-NB 5 seconds — speak NOW ===")
r = audio.Record(0)
rc = r.stream_start(4, 8000, 0)
print("stream_start ->", rc)

# 探测 stream_read 形参
print("\nProbe stream_read signature:")
for args in ((), (4096,), (1024,), (0,), (1,)):
    try:
        d = r.stream_read(*args)
        print("  read", args, "->", type(d).__name__, len(d) if hasattr(d, "__len__") else d)
    except Exception as e:
        print("  read", args, "err:", e)

# 录5秒
print("\n=== Recording 5 seconds — speak NOW ===")
f = open(TMP, "wb")
total = 0
read_args = (4096,)   # 默认先用这个
for i in range(50):
    utime.sleep_ms(100)
    try:
        d = r.stream_read(*read_args)
    except Exception as e:
        if i == 0:
            # 试空参
            try:
                d = r.stream_read()
                read_args = ()
                print("switching to no-arg read")
            except Exception as e2:
                print("read err:", e2)
                d = None
        else:
            d = None
    if d and not isinstance(d, int):
        f.write(d)
        total += len(d)
    if i % 10 == 9:
        print("  t=%.1fs total=%d" % ((i+1)/10.0, total))

f.close()
try: r.stream_stop()
except Exception as e: print("stream_stop err:", e)

print("Total AMR bytes =", total)

try:
    sz = uos.stat(TMP)[6]
    print("File size =", sz)
    f = open(TMP, "rb")
    head = f.read(16)
    f.close()
    print("First 16 hex:", "".join("%02x" % b for b in head))
    # AMR-NB magic: "#!AMR\n" = 23 21 41 4d 52 0a
    if head[:6] == b"#!AMR\n":
        print(">>> Valid AMR-NB header")
    else:
        print(">>> No AMR header — raw frames? (we'll need to prepend it)")
except Exception as e:
    print("stat err:", e)

print("=== DONE ===")
