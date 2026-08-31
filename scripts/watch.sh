#!/bin/bash
# ============================================================
# 小红书主播监听+录制脚本（账号监控模式）
# 功能：监控主播账号，开播自动获取房间ID并录制，下播自动停止
# 用法：./watch.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config.json"

# 读取配置
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[ERROR] 未找到 config.json，请先复制 config.example.json"
    exit 1
fi

HOST_ID=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['host_id'])")
HOST_USERNAME=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['username'])")
CHECK_INTERVAL=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('check_interval', 3600))")
CHECK_LIVE_INTERVAL=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('check_live_interval', 600))")

OUTPUT_DIR="${OUTPUT_DIR:-./recordings}"
WATCH_LOG="$OUTPUT_DIR/watch.log"

mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR" || exit 1

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$WATCH_LOG"
}

# 检查主播账号是否在直播，返回房间ID
check_host() {
    python3 "$SCRIPT_DIR/check_live.py" "$HOST_ID" "$HOST_USERNAME" 2>/dev/null
}

# 获取指定房间的直播流地址
get_stream_url() {
    local room_id="$1"
    python3 -c "
import json, re, ssl, urllib.request

room_id = '$room_id'
headers = {
    'User-Agent': 'ios/7.830 (ios 17.0; ; iPhone 15 (A2846/A3089/A3090/A3092))',
    'Referer': 'https://app.xhs.cn/',
}

urls = [
    f'https://www.xiaohongshu.com/livestream/dynpathBZhuJjtn/{room_id}',
    f'https://www.xiaohongshu.com/livestream/{room_id}',
]

for url in urls:
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except:
        continue
    
    m = re.search(r'window\.__INITIAL_STATE__\s*=\s*', html)
    if not m:
        continue
    
    start = m.end()
    end = html.find('</script>', start)
    blob = html[start:end].rstrip().rstrip(';').replace('undefined', 'null')
    
    try:
        state = json.loads(blob)
    except:
        continue
    
    live_stream = state.get('liveStream') or {}
    if live_stream.get('liveStatus') != 'success':
        continue
    
    room_info = (live_stream.get('roomData') or {}).get('roomInfo') or {}
    title = room_info.get('roomTitle', '')
    pull_config = room_info.get('pullConfig')
    
    if not pull_config:
        continue
    
    cfg = json.loads(pull_config)
    streams = cfg.get('h264') or cfg.get('h265') or []
    
    for s in streams:
        stream_url = s.get('master_url', '')
        if stream_url.endswith('.flv'):
            print(f'LIVE|{room_id}|{title}|{stream_url}')
            exit(0)
    
    if streams:
        print(f'LIVE|{room_id}|{title}|{streams[0].get(\"master_url\", \"\")}')
        exit(0)

print('NOT_LIVE')
" 2>&1
}

start_recording() {
    local stream_url="$1"
    local title="$2"
    local room_id="$3"

    log "开始录制: $title (房间: $room_id)"

    tmux has-session -t xhs_record 2>/dev/null && tmux kill-session -t xhs_record
    tmux new-session -d -s xhs_record
    tmux send-keys -t xhs_record "cd $OUTPUT_DIR && bash $SCRIPT_DIR/record.sh $room_id" Enter
    tmux new-window -t xhs_record -n danmaku
    tmux send-keys -t xhs_record:danmaku "cd $OUTPUT_DIR && python3 $SCRIPT_DIR/danmaku.py $room_id" Enter

    sleep 3
    log "录制+弹幕监控已启动 (tmux: xhs_record, window: danmaku=$room_id)"
}

stop_recording() {
    log "直播结束，停止录制+弹幕..."
    tmux has-session -t xhs_record 2>/dev/null && tmux kill-session -t xhs_record
    log "录制+弹幕监控已停止"
}

# --- 主循环 ---
log "==========================================="
log "小红书主播监听启动（账号监控模式）"
log "主播ID: $HOST_ID ($HOST_USERNAME)"
log "检查间隔: 未开播 $((CHECK_INTERVAL/60))分钟 / 直播中 $((CHECK_LIVE_INTERVAL/60))分钟"
log "==========================================="

IS_RECORDING=false
CURRENT_ROOM=""

while true; do
    # 检查主播是否在直播
    HOST_STATUS=$(check_host)
    log "检查主播状态: $HOST_STATUS"
    
    if [[ "$HOST_STATUS" == LIVE\|* ]]; then
        NEW_ROOM=$(echo "$HOST_STATUS" | cut -d'|' -f2)
        
        if [ "$IS_RECORDING" = true ] && [ "$CURRENT_ROOM" = "$NEW_ROOM" ]; then
            log "直播中，同一房间 $NEW_ROOM，${CHECK_LIVE_INTERVAL}秒后检查"
            sleep $CHECK_LIVE_INTERVAL
            continue
        fi
        
        # 获取流地址
        STREAM_RESULT=$(get_stream_url "$NEW_ROOM")
        log "获取流地址: $STREAM_RESULT"
        
        if [[ "$STREAM_RESULT" == LIVE\|* ]]; then
            TITLE=$(echo "$STREAM_RESULT" | cut -d'|' -f3)
            STREAM_URL=$(echo "$STREAM_RESULT" | cut -d'|' -f4)
            
            stop_recording 2>/dev/null
            start_recording "$STREAM_URL" "$TITLE" "$NEW_ROOM"
            IS_RECORDING=true
            CURRENT_ROOM="$NEW_ROOM"
            
            log "直播中，${CHECK_LIVE_INTERVAL}秒后检查"
            sleep $CHECK_LIVE_INTERVAL
        else
            log "获取流地址失败，${CHECK_INTERVAL}秒后重试"
            sleep $CHECK_INTERVAL
        fi
    else
        if [ "$IS_RECORDING" = true ]; then
            stop_recording
            IS_RECORDING=false
            CURRENT_ROOM=""
        fi
        
        log "主播未直播，${CHECK_INTERVAL}秒后重试"
        sleep $CHECK_INTERVAL
    fi
done
