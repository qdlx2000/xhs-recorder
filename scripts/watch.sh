#!/bin/bash
# ============================================================
# 小红书主播监听+录制脚本（账号监控模式）
# Xiaohongshu streamer monitor + recording script (account monitoring mode)
# 功能：监控主播账号，开播自动获取房间ID并录制，下播自动停止
# Features: Monitor streamer account, auto-get room ID and record when live, auto-stop when offline
# 用法：./watch.sh / Usage: ./watch.sh
# ============================================================

# Get the directory of this script (resolve symlinks)
# 获取当前脚本所在目录（解析符号链接）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Path to the configuration file / 配置文件路径
CONFIG_FILE="${SCRIPT_DIR}/../config.json"

# Read configuration from config.json
# 从 config.json 读取配置
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[ERROR] 未找到 config.json，请先复制 config.example.json"
    exit 1
fi

# Extract host_id (streamer account ID) from config / 从配置中提取 host_id（主播账号 ID）
HOST_ID=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['host_id'])")
# Extract host username from config / 从配置中提取主播用户名
HOST_USERNAME=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['username'])")
# Check interval when offline (default 3600s = 1 hour)
# 未开播时的检查间隔（默认 3600 秒 = 1 小时）
CHECK_INTERVAL=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('check_interval', 3600))")
# Check interval when live (default 600s = 10 minutes)
# 直播中的检查间隔（默认 600 秒 = 10 分钟）
CHECK_LIVE_INTERVAL=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('check_live_interval', 600))")

# Output directory and watch log file / 输出目录和监听日志文件
OUTPUT_DIR="${OUTPUT_DIR:-./recordings}"
WATCH_LOG="$OUTPUT_DIR/watch.log"

# Create output directory and enter it / 创建输出目录并进入
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR" || exit 1

# Logging function: outputs to terminal and appends to log file
# 日志函数：输出到终端并追加到日志文件
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$WATCH_LOG"
}

# Check if the streamer is currently live, returns room_id
# 检查主播是否在直播，返回房间 ID
check_host() {
    python3 "$SCRIPT_DIR/check_live.py" "$HOST_ID" "$HOST_USERNAME" 2>/dev/null
}

# Get the live stream URL for a given room_id (parses page HTML for stream config)
# 获取指定房间的直播流地址（解析页面 HTML 获取流配置）
get_stream_url() {
    local room_id="$1"
    python3 -c "
import json, re, ssl, urllib.request

room_id = '$room_id'
headers = {
    'User-Agent': 'ios/7.830 (ios 17.0; ; iPhone 15 (A2846/A3089/A3090/A3092))',
    'Referer': 'https://app.xhs.cn/',
}

# Try multiple URLs to fetch the live page / 尝试多个地址获取直播页面
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
    
    # Extract __INITIAL_STATE__ JSON blob from HTML
    # 从 HTML 中提取 __INITIAL_STATE__ JSON 数据
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
    # Check if live status is 'success' / 检查直播状态是否为 'success'
    if live_stream.get('liveStatus') != 'success':
        continue
    
    room_info = (live_stream.get('roomData') or {}).get('roomInfo') or {}
    title = room_info.get('roomTitle', '')
    pull_config = room_info.get('pullConfig')
    
    if not pull_config:
        continue
    
    # Parse pull config JSON to extract stream URLs / 解析拉流配置 JSON 以提取流地址
    cfg = json.loads(pull_config)
    streams = cfg.get('h264') or cfg.get('h265') or []
    
    # Prefer FLV streams, fallback to first available / 优先选择 FLV 流，否则取第一个可用流
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

# Start recording + danmaku capture in a tmux session
# 在 tmux 会话中启动录制 + 弹幕抓取
start_recording() {
    local stream_url="$1"
    local title="$2"
    local room_id="$3"

    log "开始录制: $title (房间: $room_id) / Starting recording: $title (room: $room_id)"

    # Kill existing session if present / 如果存在则杀掉已有会话
    tmux has-session -t xhs_record 2>/dev/null && tmux kill-session -t xhs_record
    # Create new tmux session / 创建新的 tmux 会话
    tmux new-session -d -s xhs_record
    # Launch record.sh in the session / 在会话中启动 record.sh
    tmux send-keys -t xhs_record "cd $OUTPUT_DIR && bash $SCRIPT_DIR/record.sh $room_id" Enter
    # Create danmaku window and start danmaku capture / 创建弹幕窗口并启动弹幕抓取
    tmux new-window -t xhs_record -n danmaku
    tmux send-keys -t xhs_record:danmaku "cd $OUTPUT_DIR && python3 $SCRIPT_DIR/danmaku.py $room_id" Enter

    # Brief pause to let processes initialize / 短暂等待以让进程初始化
    sleep 3
    log "录制+弹幕监控已启动 (tmux: xhs_record, window: danmaku=$room_id) / Recording + danmaku monitor started"
}

# Stop recording by killing the tmux session / 杀掉 tmux 会话以停止录制
stop_recording() {
    log "直播结束，停止录制+弹幕... / Stream ended, stopping recording + danmaku..."
    tmux has-session -t xhs_record 2>/dev/null && tmux kill-session -t xhs_record
    log "录制+弹幕监控已停止 / Recording + danmaku monitor stopped"
}

# --- Main monitoring loop / 主监听循环 ---
log "==========================================="
log "小红书主播监听启动（账号监控模式） / Xiaohongshu monitor started (account monitoring mode)"
log "主播ID: $HOST_ID ($HOST_USERNAME) / Streamer ID: $HOST_ID ($HOST_USERNAME)"
log "检查间隔: 未开播 $((CHECK_INTERVAL/60))分钟 / 直播中 $((CHECK_LIVE_INTERVAL/60))分钟 / Intervals: offline ${CHECK_INTERVAL}m / live ${CHECK_LIVE_INTERVAL}m"
log "==========================================="

# State tracking variables / 状态追踪变量
IS_RECORDING=false
CURRENT_ROOM=""

# Infinite loop: poll streamer status, start/stop recording accordingly
# 无限循环：轮询主播状态，据此启动/停止录制
while true; do
    # Check if the streamer is currently live / 检查主播是否在直播
    HOST_STATUS=$(check_host)
    log "检查主播状态: $HOST_STATUS / Host status: $HOST_STATUS"
    
    if [[ "$HOST_STATUS" == LIVE\|* ]]; then
        # Streamer is live, extract room_id / 主播在直播中，提取 room_id
        NEW_ROOM=$(echo "$HOST_STATUS" | cut -d'|' -f2)
        
        # If already recording the same room, just wait and check again
        # 如果正在录制同一房间，等待后再次检查
        if [ "$IS_RECORDING" = true ] && [ "$CURRENT_ROOM" = "$NEW_ROOM" ]; then
            log "直播中，同一房间 $NEW_ROOM，${CHECK_LIVE_INTERVAL}秒后检查 / Live, same room $NEW_ROOM, check in ${CHECK_LIVE_INTERVAL}s"
            sleep $CHECK_LIVE_INTERVAL
            continue
        fi
        
        # Fetch the stream URL for the new room / 获取新房间的流地址
        STREAM_RESULT=$(get_stream_url "$NEW_ROOM")
        log "获取流地址: $STREAM_RESULT / Stream URL: $STREAM_RESULT"
        
        if [[ "$STREAM_RESULT" == LIVE\|* ]]; then
            # Parse stream info from result / 从结果中解析流信息
            TITLE=$(echo "$STREAM_RESULT" | cut -d'|' -f3)
            STREAM_URL=$(echo "$STREAM_RESULT" | cut -d'|' -f4)
            
            # Stop any existing recording, then start new one
            # 停止已有录制，然后启动新的录制
            stop_recording 2>/dev/null
            start_recording "$STREAM_URL" "$TITLE" "$NEW_ROOM"
            IS_RECORDING=true
            CURRENT_ROOM="$NEW_ROOM"
            
            # Wait before next check during live / 直播中等待后再次检查
            log "直播中，${CHECK_LIVE_INTERVAL}秒后检查 / Live, checking in ${CHECK_LIVE_INTERVAL}s"
            sleep $CHECK_LIVE_INTERVAL
        else
            # Failed to get stream URL, retry later / 获取流地址失败，稍后重试
            log "获取流地址失败，${CHECK_INTERVAL}秒后重试 / Failed to get stream URL, retry in ${CHECK_INTERVAL}s"
            sleep $CHECK_INTERVAL
        fi
    else
        # Streamer is not live / 主播未在直播
        if [ "$IS_RECORDING" = true ]; then
            # Stream ended, stop recording / 直播结束，停止录制
            stop_recording
            IS_RECORDING=false
            CURRENT_ROOM=""
        fi
        
        # Wait before next check when offline / 未开播时等待后再次检查
        log "主播未直播，${CHECK_INTERVAL}秒后重试 / Streamer offline, retry in ${CHECK_INTERVAL}s"
        sleep $CHECK_INTERVAL
    fi
done
