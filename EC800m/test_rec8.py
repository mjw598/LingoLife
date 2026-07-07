# test_rec8.py — stream_read(2 args) probe

import audio
import utime
import uos

TMP = "/usr/test_rec.amr"

try:
    uos.remove(TMP)
except Exception:
    pass

r = audio.Record(0)
rc = r.stream_start(4, 8000, 0)
print("stream_start ->", rc)

print("\n=== stream_read 2-arg probe ===")
buf = bytearray(4096)

# 候选 2 参组合
candidates = [
    ("(buf, 4096)",     (buf, 4096)),
    ("(buf, len(buf))", (buf, len(buf))),
    ("(0, 4096)",       (0, 4096)),       # offset, size
    ("(4096, 0)",       (4096, 0)),
    ("(4096, 100)",     (4096, 100)),     # size, timeout?
]

success = None
utime.sleep(1)   # let buffer fill

for label, args in candidates:
    try:
        result = r.stream_read(*args)
        print("TRY", label, "-> type=", type(result).__name__,
              "val=", result if isinstance(result, int) else "len=" + str(len(result) if hasattr(result, "__len__") else "?"))
        if isinstance(result, int) and result > 0:
            print("  >>> got", result, "bytes — first 16 hex:",
                  "".join("%02x" % b for b in buf[:min(16, result)]))
            success = (label, args, "into-buf", result)
            break
        elif isinstance(result, (bytes, bytearray)) and len(result) > 0:
            print("  >>> got", len(result), "bytes returned — first 16 hex:",
                  "".join("%02x" % b for b in result[:16]))
            success = (label, args, "return-bytes", len(result))
            break
    except Exception as e:
        print("TRY", label, "err:", e)

if not success:
    print("\nNo signature gave data.")
else:
    print("\n=== Recording 5 seconds — speak NOW ===")
    label, args, mode, _ = success
    f = open(TMP, "wb")
    total = 0
    for i in range(50):
        utime.sleep_ms(100)
        try:
            res = r.stream_read(*args)
        except Exception:
            res = None
        if res is None:
            continue
        if mode == "into-buf" and isinstance(res, int) and res > 0:
            f.write(bytes(buf[:res]))
            total += res
        elif mode == "return-bytes" and isinstance(res, (bytes, bytearray)) and len(res):
            f.write(res)
            total += len(res)
        if i % 10 == 9:
            print("  t=%.1fs total=%d" % ((i+1)/10.0, total))
    f.close()

try: r.stream_stop()
except Exception as e: print("stream_stop err:", e)

try:
    sz = uos.stat(TMP)[6]
    print("\nFinal AMR file =", sz, "bytes")
    f = open(TMP, "rb"); head = f.read(16); f.close()
    print("First 16 hex:", "".join("%02x" % b for b in head))
    if head[:6] == b"#!AMR\n":
        print(">>> Has AMR header")
    else:
        print(">>> No AMR header (raw frames)")
except Exception as e:
    print("stat err:", e)

print("=== DONE ===")
