# test_rec6.py — 用 QuecPython 文档里的 format 值

import audio
import utime
import uos

# QuecPython 音频格式常量（部分固件）
# 0/1 在 stream_start 报 Parameter error，试这些已知值
TRY_FORMATS = [
    ("PCM 8K 16bit", 6),
    ("PCM 16K 16bit", 7),
    ("AMR-NB", 4),
    ("AMR-WB", 5),
    ("PCM raw", 8),
    ("PCM raw alt", 3),
    ("Type 2 (WAV)", 2),
]

print("=== stream_start (format, samplerate, time) value probe ===")

for name, fmt in TRY_FORMATS:
    for sr in (8000, 16000):
        for t in (0, 30, 60):
            rr = audio.Record(0)
            try:
                rc = rr.stream_start(fmt, sr, t)
                print("OK fmt=%d sr=%d t=%d -> rc=%s  [%s]" % (fmt, sr, t, rc, name))
                utime.sleep_ms(100)
                try: rr.stream_stop()
                except: pass
                # 第一个成功就停
                raise SystemExit
            except SystemExit:
                raise
            except Exception as e:
                msg = str(e)
                # 只打不一样的错误，避免刷屏
                if "Parameter error" not in msg:
                    print("fmt=%d sr=%d t=%d err: %s" % (fmt, sr, t, msg))

print("\nAll Parameter error.")
