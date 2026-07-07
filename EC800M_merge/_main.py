"""
Merged EC800M runtime for tutor/chat + xiaozhi assistant.
Base: xiaozhi_demo assistant runtime.
Added: tutor/chat UART mode with server-backed TTS and legacy ASR callbacks.
"""
import utime
from machine import ExtInt, Pin, UART
from usr.protocol import WebSocketClient
from usr.utils import ChargeManager, AudioManager, NetManager, TaskManager
from usr.threading import Thread, Event, Condition
from usr.logging import getLogger, BasicConfig
import ujson as json
import ubinascii
from usr import tutor_mode


BasicConfig.update(debug=False, level="INFO")
logger = getLogger(__name__)


class Led(object):

    def __init__(self, GPIOn):
        self.__led = Pin(
            getattr(Pin, 'GPIO{}'.format(GPIOn)),
            Pin.OUT,
            Pin.PULL_PD,
            0
        )
        self.__off_period = 1000
        self.__on_period = 1000
        self.__count = 0
        self.__running_cond = Condition()
        self.__blink_thread = None
        self.off()

    @property
    def status(self):
        with self.__running_cond:
            return self.__led.read()

    def on(self):
        with self.__running_cond:
            self.__count = 0
            return self.__led.write(1)

    def off(self):
        with self.__running_cond:
            self.__count = 0
            return self.__led.write(0)

    def blink(self, on_period=50, off_period=50, count=None):
        if not isinstance(count, (int, type(None))):
            raise TypeError('count must be int or None type')
        with self.__running_cond:
            if self.__blink_thread is None:
                self.__blink_thread = Thread(target=self.__blink_thread_worker)
                self.__blink_thread.start()
            self.__on_period = on_period
            self.__off_period = off_period
            self.__count = count
            self.__running_cond.notify_all()

    def __blink_thread_worker(self):
        while True:
            with self.__running_cond:
                if self.__count is not None:
                    self.__running_cond.wait_for(lambda: self.__count is None or self.__count > 0)
                status = self.__led.read()
                self.__led.write(1 - status)
                utime.sleep_ms(self.__on_period if status else self.__off_period)
                self.__led.write(status)
                utime.sleep_ms(self.__on_period if status else self.__off_period)
                if self.__count is not None:
                    self.__count -= 1


class Application(object):
    UART_PORT = 2
    UART_BAUD = 115200
    MODE_IDLE = "IDLE"
    MODE_ASSISTANT = "ASSISTANT"
    MODE_TUTOR = "TUTOR"
    MODE_CHAT = "CHAT"
    SOURCE_GPIO = "gpio"
    SOURCE_UART = "uart"
    def __init__(self):
        self.gpio27 = Pin(Pin.GPIO27, Pin.OUT, Pin.PULL_DISABLE, 1)
        self.talk_key = ExtInt(ExtInt.GPIO27, ExtInt.IRQ_RISING_FALLING, ExtInt.PULL_PU, self.on_talk_key_click, 50)
        self.chat_led = Led(29)
        self.charge_manager = ChargeManager()
        self.audio_manager = AudioManager()
        self.audio_manager.set_kws_cb(self.on_keyword_spotting)
        self.audio_manager.set_vad_cb(self.on_voice_activity_detection)
        self.net_manager = NetManager()
        self.task_manager = TaskManager()
        self.__protocol = None
        self.__reset_protocol()
        self.__working_thread = None
        self.__record_thread = None
        self.__record_thread_stop_event = Event()
        self.__voice_activity_event = Event()
        self.__keyword_spotting_event = Event()
        self.__mode = self.MODE_IDLE
        self.__record_source = None
        self.__uart_recording = False
        self.__uart = None
        self.__uart_thread = None
        self.__uart_buffer = b""
        self.__last_stt_text = None
        self.__last_ai_text = None
        self.__audio_error_count = 0
        self.__uart_record_start_ms = 0
        self.__assistant_ready = False
        self.__init_uart()

    def __reset_protocol(self):
        old_protocol = self.__protocol
        if old_protocol is not None:
            try:
                old_protocol.disconnect()
            except Exception:
                pass
        self.__protocol = WebSocketClient()
        self.__protocol.set_callback(
            audio_message_handler=self.on_audio_message,
            json_message_handler=self.on_json_message
        )

    def __init_uart(self):
        try:
            self.__uart = UART(self.UART_PORT, self.UART_BAUD, 8, 0, 1, 0)
            logger.info("UART{} ready @ {}".format(self.UART_PORT, self.UART_BAUD))
            tutor_mode.init(self.__uart, self.gpio27)
            self.__uart.write(b"EC_READY\n")
            logger.info("UART{} sent EC_READY".format(self.UART_PORT))
        except Exception as e:
            logger.error("init uart failed: {}".format(repr(e)))
            self.__uart = None

    @staticmethod
    def __message_dict(msg):
        return getattr(msg, "kwargs", msg)

    def __message_value(self, msg, key, default=None):
        data = self.__message_dict(msg)
        if not isinstance(data, dict):
            return default
        if key == "text":
            value_b64 = data.get("text_b64")
            if value_b64 is not None:
                try:
                    raw = ubinascii.a2b_base64(value_b64)
                    return raw.decode("utf-8", "ignore")
                except Exception as e:
                    logger.error("decode text_b64 failed: {}".format(repr(e)))
                    return "[text_b64 decode failed]"
        value = data.get(key)
        if value is not None:
            return value
        payload = data.get("payload")
        if isinstance(payload, dict):
            if key == "text":
                value_b64 = payload.get("text_b64")
                if value_b64 is not None:
                    try:
                        raw = ubinascii.a2b_base64(value_b64)
                        return raw.decode("utf-8", "ignore")
                    except Exception as e:
                        logger.error("decode payload text_b64 failed: {}".format(repr(e)))
                        return "[text_b64 decode failed]"
            value = payload.get(key)
            if value is not None:
                return value
        return default

    @staticmethod
    def __sanitize_uart_text(text):
        if text is None:
            return ""
        text = str(text).replace("\r", " ").replace("\n", " ").strip()
        while "  " in text:
            text = text.replace("  ", " ")
        return text

    def __uart_send(self, prefix, text=None):
        if self.__uart is None:
            return
        body = self.__sanitize_uart_text(text)
        if body != "" and prefix in ("ASSIST_USER", "ASSIST_AI", "ASSIST_ERR"):
            try:
                b64 = ubinascii.b2a_base64(body.encode("utf-8")).decode("ascii").strip()
                line = "{}_B64:{}".format(prefix, b64)
            except Exception as e:
                logger.error("uart b64 encode failed: {}".format(repr(e)))
                line = "{}:{}".format(prefix, body)
        else:
            line = prefix if body == "" else "{}:{}".format(prefix, body)
        try:
            self.__uart.write((line + "\n").encode("utf-8"))
        except Exception as e:
            logger.error("uart write failed: {}".format(repr(e)))

    def __notify_state(self, state):
        self.__uart_send("ASSIST_STATE", state)

    def __ensure_working_thread_started(self):
        if self.__working_thread is not None and self.__working_thread.is_running():
            return
        self.__working_thread = Thread(target=self.__working_thread_handler)
        self.__working_thread.start()

    def __start_uart_thread(self):
        if self.__uart is None:
            logger.error("uart thread not started: uart is None")
            return
        if self.__uart_thread is not None and self.__uart_thread.is_running():
            logger.info("uart thread already running")
            return
        self.__uart_thread = Thread(target=self.__uart_thread_handler)
        self.__uart_thread.start(stack_size=64)
        logger.info("uart thread started")

    def __stop_assistant_activity(self):
        self.__assistant_ready = False
        self.__uart_recording = False
        self.__record_source = None
        self.__voice_activity_event.clear()
        self.chat_led.off()
        try:
            self.__protocol.abort(reason="mode_exit")
        except Exception:
            pass
        try:
            self.audio_manager.stop()
        except Exception:
            pass
        try:
            self.audio_manager.close_opus()
        except Exception:
            pass

    def __set_mode(self, mode):
        mode = self.__sanitize_uart_text(mode).upper()
        if mode == self.MODE_ASSISTANT:
            was_assistant = self.__mode == self.MODE_ASSISTANT
            if not was_assistant and self.__working_thread is not None and self.__working_thread.is_running():
                try:
                    self.__working_thread.join()
                except Exception:
                    pass
            self.__mode = self.MODE_ASSISTANT
            self.__assistant_ready = False
            if not was_assistant:
                self.__reset_protocol()
            tutor_mode.stop_recording_if_needed()
            try:
                self.audio_manager.open_opus()
            except Exception as e:
                logger.error("assistant mode open opus failed: {}".format(repr(e)))
            self.__notify_state("connecting")
            self.__record_source = None
            self.__ensure_working_thread_started()
            logger.info("assistant mode enabled")
            return
        if mode == self.MODE_TUTOR or mode == self.MODE_CHAT:
            self.__mode = self.MODE_TUTOR
            self.__stop_assistant_activity()
            tutor_mode.stop_recording_if_needed()
            logger.info("tutor mode enabled")
            return
        if mode == self.MODE_IDLE:
            self.__mode = self.MODE_IDLE
            self.__stop_assistant_activity()
            tutor_mode.stop_recording_if_needed()
            self.__notify_state("idle")
            logger.info("all modes disabled")

    def __start_assistant_recording(self):
        if self.__mode != self.MODE_ASSISTANT:
            return
        if not self.__assistant_ready:
            self.__notify_state("reconnecting")
            return
        if self.__uart_recording:
            return
        try:
            self.audio_manager.open_opus()
        except Exception as e:
            logger.error("assistant record open opus failed: {}".format(repr(e)))
            self.__uart_send("ASSIST_ERR", "audio input failed")
            self.__notify_state("idle")
            return
        self.__uart_recording = True
        self.__record_source = self.SOURCE_UART
        self.__last_stt_text = None
        self.__last_ai_text = None
        self.__audio_error_count = 0
        self.__uart_record_start_ms = utime.ticks_ms()
        self.chat_led.on()
        self.__notify_state("listening")
        self.__voice_activity_event.set()
        self.__ensure_working_thread_started()

    def __stop_assistant_recording(self):
        if self.__mode != self.MODE_ASSISTANT:
            return
        if not self.__uart_recording:
            return
        try:
            elapsed = utime.ticks_diff(utime.ticks_ms(), self.__uart_record_start_ms)
        except Exception:
            elapsed = 800
        if elapsed < 800:
            logger.info("ignore uart record stop too soon: {} ms".format(elapsed))
            return
        self.__uart_recording = False
        self.__voice_activity_event.clear()
        self.chat_led.off()
        self.__notify_state("recognizing")

    def __handle_tutor_line(self, line):
        if line.startswith("MODE:"):
            mode = line[5:].strip().upper()
            if mode == self.MODE_CHAT or mode == self.MODE_TUTOR:
                self.__set_mode(self.MODE_TUTOR)
                return True
        if self.__mode != self.MODE_TUTOR:
            return False
        if line.startswith("SPEAK:") or line.startswith("TTS:") or line.startswith("WORD:"):
            tutor_mode.handle_line(line)
            return True
        if line.startswith("RECORD:START"):
            try:
                self.audio_manager.close_opus()
            except Exception as e:
                logger.error("record start close opus failed: {}".format(repr(e)))
            tutor_mode.handle_line(line)
            return True
        if line == "RECORD:STOP":
            tutor_mode.handle_line(line)
            return True
        return False

    def __handle_uart_line(self, line):
        line = self.__sanitize_uart_text(line)
        if not line:
            return
        logger.debug("uart rx: {}".format(line))
        if line == "MODE:ASSISTANT":
            self.__set_mode(self.MODE_ASSISTANT)
        elif line == "MODE:IDLE":
            self.__set_mode(self.MODE_IDLE)
        elif line == "RECORD:START":
            if self.__mode == self.MODE_ASSISTANT:
                self.__start_assistant_recording()
            else:
                self.__handle_tutor_line(line)
        elif line == "RECORD:STOP":
            if self.__mode == self.MODE_ASSISTANT:
                self.__stop_assistant_recording()
            else:
                self.__handle_tutor_line(line)
        elif self.__handle_tutor_line(line):
            pass
        else:
            logger.info("ignore uart line: {}".format(line))

    def __uart_thread_handler(self):
        logger.info("uart thread enter")
        idle_ticks = 0
        while True:
            try:
                tutor_mode.poll_vad()
                n = self.__uart.any()
                if n > 0:
                    data = self.__uart.read(n)
                    if data:
                        logger.debug("uart read bytes={}".format(len(data)))
                        self.__uart_buffer += data
                        while b"\n" in self.__uart_buffer:
                            idx = self.__uart_buffer.find(b"\n")
                            raw = self.__uart_buffer[:idx]
                            self.__uart_buffer = self.__uart_buffer[idx + 1:]
                            try:
                                self.__handle_uart_line(raw.decode("utf-8"))
                            except Exception as e:
                                logger.error("handle uart line failed: {}".format(repr(e)))
                        idle_ticks = 0
                else:
                    idle_ticks += 1
                    if idle_ticks % 500 == 0:
                        logger.debug("uart idle ticks={}".format(idle_ticks))
                utime.sleep_ms(20)
            except Exception as e:
                logger.error("uart thread failed: {}".format(repr(e)))
                utime.sleep_ms(100)

    def __record_thread_handler(self):
        logger.debug("record thread handler enter")
        while not self.__record_thread_stop_event.is_set():
            self.audio_manager.opus_read()
            utime.sleep_ms(5)
        logger.debug("record thread handler exit")

    def start_kws(self):
        self.audio_manager.start_kws()
        self.__record_thread_stop_event.clear()
        self.__record_thread = Thread(target=self.__record_thread_handler)
        self.__record_thread.start(stack_size=64)

    def stop_kws(self):
        self.__record_thread_stop_event.set()
        self.__record_thread.join()
        self.audio_manager.stop_kws()

    def start_vad(self):
        self.audio_manager.start_vad()

    def stop_vad(self):
        self.audio_manager.stop_vad()

    def __working_thread_handler(self):
        t = Thread(target=self.__chat_process)
        t.start(stack_size=64)
        t.join()

    def __chat_process(self):
        logger.debug("chat process enter.")
        self.charge_manager.enable_charge()
        reconnect_delay_ms = 1000
        try:
            while self.__mode == self.MODE_ASSISTANT:
                is_listen_flag = False
                self.__assistant_ready = False
                self.__notify_state("reconnecting")
                if not self.net_manager.wait_network_ready(max_attempts=3):
                    utime.sleep_ms(reconnect_delay_ms)
                    reconnect_delay_ms = min(reconnect_delay_ms * 2, 15000)
                    continue
                try:
                    with self.__protocol:
                        resp = self.__protocol.hello()
                        if resp is None:
                            raise RuntimeError("hello timeout")
                        self.__assistant_ready = True
                        reconnect_delay_ms = 1000
                        self.__notify_state("idle")
                        last_keepalive_ms = utime.ticks_ms()
                        if self.__record_source != self.SOURCE_UART:
                            self.__protocol.start_assistant_greeting()
                        while self.__mode == self.MODE_ASSISTANT:
                            if self.__voice_activity_event.is_set():
                                data = self.audio_manager.opus_read()
                                if not is_listen_flag:
                                    self.__protocol.abort()
                                    listen_mode = "manual" if self.__record_source == self.SOURCE_UART else "auto"
                                    self.__protocol.listen("start", listen_mode)
                                    is_listen_flag = True
                                self.__protocol.send(data)
                                last_keepalive_ms = utime.ticks_ms()
                            else:
                                if is_listen_flag:
                                    self.__protocol.listen("stop")
                                    is_listen_flag = False
                                    last_keepalive_ms = utime.ticks_ms()
                                elif utime.ticks_diff(utime.ticks_ms(), last_keepalive_ms) >= 540000:
                                    self.__protocol.ping()
                                    last_keepalive_ms = utime.ticks_ms()
                            if not self.__protocol.is_state_ok():
                                raise RuntimeError("websocket state not ok")
                            utime.sleep_ms(1)
                except Exception as e:
                    logger.debug("assistant connection loop got Exception: {}".format(repr(e)))
                finally:
                    self.__assistant_ready = False
                    self.__voice_activity_event.clear()
                    self.__uart_recording = False
                    self.__record_source = None
                    self.chat_led.off()
                if self.__mode == self.MODE_ASSISTANT:
                    self.__notify_state("reconnecting")
                    utime.sleep_ms(reconnect_delay_ms)
                    reconnect_delay_ms = min(reconnect_delay_ms * 2, 15000)
        finally:
            self.__assistant_ready = False
            self.__voice_activity_event.clear()
            self.__uart_recording = False
            self.__record_source = None
            self.chat_led.off()
            if self.__mode == self.MODE_ASSISTANT:
                self.__notify_state("idle")
            self.charge_manager.disable_charge()
            logger.debug("chat process exit.")
        return
        is_listen_flag = False
        try:
            with self.__protocol:
                self.__protocol.hello()
                if self.__record_source != self.SOURCE_UART:
                    self.__protocol.start_assistant_greeting()
                while True:
                    if self.__mode != self.MODE_ASSISTANT:
                        if is_listen_flag:
                            self.__protocol.listen("stop")
                            is_listen_flag = False
                        break
                    if self.__voice_activity_event.is_set():
                        data = self.audio_manager.opus_read()
                        if not is_listen_flag:
                            self.__protocol.abort()
                            listen_mode = "manual" if self.__record_source == self.SOURCE_UART else "auto"
                            self.__protocol.listen("start", listen_mode)
                            is_listen_flag = True
                        self.__protocol.send(data)
                    else:
                        if is_listen_flag:
                            self.__protocol.listen("stop")
                            is_listen_flag = False
                    if not self.__protocol.is_state_ok():
                        break
                    utime.sleep_ms(1)
        except Exception as e:
            logger.debug("working thread handler got Exception: {}".format(repr(e)))
        finally:
            self.__voice_activity_event.clear()
            self.__uart_recording = False
            self.__record_source = None
            self.chat_led.off()
            if self.__mode == self.MODE_ASSISTANT:
                self.__notify_state("idle")
        self.charge_manager.disable_charge()
        logger.debug("chat process exit.")

    def on_talk_key_click(self, args):
        args[1] = self.gpio27.read()
        logger.info("on_talk_key_click: {}".format(args))
        if self.__mode == self.MODE_TUTOR or self.__mode == self.MODE_ASSISTANT:
            return
        if args[1] == 0:
            self.__record_source = self.SOURCE_GPIO
            self.chat_led.on()
            self.__voice_activity_event.set()
        else:
            if self.__record_source == self.SOURCE_GPIO:
                self.chat_led.off()
                self.__voice_activity_event.clear()
                self.__record_source = None
        self.__ensure_working_thread_started()

    def on_keyword_spotting(self, state):
        if self.__mode == self.MODE_ASSISTANT or self.__mode == self.MODE_TUTOR:
            return
        logger.info("on_keyword_spotting: {}".format(state))
        if state[0] == 0:
            if self.__working_thread is not None and self.__working_thread.is_running():
                return
            self.__working_thread = Thread(target=self.__working_thread_handler)
            self.__working_thread.start()
            self.__keyword_spotting_event.clear()
        else:
            self.__keyword_spotting_event.set()

    def on_voice_activity_detection(self, state):
        if self.__mode == self.MODE_ASSISTANT and self.__record_source == self.SOURCE_UART:
            return
        if self.__mode == self.MODE_TUTOR:
            return
        logger.info("on_voice_activity_detection: {}".format(state))
        if state == 1:
            self.__voice_activity_event.set()
        else:
            self.__voice_activity_event.clear()

    def on_audio_message(self, raw):
        if self.__mode != self.MODE_ASSISTANT:
            return
        try:
            self.audio_manager.opus_write(raw)
            self.__audio_error_count = 0
        except Exception as e:
            self.__audio_error_count += 1
            logger.error("assistant audio write failed: {}".format(repr(e)))
            if self.__audio_error_count >= 3:
                self.__notify_state("idle")
                self.__uart_send("ASSIST_ERR", "audio playback failed")
                try:
                    self.audio_manager.close_opus()
                except Exception:
                    pass

    def on_json_message(self, msg):
        return getattr(self, "handle_{}_message".format(msg["type"]))(msg)

    def handle_stt_message(self, msg):
        logger.debug("handle_stt_message: {}".format(msg))
        text = self.__message_value(msg, "text", "")
        text = self.__sanitize_uart_text(text)
        if text and text != self.__last_stt_text:
            self.__last_stt_text = text
            self.__uart_send("ASSIST_USER", text)
            self.__notify_state("thinking")

    def handle_tts_message(self, msg):
        state = self.__message_value(msg, "state", "")
        text = self.__sanitize_uart_text(self.__message_value(msg, "text", ""))
        if state == "start":
            self.__uart_recording = False
            self.__record_source = None
            self.__voice_activity_event.clear()
            self.__audio_error_count = 0
            self.chat_led.blink(250, 250)
            self.__notify_state("speaking")
        elif state == "stop":
            self.chat_led.off()
            self.__notify_state("idle")
        elif state == "sentence_start" and text:
            if text != self.__last_ai_text:
                self.__last_ai_text = text
                self.__uart_send("ASSIST_AI", text)

    def handle_llm_message(self, msg):
        logger.debug("handle_llm_message: {}".format(msg))

    def handle_iot_message(self, msg):
        logger.debug("handle_iot_message: {}".format(msg))

    def handle_mcp_message(self, msg):
        data = msg.to_bytes()
        data_dict = json.loads(data)
        req_id = 1
        method = data_dict['payload']['method']
        if 'id' in data_dict['payload']:
            req_id = data_dict['payload']['id']
        if method == "initialize":
            self.__protocol.mcp_initialize()
        elif method == "tools/list":
            self.__protocol.mcp_tools_list()
        elif method == "tools/call":
            handle = data_dict['payload']['params']['name']
            if handle == "self.setvolume_down()":
                self.audio_manager.setvolume_down()
            elif handle == "self.setvolume_up()":
                self.audio_manager.setvolume_up()
            elif handle == "self.setvolume_close()":
                self.audio_manager.setvolume_close()
            elif handle == "self.setvolume()":
                arguments = data_dict['payload']["params"]["arguments"]["volume"]
                self.audio_manager.setvolume(arguments)
            elif handle == "self.new_name()":
                arguments = data_dict['payload']["params"]["arguments"]["name"]
                self.audio_manager.new_name(arguments)
            self.__protocol.mcp_tools_call(tool_name=handle, req_id=req_id)

    def run(self):
        self.charge_manager.enable_charge()
        self.audio_manager.open_opus()
        self.talk_key.enable()
        self.__start_uart_thread()


if __name__ == "__main__":
    app = Application()
    app.run()
