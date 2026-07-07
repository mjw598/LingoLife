# test_rec_wav16k.py - try slot_mapping + likely remaining kwargs in one shot

import audio
import utime
import uos

OUT = "/usr/probe16k.wav"

def cleanup():
    try: uos.remove(OUT)
    except: pass

def parse_wav(path):
    try:
        f = open(path, "rb"); head = f.read(44); f.close()
    except Exception as e:
        return "open err: %s" % e
    if head[:4] != b"RIFF" or head[8:12] != b"WAVE":
        return "not WAV"
    sr = head[24] | (head[25]<<8) | (head[26]<<16) | (head[27]<<24)
    bw = head[34] | (head[35]<<8)
    ch = head[22] | (head[23]<<8)
    sz = -1
    try: sz = uos.stat(path)[6]
    except: pass
    return "rate=%d ch=%d bits=%d size=%d" % (sr, ch, bw, sz)

def record_short(label):
    cleanup()
    r = audio.Record(0)
    try:
        rc = r.start(OUT, r.WAV)
    except Exception as e:
        print("[%s] start err: %s" % (label, e))
        return
    if rc not in (0, None):
        print("[%s] start rc=%s" % (label, rc))
        try: r.stop()
        except: pass
        return
    utime.sleep(2)
    try: r.stop()
    except: pass
    utime.sleep(1)
    print("[%s]" % label, parse_wav(OUT))

# Path so far: format -> sample -> num_slots -> slot_mapping -> ?
# Add slot_mapping with several common values, plus potential follow-ups.

base = {"format":0, "sample":16000, "num_slots":2}

TRIES = [
    ("sm=0",         dict(base, slot_mapping=0)),
    ("sm=1",         dict(base, slot_mapping=1)),
    ("sm=3",         dict(base, slot_mapping=3)),  # both slots bitmap
    ("sm=[0]",       dict(base, slot_mapping=[0])),
    ("sm=[0,1]",     dict(base, slot_mapping=[0,1])),
    # Plus likely-still-missing kwargs all in one go
    ("sm=0+bw+ch",   dict(base, slot_mapping=0, bitwidth=16, channel=1)),
    ("sm=0+bw+nch",  dict(base, slot_mapping=0, bitwidth=16, num_channels=1)),
    ("sm=0+sw+ch",   dict(base, slot_mapping=0, slot_width=16, channel=1)),
    ("sm=3+sw+ch",   dict(base, slot_mapping=3, slot_width=16, channel=2)),
]

for label, kw in TRIES:
    print("\n--- %s ---" % label)
    print("  kw=", kw)
    try:
        rv = audio.set_qdai_cfg(0, 0, 0, 0, **kw)
        print("  set_qdai_cfg ->", rv)
    except Exception as e:
        print("  err:", e)
        continue
    record_short(label)

print("\n=== DONE ===")
