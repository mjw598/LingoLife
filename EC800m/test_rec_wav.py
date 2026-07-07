# test_rec_wav.py - probe audio.Record.start (2-arg signature)
#
# Error message says "function takes 3 positional arguments" — that's self + 2.
# So r.start(arg1, arg2). Try the plausible orderings.

import audio
import utime
import uos

OUT = "/usr/probe_rec.wav"

def cleanup():
    try: uos.remove(OUT)
    except: pass

def file_size(path):
    try: return uos.stat(path)[6]
    except: return -1

CANDIDATES = [
    ("A: start(path, format)",        lambda r: r.start(OUT, r.WAV),       OUT),
    ("B: start(format, path)",        lambda r: r.start(r.WAV, OUT),       OUT),
    ("C: start(format, time=5)",      lambda r: r.start(r.WAV, 5),         None),
    ("D: start(time=5, format)",      lambda r: r.start(5, r.WAV),         None),
    ("E: start(format, rate=16000)",  lambda r: r.start(r.WAV, 16000),     None),
    ("F: start(rate=16000, format)",  lambda r: r.start(16000, r.WAV),     None),
]

print("=== probe audio.Record.start (2-arg) ===")
print("WAV=%d AMRNB=%d AMRWB=%d" % (audio.Record.WAV, audio.Record.AMRNB, audio.Record.AMRWB))

winner = None
for label, fn, want_path in CANDIDATES:
    cleanup()
    r = audio.Record(0)
    try:
        rc = fn(r)
        print("TRY %s -> rc=%s" % (label, rc))
    except Exception as e:
        print("TRY %s err: %s" % (label, e))
        continue

    if rc not in (0, None):
        try: r.stop()
        except: pass
        continue

    utime.sleep(2)
    path = want_path
    if path is None:
        try:
            path = r.getFilePath()
            print("   default getFilePath ->", path)
        except Exception as e:
            print("   getFilePath err:", e)

    busy = "?"
    try: busy = r.isBusy()
    except: pass
    sz = file_size(path) if path else -1
    print("   t=2s size=%s busy=%s" % (sz, busy))

    if path and sz > 0:
        winner = (label, fn, path)
        utime.sleep(4)
        try: r.stop()
        except: pass
        break

    try: r.stop()
    except: pass

if not winner:
    print("\n=== no 2-arg signature produced data ===")
    print("Trying with samplerate set via different mechanism...")
    # Some firmwares: start(format, path) defaults to 8k, no way to get 16k.
    # Or start takes (path, time). Print getFilePath to see default behavior.
    try:
        r = audio.Record(0)
        rc = r.start(r.WAV, 5)
        print("fallback start(WAV,5) rc=", rc)
        utime.sleep(6)
        try:
            p = r.getFilePath()
            print("default path:", p, "size:", file_size(p))
        except Exception as e:
            print("path err:", e)
        try: r.stop()
        except: pass
    except Exception as e:
        print("fallback err:", e)
else:
    label, fn, path = winner
    sz = file_size(path)
    print("\n=== WINNER: %s ===" % label)
    print("file=%s size=%d bytes" % (path, sz))

    try:
        f = open(path, "rb")
        head = f.read(44)
        f.close()
        print("first 44 bytes hex:", "".join("%02x" % b for b in head))
        if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
            sr = head[24] | (head[25]<<8) | (head[26]<<16) | (head[27]<<24)
            bw = head[34] | (head[35]<<8)
            ch = head[22] | (head[23]<<8)
            print(">>> RIFF/WAVE rate=%d ch=%d bits=%d" % (sr, ch, bw))
        else:
            print(">>> no RIFF header (raw PCM?)")
    except Exception as e:
        print("read err:", e)

    try:
        from machine import Pin
        pa = Pin(Pin.GPIO33, Pin.OUT, Pin.PULL_DISABLE, 0)
        pa.write(1)
        a = audio.Audio(0); a.setVolume(11)
        rc = a.play(2, 1, path)
        print("play rc=", rc)
        utime.sleep(7)
        try: a.stop()
        except: pass
        pa.write(0)
    except Exception as e:
        print("play err:", e)

print("=== DONE ===")
