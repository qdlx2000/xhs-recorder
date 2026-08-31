#!/usr/bin/env python3
"""单文件语音转写

用法: python3 transcribe.py <audio_file.m4a>
输出: 生成同名 .txt 文件，包含带时间戳的转写文本
"""
import sys
from pathlib import Path

try:
    import whisper
except ImportError:
    print("请安装 whisper: pip install openai-whisper")
    sys.exit(1)


def transcribe(audio_file: str, model_name: str = "medium", language: str = "zh"):
    """转写音频文件"""
    audio_path = Path(audio_file)
    if not audio_path.exists():
        print(f"[ERROR] 文件不存在: {audio_file}")
        sys.exit(1)
    
    txt_path = audio_path.with_suffix(".txt")
    
    print(f"[INFO] 加载模型: {model_name}")
    model = whisper.load_model(model_name)
    
    print(f"[INFO] 开始转写: {audio_path.name}")
    result = model.transcribe(str(audio_path), language=language)
    
    print(f"[INFO] 写入文件: {txt_path.name}")
    with open(txt_path, "w", encoding="utf-8") as f:
        for seg in result["segments"]:
            start = seg["start"]
            end = seg["end"]
            text = seg["text"].strip()
            m1, s1 = divmod(int(start), 60)
            m2, s2 = divmod(int(end), 60)
            f.write(f"[{m1:02d}:{s1:02d} - {m2:02d}:{s2:02d}] {text}\n")
    
    print(f"[OK] 转写完成: {txt_path.name} ({len(result['segments'])} 段)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 transcribe.py <audio_file.m4a>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "medium"
    
    transcribe(audio_file, model)
