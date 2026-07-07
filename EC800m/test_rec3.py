# test_rec3.py — stream 模式录音（手动写文件，长度可控）

import audio
import utime
import uos

TMP = "/usr/test_rec.pcm"   # 这次先录裸 PCM，自己拼 WAV 头

try:
    uos.remove(TMP)
except Exception:
    pass

print("=== stream_start probing ===")
r = audio.Record(0)

# 试几种参数组合
candidates = [
    ("()",            ()),
    ("(0,)",          (0,)),
    ("(8000,)",       (8000,)),
    ("(8000, 16, 1)", (8000, 16, 1)),
    ("(0, 0)",        (0, 0)),
    ("(8000, 1)",     (8000, 1)),
]

for label, args in candidates:
    rr = audio.Record(0)
    try:
        rc = rr.stream_start(*args)
        print("stream_start", label, "->", rc)
        # 立即停止再尝试下一个
        try:
            rr.stream_stop()
        except Exception:
            pass
    except Exception as e:
        print("stream_start", label, "err:", e)

print("\n=== Stream record 5 seconds — speak NOW ===")
r2 = audio.Record(0)

# 找到能调通的形参后直接用；先用最常见的 () 试
ok = False
for args in [(), (0,), (8000, 16, 1), (8000, 1)]:
    try:
        rc = r2.stream_start(*args)
        if rc is None or rc == 0:
            print("Using stream_start", args)
            ok = True
            break
        else:
            try: r2.stream_stop()
            except: pass
    except Exception as e:
        pass

if not ok:
    print("stream_start failed, fallback test aborted")
else:
    try:
        f = open(TMP, "wb")
    except Exception as e:
        print("open file err:", e)
        f = None

    if f:
        total = 0
        for i in range(50):   # 5秒 * 10次
            utime.sleep_ms(100)
            try:
                # stream_read 通常返回 bytes
                data = r2.stream_read(4096)
            except Exception as e:
                print("stream_read err:", e)
                break
            if data:
                if isinstance(data, int):
                    print("stream_read returned int:", data)
                    break
                f.write(data)
                total += len(data)
            if i % 10 == 9:
                print("  t=%.1fs total=%d bytes" % ((i + 1) / 10.0, total))
        f.close()
        try:
            r2.stream_stop()
        except Exception as e:
            print("stream_stop err:", e)
        print("Recorded raw PCM size =", total, "bytes")

        # 估算实际采样率
        # 5秒应该 5*8000*2 = 80000 (8k mono 16bit) 或 5*16000*2 = 160000 (16k)
        if total > 0:
            est_8k_dur = total / 16000.0
            est_16k_dur = total / 32000.0
            print("If 8kHz 16bit mono: dur =", est_8k_dur, "s")
            print("If 16kHz 16bit mono: dur =", est_16k_dur, "s")

# ---- 把 PCM 拼成 WAV 回放 ----
print("\n=== Wrap PCM as WAV and play ===")
try:
    pcm_size = uos.stat(TMP)[6]
except Exception as e:
    print("stat err:", e)
    pcm_size = 0

if pcm_size > 0:
    SR = 8000   # 假设 8kHz；如果回放速度不对就改 16000
    WAV = "/usr/test_rec_wrap.wav"
    try:
        f = open(TMP, "rb")
        pcm = f.read()
        f.close()

        def le32(v): return bytes([v & 0xff, (v>>8)&0xff, (v>>16)&0xff, (v>>24)&0xff])
        def le16(v): return bytes([v & 0xff, (v>>8)&0xff])

        data_size = len(pcm)
        chunk_size = 36 + data_size
        byte_rate = SR * 1 * 2
        header = (b"RIFF" + le32(chunk_size) + b"WAVE"
                  + b"fmt " + le32(16) + le16(1) + le16(1)
                  + le32(SR) + le32(byte_rate) + le16(2) + le16(16)
                  + b"data" + le32(data_size))
        f = open(WAV, "wb")
        f.write(header)
        f.write(pcm)
        f.close()
        print("Wrote WAV", WAV, "header SR=", SR)

        # 播放
        try:
            from machine import Pin
            pa = Pin(Pin.GPIO33, Pin.OUT, Pin.PULL_DISABLE, 0)
            pa.write(1)
        except Exception:
            pa = None
        a = audio.Audio(0)
        a.setVolume(11)
        a.play(2, 1, WAV)
        utime.sleep(int(data_size / byte_rate) + 2)
        try: a.stop()
        except: pass
        if pa:
            try: pa.write(0)
            except: pass
    except Exception as e:
        print("wrap/play err:", e)

print("=== DONE ===")
