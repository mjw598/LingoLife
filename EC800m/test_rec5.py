# test_rec5.py — stream_start(format, samplerate, time)，stream_read 拉数据

import audio
import utime
import uos

TMP = "/usr/test_rec.pcm"

try:
    uos.remove(TMP)
except Exception:
    pass

print("=== stream_start(format, samplerate, time) ===")
r = audio.Record(0)

# (format=0 PCM, samplerate=8000, time=0?  60? )
candidates = [
    ("(0, 8000, 0)",     (0, 8000, 0)),
    ("(0, 8000, 60)",    (0, 8000, 60)),
    ("(0, 16000, 0)",    (0, 16000, 0)),
    ("(0, 16000, 60)",   (0, 16000, 60)),
]

success = None
for label, args in candidates:
    rr = audio.Record(0)
    try:
        rc = rr.stream_start(*args)
        print("TRY", label, "->", rc)
        if rc is None or rc == 0:
            utime.sleep_ms(100)
            try: rr.stream_stop()
            except: pass
            success = (label, args)
            print("  >>> WORKS:", label)
            break
    except Exception as e:
        print("TRY", label, "err:", e)

if not success:
    print("\nNo signature worked.")
else:
    print("\n=== Stream record 5 seconds — speak loudly NOW ===")
    label, args = success
    r2 = audio.Record(0)
    try:
        rc = r2.stream_start(*args)
        print("stream_start ->", rc)
    except Exception as e:
        print("start err:", e)
        rc = -1

    if rc is None or rc == 0:
        f = open(TMP, "wb")
        total = 0
        for i in range(50):   # 5 sec, 100ms per loop
            utime.sleep_ms(100)
            try:
                # try several read forms
                data = None
                for read_args in ((4096,), (), (0, 4096), (1024,)):
                    try:
                        data = r2.stream_read(*read_args)
                        if data is not None:
                            break
                    except Exception:
                        continue
            except Exception as e:
                print("stream_read err:", e)
                break

            if data is None:
                if i < 3: print("  read returned None")
                continue
            if isinstance(data, int):
                if i < 3: print("  read returned int:", data)
                continue
            if data:
                f.write(data)
                total += len(data)
            if i % 10 == 9:
                print("  t=%.1fs total=%d bytes" % ((i + 1) / 10.0, total))
        f.close()
        try: r2.stream_stop()
        except Exception as e: print("stream_stop err:", e)
        print("Recorded raw size =", total)

        if total > 0:
            print("If 8kHz 16bit mono dur =", total/16000.0, "s")
            print("If 16kHz 16bit mono dur =", total/32000.0, "s")

            # Wrap as WAV (assume sample rate from args[1])
            SR = args[1]
            WAV = "/usr/test_rec_wrap.wav"
            try:
                f = open(TMP, "rb"); pcm = f.read(); f.close()
                def le32(v): return bytes([v & 0xff, (v>>8)&0xff, (v>>16)&0xff, (v>>24)&0xff])
                def le16(v): return bytes([v & 0xff, (v>>8)&0xff])
                ds = len(pcm); cs = 36 + ds; br = SR * 2
                hdr = (b"RIFF" + le32(cs) + b"WAVE"
                       + b"fmt " + le32(16) + le16(1) + le16(1)
                       + le32(SR) + le32(br) + le16(2) + le16(16)
                       + b"data" + le32(ds))
                f = open(WAV, "wb"); f.write(hdr); f.write(pcm); f.close()
                print("WAV", WAV, "size =", uos.stat(WAV)[6], "SR =", SR)

                from machine import Pin
                pa = Pin(Pin.GPIO33, Pin.OUT, Pin.PULL_DISABLE, 0)
                pa.write(1)
                a = audio.Audio(0); a.setVolume(11)
                a.play(2, 1, WAV)
                utime.sleep(int(ds/br) + 2)
                try: a.stop()
                except: pass
                pa.write(0)
            except Exception as e:
                print("wrap/play err:", e)

print("=== DONE ===")
