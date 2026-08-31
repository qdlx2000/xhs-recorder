#!/bin/bash
# ============================================================
# 小红书直播音频录制脚本
# 功能：只录音频，每小时自动分段保存，直播中断自动重连
# 用法：./record.sh <room_id>
# 停止：Ctrl+C
# ============================================================

ROOM_ID="${1:?用法: ./record.sh <room_id>}"
STREAM_URL="http://live-source-play.xhscdn.com/live/${ROOM_ID}.flv"
OUTPUT_DIR="${OUTPUT_DIR:-./recordings}"
SEGMENT_TIME="${SEGMENT_TIME:-3600}"  # 每小时分段（秒）
USER_AGENT="ios/7.830 (ios 17.0; ; iPhone 15 (A2846/A3089/A3090/A3092))"
REFERER="https://app.xhs.cn/"

mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR" || { echo "无法进入输出目录 $OUTPUT_DIR"; exit 1; }

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

log "==========================================="
log "小红书直播音频录制启动"
log "==========================================="
log "房间ID: $ROOM_ID"
log "流地址: $STREAM_URL"
log "输出目录: $OUTPUT_DIR"
log "分段时长: ${SEGMENT_TIME}秒"
log "格式: M4A (纯音频)"
log "按 Ctrl+C 停止录制"
log "==========================================="

RETRY_COUNT=0

cleanup() {
    log ""
    log "收到停止信号，录制结束"
    log "已录制文件："
    ls -lh "$OUTPUT_DIR"/xhs_audio_*.m4a 2>/dev/null | awk '{print "  " $NF " (" $5 ")"}'
    exit 0
}

trap cleanup SIGINT SIGTERM

while true; do
    SESSION_ID=$(date '+%Y%m%d_%H%M%S')
    OUTPUT_PATTERN="xhs_audio_${SESSION_ID}_%03d.m4a"
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    log "第 ${RETRY_COUNT} 次录制开始，session: $SESSION_ID"
    
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
    
    EXIT_CODE=${PIPESTATUS[0]}
    
    if [ $EXIT_CODE -eq 0 ]; then
        log "录制正常结束（直播可能已结束）"
        break
    else
        log "录制中断 (exit code: $EXIT_CODE)，10秒后重连..."
        sleep 10
    fi
done

log "录制脚本退出"
