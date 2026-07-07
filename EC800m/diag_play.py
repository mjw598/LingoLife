import audio
import utime
from machine import Pin

pa = Pin(Pin.GPIO33, Pin.OUT, Pin.PULL_DISABLE, 0)
pa.write(1)
utime.sleep(1)

aud = audio.Audio(0)
aud.setVolume(8)

print("--- file size check ---")
try:
    f = open("/usr/tts_tmp.wav", "rb")
    data = f.read()
    f.close()
    print("size:", len(data), "head:", data[:12], "tail:", data[-8:])
except Exception as e:
    print("read err:", e)
    pa.write(0)
    raise

# Truncate to first 50000 bytes (~3s audio at 16kHz/16bit) and try playing
print("--- write truncated 50000 bytes ---")
trunc = data[:44] + data[44:50000]  # keep RIFF header, take first 50000 bytes total
f = open("/usr/tts_short.wav", "wb")
f.write(trunc)
f.close()
print("trunc size:", len(trunc))

print("--- play truncated 50000 bytes ---")
rc = aud.play(2, 1, "/usr/tts_short.wav")
print("rc=", rc)
for i in range(20):
    utime.sleep(1)
    s = aud.getState()
    print(i, "state=", s)
    if i > 1 and s == 0:
        break

print("--- play full file again ---")
try:
    aud.stop()
except Exception:
    pass
utime.sleep(2)
rc = aud.play(2, 1, "/usr/tts_tmp.wav")
print("rc=", rc)
for i in range(20):
    utime.sleep(1)
    s = aud.getState()
    print(i, "state=", s)
    if i > 1 and s == 0:
        break

pa.write(0)
print("done")
