#!/usr/bin/env python3
"""单文件语音转写 / Single-file audio transcription

用法 / Usage: python3 transcribe.py <audio_file.m4a>
输出 / Output: 生成同名 .txt 文件，包含带时间戳的转写文本 / Generates a .txt file with timestamped transcription
"""
import sys
from pathlib import Path

try:
    import whisper
except ImportError:
    print("请安装 whisper / Please install whisper: pip install openai-whisper")
    sys.exit(1)


def transcribe(audio_file: str, model_name: str = "medium", language: str = "zh"):
    """转写音频文件 / Transcribe an audio file"""
    audio_path = Path(audio_file)
    if not audio_path.exists():
        print(f"[ERROR] 文件不存在 / File not found: {audio_file}")
        sys.exit(1)
    
    # 输出文件与输入文件同目录、同名，后缀改为 .txt / Output file is in same directory, same name, with .txt extension
    txt_path = audio_path.with_suffix(".txt")
    
    print(f"[INFO] 加载模型 / Loading model: {model_name}")
    model = whisper.load_model(model_name)
    
    print(f"[INFO] 开始转写 / Starting transcription: {audio_path.name}")
    result = model.transcribe(str(audio_path), language=language)
    
    # 写入带时间戳的转写结果 / Write timestamped transcription results
    print(f"[INFO] 写入文件 / Writing to file: {txt_path.name}")
    with open(txt_path, "w", encoding="utf-8") as f:
        for seg in result["segments"]:
            start = seg["start"]
            end = seg["end"]
            text = seg["text"].strip()
            m1, s1 = divmod(int(start), 60)
            m2, s2 = divmod(int(end), 60)
            f.write(f"[{m1:02d}:{s1:02d} - {m2:02d}:{s2:02d}] {text}\n")
    
    print(f"[OK] 转写完成 / Transcription complete: {txt_path.name} ({len(result['segments'])} 段 / segments)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法 / Usage: python3 transcribe.py <audio_file.m4a>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "medium"
    
    transcribe(audio_file, model)
