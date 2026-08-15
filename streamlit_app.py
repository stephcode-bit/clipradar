"""Streamlit web front-end for ClipRadar — for Streamlit Community Cloud's
free, permanent hosting tier.

This is a UI-only alternative to app.py (which is Gradio, for Colab/Cloud
Run/local). Both call the exact same clipradar/ pipeline — nothing about
scoring, rendering, or metadata logic changes between them.

Streamlit Community Cloud's free tier guarantees only 1GB RAM, so this
defaults to the "tiny.en" Whisper model instead of app.py's "small.en" —
lighter weight, some transcription-accuracy trade-off. Override with the
CLIPRADAR_WHISPER_MODEL env var (Streamlit Cloud: App settings -> Secrets)
if you're testing locally or move to a paid tier.

Run locally:  streamlit run streamlit_app.py
Deploy free:  see FREE_HOSTING.md
"""

import os
import tempfile
import traceback

import streamlit as st

from clipradar import audio_energy, clipper, download, metadata, report, scoring, thumbnail, transcribe
from clipradar.captions import write_ass
from clipradar.cli import slugify

WHISPER_MODEL = os.environ.get("CLIPRADAR_WHISPER_MODEL", "tiny.en")

st.set_page_config(page_title="ClipRadar", page_icon="\U0001F3AC", layout="wide")

st.title("ClipRadar")
st.caption(
    "Long-form video in. Ranked, ready-to-post vertical clips out — with a reason for every pick."
)

with st.sidebar:
    st.header("Source")
    source_url = st.text_input("Video URL", placeholder="https://youtube.com/watch?v=...")
    source_file = st.file_uploader(
        "...or upload a file",
        type=["mp4", "mov", "mkv", "webm", "m4a", "mp3", "wav"],
    )
    st.header("Clip settings")
    num_clips = st.slider("Number of clips", 1, 8, 3)
    min_dur = st.slider("Min clip duration (s)", 5, 60, 15)
    max_dur = st.slider("Max clip duration (s)", 15, 120, 60)
    run_clicked = st.button("Generate clips", type="primary", use_container_width=True)
    st.caption(f"Whisper model: `{WHISPER_MODEL}` (set via CLIPRADAR_WHISPER_MODEL)")


def process(source_url, uploaded_file, num_clips, min_dur, max_dur):
    work_root = tempfile.mkdtemp(prefix="clipradar_")
    progress = st.progress(0, text="Starting...")

    if uploaded_file is not None:
        source_path = os.path.join(work_root, uploaded_file.name)
        with open(source_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        video_title = os.path.splitext(uploaded_file.name)[0]
    else:
        progress.progress(2, text="Fetching source video...")
        source_path = download.download_video(source_url, os.path.join(work_root, "_source"))
        video_title = os.path.basename(source_path)

    slug = slugify(video_title)
    out_dir = os.path.join(work_root, slug)
    os.makedirs(out_dir, exist_ok=True)

    progress.progress(12, text=f"Transcribing locally ({WHISPER_MODEL})... this is the slow step")
    sentences, words = transcribe.get_sentences(media_path=source_path, model_size=WHISPER_MODEL)
    if not sentences:
        progress.empty()
        st.error("Couldn't get a transcript from that source — check the URL/file and try again.")
        return

    progress.progress(55, text="Analyzing audio energy...")
    try:
        energy_fn = audio_energy.build_energy_lookup(source_path)
    except Exception:
        energy_fn = None

    progress.progress(62, text="Scoring candidate moments...")
    chosen = scoring.rank_transcript(
        sentences, min_dur=float(min_dur), max_dur=float(max_dur),
        num_clips=int(num_clips), energy_fn=energy_fn,
    )
    if not chosen:
        progress.empty()
        st.error("No candidate moments matched your duration range — try widening min/max duration.")
        return

    clip_records = []
    video_paths, thumb_paths = [], []
    for i, cand in enumerate(chosen, 1):
        frac = 62 + int(35 * (i / len(chosen)))
        progress.progress(frac, text=f"Rendering clip {i}/{len(chosen)}...")

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

    progress.progress(98, text="Writing report...")
    _json_path, md_path = report.build_report(video_title, source_url or "uploaded file", clip_records, out_dir)
    with open(md_path) as f:
        report_md = f.read()

    progress.progress(100, text="Done")
    progress.empty()

    st.success(f"Generated {len(clip_records)} clip(s).")

    cols = st.columns(len(clip_records))
    for col, rec, vpath in zip(cols, clip_records, video_paths):
        with col:
            st.video(vpath)
            st.metric("Score", rec["candidate"]["total"])
            st.caption(rec["metadata"].get("title", ""))
            with open(vpath, "rb") as vf:
                st.download_button(
                    "Download clip", vf, file_name=os.path.basename(vpath), key=vpath,
                )

    st.markdown("---")
    st.markdown(report_md)


if run_clicked:
    if not source_url and source_file is None:
        st.error("Provide a video URL or upload a file.")
    else:
        try:
            process(source_url, source_file, num_clips, min_dur, max_dur)
        except Exception as e:
            traceback.print_exc()
            st.error(f"Something went wrong: {e}")
else:
    st.info("Paste a video URL or upload a file in the sidebar, then click **Generate clips**.")
