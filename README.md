[README.md](https://github.com/user-attachments/files/29746480/README.md)
# LingoLife

LingoLife 是一个面向嵌入式学习终端的 AI 英语学习项目。当前工程由两部分协同工作：

- `english_tutor`：运行在 QSM368/RK3568 主板上的 Qt/C++ 全屏应用，负责 UI、摄像头、视觉识别、单词学习、场景英语对话、学习统计、日报和宠物陪伴。
- `EC800M_merge`：运行在 EC800M 模块上的 QuecPython 语音运行时，负责录音、ASR/TTS、云端语音助手以及通过 UART 与 Qt 主程序通信。

项目不是一个单纯 demo，而是包含主应用、模型、板端部署脚本、EC800M 侧运行时和若干调试/备份文件的完整嵌入式应用工程。

## 功能概览

- 摄像头取景与单词/物体识别
- RKNN/YOLOv5 本地视觉推理
- DashScope 视觉理解与英语学习内容生成
- 单词卡片、发音、例句、单词本
- 场景英语会话练习，场景配置来自 `scenes.json`
- EC800M 语音输入输出，支持录音、TTS、ASR 回传
- 云端 Assistant 模式，兼容小智 WebSocket 协议
- 番茄钟/学习陪伴页面
- 宠物状态和学习激励反馈
- 学习时长、今日单词、日报生成和 Notion 更新入口

## 目录结构

```text
.
|-- *.cpp / *.h                 # Qt/C++ 主应用源码
|-- english_tutor.pro           # qmake 工程文件
|-- build.sh                    # 交叉编译、推送并生成板端运行脚本
|-- run.sh                      # 本地构建、推送资源并直接运行
|-- scenes.json                 # 场景英语对话配置
|-- model/
|   |-- yolov5s_qsm368zp.rknn   # RKNN 模型
|   `-- coco_80_labels_list.txt # YOLO 标签
|-- EC800M_merge/               # EC800M 融合运行时
|-- xiaozhi_demo/               # 原始/参考小智运行时
|-- EC800m/                     # EC800M 调试脚本
|-- english_tutor/              # 已生成的可执行文件目录
|-- _backup_2026-06-09_working/ # 历史备份
`-- boot*.img / parameter*.txt  # 板端镜像与参数文件
```

## 主应用模块

| 模块 | 文件 | 说明 |
| --- | --- | --- |
| 启动入口 | `main.cpp` | 设置 Qt 平台、字体、OpenGL，启动全屏 `MainWindow` |
| 主窗口/流程 | `mainwindow.*` | 页面导航、状态调度、UART、云端、学习流程的总入口 |
| 摄像头 | `camerawidget.*` | 取景与图像帧获取 |
| 本地 AI | `ai_engine.*`, `postprocess.*` | 加载 RKNN 模型并处理 YOLO 检测结果 |
| 云端 AI | `AiCloudClient.*` | 调用 DashScope 兼容 OpenAI Chat Completions 接口 |
| UART | `uart_client.*` | 与 EC800M/外设串口通信 |
| 学习状态 | `action_manager.*`, `study_session_manager.*` | 学习会话、时长、日报统计 |
| 单词本 | `word_book_manager.*` | 保存识别过的单词和聊天次数 |
| 场景聊天 | `chat_session.*`, `scenes.json` | 场景选择、角色 prompt、对话历史 |
| 报告组件 | `report_widgets.*` | 学习日报图表/KPI UI |
| 陪伴学习 | `companion_page.*`, `pomodoro_controller.*` | 番茄钟和学科陪伴 |
| 宠物反馈 | `pet_emotion.*`, `pet_mood_controller.*` | 宠物动画、心情和气泡提示 |

## EC800M 运行时

`EC800M_merge` 是融合后的 EC800M 侧工程，入口为 `_main.py`。

核心文件：

- `_main.py`：运行时入口，初始化 UART、音频、网络和 WebSocket 协议。
- `protocol.py`：小智 WebSocket 协议封装。
- `tutor_mode.py`：Tutor/Chat 模式，处理 `SPEAK`、`TTS`、`WORD`、`RECORD` 等命令。
- `config.py`：默认 WebSocket 地址、Token 和协议版本。
- `utils.py`、`threading.py`、`logging.py`：QuecPython 工具模块。
- `SERVER_PROMPT.md`：服务端改造参考 prompt。

默认配置示例：

```python
DEFAULT_WS_URL = "ws://139.196.33.144:8000/xiaozhi/v1/"
DEFAULT_ACCESS_TOKEN = "test-token"
DEFAULT_PROTOCOL_VERSION = "1"
```

Tutor TTS 服务配置位于 `EC800M_merge/tutor_mode.py`：

```python
SERVER_TTS_HOST = "139.196.33.144"
SERVER_TTS_PORT = 8003
SERVER_TTS_PATH = "/api/ec800m/tts"
```

## UART 协议

Qt 主程序默认打开：

- `/dev/ttyS1`，115200
- `/dev/ttyS8`，115200，用于 EC800M

Qt 发送给 EC800M 的主要命令：

```text
MODE:CHAT
MODE:ASSISTANT
MODE:IDLE
RECORD:START
RECORD:START_MANUAL
RECORD:STOP
SPEAK:<text>
TTS:<text>
WORD:<english>:<chinese>
```

EC800M 回传的主要消息：

```text
EC_READY
USER:<asr_text>
ASR:ERR
RECORD:READY
RECORD:VAD
SPEAK:DONE
TTS:DONE
ASSIST_STATE:<state>
ASSIST_USER:<text>
ASSIST_AI:<text>
ASSIST_ERR:<error>
```

其中 Assistant 文本可能使用 Base64 形式回传，例如 `ASSIST_USER_B64:` 和 `ASSIST_AI_B64:`。

## 运行环境

主应用面向 Linux 嵌入式板端环境，代码和脚本中默认使用：

- QSM368/RK3568 SDK
- Buildroot 交叉编译工具链
- Qt Widgets / GUI / OpenGL / Network
- RKNN Runtime / RKNPU2
- ADB
- `/data` 作为板端部署目录
- EGLFS/KMS 或 Wayland 显示后端

`english_tutor.pro` 中 RKNN 头文件和库路径目前写死为开发机路径：

```qmake
RKNN_INC = /home/mjw/qsm_software/.../librknn_api/include
RKNN_LIB = /home/mjw/qsm_software/.../librknn_api/aarch64
```

如果换机器或 SDK 路径，需要同步修改 `english_tutor.pro`、`build.sh` 和 `run.sh` 中的 SDK 路径。

## 构建与部署

在 Linux/WSL/开发机上准备好 QSM368 SDK、qmake、make 和 adb 后执行：

```bash
chmod +x build.sh run.sh
./run.sh
```

`run.sh` 会执行：

1. 调用 SDK 内的 `qmake`
2. `make -j$(nproc)` 构建 `english_tutor`
3. 通过 `adb push` 推送主程序、模型、字体、宠物资源和 RKNN 库
4. 生成并推送 `/data/kms.json`
5. 停止 `weston`，同步时间
6. 使用 `QT_QPA_PLATFORM=eglfs` 启动 `/data/english_tutor`

`build.sh` 则会在 `/tmp/english_tutor_build` 中进行临时构建，并生成板端 `/data/run.sh`。

## 板端资源路径

主程序运行时依赖以下路径：

```text
/data/english_tutor
/data/model/yolov5s_qsm368zp.rknn
/data/model/coco_80_labels_list.txt
/data/scenes.json
/data/fonts/
/data/pets/
/data/study.json
/data/word_book.json
/data/kms.json
```

注意：当前源码中模型加载路径存在差异：

- `run.sh` 推送模型到 `/data/model/yolov5s_qsm368zp.rknn`
- `mainwindow.cpp` 中有加载 `/data/yolov5s_qsm368zp.rknn` 的逻辑

部署时请确认模型实际路径与代码一致，必要时调整 `mainwindow.cpp` 或推送路径。

## 云端接口

`AiCloudClient.cpp` 使用 DashScope 兼容 OpenAI 的接口：

```text
https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
```

当前使用模型：

- 图像理解：`qwen-vl-plus`
- 场景聊天/日报：`qwen-plus`

安全注意：`mainwindow.cpp` 中目前存在硬编码 API Key。正式使用前建议：

1. 立即轮换已提交过的 Key。
2. 改为从环境变量、配置文件或板端安全存储读取。
3. 不要把真实 Key 提交到仓库。

## 数据文件

学习数据以 JSON 形式保存在板端 `/data` 下：

- `/data/study.json`：学习会话、每日学习时长、今日单词数。
- `/data/word_book.json`：单词本，包含英文、中文、音标、描述、首次识别时间、最近识别时间、识别次数和聊天次数。

## 常见问题

### 触摸无响应

`run.sh` 会自动扫描 `/dev/input/event*` 中带 `ABS_MT_POSITION_X` 或 `BTN_TOUCH` 的设备，并通过 `QT_QPA_GENERIC_PLUGINS=evdevtouch:<device>` 绑定触摸屏。若仍无效，先在板端用 `getevent -lp` 确认触摸设备。

### 黑屏或 DRM 冲突

脚本会停止 `weston` 并通过 `eglfs` 直接接管显示。如果需要恢复桌面环境，可以重启设备：

```bash
adb reboot
```

### HTTPS/TLS 请求失败

板端时间错误会导致 TLS 校验失败。`run.sh` 中已尝试使用 `chronyd` 同步阿里云 NTP；如果失败，请先确认网络和系统时间。

### 字体或 emoji 显示异常

确认字体已推送到 `/data/fonts/`。`main.cpp` 会尝试加载 Noto/Segoe emoji 字体，但当前代码还尝试加载 `/data/fonts/NotoSansCJK.ttc`，而脚本主要推送的是 `NotoSans-Regular.ttf`，如需中文字体建议补齐 CJK 字体或调整加载路径。

## 开发注意事项

- 仓库中包含 `.o`、`moc_*.cpp`、`Makefile`、可执行文件和镜像文件，若要整理版本管理，建议后续增加 `.gitignore` 并清理生成物。
- `PROJECT_STRUCTURE_HANDOFF.md` 和部分 JSON/源码注释在当前环境中显示为乱码，可能存在编码不一致问题。
- `EC800M_merge` 与 `xiaozhi_demo` 存在同名模块，部署到 EC800M 时应确认最终使用的是融合目录。
- 修改 UART 协议时，需要同时更新 Qt 主程序和 `EC800M_merge/tutor_mode.py`/`_main.py`。
