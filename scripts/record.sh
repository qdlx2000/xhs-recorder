#!/bin/bash
# ============================================================
# 小红书直播音频录制脚本 / Xiaohongshu live stream audio recording script
# 功能：只录音频，每小时自动分段保存，直播中断自动重连
# Features: Audio-only recording, auto-segment every hour, auto-reconnect on stream interruption
# 用法：./record.sh <room_id> / Usage: ./record.sh <room_id>
# 停止：Ctrl+C / Stop: Press Ctrl+C
# ============================================================

# Required argument: room_id, error if missing / 必需参数：room_id，缺失时报错
ROOM_ID="${1:?用法: ./record.sh <room_id>}"
# Construct FLV stream URL from room_id / 根据 room_id 构造 FLV 流地址
STREAM_URL="http://live-source-play.xhscdn.com/live/${ROOM_ID}.flv"
# Output directory, default to ./recordings / 输出目录，默认为 ./recordings
OUTPUT_DIR="${OUTPUT_DIR:-./recordings}"
# Segment duration in seconds (3600 = 1 hour) / 分段时长（秒）（3600 = 1小时）
SEGMENT_TIME="${SEGMENT_TIME:-3600}"  # 每小时分段（秒） / Segments every hour
# Spoofed iOS user-agent to bypass CDN restrictions / 伪装 iOS User-Agent 以绕过 CDN 限制
USER_AGENT="ios/7.830 (ios 17.0; ; iPhone 15 (A2846/A3089/A3090/A3092))"
# Referer header required by the CDN / CDN 所需的 Referer 头
REFERER="https://app.xhs.cn/"

# Create output directory if it doesn't exist / 如输出目录不存在则创建
mkdir -p "$OUTPUT_DIR"
# Enter output directory, exit on failure / 进入输出目录，失败则退出
cd "$OUTPUT_DIR" || { echo "无法进入输出目录 $OUTPUT_DIR"; exit 1; }

# Logging function with timestamp / 带时间戳的日志函数
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

# Print startup banner / 打印启动横幅
log "==========================================="
log "小红书直播音频录制启动 / Xiaohongshu audio recording started"
log "==========================================="
log "房间ID: $ROOM_ID / Room ID: $ROOM_ID"
log "流地址: $STREAM_URL / Stream URL: $STREAM_URL"
log "输出目录: $OUTPUT_DIR / Output dir: $OUTPUT_DIR"
log "分段时长: ${SEGMENT_TIME}秒 / Segment duration: ${SEGMENT_TIME}s"
log "格式: M4A (纯音频) / Format: M4A (audio only)"
log "按 Ctrl+C 停止录制 / Press Ctrl+C to stop recording"
log "==========================================="

# Track number of retry attempts / 记录重试次数
RETRY_COUNT=0

# Cleanup handler: called on SIGINT/SIGTERM, lists recorded files
# 清理处理函数：收到 SIGINT/SIGTERM 时调用，列出已录制文件
cleanup() {
    log ""
    log "收到停止信号，录制结束 / Stop signal received, recording ended"
    log "已录制文件： / Recorded files:"
    ls -lh "$OUTPUT_DIR"/xhs_audio_*.m4a 2>/dev/null | awk '{print "  " $NF " (" $5 ")"}'
    exit 0
}

# Register cleanup handler for Ctrl+C and termination signals
# 注册清理处理函数，捕获 Ctrl+C 和终止信号
trap cleanup SIGINT SIGTERM

# Main recording loop: reconnects on failure, breaks on normal exit
# 主录制循环：失败时重连，正常退出时跳出循环
while true; do
    # Generate unique session ID from current timestamp / 用当前时间戳生成唯一 session ID
    SESSION_ID=$(date '+%Y%m%d_%H%M%S')
    OUTPUT_PATTERN="xhs_audio_${SESSION_ID}_%03d.m4a"
    
    # Increment and log retry counter / 递增并记录重试计数
    RETRY_COUNT=$((RETRY_COUNT + 1))
    log "第 ${RETRY_COUNT} 次录制开始，session: $SESSION_ID / Recording #${RETRY_COUNT} started, session: $SESSION_ID"
    
    # Run FFmpeg: record FLV stream, extract audio only, segment by time
    # 运行 FFmpeg：录制 FLV 流，仅提取音频，按时长分段
    ffmpeg -y \
        -user_agent "$USER_AGENT" \
        -headers "Referer: ${REFERER}\r\n" \
        -reconnect 1 \
        -reconnect_streamed 1 \
        -reconnect_delay_max 10 \
        -i "$STREAM_URL" \
        -vn \
        -acodec copy \
        -f segment \
        -segment_time $SEGMENT_TIME \
        -reset_timestamps 1 \
        "$OUTPUT_PATTERN" \
        2>&1 | while IFS= read -r line; do
            if echo "$line" | grep -qE "size=|time=|Error|error|Opening|session"; then
                log "$line"
            fi
        done
    
    # Capture FFmpeg's exit code from the pipeline / 捕获 FFmpeg 管道的退出码
    EXIT_CODE=${PIPESTATUS[0]}
    
    if [ $EXIT_CODE -eq 0 ]; then
        # Exit code 0 = normal end (live stream likely ended)
        # 退出码 0 = 正常结束（直播可能已结束）
        log "录制正常结束（直播可能已结束） / Recording ended normally (stream likely ended)"
        break
    else
        # Non-zero exit = interrupted, wait and retry
        # 非零退出码 = 被中断，等待后重试
        log "录制中断 (exit code: $EXIT_CODE)，10秒后重连... / Recording interrupted (exit code: $EXIT_CODE), reconnecting in 10s..."
        sleep 10
    fi
done

log "录制脚本退出 / Recording script exited"
