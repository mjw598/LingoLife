请基于我当前的自建 xiaozhi / tutor 体系，为 EC800M 的 tutor/chat 模式新增一个 **服务器端 TTS HTTP 接口**。注意：

- **不要改坏现有 xiaozhi assistant websocket 语音链路**
- assistant 模式继续走当前 OTA + `/xiaozhi/v1/` websocket + 服务端流式 TTS 回传
- 这次新增的是给 **EC800M tutor/chat 模式** 用的一个独立 HTTP TTS 接口

# 目标
EC800M tutor/chat 模式收到：
- `SPEAK:<text>`
- `TTS:<text>`

时，不再直接调用云 TTS，而是：
1. 向我的服务器发 HTTPS POST 请求
2. 服务器端调用 EdgeTTS（或我指定的服务端 TTS 引擎）
3. 服务器直接返回 MP3 二进制音频
4. EC800M 保存到本地并播放

# 请你实现的服务端能力

## 1. 新增 HTTP 接口
推荐新增其中一个接口：
- `POST /api/ec800m/tts`

如果你更想做成 OpenAI 兼容风格，也可以：
- `POST /v1/audio/speech`

但无论路径是什么，要求都一样：
- **同步返回音频二进制**
- 不要让设备先拿 JSON 再二次下载
- 尽量不要依赖复杂轮询机制

## 2. 请求体格式
接口接受 JSON，请至少支持这些字段：

```json
{
  "text": "How are you today?",
  "lang": "en",
  "voice": "en-US-AvaMultilingualNeural",
  "format": "mp3",
  "sample_rate": 16000,
  "purpose": "tutor_chat"
}
```

字段要求：
- `text`：必填
- `lang`：可选，支持 `en` / `zh` / `mixed`
- `voice`：可选
- `format`：默认 `mp3`
- `sample_rate`：默认 `16000`
- `purpose`：可选，支持：
  - `word`
  - `sentence`
  - `tutor_chat`

## 3. 响应格式
成功时要求：
- HTTP 200
- `Content-Type: audio/mpeg`
- body 直接返回 MP3 字节流

不要返回 JSON 包音频 URL。
设备端是资源受限客户端，最适合直接拿二进制 body。

## 4. 失败时要求
失败时返回：
- 合适的 4xx / 5xx HTTP 状态码
- JSON 错误信息，例如：

```json
{
  "error": "tts_failed",
  "message": "reason here"
}
```

## 5. TTS 后端要求
服务器端内部请接入 EdgeTTS（或我指定的服务端 TTS 引擎），但注意：
- **EdgeTTS 调用只发生在服务器端**
- EC800M 不直接碰 EdgeTTS
- 尽量降低短句延迟
- 对 tutor 单词发音和完整句子可做不同 voice/style 策略

建议策略：
- `purpose = word`：更慢、更清晰
- `purpose = sentence`：自然但稍慢
- `purpose = tutor_chat`：更自然、偏对话

## 6. 输入控制与健壮性
请补上：
- 文本长度上限
- 非法输入拦截
- 超时控制
- TTS 失败日志
- 基本鉴权（如果我配置了 API key）

如果请求头带：
- `Authorization: Bearer <token>`

则在服务端校验它；如果我没配置 token，可允许关闭鉴权。

## 7. 与现有 xiaozhi-server 的关系
请尽量让这个接口设计兼容现有 `xiaozhi-server` 的 TTS provider 思路：
- 最好兼容 `CustomTTS` 或 `OpenAITTS` 风格
- 但本轮不要改坏现有 websocket assistant 流程

也就是说：
- **assistant 继续保持原状**
- **新增 tutor 专用 HTTP TTS 接口**

## 8. 输出内容
请输出：
1. 服务端修改的代码
2. 新增/修改的配置项说明
3. 如何本地测试这个接口
4. curl 示例
5. 返回 MP3 的完整行为说明

## 9. 额外建议
如果实现成本不高，请顺手加：
- `health` 检查接口
- 简单的 TTS 请求日志
- 清晰的错误日志

目标是让 EC800M tutor/chat 模式后续只需要：
- POST 文本
- 收到 MP3
- 本地播放

即可工作。
