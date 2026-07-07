# xiaozhi_merge1

这是一个 **可回退** 的新 EC800M 融合工程，放在：

- `D:\QSM368\EC800M_Project\xiaozhi_merge1`

## 目标
在不修改原目录的前提下，把：
- `xiaozhi_demo` 的 assistant 模式
- `eng_tutor_ec800` 风格的 tutor/chat 串口协议能力

融合成一个新运行时。

## 当前设计
### Assistant 模式
保留 `xiaozhi_demo` 原有逻辑：
- `MODE:ASSISTANT`
- `RECORD:START`
- `RECORD:STOP`
- 回传：
  - `ASSIST_STATE:*`
  - `ASSIST_USER:*`
  - `ASSIST_AI:*`

### Tutor / Chat 模式
兼容 `quectel` 主程序原有调用：
- `MODE:CHAT`
- `SPEAK:*`
- `TTS:*`
- `WORD:*`
- `RECORD:START`
- `RECORD:STOP`

并回传：
- `USER:*`
- `ASR:ERR`
- `RECORD:READY`
- `RECORD:VAD`

## Tutor TTS 新策略
Tutor 模式下不再让 EC800M 直接调用 EdgeTTS。
而是：
- EC800M 请求用户自己的服务器 TTS 接口
- 服务器返回 MP3 音频字节
- EC800M 本地保存并播放

## 当前文件
- `_main.py`：融合入口
- `protocol.py`：沿用 xiaozhi websocket 协议层
- `config.py`：沿用基础配置
- `utils.py`：沿用基础工具
- `tutor_mode.py`：新增 tutor/chat 模式逻辑
- `SERVER_PROMPT.md`：给服务器端改造使用的 prompt

## 需要用户补充/确认
在 `tutor_mode.py` 中，需要按你的真实服务器配置填写：
- `SERVER_TTS_HOST`
- `SERVER_TTS_PATH`
- `SERVER_TTS_API_KEY`
- 以及 voice / sample rate 等参数

## 说明
首版仍保留旧 Baidu TTS / 本地 TTS fallback，避免服务器接口未就绪时完全无声。
