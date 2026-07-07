import audio
import utime
import ujson
import request
import usocket
import ussl
import uos
import ubinascii
from machine import UART, Pin

# ---- 硬件配置 ----
# 主串口 PIN17/18 = QuecPython UART2，接 qsm368zp ttyS8
# PA 控制引脚 29 = QuecPython GPIO33
UART_PORT = UART.UART2
BAUD = 115200
PA_GPIO  = Pin.GPIO33

# ---- 百度云 TTS ----
BAIDU_API_KEY    = "ccFGe5LvukV9tmSNfLqvZMD4"
BAIDU_SECRET_KEY = "5q2zGackMBQ8uQnjoFcv7mJ8wlqRRXaS"
BAIDU_PER = 0    # 0=度小美 (free, soft female). Premium voices (4106/5118/5003)
                 # require enabling 精品音库 on the Baidu console.
BAIDU_SPD = 4    # speed 0-15 (5=normal, 4=slightly slow for English learners)
TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
TTS_URL   = "https://tsn.baidu.com/text2audio"
TMP_MP3   = "/usr/tts_tmp.mp3"

# ---- 阿里云 CosyVoice TTS (preferred — sounds more natural than Baidu) ----
# Async pattern: POST submit -> GET poll task_id until SUCCEEDED -> GET audio.url
COSY_API_KEY = "sk-6bfcca7f0f484e429ce29770ec0774d5"
COSY_HOST    = "dashscope.aliyuncs.com"
COSY_SUBMIT_PATH = "/api/v1/services/audio/tts"
COSY_SYNC_PATH   = "/compatible-mode/v1/audio/speech"  # OpenAI-compat sync TTS
COSY_TASK_PATH   = "/api/v1/tasks/"
COSY_MODEL   = "cosyvoice-v3.5-flash"
COSY_VOICE   = "longxiaochun"
COSY_FORMAT  = "mp3"
COSY_RATE    = 16000

# ---- 百度语音识别 (ASR) ----
# Use audio.Audio.PCM for 16kHz raw PCM capture (16-bit mono, blocking).
# Sent to Baidu ASR as format="pcm", rate=16000.
ASR_URL_HOST = "vop.baidu.com"
ASR_URL_PATH = "/server_api"
ASR_DEV_PID  = 1737   # 1737=纯英文; 1537=普通话; 1936=中英混合(now usable @ 16k)
TMP_REC      = "/usr/rec_tmp.pcm"
ASR_RATE     = 16000
ASR_FORMAT   = "pcm"

# ---- DashScope Paraformer realtime ASR (streaming WebSocket) ----
DASHSCOPE_API_KEY = "sk-6bfcca7f0f484e429ce29770ec0774d5"
PARAFORMER_HOST   = "dashscope.aliyuncs.com"
PARAFORMER_PATH   = "/api-ws/v1/inference/"
PARAFORMER_PORT   = 443
PARAFORMER_MODEL  = "paraformer-realtime-v2"
PCM_DEVICE   = 1      # demo: 1 = headset mic; try 0 if device=1 fails

_token = None
_token_expire_ts = 0

def _url_quote(s):
    safe = b"-._~"
    out = []
    for b in s.encode("utf-8"):
        if (0x30 <= b <= 0x39) or (0x41 <= b <= 0x5A) or (0x61 <= b <= 0x7A) or b in safe:
            out.append(chr(b))
        else:
            out.append("%%%02X" % b)
    return "".join(out)

def get_token():
    global _token, _token_expire_ts
    now = utime.time()
    if _token and now < _token_expire_ts - 600:
        return _token
    url = "%s?grant_type=client_credentials&client_id=%s&client_secret=%s" % (
        TOKEN_URL, BAIDU_API_KEY, BAIDU_SECRET_KEY)
    print("[EC800M] fetching token...")
    try:
        r = request.get(url)
    except Exception as e:
        print("[EC800M] token fetch err:", e)
        return None
    try:
        body = b""
        for chunk in r.content:
            body += chunk
        j = ujson.loads(body)
        _token = j["access_token"]
        _token_expire_ts = now + int(j.get("expires_in", 2592000))
        print("[EC800M] token OK, expires in", j.get("expires_in"), "s")
        return _token
    except Exception as e:
        print("[EC800M] token parse err:", e)
        return None
    finally:
        try: r.close()
        except Exception: pass

def _http_post_binary(host, port, path, body, use_tls=True,
                      content_type="application/x-www-form-urlencoded"):
    """Send HTTP POST and read full response by Content-Length.
    Returns (status, headers_dict, body_bytes) or (-1, {}, b"") on failure."""
    addr = usocket.getaddrinfo(host, port)[0][-1]
    s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
    s.settimeout(30)
    s.connect(addr)
    if use_tls:
        s = ussl.wrap_socket(s, server_hostname=host)

    body_bytes = body.encode("utf-8") if isinstance(body, str) else body
    req = ("POST %s HTTP/1.1\r\n"
           "Host: %s\r\n"
           "Content-Type: %s\r\n"
           "Content-Length: %d\r\n"
           "Connection: close\r\n"
           "\r\n") % (path, host, content_type, len(body_bytes))
    s.write(req.encode("utf-8"))
    s.write(body_bytes)

    # read header until \r\n\r\n
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.read(512)
        if not chunk:
            break
        buf += chunk
        if len(buf) > 16384:
            break

    sep = buf.find(b"\r\n\r\n")
    if sep < 0:
        s.close()
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

    headers = {}
    for line in head_lines[1:]:
        try:
            line_str = line.decode("utf-8", "ignore")
            i = line_str.find(":")
            if i > 0:
                headers[line_str[:i].strip().lower()] = line_str[i + 1:].strip()
        except Exception:
            pass

    expected = -1
    cl = headers.get("content-length")
    if cl:
        try:
            expected = int(cl)
        except Exception:
            pass

    body_out = body_so_far
    if expected > 0:
        while len(body_out) < expected:
            need = expected - len(body_out)
            chunk = s.read(min(4096, need))
            if not chunk:
                break
            body_out += chunk
    else:
        while True:
            chunk = s.read(4096)
            if not chunk:
                break
            body_out += chunk

    try:
        s.close()
    except Exception:
        pass
    return status, headers, body_out


# ---- 串口 ----
uart = UART(UART_PORT, BAUD, 8, 0, 1, 0)
print("[EC800M] UART2 ready @", BAUD)
# self-test: prove EC800M -> Qt UART read path is alive
uart.write(b"USER:__SELFTEST__\n")
print("[EC800M] sent USER:__SELFTEST__ self-test")

# ---- PA 功放使能 ----
pa = Pin(PA_GPIO, Pin.OUT, Pin.PULL_DISABLE, 0)

def pa_on():
    pa.write(1)

def pa_off():
    pa.write(0)

# ---- 本机 TTS（兜底，拼字母） ----
tts = audio.TTS(0)
tts.setVolume(8)
tts.setSpeed(5)

def tts_busy():
    try:
        return tts.getState() != 0
    except Exception:
        return False

def speak_local_fallback(text):
    print("[EC800M] fallback speak:", text)
    pa_on()
    tts.play(2, 0, tts.text_utf8, text)
    for _ in range(60):
        utime.sleep(1)
        if not tts_busy():
            break
    pa_off()

# ---- 云端 mp3 播放 ----
aud = audio.Audio(0)
aud.setVolume(8)

def aud_busy():
    try:
        return aud.getState() != 0
    except Exception:
        return False

def fetch_tts_to_file(text, lang, path):
    """Fetch TTS MP3 from Baidu and save to given path. Using aue=3 (16kHz mp3)
    keeps 16kHz quality but compressed size stays under the chip's per-call
    playback budget for a typical sentence.

    Note: lan is hardcoded to "zh" because Baidu's free voices (per=0/1/3/4)
    only register under the Chinese cluster. They CAN read English text — the
    pronunciation is just slightly accented. Sending lan=en triggers an
    err_no=501 "failed to find cluster" because per=0 + lan=en isn't a valid
    combination unless the account has premium English voices enabled."""
    tok = get_token()
    if not tok:
        return False
    tex = _url_quote(text)
    body_str = ("tex=%s&tok=%s&cuid=ec800m&ctp=1&lan=zh&per=%d&spd=%d&pit=5&vol=9&aue=3"
                % (tex, tok, BAIDU_PER, BAIDU_SPD))
    print("[EC800M] tts POST len(text)=", len(text))
    try:
        status, headers, body = _http_post_binary(
            "tsn.baidu.com", 443, "/text2audio", body_str, use_tls=True)
    except Exception as e:
        print("[EC800M] tts socket err:", e)
        return False

    expected = -1
    cl = headers.get("content-length")
    if cl:
        try:
            expected = int(cl)
        except Exception:
            pass
    print("[EC800M] tts status=", status, "body_len=", len(body), "expected=", expected)
    if status != 200 or len(body) < 200 or body[:1] == b"{":
        print("[EC800M] tts fetch failed:", body[:200])
        return False
    if expected > 0 and len(body) != expected:
        print("[EC800M] tts body mismatch:", len(body), "vs", expected)
        return False
    try: uos.remove(path)
    except Exception: pass
    f = open(path, "wb")
    f.write(body)
    f.close()
    print("[EC800M] mp3 saved", len(body), "bytes")
    return True


def fetch_tts_mp3(text, lang="en"):
    return fetch_tts_to_file(text, lang, TMP_MP3)


def _http_request(method, host, port, path, headers, body=b"", use_tls=True, timeout=30):
    """Generic HTTP request. Returns (status, headers_dict, body_bytes) or (-1, {}, b"")."""
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
            try: s.close()
            except: pass
            return -1, {}, b""
        head_bytes = buf[:sep]
        body_so_far = buf[sep + 4:]
        head_lines = head_bytes.split(b"\r\n")
        status_line = head_lines[0].decode("utf-8", "ignore")
        status = -1
        parts = status_line.split(" ", 2)
        if len(parts) >= 2:
            try: status = int(parts[1])
            except Exception: pass
        hdrs = {}
        is_chunked = False
        expected = -1
        for line in head_lines[1:]:
            try:
                line_str = line.decode("utf-8", "ignore")
                i = line_str.find(":")
                if i > 0:
                    k = line_str[:i].strip().lower()
                    v = line_str[i+1:].strip()
                    hdrs[k] = v
                    if k == "transfer-encoding" and "chunked" in v.lower():
                        is_chunked = True
                    if k == "content-length":
                        try: expected = int(v)
                        except Exception: pass
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
        try: s.close()
        except: pass
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
        print("[EC800M] http err:", e)
        return -1, {}, b""


_cosy_async_only = False
_cosy_disabled = False

def _fetch_tts_cosy_sync(text, path):
    """Sync HTTP TTS via OpenAI-compatible /audio/speech endpoint.
    Returns mp3 bytes directly in body — no submit/poll/download cycle."""
    body_str = ujson.dumps({
        "model": COSY_MODEL,
        "input": text,
        "voice": COSY_VOICE,
        "response_format": COSY_FORMAT,
    })
    headers = {
        "Authorization": "Bearer " + COSY_API_KEY,
        "Content-Type": "application/json",
    }
    t0 = utime.ticks_ms()
    status, hdrs, body = _http_request("POST", COSY_HOST, 443, COSY_SYNC_PATH,
                                        headers, body_str, True, 30)
    elapsed = utime.ticks_diff(utime.ticks_ms(), t0)
    if status != 200 or len(body) < 200:
        print("[EC800M] cosy sync fail %dms status=%s len=%d body=%s" % (
            elapsed, status, len(body), body[:120]))
        return False
    ctype = hdrs.get("content-type", "").lower()
    is_audio = ("audio" in ctype) or body[:3] == b"ID3" or \
               (len(body) >= 2 and body[0] == 0xFF and (body[1] & 0xE0) == 0xE0)
    if not is_audio:
        print("[EC800M] cosy sync non-audio %dms ctype=%s body=%s" % (
            elapsed, ctype, body[:120]))
        return False
    try: uos.remove(path)
    except Exception: pass
    f = open(path, "wb")
    f.write(body)
    f.close()
    print("[EC800M] cosy sync mp3 %dms %d bytes" % (elapsed, len(body)))
    return True


def _fetch_tts_cosy_async(text, path):
    """Async pattern: POST submit -> poll task -> GET audio.url. Fallback path."""
    submit_body = ujson.dumps({
        "model": COSY_MODEL,
        "input": {"text": text},
        "parameters": {
            "voice": COSY_VOICE,
            "format": COSY_FORMAT,
            "sample_rate": COSY_RATE,
            "volume": 80,
            "rate": 1.0,
            "pitch": 1.0,
        },
    })
    headers = {
        "Authorization": "Bearer " + COSY_API_KEY,
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    t0 = utime.ticks_ms()
    print("[EC800M] cosy async submit len(text)=", len(text))
    status, _, body = _http_request("POST", COSY_HOST, 443, COSY_SUBMIT_PATH,
                                    headers, submit_body, True, 20)
    if status != 200:
        print("[EC800M] cosy async submit fail status=", status, "body=", body[:200])
        return False
    try:
        j = ujson.loads(body)
        task_id = j["output"]["task_id"]
    except Exception as e:
        print("[EC800M] cosy async submit parse err:", e, "body=", body[:200])
        return False
    t_submit = utime.ticks_diff(utime.ticks_ms(), t0)

    poll_path = COSY_TASK_PATH + task_id
    poll_headers = {"Authorization": "Bearer " + COSY_API_KEY}
    audio_url = ""
    polls = 0
    t_poll_start = utime.ticks_ms()
    for i in range(50):
        utime.sleep_ms(200 if i == 0 else 300)
        polls += 1
        st, _, pb = _http_request("GET", COSY_HOST, 443, poll_path,
                                  poll_headers, b"", True, 15)
        if st != 200:
            print("[EC800M] cosy poll fail status=", st)
            continue
        try:
            pj = ujson.loads(pb)
            task_status = pj["output"]["task_status"]
        except Exception as e:
            print("[EC800M] cosy poll parse err:", e)
            continue
        if task_status == "SUCCEEDED":
            try:
                audio_url = pj["output"]["audio"]["url"]
            except Exception:
                audio_url = pj["output"].get("audio_url", "")
            break
        if task_status in ("FAILED", "CANCELED", "UNKNOWN"):
            print("[EC800M] cosy task", task_status, pj.get("output"))
            return False
    t_poll = utime.ticks_diff(utime.ticks_ms(), t_poll_start)
    if not audio_url:
        print("[EC800M] cosy poll timeout polls=%d" % polls)
        return False

    print("[EC800M] cosy audio url=", audio_url[:80])
    use_tls = audio_url.startswith("https://")
    rest = audio_url.split("://", 1)[1]
    slash = rest.find("/")
    if slash < 0:
        return False
    host = rest[:slash]
    if ":" in host:
        host_part, port_str = host.split(":", 1)
        try: port = int(port_str)
        except Exception: port = 443 if use_tls else 80
        host = host_part
    else:
        port = 443 if use_tls else 80
    url_path = rest[slash:]
    t_dl = utime.ticks_ms()
    st, _, audio_body = _http_request("GET", host, port, url_path,
                                      {"Host": host}, b"", use_tls, 30)
    t_dl_ms = utime.ticks_diff(utime.ticks_ms(), t_dl)
    if st != 200 or len(audio_body) < 200:
        print("[EC800M] cosy download fail status=", st, "len=", len(audio_body))
        return False
    try: uos.remove(path)
    except Exception: pass
    f = open(path, "wb")
    f.write(audio_body)
    f.close()
    print("[EC800M] cosy async mp3 submit=%dms poll=%dms*%d dl=%dms %d bytes" % (
        t_submit, t_poll, polls, t_dl_ms, len(audio_body)))
    return True


def fetch_tts_cosyvoice(text, path):
    """Try sync HTTP first; pin to async-only after first sync failure;
    fully disable for session if async also fails (avoids 500ms+ wasted per call)."""
    global _cosy_async_only, _cosy_disabled
    if _cosy_disabled:
        return False
    if not _cosy_async_only:
        if _fetch_tts_cosy_sync(text, path):
            return True
        _cosy_async_only = True
        print("[EC800M] cosy switching to async-only for this session")
    if _fetch_tts_cosy_async(text, path):
        return True
    _cosy_disabled = True
    print("[EC800M] cosy fully disabled this session — using Baidu only")
    return False


def play_file_inline(path):
    try:
        f = open(path, "rb")
        f.seek(0, 2)
        size = f.tell()
        f.close()
    except Exception as e:
        print("[EC800M] play stat err:", e)
        return False
    # MP3 from Baidu TTS is roughly 64kbps = 8KB/s
    dur = size / 8000.0
    rc = aud.play(2, 1, path)
    print("[EC800M] aud.play rc=", rc, "size=", size, "est_dur=", dur)
    if rc < 0:
        return False
    utime.sleep(dur + 0.2)
    return True


def play_wav(path):
    pa_on()
    ok = play_file_inline(path)
    try:
        aud.stop()
    except Exception:
        pass
    pa_off()
    return ok


def speak(text, lang="en"):
    print("[EC800M] speak len=", len(text), "lang=", lang)
    text = text.strip()
    if not text:
        return
    # Baidu cloud TTS (fast, ~1.5s end-to-end on 4G)
    try:
        if fetch_tts_to_file(text, lang, TMP_MP3) and play_wav(TMP_MP3):
            print("[EC800M] speak done (baidu)")
            return
    except Exception as e:
        print("[EC800M] baidu tts err:", e)
    # on-chip local TTS (letter-spell fallback)
    speak_local_fallback(text)
    print("[EC800M] speak done (fallback)")

# ---- 录音 + 百度 ASR ----
import _thread

# ---- 极简 WebSocket 客户端 (RFC 6455, client-only, masked, single-fragment) ----
# 仅实现 DashScope realtime 协议需要的最小子集:
#   - 发送 text(0x1) / binary(0x2) / close(0x8)
#   - 接收任意帧, 支持 7/16/64 位长度, 服务端不应 mask (RFC: server->client MUST NOT mask)
# 不支持: 分片、扩展、ping/pong (DashScope 不发).

def _ws_mask_key():
    try:
        return uos.urandom(4)
    except Exception:
        # urandom 不可靠时退回 ticks
        t = utime.ticks_us()
        return bytes(((t >> (i*8)) & 0xff) for i in range(4))

def _ws_build_frame(opcode, payload):
    """Build a single-fragment masked client frame."""
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    n = len(payload)
    hdr = bytearray()
    hdr.append(0x80 | (opcode & 0x0f))   # FIN=1, opcode
    if n < 126:
        hdr.append(0x80 | n)              # MASK=1
    elif n < 65536:
        hdr.append(0x80 | 126)
        hdr.append((n >> 8) & 0xff)
        hdr.append(n & 0xff)
    else:
        hdr.append(0x80 | 127)
        for i in range(7, -1, -1):
            hdr.append((n >> (i*8)) & 0xff)
    mask = _ws_mask_key()
    hdr.extend(mask)
    masked = bytearray(n)
    for i in range(n):
        masked[i] = payload[i] ^ mask[i & 3]
    return bytes(hdr) + bytes(masked)

def _ws_connect(host, path, port=443, extra_headers=None, timeout=15):
    """Open TLS socket and complete WebSocket upgrade. Returns sock or None."""
    addr = usocket.getaddrinfo(host, port)[0][-1]
    s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect(addr)
    s = ussl.wrap_socket(s, server_hostname=host)
    # build a 16-byte random key, base64-encoded
    try:
        key_raw = uos.urandom(16)
    except Exception:
        key_raw = bytes((utime.ticks_us() >> (i % 32)) & 0xff for i in range(16))
    sec_key = ubinascii.b2a_base64(key_raw).decode("ascii").strip()
    req = ("GET %s HTTP/1.1\r\n"
           "Host: %s\r\n"
           "Upgrade: websocket\r\n"
           "Connection: Upgrade\r\n"
           "Sec-WebSocket-Key: %s\r\n"
           "Sec-WebSocket-Version: 13\r\n") % (path, host, sec_key)
    if extra_headers:
        for k, v in extra_headers.items():
            req += "%s: %s\r\n" % (k, v)
    req += "\r\n"
    s.write(req.encode("ascii"))
    # read response headers up to \r\n\r\n
    resp = b""
    while b"\r\n\r\n" not in resp:
        try:
            chunk = s.read(256)
        except Exception:
            chunk = None
        if not chunk:
            break
        resp += chunk
        if len(resp) > 4096:
            break
    if b"101" not in resp.split(b"\r\n", 1)[0]:
        try: s.close()
        except Exception: pass
        print("[EC800M] ws upgrade failed:", resp[:200])
        return None
    return s

def _ws_send_text(sock, payload):
    sock.write(_ws_build_frame(0x1, payload))

def _ws_send_binary(sock, payload):
    sock.write(_ws_build_frame(0x2, payload))

def _ws_send_close(sock):
    try:
        sock.write(_ws_build_frame(0x8, b""))
    except Exception:
        pass

def _ws_recv_frame(sock):
    """Read one frame. Returns (opcode, payload_bytes) or (None, None) on EOF/error.
    Caller controls timeout via sock.settimeout()."""
    try:
        hdr = sock.read(2)
    except Exception:
        return (None, None)
    if not hdr or len(hdr) < 2:
        return (None, None)
    b0 = hdr[0]
    b1 = hdr[1]
    opcode = b0 & 0x0f
    masked = (b1 & 0x80) != 0
    plen = b1 & 0x7f
    if plen == 126:
        ext = sock.read(2)
        if not ext or len(ext) < 2: return (None, None)
        plen = (ext[0] << 8) | ext[1]
    elif plen == 127:
        ext = sock.read(8)
        if not ext or len(ext) < 8: return (None, None)
        plen = 0
        for i in range(8):
            plen = (plen << 8) | ext[i]
    mkey = b""
    if masked:
        mkey = sock.read(4)
        if not mkey or len(mkey) < 4: return (None, None)
    # read payload (possibly fragmented over read() calls)
    payload = b""
    remaining = plen
    while remaining > 0:
        chunk = sock.read(remaining)
        if not chunk:
            break
        payload += chunk
        remaining -= len(chunk)
    if masked and mkey:
        payload = bytes(payload[i] ^ mkey[i & 3] for i in range(len(payload)))
    return (opcode, payload)

# ---- DashScope Paraformer streaming session ----
class _ParaformerSession:
    """One streaming ASR session over WebSocket. Lifecycle:
    start() -> send_audio() x N -> finish() -> close()
    Recv runs on a background thread; main thread only writes."""

    def __init__(self):
        self.sock = None
        self.task_id = None
        self.result_text = ""
        self.final_text = ""
        self.task_started = False
        self.task_finished = False
        self.error = None
        self.alive = False
        self.pending = []           # PCM chunks queued before task-started
        self.pending_bytes = 0
        self.want_finish = False    # set by finish() so the worker can send it after task-started
        self.run_task_payload = None  # serialized run-task json, set by start()

    def _make_task_id(self):
        try:
            return ubinascii.hexlify(uos.urandom(16)).decode("ascii")
        except Exception:
            t = utime.ticks_us()
            return "ec800m%016x" % (t & 0xffffffffffffffff)

    def start(self):
        """Non-blocking: spawns a worker that does TLS+upgrade+run-task+recv.
        Returns True if the worker thread was launched, regardless of whether
        the WS handshake will eventually succeed. Audio sent via send_audio()
        before task-started is queued and flushed on task-started arrival."""
        self.task_id = self._make_task_id()
        run_task = {
            "header": {
                "action": "run-task",
                "task_id": self.task_id,
                "streaming": "duplex",
            },
            "payload": {
                "task_group": "audio",
                "task": "asr",
                "function": "recognition",
                "model": PARAFORMER_MODEL,
                "parameters": {
                    "format": "pcm",
                    "sample_rate": ASR_RATE,
                    "language_hints": ["en"],
                    "disfluency_removal_enabled": False,
                },
                "input": {},
            },
        }
        self.run_task_payload = ujson.dumps(run_task)
        self.alive = True
        try:
            _thread.start_new_thread(self._connect_and_recv_loop, ())
        except Exception as e:
            self.error = "thread start: %s" % e
            self.alive = False
            return False
        return True

    def _connect_and_recv_loop(self):
        # Phase 1: TLS + WS upgrade (slow on cold 4G, ~10s)
        t_start = utime.ticks_ms()
        try:
            self.sock = _ws_connect(
                PARAFORMER_HOST, PARAFORMER_PATH, PARAFORMER_PORT,
                extra_headers={
                    "Authorization": "bearer " + DASHSCOPE_API_KEY,
                    "X-DashScope-DataInspection": "enable",
                },
                timeout=15,
            )
        except Exception as e:
            self.error = "ws connect: %s" % e
            self.alive = False
            print("[EC800M] pf ws connect ex:", e)
            return
        if self.sock is None:
            self.error = "ws connect failed"
            self.alive = False
            print("[EC800M] pf ws connect failed")
            return
        t_connected = utime.ticks_ms()
        print("[EC800M] pf ws connected in %dms" % utime.ticks_diff(t_connected, t_start))
        # Phase 2: send run-task
        try:
            _ws_send_text(self.sock, self.run_task_payload)
        except Exception as e:
            self.error = "run-task send: %s" % e
            self.alive = False
            try: self.sock.close()
            except Exception: pass
            print("[EC800M] pf run-task send ex:", e)
            return
        # Phase 3: recv loop. set short read timeout so we can also drive the
        # send side (flush pending, send finish-task) from this same thread.
        try:
            self.sock.settimeout(0.2)
        except Exception:
            pass
        finish_sent = False
        t_started_logged = False
        results_count = 0
        while self.alive:
            opcode, payload = _ws_recv_frame(self.sock)
            if opcode is None:
                # timeout (no frame): use this tick to flush queued audio /
                # send finish-task if requested
                if self.task_started:
                    if self.pending:
                        n = len(self.pending)
                        try:
                            while self.pending:
                                _ws_send_binary(self.sock, self.pending.pop(0))
                        except Exception as e:
                            self.error = "flush: %s" % e
                            self.alive = False
                            print("[EC800M] pf flush ex:", e)
                            break
                        print("[EC800M] pf flushed %d queued chunks (%dB)" % (n, self.pending_bytes))
                        self.pending_bytes = 0
                    if self.want_finish and not finish_sent:
                        try:
                            fin = {
                                "header": {
                                    "action": "finish-task",
                                    "task_id": self.task_id,
                                    "streaming": "duplex",
                                },
                                "payload": {"input": {}},
                            }
                            _ws_send_text(self.sock, ujson.dumps(fin))
                            finish_sent = True
                            print("[EC800M] pf finish-task sent")
                        except Exception as e:
                            self.error = "finish send: %s" % e
                            self.alive = False
                            print("[EC800M] pf finish send ex:", e)
                            break
                continue
            if opcode == 0x8:   # close
                print("[EC800M] pf got close frame")
                self.alive = False
                break
            if opcode == 0x9:   # ping -> pong
                try: self.sock.write(_ws_build_frame(0xA, payload or b""))
                except Exception: pass
                continue
            if opcode != 0x1:
                continue
            try:
                msg = ujson.loads(payload)
            except Exception as e:
                print("[EC800M] ws json err:", e)
                continue
            hdr = msg.get("header") or {}
            ev = hdr.get("event")
            if ev == "task-started":
                self.task_started = True
                if not t_started_logged:
                    print("[EC800M] pf task-started at +%dms" % utime.ticks_diff(utime.ticks_ms(), t_start))
                    t_started_logged = True
            elif ev == "result-generated":
                pl = msg.get("payload") or {}
                out = pl.get("output") or {}
                sent = out.get("sentence") or {}
                txt = sent.get("text")
                if txt:
                    self.result_text = txt
                    results_count += 1
                    if results_count <= 3 or results_count % 5 == 0:
                        print("[EC800M] pf result #%d: %r" % (results_count, txt))
            elif ev == "task-finished":
                print("[EC800M] pf task-finished at +%dms text=%r" % (
                    utime.ticks_diff(utime.ticks_ms(), t_start), self.result_text))
                self.final_text = self.result_text
                self.task_finished = True
                self.alive = False
                break
            elif ev == "task-failed":
                err = hdr.get("error_message") or hdr.get("error_code") or "task-failed"
                self.error = err
                print("[EC800M] pf task-failed:", err)
                self.alive = False
                break

    def send_audio(self, chunk):
        """Queue audio chunk. Worker thread flushes once task-started arrives.
        Bounded by 1MB to survive a stuck handshake without OOM."""
        if not self.alive or self.error:
            return
        if self.pending_bytes > 1024 * 1024:
            return  # drop
        self.pending.append(chunk)
        self.pending_bytes += len(chunk)

    def finish(self, wait_ms=1500):
        """Wait briefly for task-finished, return transcript.
        If task-started never arrived (handshake too slow), give up immediately
        so the caller can run the Baidu fallback without dragging an extra
        wait_ms onto the user's perceived latency."""
        # Fast path: handshake never completed -> Paraformer is hopeless.
        if not self.task_started:
            self.error = self.error or "no task-started"
            if self.sock is not None:
                try: self.sock.close()
                except Exception: pass
                self.sock = None
            self.alive = False
            return ""
        self.want_finish = True
        t0 = utime.ticks_ms()
        while utime.ticks_diff(utime.ticks_ms(), t0) < wait_ms:
            if self.task_finished or self.error or not self.alive:
                break
            utime.sleep_ms(20)
        if not self.task_finished and not self.error:
            self.error = "task-finished timeout"
        # tear down
        if self.sock is not None:
            try: _ws_send_close(self.sock)
            except Exception: pass
            try: self.sock.close()
            except Exception: pass
            self.sock = None
        self.alive = False
        return self.final_text or self.result_text

_asr_session = None  # current session, set by record_start, consumed by do_asr_and_send

# probe whether audio.Audio.PCM exists on this firmware build
try:
    _PCM_CLS = audio.Audio.PCM
    _PCM_MONO = audio.Audio.PCM.MONO
    _PCM_RO = audio.Audio.PCM.READONLY
    _PCM_BLOCK = audio.Audio.PCM.BLOCK
    print("[EC800M] audio.Audio.PCM available")
except Exception as e:
    print("[EC800M] audio.Audio.PCM NOT available:", e)
    _PCM_CLS = None

_pcm = None
_rec_buf = bytearray()
_rec_len = 0                     # logical length of valid PCM in _rec_buf — set by trim, used by ASR upload
_recording = False
_worker_alive = False
_vad_pending = False
MAX_REC_BYTES = 20 * 16000 * 2   # 20 seconds @ 16kHz 16-bit (hard cap; VAD usually ends earlier)
VAD_THRESHOLD = 600              # peak abs sample value: above = speech, below = silence
VAD_SILENCE_FRAMES = 150         # 3.0s of silence after speech triggers auto-stop (20ms/frame)

def _uart_log(msg):
    """Send a LOG: line to Qt with a small post-write pacing delay.
    EC800M UART2 TX FIFO is small; back-to-back writes from the main thread
    can lose trailing bytes (including the \\n), causing Qt to merge two
    distinct log lines into one. Sleeping ~5ms after each write lets the
    FIFO drain at 115200 (~88us/byte; 50-byte msg = ~4.4ms)."""
    try:
        uart.write(("LOG:" + msg + "\n").encode("utf-8"))
        utime.sleep_ms(5)
    except Exception:
        pass
    print("[EC800M]", msg)

def _pcm_worker():
    """Background thread: blocking-read 640-byte (20ms) frames from PCM.
    Auto-stops when (a) buffer hits MAX_REC_BYTES or (b) VAD detects speech
    followed by VAD_SILENCE_FRAMES of silence."""
    global _rec_buf, _worker_alive, _recording, _pcm, _vad_pending
    _worker_alive = True
    iters = 0
    total = 0
    speech_started = False
    silent_frames = 0
    sess = _asr_session   # snapshot — main thread may null _asr_session in do_asr_and_send
    while _recording:
        try:
            chunk = _pcm.read(640)
        except Exception as e:
            _uart_log("pcm read err: %s" % e)
            break
        if chunk and chunk != -1:
            _rec_buf += chunk
            total += len(chunk)
            # stream this frame to Paraformer WS if open
            if sess is not None and sess.alive and not sess.error:
                try:
                    sess.send_audio(bytes(chunk))
                except Exception as e:
                    _uart_log("ws send err: %s" % e)
                    sess.error = str(e)
            # decimated peak — sample every 4th to keep it cheap (~80 iters/frame)
            peak = 0
            i = 0
            n = len(chunk)
            while i < n - 1:
                lo = chunk[i]
                hi = chunk[i + 1]
                v = lo | (hi << 8)
                if v >= 0x8000:
                    v -= 0x10000
                av = v if v >= 0 else -v
                if av > peak:
                    peak = av
                    if peak >= VAD_THRESHOLD:
                        break
                i += 8
            if peak >= VAD_THRESHOLD:
                speech_started = True
                silent_frames = 0
            elif speech_started:
                silent_frames += 1
                if silent_frames >= VAD_SILENCE_FRAMES:
                    _uart_log("vad: %d silent frames after speech, auto-stop @ %dB" % (
                        silent_frames, total))
                    _recording = False
                    _vad_pending = True
                    try:
                        if _pcm is not None:
                            _pcm.close()
                            _pcm = None
                    except Exception as e:
                        _uart_log("pcm close-on-vad err: %s" % e)
                    break
        iters += 1
        # safety cap: if UI never sends STOP and VAD never fires, force-stop at 12s.
        if total >= MAX_REC_BYTES:
            _uart_log("pcm cap reached @ %d bytes - auto stop" % total)
            _recording = False
            try:
                if _pcm is not None:
                    _pcm.close()
                    _pcm = None
            except Exception as e:
                _uart_log("pcm close-on-cap err: %s" % e)
            try: uart.write(b"RECORD:CAP\n")
            except Exception: pass
            break
        if iters % 50 == 0:
            _uart_log("pcm iter=%d total=%d rec=%s" % (iters, total, _recording))
    _worker_alive = False
    _uart_log("pcm worker exit iters=%d total=%d" % (iters, total))

def record_start():
    """Start 16kHz PCM recording into in-memory buffer."""
    global _pcm, _rec_buf, _rec_len, _recording, _asr_session
    if _PCM_CLS is None:
        _uart_log("no PCM class")
        return False
    if _recording:
        _uart_log("already recording")
        return False
    _rec_buf = bytearray()
    _rec_len = 0
    try:
        _pcm = _PCM_CLS(PCM_DEVICE, _PCM_MONO, ASR_RATE, _PCM_RO, _PCM_BLOCK)
        _uart_log("PCM init OK dev=%d rate=%d" % (PCM_DEVICE, ASR_RATE))
    except Exception as e:
        _uart_log("PCM init err: %s" % e)
        _pcm = None
        return False
    # open Paraformer streaming WS (non-blocking; handshake runs in background.
    # PCM frames are queued by send_audio() until task-started, then flushed.)
    _asr_session = _ParaformerSession()
    if not _asr_session.start():
        _uart_log("paraformer start failed: %s; will fall back to baidu" % _asr_session.error)
        _asr_session = None
    else:
        _uart_log("paraformer ws spawning tid=%s" % _asr_session.task_id[:8])
    _recording = True
    try:
        _thread.start_new_thread(_pcm_worker, ())
    except Exception as e:
        _uart_log("thread err: %s" % e)
        _recording = False
        try: _pcm.close()
        except: pass
        _pcm = None
        return False
    _uart_log("recording 16k PCM...")
    uart.write(b"RECORD:READY\n")
    return True

def record_stop():
    """Stop recording. PCM stays in _rec_buf — no disk write (saves /usr space).
    Tolerates the case where the worker already auto-stopped (cap reached) and
    cleans up _pcm regardless of _recording flag."""
    global _recording, _pcm
    _recording = False
    # let blocking read return and worker exit
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
    sz = len(_rec_buf)
    _uart_log("rec done size=%d (%.2fs) - kept in RAM" % (sz, sz / (ASR_RATE * 2.0)))
    return sz

def asr_recognize(path):
    """POST in-memory PCM (_rec_buf) to Baidu ASR using "raw audio" mode.
    URL carries params; body is binary PCM directly. No base64, no JSON —
    avoids ~3x memory blowup that otherwise OOMs on 5+s clips.
    `path` arg kept for ABI; ignored."""
    tok = get_token()
    if not tok:
        _uart_log("asr no token")
        return ""
    # _rec_len is the trimmed logical length set by _trim_trailing_silence;
    # fall back to full buffer if trim never ran.
    pcm_len = _rec_len if _rec_len > 0 else len(_rec_buf)
    _uart_log("asr buf bytes=%d (raw=%d)" % (pcm_len, len(_rec_buf)))
    if pcm_len < 16000:   # 0.5s of 16kHz 16-bit PCM
        _uart_log("asr too short")
        return ""

    q = ("?cuid=ec800m&token=%s&dev_pid=%d"
         % (tok, ASR_DEV_PID))
    url_path = ASR_URL_PATH + q
    ctype = "audio/pcm;rate=%d" % ASR_RATE

    try:
        addr = usocket.getaddrinfo(ASR_URL_HOST, 443)[0][-1]
        s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
        s.settimeout(30)
        s.connect(addr)
        s = ussl.wrap_socket(s, server_hostname=ASR_URL_HOST)
        req = ("POST %s HTTP/1.1\r\n"
               "Host: %s\r\n"
               "Content-Type: %s\r\n"
               "Content-Length: %d\r\n"
               "Connection: close\r\n"
               "\r\n") % (url_path, ASR_URL_HOST, ctype, pcm_len)
        s.write(req.encode("utf-8"))
        # stream PCM directly from _rec_buf — no copy, no base64, no JSON.
        sent = 0
        view = memoryview(_rec_buf)
        while sent < pcm_len:
            n = s.write(view[sent:sent + 4096])
            if not n:
                break
            sent += n
        # read response headers
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
            try: s.close()
            except: pass
            return ""
        head_bytes = buf[:sep]
        body_so_far = buf[sep + 4:]
        while True:
            chunk = s.read(2048)
            if not chunk:
                break
            body_so_far += chunk
        try: s.close()
        except: pass
    except Exception as e:
        _uart_log("asr socket err: %s" % e)
        return ""

    # parse headers to detect chunked transfer
    is_chunked = False
    for line in head_bytes.split(b"\r\n")[1:]:
        i = line.find(b":")
        if i > 0:
            k = line[:i].strip().lower()
            v = line[i+1:].strip().lower()
            if k == b"transfer-encoding" and b"chunked" in v:
                is_chunked = True
                break

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
            except Exception as e:
                _uart_log("chunk size parse err: %s" % e)
                break
            p = crlf + 2
            if size == 0:
                break
            if p + size > n:
                break
            decoded += body_so_far[p:p + size]
            p += size + 2
        body_so_far = bytes(decoded)

    _uart_log("asr resp len=%d head=%s" % (len(body_so_far), body_so_far[:80]))
    try:
        j = ujson.loads(body_so_far)
        if j.get("err_no", -1) != 0:
            _uart_log("asr err_no=%s msg=%s" % (j.get("err_no"), j.get("err_msg")))
            return ""
        result = j.get("result")
        if isinstance(result, list) and result:
            return result[0]
        return ""
    except Exception as e:
        _uart_log("asr json err: %s" % e)
        return ""

def _trim_trailing_silence(threshold=150, keep_min_ms=500):
    """Set _rec_len to exclude trailing silence — does NOT shrink _rec_buf
    (a slice copy on a 500KB buffer would OOM the EC800M). PCM is 16-bit
    signed LE @ 16kHz. Walks backwards in 20ms frames; stops at first frame
    whose peak abs sample >= threshold. Never trims below keep_min_ms.

    threshold=150 (lowered from 400) — earlier value was clipping the soft
    tail of normal-voice English sentences (last consonants / breath), which
    Baidu's short-utterance ASR then cut the recognition short on. Lower
    threshold = only trims true silence at the price of a tiny bit more
    audio sent to ASR (cheap)."""
    global _rec_len
    n = len(_rec_buf)
    _rec_len = n
    frame_bytes = 640                 # 20ms @ 16kHz mono 16-bit
    keep_min = keep_min_ms * 32       # 1ms = 32 bytes
    if n <= keep_min:
        return n
    end = n
    buf = _rec_buf
    while end >= keep_min + frame_bytes:
        start = end - frame_bytes
        peak = 0
        i = start
        while i < end:
            lo = buf[i]
            hi = buf[i + 1]
            v = lo | (hi << 8)
            if v >= 0x8000:
                v -= 0x10000
            av = v if v >= 0 else -v
            if av > peak:
                peak = av
                if peak >= threshold:
                    break
            i += 2
        if peak >= threshold:
            break
        end -= frame_bytes
    _rec_len = end
    return _rec_len


def do_asr_and_send():
    global _rec_buf, _rec_len, _asr_session
    try:
        t0 = utime.ticks_ms()
        sz = record_stop()
        t1 = utime.ticks_ms()
        if sz <= 0:
            # also tear down any half-open WS
            if _asr_session is not None:
                try: _asr_session.finish(wait_ms=100)
                except Exception: pass
                _asr_session = None
            uart.write(b"ASR:ERR\n")
            return
        # Path A: Paraformer streaming finish
        text = ""
        sess = _asr_session
        _asr_session = None
        t_pf = 0
        if sess is not None:
            t_pf0 = utime.ticks_ms()
            text = sess.finish(wait_ms=1500) or ""
            t_pf = utime.ticks_diff(utime.ticks_ms(), t_pf0)
            _uart_log("paraformer finish=%dms err=%s text=%r" % (
                t_pf, sess.error, text))
        # Path B: fallback to Baidu HTTP ASR
        if not text:
            sz_after = _trim_trailing_silence()
            t2 = utime.ticks_ms()
            text = asr_recognize(TMP_REC) or ""
            t3 = utime.ticks_ms()
            _uart_log("fallback baidu trim=%d->%d asr=%dms" % (
                sz, sz_after, utime.ticks_diff(t3, t2)))
        t_end = utime.ticks_ms()
        _uart_log("timing stop=%dms paraformer=%dms total=%dms" % (
            utime.ticks_diff(t1, t0), t_pf,
            utime.ticks_diff(t_end, t0)))
        if text:
            line = "USER:%s\n" % text
            print("[EC800M] ASR ->", text)
            uart.write(line.encode("utf-8"))
        else:
            uart.write(b"ASR:ERR\n")
    except Exception as e:
        print("[EC800M] asr fatal:", e)
        try: uart.write(b"ASR:ERR\n")
        except Exception: pass
    finally:
        # always consume the buffer — duplicate STOP (after VAD or on retry)
        # must not re-process the same audio
        _rec_buf = bytearray()
        _rec_len = 0

def paraformer_smoketest():
    """Open WS, send 1s of silence as PCM, send finish, print events.
    Run via UART command "MODE:WS_TEST" to verify handshake before wiring
    into the recording path."""
    _uart_log("paraformer smoketest start")
    sess = _ParaformerSession()
    t0 = utime.ticks_ms()
    if not sess.start():
        _uart_log("smoketest start failed: %s" % sess.error)
        return
    _uart_log("smoketest task-started in %dms tid=%s" % (
        utime.ticks_diff(utime.ticks_ms(), t0), sess.task_id[:8]))
    # send 50 frames of 20ms silence (~1s of 16kHz 16-bit mono)
    silence = bytes(640)
    for _ in range(50):
        sess.send_audio(silence)
        utime.sleep_ms(20)
    final = sess.finish(wait_ms=3000)
    _uart_log("smoketest finish err=%s text=%r" % (sess.error, final))

# ---- 协议解析 ----
last_word_en = ""
last_word_cn = ""

def handle_line(line):
    global last_word_en, last_word_cn
    line = line.strip()
    if not line:
        return
    print("[EC800M] RX:", line)

    if line.startswith("SPEAK:"):
        text = line[6:].strip()
        if text:
            speak(text, "en")

    elif line.startswith("WORD:"):
        # WORD:apple:苹果
        body = line[5:]
        parts = body.split(":", 1)
        last_word_en = parts[0].strip()
        last_word_cn = parts[1].strip() if len(parts) > 1 else ""
        print("[EC800M] WORD locked:", last_word_en, "/", last_word_cn)

    elif line.startswith("RECORD:START"):
        record_start()

    elif line.startswith("RECORD:STOP"):
        do_asr_and_send()

    elif line.startswith("MODE:"):
        mode = line[5:].strip()
        print("[EC800M] MODE:", mode)
        if mode == "WS_TEST":
            paraformer_smoketest()

    else:
        print("[EC800M] unknown:", line)

# ---- 主循环 ----
def main_loop():
    global _vad_pending
    buf = b""
    # purge stale recording/TTS temp files in /usr to free flash space
    try:
        for fn in uos.listdir('/usr'):
            ext_match = (fn.endswith('.amr') or fn.endswith('.wav')
                         or fn.endswith('.pcm') or fn.endswith('.mp3'))
            if ext_match and not fn.startswith('test'):
                try: uos.remove('/usr/' + fn)
                except Exception: pass
        try:
            free = uos.statvfs('/usr')
            print("[EC800M] /usr after cleanup:", free)
        except Exception:
            pass
    except Exception as e:
        print("[EC800M] cleanup err:", e)
    print("[EC800M] english_tutor companion ready")
    while True:
        if _vad_pending:
            _vad_pending = False
            try: uart.write(b"RECORD:VAD\n")
            except Exception: pass
            do_asr_and_send()
        n = uart.any()
        if n > 0:
            data = uart.read(n)
            if data:
                buf += data
                while b"\n" in buf:
                    idx = buf.find(b"\n")
                    raw = buf[:idx]
                    buf = buf[idx+1:]
                    try:
                        handle_line(raw.decode("utf-8"))
                    except Exception as e:
                        print("[EC800M] handle err:", e)
        utime.sleep_ms(20)

main_loop()
