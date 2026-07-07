import audio
import utime
import ujson
import request
import usocket
import ussl
import uos
import ubinascii
import _thread
import gc

TMP_MP3 = "/usr/tts_tmp.mp3"
TMP_REC = "/usr/rec_tmp.pcm"
ASR_URL_HOST = "vop.baidu.com"
ASR_URL_PATH = "/server_api"
ASR_DEV_PID = 1737
ASR_RATE = 16000
PCM_DEVICE = 1
_asr_addr = None   # cached getaddrinfo result for ASR_URL_HOST (DNS per-turn is slow on cellular)

SERVER_TTS_HOST = "139.196.33.144"
SERVER_TTS_PORT = 8003
SERVER_TTS_USE_TLS = False
SERVER_TTS_PATH = "/api/ec800m/tts"
SERVER_TTS_API_KEY = ""
SERVER_TTS_VOICE_EN = "en-US-AvaMultilingualNeural"
SERVER_TTS_VOICE_ZH = "zh-CN-XiaoxiaoNeural"
SERVER_TTS_FORMAT = "mp3"
SERVER_TTS_SAMPLE_RATE = 16000
SERVER_ASR_HOST = ""   # empty -> skip server ASR, go straight to Baidu (faster, matches English project)
SERVER_ASR_PORT = 8003
SERVER_ASR_USE_TLS = False
SERVER_ASR_PATH = "/api/ec800m/asr"
SERVER_ASR_API_KEY = ""

BAIDU_API_KEY = "ccFGe5LvukV9tmSNfLqvZMD4"
BAIDU_SECRET_KEY = "5q2zGackMBQ8uQnjoFcv7mJ8wlqRRXaS"
TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
BAIDU_PER = 0
BAIDU_SPD = 4

_tts = audio.TTS(0)
_tts.setVolume(8)
_tts.setSpeed(5)
_aud = audio.Audio(0)
_aud.setVolume(8)

try:
    _PCM_CLS = audio.Audio.PCM
    _PCM_MONO = audio.Audio.PCM.MONO
    _PCM_RO = audio.Audio.PCM.READONLY
    _PCM_BLOCK = audio.Audio.PCM.BLOCK
except Exception:
    _PCM_CLS = None
    _PCM_MONO = None
    _PCM_RO = None
    _PCM_BLOCK = None

_pa = None
_uart = None
_recording = False
_worker_alive = False
_vad_pending = False
_vad_enabled = True
_last_word_en = ""
_last_word_cn = ""
# Audio is captured as a LIST of small PCM chunks in RAM (_rec_chunks). Every
# other approach failed on this module:
#   * bytearray += chunk  -> heap fragmentation, MemoryError at ~3 s (one big
#     contiguous block can't be reallocated).
#   * bytearray[a:b]=chunk -> this MicroPython build has no slice assignment.
#   * streaming to a flash file -> ENOSPC (err 28), the partition is tiny.
# A list of ~640-byte chunks needs no large contiguous block and no flash, and
# if RAM ever runs low the append just fails and we upload what we captured.
MAX_REC_BYTES = 15 * 16000 * 2
_rec_chunks = []      # list of bytes objects captured this recording
_rec_pos = 0          # total PCM bytes captured this recording
_voice_start = -1     # byte offset of first voiced frame (-1 = none yet)
_voice_end = 0        # byte offset just past last voiced frame
_rec_len = 0
_rec_start = 0
_pcm = None
_asr_session = None
VAD_THRESHOLD = 600
# PCM reads 640 bytes at 16 kHz mono 16-bit: 320 samples ~= 20 ms.
# Keep the legacy tutor/chat feel: stop after roughly 200 ms of silence.
VAD_SILENCE_FRAMES = 10
# Keep a short pad of silence around speech before uploading so dead air at the
# start/end of a manual recording doesn't bloat the ASR upload. ~120 ms each
# side (6 frames * 20 ms) is enough to avoid clipping the first/last word.
TRIM_PAD_FRAMES = 6
_token = None
_token_expire_ts = 0


def init(uart, pa_pin):
    global _uart, _pa
    _uart = uart
    _pa = pa_pin


def set_server_tts_config(host=None, path=None, api_key=None, voice_en=None, voice_zh=None, fmt=None, sample_rate=None, port=None, use_tls=None):
    global SERVER_TTS_HOST, SERVER_TTS_PORT, SERVER_TTS_USE_TLS, SERVER_TTS_PATH, SERVER_TTS_API_KEY
    global SERVER_TTS_VOICE_EN, SERVER_TTS_VOICE_ZH, SERVER_TTS_FORMAT, SERVER_TTS_SAMPLE_RATE
    if host:
        SERVER_TTS_HOST = host
    if port is not None:
        SERVER_TTS_PORT = int(port)
    if use_tls is not None:
        SERVER_TTS_USE_TLS = bool(use_tls)
    if path:
        SERVER_TTS_PATH = path
    if api_key is not None:
        SERVER_TTS_API_KEY = api_key
    if voice_en:
        SERVER_TTS_VOICE_EN = voice_en
    if voice_zh:
        SERVER_TTS_VOICE_ZH = voice_zh
    if fmt:
        SERVER_TTS_FORMAT = fmt
    if sample_rate:
        SERVER_TTS_SAMPLE_RATE = sample_rate


def set_server_asr_config(host=None, path=None, api_key=None, port=None, use_tls=None):
    global SERVER_ASR_HOST, SERVER_ASR_PORT, SERVER_ASR_USE_TLS, SERVER_ASR_PATH, SERVER_ASR_API_KEY
    if host:
        SERVER_ASR_HOST = host
    if port is not None:
        SERVER_ASR_PORT = int(port)
    if use_tls is not None:
        SERVER_ASR_USE_TLS = bool(use_tls)
    if path:
        SERVER_ASR_PATH = path
    if api_key is not None:
        SERVER_ASR_API_KEY = api_key


def _uart_send(line):
    if _uart is None:
        return
    try:
        _uart.write((line + "\n").encode("utf-8"))
        utime.sleep_ms(5)
    except Exception:
        pass


def _uart_log(msg):
    _uart_send("LOG:" + str(msg))


def _pa_on():
    if _pa is not None:
        _pa.write(1)


def _pa_off():
    if _pa is not None:
        _pa.write(0)


def _url_quote(s):
    safe = b"-._~"
    out = []
    for b in s.encode("utf-8"):
        if (0x30 <= b <= 0x39) or (0x41 <= b <= 0x5A) or (0x61 <= b <= 0x7A) or b in safe:
            out.append(chr(b))
        else:
            out.append("%%%02X" % b)
    return "".join(out)


def _contains_cjk(text):
    for ch in text:
        code = ord(ch)
        if 0x4E00 <= code <= 0x9FFF:
            return True
    return False


def _looks_like_mp3(data):
    if not data or len(data) < 200:
        return False
    if data[:3] == b"ID3":
        return True
    if len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return True
    return False


def _http_request(method, host, port, path, headers, body=b"", use_tls=True, timeout=30):
    body_bytes = body.encode("utf-8") if isinstance(body, str) else body
    try:
        addr = usocket.getaddrinfo(host, port)[0][-1]
        s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(addr)
        if use_tls:
            s = ussl.wrap_socket(s, server_hostname=host)
        req = "%s %s HTTP/1.1\r\nHost: %s\r\n" % (method, path, host)
        for k, v in headers.items():
            req += "%s: %s\r\n" % (k, v)
        if body_bytes:
            req += "Content-Length: %d\r\n" % len(body_bytes)
        req += "Connection: close\r\n\r\n"
        s.write(req.encode("utf-8"))
        if body_bytes:
            s.write(body_bytes)
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = s.read(512)
            if not chunk:
                break
            buf += chunk
            if len(buf) > 32768:
                break
        sep = buf.find(b"\r\n\r\n")
        if sep < 0:
            try:
                s.close()
            except Exception:
                pass
            return -1, {}, b""
        head_bytes = buf[:sep]
        body_so_far = buf[sep + 4:]
        head_lines = head_bytes.split(b"\r\n")
        status_line = head_lines[0].decode("utf-8", "ignore")
        status = -1
        parts = status_line.split(" ", 2)
        if len(parts) >= 2:
            try:
                status = int(parts[1])
            except Exception:
                pass
        hdrs = {}
        is_chunked = False
        expected = -1
        for line in head_lines[1:]:
            try:
                line_str = line.decode("utf-8", "ignore")
                i = line_str.find(":")
                if i > 0:
                    k = line_str[:i].strip().lower()
                    v = line_str[i + 1:].strip()
                    hdrs[k] = v
                    if k == "transfer-encoding" and "chunked" in v.lower():
                        is_chunked = True
                    if k == "content-length":
                        try:
                            expected = int(v)
                        except Exception:
                            pass
            except Exception:
                pass
        if expected > 0:
            while len(body_so_far) < expected:
                chunk = s.read(min(4096, expected - len(body_so_far)))
                if not chunk:
                    break
                body_so_far += chunk
        else:
            while True:
                chunk = s.read(4096)
                if not chunk:
                    break
                body_so_far += chunk
        try:
            s.close()
        except Exception:
            pass
        if is_chunked:
            decoded = bytearray()
            p = 0
            n = len(body_so_far)
            while p < n:
                crlf = body_so_far.find(b"\r\n", p)
                if crlf < 0:
                    break
                try:
                    size = int(body_so_far[p:crlf].split(b";", 1)[0].strip(), 16)
                except Exception:
                    break
                p = crlf + 2
                if size == 0:
                    break
                if p + size > n:
                    break
                decoded += body_so_far[p:p + size]
                p += size + 2
            body_so_far = bytes(decoded)
        return status, hdrs, body_so_far
    except Exception as e:
        _uart_log("http err: %s" % e)
        return -1, {}, b""


def _play_file(path):
    try:
        _aud.stop()
    except Exception:
        pass
    try:
        f = open(path, "rb")
        f.seek(0, 2)
        size = f.tell()
        f.close()
    except Exception as e:
        _uart_log("play stat err: %s" % e)
        return False
    dur = max(1.0, size / 5000.0)
    try:
        _pa_on()
        rc = _aud.play(2, 1, path)
        if rc < 0:
            return False
        utime.sleep(dur + 0.8)
        return True
    finally:
        try:
            _aud.stop()
        except Exception:
            pass
        _pa_off()


def _tts_busy():
    try:
        return _tts.getState() != 0
    except Exception:
        return False


def _speak_local_fallback(text):
    _pa_on()
    _tts.play(2, 0, _tts.text_utf8, text)
    for _ in range(60):
        utime.sleep(1)
        if not _tts_busy():
            break
    _pa_off()


def _get_baidu_token():
    global _token, _token_expire_ts
    now = utime.time()
    if _token and now < _token_expire_ts - 600:
        return _token
    url = "%s?grant_type=client_credentials&client_id=%s&client_secret=%s" % (
        TOKEN_URL, BAIDU_API_KEY, BAIDU_SECRET_KEY)
    try:
        r = request.get(url)
    except Exception as e:
        _uart_log("token fetch err: %s" % e)
        return None
    try:
        body = b""
        for chunk in r.content:
            body += chunk
        j = ujson.loads(body)
        _token = j["access_token"]
        _token_expire_ts = now + int(j.get("expires_in", 2592000))
        return _token
    except Exception as e:
        _uart_log("token parse err: %s" % e)
        return None
    finally:
        try:
            r.close()
        except Exception:
            pass


def _fetch_tts_baidu(text, lang, path):
    tok = _get_baidu_token()
    if not tok:
        return False
    tex = _url_quote(text)
    body_str = ("tex=%s&tok=%s&cuid=ec800m&ctp=1&lan=zh&per=%d&spd=%d&pit=5&vol=9&aue=3"
                % (tex, tok, BAIDU_PER, BAIDU_SPD))
    status, headers, body = _http_request(
        "POST", "tsn.baidu.com", 443, "/text2audio",
        {"Content-Type": "application/x-www-form-urlencoded"},
        body_str, True, 30)
    if status != 200 or not _looks_like_mp3(body):
        return False
    try:
        uos.remove(path)
    except Exception:
        pass
    f = open(path, "wb")
    f.write(body)
    f.close()
    return True


def _fetch_tts_server(text, lang, path, purpose="tutor_chat"):
    if not SERVER_TTS_HOST:
        _uart_log("server tts host not configured")
        return False
    voice = SERVER_TTS_VOICE_ZH if _contains_cjk(text) else SERVER_TTS_VOICE_EN
    body = ujson.dumps({
        "text": text,
        "lang": lang,
        "voice": voice,
        "format": SERVER_TTS_FORMAT,
        "sample_rate": SERVER_TTS_SAMPLE_RATE,
        "purpose": purpose,
    })
    headers = {"Content-Type": "application/json"}
    if SERVER_TTS_API_KEY:
        headers["Authorization"] = "Bearer " + SERVER_TTS_API_KEY
    status, hdrs, audio_body = _http_request(
        "POST", SERVER_TTS_HOST, SERVER_TTS_PORT, SERVER_TTS_PATH, headers, body, SERVER_TTS_USE_TLS, 30)
    if status != 200 or len(audio_body) < 200:
        _uart_log("server tts failed status=%s len=%d" % (status, len(audio_body)))
        return False
    ctype = hdrs.get("content-type", "").lower()
    if not _looks_like_mp3(audio_body):
        head = audio_body[:24]
        try:
            head = head.decode("utf-8", "ignore")
        except Exception:
            head = str(head)
        _uart_log("server tts invalid mp3 ctype=%s head=%s" % (ctype, head))
        return False
    try:
        uos.remove(path)
    except Exception:
        pass
    f = open(path, "wb")
    f.write(audio_body)
    f.close()
    return True


def speak(text, lang="en", purpose="tutor_chat"):
    text = (text or "").strip()
    if not text:
        return False
    try:
        if _fetch_tts_server(text, lang, TMP_MP3, purpose) and _play_file(TMP_MP3):
            return True
    except Exception as e:
        _uart_log("server tts err: %s" % e)
    try:
        if _fetch_tts_baidu(text, lang, TMP_MP3) and _play_file(TMP_MP3):
            return True
    except Exception as e:
        _uart_log("baidu tts err: %s" % e)
    _speak_local_fallback(text)
    return True


class _ParaformerSession(object):
    def __init__(self):
        self.error = "disabled in merge build"
        self.alive = False

    def start(self):
        return False

    def finish(self, wait_ms=0):
        return ""


_asr_session = None


def _chunk_peak(chunk, n):
    # Max abs sample in `chunk` (first n bytes, subsampled) for VAD.
    peak = 0
    i = 0
    while i < n - 1:
        v = chunk[i] | (chunk[i + 1] << 8)
        if v & 0x8000:
            v -= 0x10000
        if v < 0:
            v = -v
        if v > peak:
            peak = v
        i += 8
    return peak


def _compute_trim():
    # Turn the voiced-frame offsets captured during recording into an upload
    # span [_rec_start, _rec_len), keeping ~TRIM_PAD_FRAMES of pad each side.
    global _rec_start, _rec_len
    frame_bytes = 640
    if _voice_start < 0:
        # No frame ever crossed the VAD threshold; upload the whole recording
        # rather than sending nothing.
        _rec_start = 0
        _rec_len = _rec_pos
        return _rec_pos
    start = _voice_start - TRIM_PAD_FRAMES * frame_bytes
    if start < 0:
        start = 0
    end = _voice_end + TRIM_PAD_FRAMES * frame_bytes
    if end > _rec_pos:
        end = _rec_pos
    _rec_start = start
    _rec_len = end
    return end - start


def _pcm_worker():
    global _rec_pos, _voice_start, _voice_end, _worker_alive, _recording, _pcm, _vad_pending
    _worker_alive = True
    speech_started = False
    silent_frames = 0
    while _recording:
        try:
            chunk = _pcm.read(640)
        except Exception as e:
            _uart_log("pcm read err: %s" % e)
            break
        if chunk and chunk != -1:
            n = len(chunk)
            if _rec_pos + n > MAX_REC_BYTES:
                n = MAX_REC_BYTES - _rec_pos
            if n > 0:
                # Append to the in-RAM chunk list. bytes(chunk) copies the
                # driver buffer so it stays valid after the next read().
                try:
                    if n == len(chunk):
                        _rec_chunks.append(bytes(chunk))
                    else:
                        _rec_chunks.append(bytes(chunk[:n]))
                except Exception as e:
                    _uart_log("rec mem err: %s" % e)
                    _recording = False
                    break
                frame_off = _rec_pos
                _rec_pos += n
            else:
                frame_off = _rec_pos
            peak = _chunk_peak(chunk, n)
            if peak >= VAD_THRESHOLD:
                speech_started = True
                silent_frames = 0
                if _voice_start < 0:
                    _voice_start = frame_off
                _voice_end = frame_off + n
            elif _vad_enabled and speech_started:
                silent_frames += 1
                if silent_frames >= VAD_SILENCE_FRAMES:
                    _vad_pending = True
                    _recording = False
                    break
            if _rec_pos >= MAX_REC_BYTES:
                _recording = False
                break
    _worker_alive = False


def record_start(vad_enabled=True):
    global _pcm, _rec_chunks, _rec_pos, _rec_len, _rec_start, _voice_start, _voice_end
    global _recording, _asr_session, _vad_pending, _vad_enabled
    _uart_log("record_start begin")
    if _PCM_CLS is None:
        _uart_log("no PCM class")
        return False
    if _recording:
        _uart_log("record_start ignored already recording")
        return False
    # Drop the previous recording's chunks and reclaim RAM before the next one.
    _rec_chunks = []
    _rec_pos = 0
    _rec_len = 0
    _rec_start = 0
    _voice_start = -1
    _voice_end = 0
    _vad_pending = False
    _vad_enabled = vad_enabled
    try:
        gc.collect()
    except Exception:
        pass
    try:
        _pcm = _PCM_CLS(PCM_DEVICE, _PCM_MONO, ASR_RATE, _PCM_RO, _PCM_BLOCK)
    except Exception as e:
        _uart_log("PCM init err: %s" % e)
        _pcm = None
        return False
    _asr_session = _ParaformerSession()
    _recording = True
    try:
        _thread.start_new_thread(_pcm_worker, ())
    except Exception as e:
        _uart_log("thread err: %s" % e)
        _recording = False
        try:
            _pcm.close()
        except Exception:
            pass
        _pcm = None
        return False
    _uart_send("RECORD:READY")
    _uart_log("record_start ready")
    return True


def record_stop():
    global _recording, _pcm
    _uart_log("record_stop begin recording=%s worker=%s bytes=%d" % (_recording, _worker_alive, _rec_pos))
    _recording = False
    for _ in range(20):
        if not _worker_alive:
            break
        utime.sleep_ms(50)
    if _pcm is not None:
        try:
            _pcm.close()
        except Exception as e:
            _uart_log("pcm close err: %s" % e)
        _pcm = None
    _uart_log("record_stop end bytes=%d" % _rec_pos)
    return _rec_pos


def stop_recording_if_needed():
    if _recording:
        try:
            record_stop()
        except Exception:
            pass


def _collect_span(start, pcm_len):
    # Concatenate chunk-list bytes in [start, start+pcm_len) into one bytes.
    # Only used by server ASR (disabled by default); Baidu streams the chunk
    # list directly to avoid building this large contiguous block.
    out = bytearray()
    pos = 0
    want_end = start + pcm_len
    for c in _rec_chunks:
        clen = len(c)
        cstart = pos
        cend = pos + clen
        pos = cend
        if cend <= start:
            continue
        if cstart >= want_end:
            break
        a = start - cstart
        if a < 0:
            a = 0
        b = want_end - cstart
        if b > clen:
            b = clen
        if b > a:
            out += c[a:b]
    return bytes(out)


def _asr_recognize_server(start, pcm_len):
    if not SERVER_ASR_HOST:
        return ""
    headers = {"Content-Type": "audio/pcm;rate=%d" % ASR_RATE}
    if SERVER_ASR_API_KEY:
        headers["Authorization"] = "Bearer " + SERVER_ASR_API_KEY
    try:
        status, hdrs, body = _http_request(
            "POST",
            SERVER_ASR_HOST,
            SERVER_ASR_PORT,
            SERVER_ASR_PATH,
            headers,
            _collect_span(start, pcm_len),
            SERVER_ASR_USE_TLS,
            20,
        )
    except Exception as e:
        _uart_log("server asr err: %s" % e)
        return ""
    if status != 200:
        _uart_log("server asr failed status=%s len=%d" % (status, len(body)))
        return ""
    try:
        j = ujson.loads(body)
    except Exception:
        _uart_log("server asr json parse failed len=%d" % len(body))
        return ""
    text = str(j.get("text") or "").strip()
    if text:
        _uart_log("server asr ok text_len=%d" % len(text))
    else:
        _uart_log("server asr empty")
    return text


def _asr_recognize_baidu(path, start, pcm_len):
    _uart_log("asr_recognize begin")
    tok = _get_baidu_token()
    if not tok:
        _uart_log("asr token empty")
        return ""
    _uart_log("asr post pcm_len=%d" % pcm_len)
    q = "?cuid=ec800m&token=%s&dev_pid=%d" % (tok, ASR_DEV_PID)
    url_path = ASR_URL_PATH + q
    ctype = "audio/pcm;rate=%d" % ASR_RATE
    try:
        global _asr_addr
        _t_conn0 = utime.ticks_ms()
        if _asr_addr is None:
            _asr_addr = usocket.getaddrinfo(ASR_URL_HOST, 443)[0][-1]
        addr = _asr_addr
        s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
        s.settimeout(30)
        s.connect(addr)
        s = ussl.wrap_socket(s, server_hostname=ASR_URL_HOST)
        _t_up0 = utime.ticks_ms()
        _uart_log("asr connect ms=%d" % utime.ticks_diff(_t_up0, _t_conn0))
        req = ("POST %s HTTP/1.1\r\n"
               "Host: %s\r\n"
               "Content-Type: %s\r\n"
               "Content-Length: %d\r\n"
               "Connection: close\r\n"
               "\r\n") % (url_path, ASR_URL_HOST, ctype, pcm_len)
        s.write(req.encode("utf-8"))
        # Walk the chunk list, sending only bytes in [start, start+pcm_len).
        sent = 0
        pos = 0
        want_end = start + pcm_len
        for c in _rec_chunks:
            clen = len(c)
            cstart = pos
            cend = pos + clen
            pos = cend
            if cend <= start:
                continue
            if cstart >= want_end:
                break
            a = start - cstart
            if a < 0:
                a = 0
            b = want_end - cstart
            if b > clen:
                b = clen
            if b > a:
                s.write(c[a:b] if (a > 0 or b < clen) else c)
                sent += b - a
        _t_resp0 = utime.ticks_ms()
        _uart_log("asr upload ms=%d sent=%d" % (utime.ticks_diff(_t_resp0, _t_up0), sent))
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = s.read(512)
            if not chunk:
                break
            buf += chunk
            if len(buf) > 32768:
                break
        _uart_log("asr wait_resp ms=%d" % utime.ticks_diff(utime.ticks_ms(), _t_resp0))
        sep = buf.find(b"\r\n\r\n")
        if sep < 0:
            try:
                s.close()
            except Exception:
                pass
            return ""
        head_bytes = buf[:sep]
        body_so_far = buf[sep + 4:]
        while True:
            chunk = s.read(2048)
            if not chunk:
                break
            body_so_far += chunk
        try:
            s.close()
        except Exception:
            pass
    except Exception as e:
        _uart_log("asr socket err: %s" % e)
        return ""
    is_chunked = False
    for line in head_bytes.split(b"\r\n")[1:]:
        i = line.find(b":")
        if i > 0:
            k = line[:i].strip().lower()
            v = line[i + 1:].strip().lower()
            if k == b"transfer-encoding" and b"chunked" in v:
                is_chunked = True
                break
    body = body_so_far
    if is_chunked:
        decoded = bytearray()
        p = 0
        n = len(body)
        while p < n:
            crlf = body.find(b"\r\n", p)
            if crlf < 0:
                break
            try:
                size = int(body[p:crlf].split(b";", 1)[0].strip(), 16)
            except Exception:
                break
            p = crlf + 2
            if size == 0:
                break
            if p + size > n:
                break
            decoded += body[p:p + size]
            p += size + 2
        body = bytes(decoded)
    try:
        j = ujson.loads(body)
    except Exception:
        _uart_log("asr json parse failed len=%d" % len(body))
        return ""
    if int(j.get("err_no", -1)) != 0:
        _uart_log("asr err_no=%s" % j.get("err_no", -1))
        return ""
    result = j.get("result")
    if isinstance(result, list) and result:
        _uart_log("asr ok text_len=%d" % len(str(result[0])))
        return str(result[0]).strip()
    _uart_log("asr empty result")
    return ""


def asr_recognize(path):
    # Upload span is the trimmed voiced region [_rec_start, _rec_len) computed
    # by _compute_trim(); fall back to the whole recording if trim not run.
    if _rec_len > _rec_start:
        start = _rec_start
        pcm_len = _rec_len - _rec_start
    else:
        start = 0
        pcm_len = _rec_pos
    if pcm_len < 16000:
        _uart_log("asr pcm too short len=%d" % pcm_len)
        return ""
    text = _asr_recognize_server(start, pcm_len)
    if text:
        return text
    if SERVER_ASR_HOST:
        _uart_log("server asr fallback baidu")
    return _asr_recognize_baidu(path, start, pcm_len)


def do_asr_and_send():
    global _rec_chunks, _rec_pos, _rec_len, _rec_start, _asr_session
    try:
        _uart_log("do_asr begin")
        sz = record_stop()
        if sz <= 0:
            _uart_log("do_asr no audio")
            _uart_send("ASR:ERR")
            return
        trimmed = _compute_trim()
        _uart_log("do_asr sizes raw=%d trimmed=%d" % (sz, trimmed))
        text = asr_recognize(TMP_REC) or ""
        if text:
            _uart_log("do_asr send USER len=%d" % len(text))
            _uart_send("USER:" + text)
        else:
            _uart_log("do_asr send ASR_ERR")
            _uart_send("ASR:ERR")
    except Exception as e:
        _uart_log("asr fatal: %s" % e)
        _uart_send("ASR:ERR")
    finally:
        # Free the captured audio immediately so RAM isn't held between turns.
        _rec_chunks = []
        _rec_pos = 0
        _rec_len = 0
        _rec_start = 0
        _asr_session = None
        try:
            gc.collect()
        except Exception:
            pass


def handle_line(line):
    global _last_word_en, _last_word_cn
    line = (line or "").strip()
    if not line:
        return
    if line.startswith("SPEAK:"):
        text = line[6:].strip()
        _uart_log("rx SPEAK len=%d" % len(text))
        if text:
            speak(text, "en", "tutor_chat")
        _uart_send("SPEAK:DONE")
        _uart_log("send SPEAK:DONE")
    elif line.startswith("TTS:"):
        text = line[4:].strip()
        _uart_log("rx TTS len=%d" % len(text))
        if text:
            speak(text, "en", "word")
        _uart_send("TTS:DONE")
        _uart_log("send TTS:DONE")
    elif line.startswith("WORD:"):
        body = line[5:]
        parts = body.split(":", 1)
        _last_word_en = parts[0].strip()
        _last_word_cn = parts[1].strip() if len(parts) > 1 else ""
        _uart_log("rx WORD en=%s cn_len=%d" % (_last_word_en, len(_last_word_cn)))
    elif line.startswith("RECORD:START_MANUAL"):
        record_start(False)
    elif line.startswith("RECORD:START"):
        record_start(True)
    elif line.startswith("RECORD:STOP"):
        do_asr_and_send()
    elif line.startswith("MODE:"):
        mode = line[5:].strip()
        if mode == "WS_TEST":
            _uart_log("WS_TEST ignored in merge build")


def poll_vad():
    global _vad_pending
    if _vad_pending:
        _vad_pending = False
        _uart_send("RECORD:VAD")
        do_asr_and_send()
        return True
    return False
