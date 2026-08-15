"""ClipRadar CLI — drop in a long-form video, get back ranked, ready-to-post
vertical clips with burned captions, thumbnails, and metadata.

Usage:
    python -m clipradar.cli --url https://youtube.com/watch?v=... --out output/
    python -m clipradar.cli --file podcast.mp4 --out output/
    python -m clipradar.cli --file podcast.mp4 --transcript transcript.json --out output/  # skip whisper
"""

import argparse
import os
import re
import sys
import time

from . import audio_energy, clipper, download, metadata, report, scoring, thumbnail, transcribe


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:40] or "video"


def log(msg: str):
    print(f"[clipradar] {msg}", flush=True)


def run(args):
    t0 = time.time()
    os.makedirs(args.out, exist_ok=True)

    if args.url:
        log(f"Downloading source video: {args.url}")
        source_path = download.download_video(args.url, os.path.join(args.out, "_source"))
        video_title = args.title or os.path.basename(source_path)
    elif args.file:
        source_path = args.file
        video_title = args.title or os.path.splitext(os.path.basename(args.file))[0]
    else:
        raise SystemExit("Provide --url or --file")

    slug = slugify(video_title)
    work_dir = os.path.join(args.out, slug)
    os.makedirs(work_dir, exist_ok=True)

    log("Transcribing..." if not args.transcript else f"Loading transcript: {args.transcript}")
    sentences, words = transcribe.get_sentences(
        media_path=source_path, model_size=args.whisper_model, transcript_json=args.transcript
    )
    log(f"Got {len(sentences)} sentences / {len(words)} words")
    if not args.no_cache_transcript and not args.transcript:
        transcribe.dump_transcript_json(words, os.path.join(work_dir, "transcript.json"))

    energy_fn = None
    if not args.skip_energy:
        log("Analyzing audio energy...")
        try:
            energy_fn = audio_energy.build_energy_lookup(source_path)
        except Exception as e:
            log(f"Audio energy analysis skipped ({e})")

    log("Scoring candidate moments...")
    chosen = scoring.rank_transcript(
        sentences, min_dur=args.min_dur, max_dur=args.max_dur, num_clips=args.num_clips, energy_fn=energy_fn
    )
    log(f"Selected {len(chosen)} clips")

    clip_records = []
    for i, cand in enumerate(chosen, 1):
        log(f"Rendering clip {i}/{len(chosen)}  score={cand.total}  "
            f"[{cand.start:.1f}s - {cand.end:.1f}s]  \"{cand.text[:60]}...\"")

        ass_path = os.path.join(work_dir, f"clip{i}.ass")
        from .captions import write_ass
        write_ass(words, cand.start, cand.end, ass_path)

        video_out = os.path.join(work_dir, f"clip{i}.mp4")
        clipper.render_vertical_clip(source_path, cand.start, cand.end, ass_path, video_out)

        frame_path = os.path.join(work_dir, f"clip{i}_frame.jpg")
        frame_ts = cand.start + min(1.0, (cand.end - cand.start) / 3)
        clipper.extract_vertical_frame(source_path, frame_ts, frame_path)

        thumb_path = os.path.join(work_dir, f"clip{i}_thumb.jpg")
        thumbnail.make_thumbnail(frame_path, cand.sentences[0].text, f"{cand.total:.0f}", thumb_path)

        base_meta = metadata.build_metadata(cand, source_title=video_title)
        final_meta = metadata.enhance_with_claude(cand, base_meta)

        clip_records.append({
            "candidate": {
                "start": cand.start, "end": cand.end, "duration": cand.duration,
                "text": cand.text, "total": cand.total, "scores": cand.scores, "reasons": cand.reasons,
            },
            "metadata": final_meta,
            "video_file": os.path.basename(video_out),
            "thumbnail_file": os.path.basename(thumb_path),
        })

    json_path, md_path = report.build_report(video_title, args.url or args.file, clip_records, work_dir)
    log(f"Report written: {md_path}")
    log(f"Done in {time.time() - t0:.1f}s. Output: {work_dir}")
    return work_dir


def main():
    p = argparse.ArgumentParser(description="ClipRadar: long-form -> ranked short-form clips")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="YouTube (or any yt-dlp supported) URL")
    src.add_argument("--file", help="Local video/audio file path")
    p.add_argument("--out", default="output", help="Output directory")
    p.add_argument("--title", help="Override video title used for slug/metadata")
    p.add_argument("--transcript", help="Path to a pre-computed transcript.json (skips Whisper)")
    p.add_argument("--no-cache-transcript", action="store_true", help="Don't save transcript.json")
    p.add_argument("--whisper-model", default="small.en", help="faster-whisper model size")
    p.add_argument("--num-clips", type=int, default=5)
    p.add_argument("--min-dur", type=float, default=15.0)
    p.add_argument("--max-dur", type=float, default=60.0)
    p.add_argument("--skip-energy", action="store_true", help="Skip audio-energy scoring signal")
    args = p.parse_args()
    run(args)


if __name__ == "__main__":
    main()
