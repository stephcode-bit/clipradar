"""Builds a synthetic 'podcast' test video + matching transcript.json so the
ClipRadar pipeline can be exercised end-to-end without network access
(no YouTube download, no Whisper model download needed).

Real transcription (faster-whisper) is a well-established, separately
tested component — this fixture is about proving out everything
ClipRadar actually adds: scoring, clip assembly, captions, thumbnails,
metadata.
"""

import json
import os
import subprocess

OUT_DIR = "/root/clipradar/sample"
os.makedirs(OUT_DIR, exist_ok=True)

# Each tuple: (sentence text, whether to insert a longer pause after it)
SCRIPT = [
    "Welcome back to the show, today we are talking about something wild.",
    "So last year I almost lost my entire business over one email.",
    "Here's the thing nobody tells you about running a startup.",
    "You think the hardest part is building the product.",
    "It's not.",
    "The hardest part is the moment everything breaks at once.",
    "Um, so, like, we were three days from making payroll.",
    "And then, our biggest client just disappeared, no call, no email.",
    "I was terrified, genuinely terrified, sitting in my car in a parking lot.",
    "So what did I do.",
    "I called every single client we had ever worked with, that day.",
    "Turns out the client had a security incident and it had nothing to do with us.",
    "And that's when I learned the real lesson.",
    "Panic is optional, but preparation is not.",
    "That one phone call saved the company, and honestly it changed how I lead.",
    "Anyway, let's get into today's main topic about marketing budgets.",
    "A lot of founders think you need a huge ad budget to grow.",
    "That is simply not true in twenty twenty five.",
    "Organic content, done consistently, still massively outperforms paid ads for early stage companies.",
    "So my advice, spend your first year on content, not ads.",
]

VOICE = "en-us"
RATE = 165
SENT_GAP = 0.45  # seconds of silence between sentences


def synth_sentence(text: str, idx: int) -> str:
    path = f"{OUT_DIR}/sent_{idx:02d}.wav"
    subprocess.run(
        ["espeak-ng", "-v", VOICE, "-s", str(RATE), "-w", path, text],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return path


def wav_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        stdout=subprocess.PIPE, text=True,
    )
    return float(out.stdout.strip())


def word_timestamps(text: str, start: float, end: float):
    words = text.split()
    total_chars = sum(len(w) for w in words) or 1
    duration = end - start
    t = start
    out = []
    for w in words:
        w_dur = duration * (len(w) / total_chars)
        out.append({"text": w, "start": round(t, 3), "end": round(t + w_dur, 3)})
        t += w_dur
    return out


def main():
    cursor = 0.0
    all_words = []
    concat_list = []
    for i, sentence in enumerate(SCRIPT):
        wav_path = synth_sentence(sentence, i)
        dur = wav_duration(wav_path)
        all_words.extend(word_timestamps(sentence, cursor, cursor + dur))
        concat_list.append(wav_path)
        cursor += dur + SENT_GAP

        if SENT_GAP > 0:
            silence_path = f"{OUT_DIR}/silence_{i:02d}.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                 f"anullsrc=r=22050:cl=mono", "-t", str(SENT_GAP), silence_path],
                check=True,
            )
            concat_list.append(silence_path)

    # concat all wavs
    list_file = f"{OUT_DIR}/concat.txt"
    with open(list_file, "w") as f:
        for p in concat_list:
            f.write(f"file '{os.path.abspath(p)}'\n")
    audio_out = f"{OUT_DIR}/audio.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", list_file, audio_out],
        check=True,
    )

    total_dur = cursor
    video_out = f"{OUT_DIR}/test_source.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", f"mandelbrot=size=1280x720:rate=24",
            "-i", audio_out,
            "-t", f"{total_dur:.2f}",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            video_out,
        ],
        check=True,
    )

    transcript_out = f"{OUT_DIR}/test_transcript.json"
    with open(transcript_out, "w") as f:
        json.dump({"words": all_words}, f, indent=2)

    print(f"video: {video_out} ({total_dur:.1f}s)")
    print(f"transcript: {transcript_out} ({len(all_words)} words)")


if __name__ == "__main__":
    main()
