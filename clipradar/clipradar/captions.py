"""Burn-in caption generation (ASS subtitle format, rendered via ffmpeg's
libass filter).

Style: short punchy phrase chunks (2-4 words) that pop on screen in sync
with speech — the standard "Shorts/Reels" caption look — rather than full
subtitle lines sitting on screen for 5+ seconds.
"""

MAX_WORDS_PER_CHUNK = 3
CHUNK_PAUSE_BREAK = 0.5

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,72,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5,0,2,70,70,340,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _fmt_ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _chunk_words(words, clip_start: float):
    """Group a clip's word list into short display chunks."""
    chunks = []
    current = []
    for i, w in enumerate(words):
        current.append(w)
        at_limit = len(current) >= MAX_WORDS_PER_CHUNK
        ends_punct = w.text.rstrip().endswith((".", "?", "!", ","))
        pause = False
        if i + 1 < len(words):
            gap = words[i + 1].start - w.end
            pause = gap >= CHUNK_PAUSE_BREAK
        if at_limit or ends_punct or pause or i == len(words) - 1:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    return chunks


def build_ass(words, clip_start: float, clip_end: float) -> str:
    """Build ASS subtitle content for a single clip. Timestamps in `words`
    are absolute (relative to the source media); we rebase them to the
    clip's own timeline starting at 0."""
    lines = [ASS_HEADER]
    in_clip = [w for w in words if w.end > clip_start and w.start < clip_end]
    chunks = _chunk_words(in_clip, clip_start)
    for chunk in chunks:
        start = max(0.0, chunk[0].start - clip_start)
        end = max(start + 0.05, chunk[-1].end - clip_start)
        text = " ".join(w.text.upper() for w in chunk)
        text = text.replace("\n", " ")
        lines.append(
            f"Dialogue: 0,{_fmt_ts(start)},{_fmt_ts(end)},Caption,,0,0,0,,{text}"
        )
    return "\n".join(lines) + "\n"


def write_ass(words, clip_start: float, clip_end: float, out_path: str):
    content = build_ass(words, clip_start, clip_end)
    with open(out_path, "w") as f:
        f.write(content)
    return out_path
