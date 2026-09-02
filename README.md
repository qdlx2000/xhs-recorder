# XHS Recorder

小红书直播录制工具 - 自动录制音频 + 弹幕抓取 + Whisper 语音转写

Xiaohongshu (Little Red Book) Livestream Recorder — auto audio recording + danmaku capture + Whisper transcription

## 功能 / Features

- **音频录制**: 只录制直播音频，每小时自动分段，中断自动重连
  **Audio Recording**: Record audio only with automatic hourly segmentation and auto-reconnect on interruption
- **弹幕抓取**: 实时捕获直播间弹幕、礼物、进入、关注等事件
  **Danmaku Capture**: Real-time capture of livestream comments, gifts, entry events, follows, etc.
- **自动监控**: 基于账号监控（非房间），主播换房间也能自动追踪
  **Auto Monitoring**: Account-based (not room-based), automatically tracks streamers across room changes
- **语音转写**: 使用 Whisper 将录音转为带时间戳的文字
  **Transcription**: Convert recordings to timestamped text using Whisper

## 快速开始 / Quick Start

### 1. 安装依赖 / Install Dependencies

```bash
pip install playwright openai-whisper
playwright install chromium
```

### 2. 配置 / Configuration

复制配置文件并填入你的 Cookie：

Copy the config template and fill in your cookies:

```bash
cp config.example.json config.json
# 编辑 config.json，填入你的小红书 Cookie
# Edit config.json with your Xiaohongshu cookies
```

### 3. 使用 / Usage

#### 直接录制指定房间 / Record a specific room

```bash
bash scripts/record.sh <room_id>
```

#### 自动监控+录制 / Auto monitor + record

```bash
bash scripts/watch.sh
```

#### 单次转写 / Transcribe a single file

```bash
python scripts/transcribe.py <audio_file.m4a>
```

#### 批量转写 / Batch transcription

```bash
bash scripts/batch_transcribe.sh
```

## 项目结构 / Project Structure

```
xhs-recorder/
├── README.md
├── config.example.json    # 配置模板 / Config template
├── requirements.txt       # Python 依赖 / Python dependencies
├── scripts/
│   ├── record.sh         # 音频录制 / Audio recording
│   ├── watch.sh          # 自动监控+录制 / Auto monitor + record
│   ├── danmaku.py        # 弹幕抓取 / Danmaku capture
│   ├── check_live.py     # 检查直播状态 / Check livestream status
│   ├── transcribe.py     # 单文件转写 / Single file transcription
│   └── batch_transcribe.sh  # 批量转写 / Batch transcription
└── src/
    └── xhs_monitor/      # Python 包（可选）/ Python package (optional)
        ├── __init__.py
        ├── config.py
        ├── detector.py
        ├── monitor.py
        └── client.py
```

## 技术原理 / Technical Details

### 直播检测 / Livestream Detection

使用小红书搜索 API (`/api/sns/web/v1/search/onebox`) 检测主播是否在直播。当主播开播时，搜索结果会返回 `live_info.room_id`。

Uses the Xiaohongshu search API to detect whether a streamer is live. When live, the search results return `live_info.room_id`.

### 音频录制 / Audio Recording

使用 FFmpeg 直接从直播流地址录制音频：
Uses FFmpeg to record audio directly from the livestream URL:

- 流地址格式: `http://live-source-play.xhscdn.com/live/{room_id}.flv`
  Stream format: `http://live-source-play.xhscdn.com/live/{room_id}.flv`
- 使用 `-f segment` 实现自动分段 / Automatic segmentation via `-f segment`
- 支持断线重连 / Auto-reconnect on disconnection

### 弹幕抓取 / Danmaku Capture

通过 Playwright 拦截 WebSocket 消息，解析 base64 编码的 `customData` 字段获取弹幕内容。

Intercepts WebSocket messages via Playwright and decodes base64-encoded `customData` fields to extract danmaku content.

### 语音转写 / Transcription

使用 OpenAI Whisper (medium 模型) 进行中文语音识别，输出带时间戳的文本。

Uses OpenAI Whisper (medium model) for Chinese speech recognition, outputting timestamped text.

## 配置说明 / Configuration

| 字段 / Field | 说明 / Description |
|------|------|
| `host_id` | 主播的 user_id（从主页URL获取） / Streamer's user_id (from profile URL) |
| `username` | 主播用户名（用于搜索API检测） / Streamer's username (for search API detection) |
| `cookies.a1` | 小红书 Cookie / Xiaohongshu Cookie |
| `cookies.web_session` | 小红书 Cookie / Xiaohongshu Cookie |
| `check_interval` | 未开播时检查间隔（秒） / Check interval when offline (seconds) |
| `check_live_interval` | 直播中检查间隔（秒） / Check interval when live (seconds) |
| `whisper_model` | Whisper 模型大小（tiny/base/small/medium/large） / Whisper model size |

## 注意事项 / Notes

- Cookie 会过期，需要定期更新
  Cookies expire and need regular updates
- 高并发请求可能触发小红书风控
  High-frequency requests may trigger XHS rate limiting
- Whisper medium 模型在 CPU 上转写较慢，建议有 GPU 时使用 large 模型
  Whisper medium is slow on CPU; consider using large model with GPU
- 录制文件保存在外部硬盘，注意磁盘空间
  Recordings are saved to external drive — monitor disk space

## License

MIT
