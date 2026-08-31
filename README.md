# XHS Recorder

小红书直播录制工具 - 自动录制音频 + 弹幕抓取 + Whisper 语音转写

## 功能

- **音频录制**: 只录制直播音频，每小时自动分段，中断自动重连
- **弹幕抓取**: 实时捕获直播间弹幕、礼物、进入、关注等事件
- **自动监控**: 基于账号监控（非房间），主播换房间也能自动追踪
- **语音转写**: 使用 Whisper 将录音转为带时间戳的文字

## 快速开始

### 1. 安装依赖

```bash
pip install playwright openai-whisper
playwright install chromium
```

### 2. 配置

复制配置文件并填入你的 Cookie：

```bash
cp config.example.json config.json
# 编辑 config.json，填入你的小红书 Cookie
```

### 3. 使用

#### 直接录制指定房间

```bash
bash scripts/record.sh <room_id>
```

#### 自动监控+录制

```bash
bash scripts/watch.sh
```

#### 单次转写

```bash
python scripts/transcribe.py <audio_file.m4a>
```

#### 批量转写

```bash
bash scripts/batch_transcribe.sh
```

## 项目结构

```
xhs-recorder/
├── README.md
├── config.example.json    # 配置模板
├── requirements.txt       # Python 依赖
├── scripts/
│   ├── record.sh         # 音频录制
│   ├── watch.sh          # 自动监控+录制
│   ├── danmaku.py        # 弹幕抓取
│   ├── check_live.py     # 检查直播状态
│   ├── transcribe.py     # 单文件转写
│   └── batch_transcribe.sh  # 批量转写
└── src/
    └── xhs_monitor/      # Python 包（可选）
        ├── __init__.py
        ├── config.py
        ├── detector.py
        ├── monitor.py
        └── client.py
```

## 技术原理

### 直播检测

使用小红书搜索 API (`/api/sns/web/v1/search/onebox`) 检测主播是否在直播。当主播开播时，搜索结果会返回 `live_info.room_id`。

### 音频录制

使用 FFmpeg 直接从直播流地址录制音频：
- 流地址格式: `http://live-source-play.xhscdn.com/live/{room_id}.flv`
- 使用 `-f segment` 实现自动分段
- 支持断线重连

### 弹幕抓取

通过 Playwright 拦截 WebSocket 消息，解析 base64 编码的 `customData` 字段获取弹幕内容。

### 语音转写

使用 OpenAI Whisper (medium 模型) 进行中文语音识别，输出带时间戳的文本。

## 配置说明

| 字段 | 说明 |
|------|------|
| `host_id` | 主播的 user_id（从主页URL获取） |
| `username` | 主播用户名（用于搜索API检测） |
| `cookies.a1` | 小红书 Cookie |
| `cookies.web_session` | 小红书 Cookie |
| `check_interval` | 未开播时检查间隔（秒） |
| `check_live_interval` | 直播中检查间隔（秒） |
| `whisper_model` | Whisper 模型大小（tiny/base/small/medium/large） |

## 注意事项

- Cookie 会过期，需要定期更新
- 高并发请求可能触发小红书风控
- Whisper medium 模型在 CPU 上转写较慢，建议有 GPU 时使用 large 模型
- 录制文件保存在外部硬盘，注意磁盘空间

## License

MIT
