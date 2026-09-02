#!/bin/bash
# ============================================================
# 批量转写所有未转写的音频文件
# Batch transcribe all untranscribed audio files
# 用法: ./batch_transcribe.sh [model] / Usage: ./batch_transcribe.sh [model]
# 默认使用 medium 模型 / Defaults to the "medium" model
# ============================================================

# Whisper model size to use (tiny/base/small/medium/large)
# 使用的 Whisper 模型大小（tiny/base/small/medium/large）
MODEL="${1:-medium}"
# Output directory containing audio files / 包含音频文件的输出目录
OUTPUT_DIR="${OUTPUT_DIR:-./recordings}"
# Log file for batch transcription / 批量转写日志文件
LOG_FILE="$OUTPUT_DIR/batch_transcribe.log"

# Enter output directory, exit on failure / 进入输出目录，失败则退出
cd "$OUTPUT_DIR" || { echo "无法进入输出目录 $OUTPUT_DIR"; exit 1; }

# Logging function with timestamp and log file output
# 带时间戳的日志函数，同时输出到终端和日志文件
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG_FILE"
}

# Print batch start banner / 打印批量转写开始横幅
log "===== 开始批量转写 ===== / ===== Batch transcription started ====="
log "模型: $MODEL / Model: $MODEL"

# Count total audio files / 统计音频文件总数
log "共找到 $(ls xhs_audio_*.m4a 2>/dev/null | wc -l) 个音频文件 / Found $(ls xhs_audio_*.m4a 2>/dev/null | wc -l) audio files"

# Counter and total for progress tracking / 计数器和总数用于进度追踪
COUNT=0
TOTAL=$(ls xhs_audio_*.m4a 2>/dev/null | wc -l)

# Iterate over all audio files / 遍历所有音频文件
for audio in xhs_audio_*.m4a; do
    # Skip if no files match the glob / 如果没有匹配的文件则跳过
    [ -f "$audio" ] || continue
    
    # Derive expected transcript filename (.txt) from audio filename (.m4a)
    # 从音频文件名（.m4a）推导出预期的转写文本文件名（.txt）
    txt="${audio%.m4a}.txt"
    
    # Only transcribe if .txt does not already exist (skip already-transcribed files)
    # 仅在 .txt 不存在时进行转写（跳过已转写的文件）
    if [ ! -f "$txt" ]; then
        COUNT=$((COUNT + 1))
        log "[$COUNT/$TOTAL] 转写: $audio / Transcribing: $audio"
        
        # Run the transcription script on this audio file
        # 对该音频文件运行转写脚本
        python3 "$(dirname "$0")/transcribe.py" "$audio" "$MODEL" 2>&1 | tee -a "$LOG_FILE"
        
        # Verify transcription succeeded by checking for output file
        # 通过检查输出文件来验证转写是否成功
        if [ -f "$txt" ]; then
            SIZE=$(wc -c < "$txt")
            log "✅ 转写完成: $txt ($SIZE bytes) / Transcription complete: $txt ($SIZE bytes)"
        else
            log "❌ 转写失败: $audio / Transcription failed: $audio"
        fi
    fi
done

# Print batch completion banner / 打印批量转写完成横幅
log "===== 批量转写完成 ===== / ===== Batch transcription complete ====="
log "共转写 $COUNT 个文件 / Transcribed $COUNT files"
