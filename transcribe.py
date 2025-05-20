#!/usr/bin/env python3
"""Transcribe audio files in 5-minute chunks using OpenAI."""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from pydub import AudioSegment
import openai

CHUNK_MS = 5 * 60 * 1000  # 5 minutes in milliseconds


def split_audio(audio: AudioSegment) -> list[AudioSegment]:
    """Split AudioSegment into 5-minute chunks."""
    return [audio[i : i + CHUNK_MS] for i in range(0, len(audio), CHUNK_MS)]


def transcribe_segment(segment: AudioSegment, idx: int, base: Path, model: str, language: str | None) -> str:
    """Export the segment to a temporary file and transcribe it."""
    temp_file = base.with_name(f"{base.stem}_part{idx}.mp3")
    segment.export(temp_file, format="mp3")
    try:
        with open(temp_file, "rb") as f:
            response = openai.Audio.transcribe(model=model, file=f, language=language)
        return response["text"]
    finally:
        temp_file.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transcribe an audio file with OpenAI in 5-minute chunks."
    )
    parser.add_argument("input", type=Path, help="Path to the audio file")
    parser.add_argument("-o", "--output", type=Path, help="File to save the transcription")
    parser.add_argument(
        "-l",
        "--language",
        type=str,
        default=None,
        help="Optional language code, e.g. 'en'",
    )
    parser.add_argument(
        "-m", "--model", type=str, default="whisper-1", help="OpenAI transcription model"
    )
    args = parser.parse_args()

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit(
            "OPENAI_API_KEY not set. Add it to a .env file in this directory."
        )
    openai.api_key = api_key

    audio = AudioSegment.from_file(args.input)
    chunks = split_audio(audio)
    base = args.input

    texts = []
    for idx, chunk in enumerate(chunks):
        texts.append(transcribe_segment(chunk, idx, base, args.model, args.language))

    result = "\n".join(texts)
    if args.output:
        args.output.write_text(result)
    else:
        print(result)


if __name__ == "__main__":
    main()
