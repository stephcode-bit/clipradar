"""Gradio web front-end for ClipRadar, built to run on Hugging Face Spaces'
free CPU Basic tier (16GB RAM / 2 vCPU, no cost, no credit card).

This reuses every module in clipradar/ as-is — it's a thin UI layer over
the same pipeline the CLI drives (clipradar/cli.py). Nothing about the
scoring, rendering, or metadata logic changes; this just gives it a
browser front-end instead of argparse flags.

Run locally:      python app.py
Deploy to Spaces:  see SPACES.md
"""

import os
import shutil
import tempfile
import traceback

import gradio as gr

from clipradar import audio_energy, clipper, download, metadata, report, scoring, thumbnail, transcribe
from clipradar.captions import write_ass
from clipradar.cli import slugify

WHISPER_MODEL = os.environ.get("CLIPRADAR_WHISPER_MODEL", "small.en")


def process(source_url, source_file, num_clips, min_dur, max_dur, progress=gr.Progress()):
    if not source_url and source_file is None:
        raise gr.Error("Provide a video URL or upload a file.")

    work_root = tempfile.mkdtemp(prefix="clipradar_")
    try:
        progress(0.02, desc="Fetching source video...")
        if source_file is not None:
            source_path = source_file
            video_title = os.path.splitext(os.path.basename(source_file))[0]
        else:
            source_path = download.download_video(source_url, os.path.join(work_root, "_source"))
            video_title = os.path.basename(source_path)

        slug = slugify(video_title)
        out_dir = os.path.join(work_root, slug)
        os.makedirs(out_dir, exist_ok=True)

        progress(0.12, desc=f"Transcribing locally ({WHISPER_MODEL})... this is the slow step")
        sentences, words = transcribe.get_sentences(media_path=source_path, model_size=WHISPER_MODEL)
        if not sentences:
            raise gr.Error("Couldn't get a transcript from that source — check the URL/file and try again.")

        progress(0.55, desc="Analyzing audio energy...")
        try:
            energy_fn = audio_energy.build_energy_lookup(source_path)
        except Exception:
            energy_fn = None

        progress(0.62, desc="Scoring candidate moments...")
        chosen = scoring.rank_transcript(
            sentences, min_dur=float(min_dur), max_dur=float(max_dur),
            num_clips=int(num_clips), energy_fn=energy_fn,
        )
        if not chosen:
            raise gr.Error("No candidate moments matched your duration range — try widening min/max duration.")

        clip_records = []
        video_paths, thumb_paths = [], []
        for i, cand in enumerate(chosen, 1):
            frac = 0.62 + 0.35 * (i / len(chosen))
            progress(frac, desc=f"Rendering clip {i}/{len(chosen)}...")

            ass_path = os.path.join(out_dir, f"clip{i}.ass")
            write_ass(words, cand.start, cand.end, ass_path)

            video_out = os.path.join(out_dir, f"clip{i}.mp4")
            clipper.render_vertical_clip(source_path, cand.start, cand.end, ass_path, video_out)

            frame_path = os.path.join(out_dir, f"clip{i}_frame.jpg")
            frame_ts = cand.start + min(1.0, (cand.end - cand.start) / 3)
            clipper.extract_vertical_frame(source_path, frame_ts, frame_path)

            thumb_path = os.path.join(out_dir, f"clip{i}_thumb.jpg")
            thumbnail.make_thumbnail(frame_path, cand.sentences[0].text, f"{cand.total:.0f}", thumb_path)

            meta = metadata.enhance_with_claude(cand, metadata.build_metadata(cand, source_title=video_title))

            clip_records.append({
                "candidate": {
                    "start": cand.start, "end": cand.end, "duration": cand.duration,
                    "text": cand.text, "total": cand.total, "scores": cand.scores, "reasons": cand.reasons,
                },
                "metadata": meta,
                "video_file": os.path.basename(video_out),
                "thumbnail_file": os.path.basename(thumb_path),
            })
            video_paths.append(video_out)
            thumb_paths.append(thumb_path)

        progress(0.98, desc="Writing report...")
        _json_path, md_path = report.build_report(video_title, source_url or "uploaded file", clip_records, out_dir)
        with open(md_path) as f:
            report_md = f.read()

        gallery = list(zip(thumb_paths, [f"Clip {i+1} — score {c['candidate']['total']}" for i, c in enumerate(clip_records)]))
        first_video = video_paths[0] if video_paths else None
        progress(1.0, desc="Done")
        return first_video, gallery, report_md, video_paths

    except gr.Error:
        raise
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(f"Something went wrong: {e}")


with gr.Blocks(title="ClipRadar") as demo:
    gr.Markdown(
        "# ClipRadar\n"
        "Long-form video in. Ranked, ready-to-post vertical clips out — with a reason for every pick.\n\n"
        "Paste a video URL (anything `yt-dlp` supports) **or** upload a file. "
        "First run downloads the Whisper model, so it's slower — after that it's just transcription + render time."
    )
    with gr.Row():
        with gr.Column(scale=1):
            url_in = gr.Textbox(label="Video URL", placeholder="https://youtube.com/watch?v=...")
            file_in = gr.Video(label="...or upload a file", sources=["upload"])
            num_clips = gr.Slider(1, 8, value=3, step=1, label="Number of clips")
            min_dur = gr.Slider(5, 60, value=15, step=1, label="Min clip duration (s)")
            max_dur = gr.Slider(15, 120, value=60, step=1, label="Max clip duration (s)")
            run_btn = gr.Button("Generate clips", variant="primary")
        with gr.Column(scale=1):
            preview = gr.Video(label="Top clip preview")
            gallery = gr.Gallery(label="All clips (ranked)", columns=4, height=260)
    report_out = gr.Markdown(label="Report")
    files_out = gr.File(label="Download all clips", file_count="multiple")

    run_btn.click(
        process,
        inputs=[url_in, file_in, num_clips, min_dur, max_dur],
        outputs=[preview, gallery, report_out, files_out],
    )

if __name__ == "__main__":
    demo.queue().launch()
