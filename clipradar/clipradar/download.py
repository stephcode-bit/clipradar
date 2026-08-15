"""Thin wrapper around yt-dlp for pulling a source video down to local disk."""

import os


def download_video(url: str, out_dir: str) -> str:
    import yt_dlp

    os.makedirs(out_dir, exist_ok=True)
    out_tmpl = os.path.join(out_dir, "source.%(ext)s")
    ydl_opts = {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "outtmpl": out_tmpl,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    for fname in os.listdir(out_dir):
        if fname.startswith("source."):
            return os.path.join(out_dir, fname)
    raise RuntimeError("yt-dlp reported success but no source file was found")
