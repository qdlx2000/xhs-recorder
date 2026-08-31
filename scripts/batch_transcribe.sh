#!/bin/bash
# ============================================================
# 批量转写所有未转写的音频文件
# 用法: ./batch_transcribe.sh [model]
# 默认使用 medium 模型
# ============================================================

MODEL="${1:-medium}"
OUTPUT_DIR="${OUTPUT_DIR:-./recordings}"
LOG_FILE="$OUTPUT_DIR/batch_transcribe.log"

cd "$OUTPUT_DIR" || { echo "无法进入输出目录 $OUTPUT_DIR"; exit 1; }

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

log "===== 开始批量转写 ====="
log "模型: $MODEL"
log "共找到 $(ls xhs_audio_*.m4a 2>/dev/null | wc -l) 个音频文件"

COUNT=0
TOTAL=$(ls xhs_audio_*.m4a 2>/dev/null | wc -l)

for audio in xhs_audio_*.m4a; do
    [ -f "$audio" ] || continue
    
    txt="${audio%.m4a}.txt"
    
    if [ ! -f "$txt" ]; then
        COUNT=$((COUNT + 1))
        log "[$COUNT/$TOTAL] 转写: $audio"
        
        python3 "$(dirname "$0")/transcribe.py" "$audio" "$MODEL" 2>&1 | tee -a "$LOG_FILE"
        
        if [ -f "$txt" ]; then
            SIZE=$(wc -c < "$txt")
            log "✅ 转写完成: $txt ($SIZE bytes)"
        else
            log "❌ 转写失败: $audio"
        fi
    fi
done

log "===== 批量转写完成 ====="
log "共转写 $COUNT 个文件"
