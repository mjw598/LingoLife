# test_rec4.py — stream_start 用 callback 模式

import audio
import utime
import uos

TMP = "/usr/test_rec.pcm"

try:
    uos.remove(TMP)
except Exception:
    pass

# 全局状态
_buf = bytearray()
_chunks = 0

def on_audio(args):
    """callback 收到音频块"""
    global _buf, _chunks
    _chunks += 1
    # args 可能是 (data,) 或 data 直接 bytes
    if isinstance(args, (bytes, bytearray)):
        _buf += args
    elif isinstance(args, tuple):
        for a in args:
            if isinstance(a, (bytes, bytearray)):
                _buf += a
                break
    if _chunks <= 3 or _chunks % 20 == 0:
        print("  cb #%d type=%s len=%s total=%d" %
              (_chunks, type(args).__name__,
               len(args) if hasattr(args, "__len__") else "?",
               len(_buf)))

print("=== stream_start with callback ===")
r = audio.Record(0)

# 探测形参组合
candidates = [
    ("(format, samplerate, channel, time, cb)", (0, 8000, 1, 0, on_audio)),
    ("(format, samplerate, channel, cb, time)", (0, 8000, 1, on_audio, 0)),
    ("(format, samplerate, time, cb)",          (0, 8000, 0, on_audio)),
    ("(format, samplerate, cb, time)",          (0, 8000, on_audio, 0)),
    ("(format, samplerate, channel, cb)",       (0, 8000, 1, on_audio)),
    ("(format, samplerate, cb)",                (0, 8000, on_audio)),
]

success = None
for label, args in candidates:
    try:
        rc = r.stream_start(*args)
        print("TRY", label, "->", rc)
        if rc is None or rc == 0:
            # 立刻停掉
            utime.sleep_ms(200)
            try: r.stream_stop()
            except: pass
            success = (label, args)
            print("  >>> WORKS:", label)
            break
    except Exception as e:
        print("TRY", label, "err:", e)

if not success:
    print("\nNo signature worked. Stop here.")
else:
    print("\n=== Stream record 5 seconds — speak loudly NOW ===")
    _buf = bytearray()
    _chunks = 0
    label, args = success
    r2 = audio.Record(0)
    try:
        rc = r2.stream_start(*args)
        print("stream_start ->", rc)
        for i in range(5):
            utime.sleep(1)
            print("  t=%ds chunks=%d total=%d" % (i + 1, _chunks, len(_buf)))
        try:
            r2.stream_stop()
        except Exception as e:
            print("stream_stop err:", e)
    except Exception as e:
        print("record err:", e)

    print("Total chunks =", _chunks, "bytes =", len(_buf))

    # 估算采样率
    if len(_buf) > 0:
        print("If 8kHz 16bit mono dur =", len(_buf)/16000.0, "s")
        print("If 16kHz 16bit mono dur =", len(_buf)/32000.0, "s")

        # 写文件
        try:
            f = open(TMP, "wb")
            f.write(_buf)
            f.close()
            print("Wrote PCM size =", uos.stat(TMP)[6])
        except Exception as e:
            print("write err:", e)

        # 拼 WAV 头并播放
        SR = 8000
        WAV = "/usr/test_rec_wrap.wav"
        try:
            def le32(v): return bytes([v & 0xff, (v>>8)&0xff, (v>>16)&0xff, (v>>24)&0xff])
            def le16(v): return bytes([v & 0xff, (v>>8)&0xff])
            pcm = bytes(_buf)
            ds = len(pcm)
            cs = 36 + ds
            br = SR * 2
            hdr = (b"RIFF" + le32(cs) + b"WAVE"
                   + b"fmt " + le32(16) + le16(1) + le16(1)
                   + le32(SR) + le32(br) + le16(2) + le16(16)
                   + b"data" + le32(ds))
            f = open(WAV, "wb"); f.write(hdr); f.write(pcm); f.close()
            print("WAV header SR =", SR, "size =", uos.stat(WAV)[6])

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
