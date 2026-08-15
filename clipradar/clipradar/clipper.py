"""ffmpeg-based clip assembly: cut the source, reframe to vertical 9:16 with
a blurred fill background, and burn in the ASS captions — all in one pass.
"""

import os
import subprocess

OUT_W, OUT_H = 1080, 1920


def _escape_filter_path(path: str) -> str:
    abspath = os.path.abspath(path)
    return abspath.replace("\\", "/").replace(":", "\\:")


def render_vertical_clip(source_path: str, start: float, end: float, ass_path: str, out_path: str,
                          pad_before: float = 0.15, pad_after: float = 0.35):
    duration = max(0.5, (end - start) + pad_before + pad_after)
    ss = max(0.0, start - pad_before)
    ass_escaped = _escape_filter_path(ass_path)

    filter_complex = (
        f"[0:v]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
        f"crop={OUT_W}:{OUT_H},gblur=sigma=25,eq=brightness=-0.08[bg];"
        f"[0:v]scale={OUT_W}:-2:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2[base];"
        f"[base]ass='{ass_escaped}'[outv]"
    )

    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{ss:.3f}", "-i", source_path,
        "-t", f"{duration:.3f}",
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        out_path,
    ]
    subprocess.run(cmd, check=True)
    return out_path


def extract_frame(source_path: str, timestamp: float, out_path: str):
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{max(0.0, timestamp):.3f}", "-i", source_path,
        "-frames:v", "1",
        out_path,
    ]
    subprocess.run(cmd, check=True)
    return out_path


def extract_vertical_frame(source_path: str, timestamp: float, out_path: str):
    """Grab a single frame from the *source* (no captions) and reframe it to
    the same vertical blurred-background composite used for clips — used
    for thumbnail generation so the base image is clean text-free footage."""
    filter_complex = (
        f"[0:v]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
        f"crop={OUT_W}:{OUT_H},gblur=sigma=25,eq=brightness=-0.08[bg];"
        f"[0:v]scale={OUT_W}:-2:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
    )
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{max(0.0, timestamp):.3f}", "-i", source_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-frames:v", "1",
        out_path,
    ]
    subprocess.run(cmd, check=True)
    return out_path


def probe_duration(media_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", media_path,
    ]
    out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0
