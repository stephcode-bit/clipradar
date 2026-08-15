# ClipRadar

**Long-form video in → ranked, ready-to-post vertical clips out — with an explainable "why this clip" score for every pick.**

Built solo for the Social Media Automation Hackathon.

## The problem

Repurposing a podcast or long-form video into Shorts/Reels/TikToks is the single most repetitive task in a creator's pipeline: scrub through 60+ minutes, guess which 30 seconds might hit, cut it, reframe it vertically, caption it by hand, come up with a title, write a description, pick hashtags. Most "auto-clip" tools either (a) just detect silence/scene changes and call it a highlight, or (b) pipe your transcript into an LLM and hope, with zero explanation of *why* it picked what it picked — which means you still have to watch every candidate to know if it's trustworthy.

## What ClipRadar does

Point it at a video (`--url` for YouTube/anything yt-dlp supports, or `--file` for a local file) and it:

1. **Transcribes** locally with word-level timestamps (`faster-whisper`, no API key, no per-minute cost).
2. **Scores every possible moment** in the video on 8 independent, human-readable signals — hook strength, emotional density, setup/payoff arc completeness, filler-word cleanliness, ideal duration fit, topical novelty vs. the rest of the video (TF-based), speech-pacing dynamics, and audio energy spikes — and combines them into a single 0–100 **explainable viral-moment score**.
3. **Picks the top N non-overlapping moments** (greedy selection with overlap suppression, so you don't get five versions of the same 40 seconds).
4. **Renders each as a vertical 9:16 clip** with a blurred-fill background (so no black bars) and burned-in, word-synced pop-up captions.
5. **Generates a thumbnail** — clean source frame + bold hook-text overlay + score badge.
6. **Writes title options, a description, and hashtags** for each clip, derived from the actual clip content (with an optional Claude-powered polish pass if `ANTHROPIC_API_KEY` is set — falls back silently to the rule-based copy if it's not, so a live demo never depends on network).
7. **Writes a full report** (`report.md` + `report.json`) showing every clip's score breakdown and the exact reasons it was picked — this is the artifact you'd actually show a client or teammate to justify the edit.

Nothing here is a black box. Every score factor is a small, readable function in `clipradar/scoring.py` — you can point at any clip and explain in one sentence why it beat the other 40 minutes of footage.

## Quickstart

```bash
pip install -r requirements.txt
# ffmpeg must be on PATH (with libass support, which most builds have)

python -m clipradar.cli --url "https://www.youtube.com/watch?v=XXXXXXXX" --num-clips 5
# or, on a local file:
python -m clipradar.cli --file podcast.mp4 --num-clips 5

# Already have a transcript (YouTube captions, Descript, Otter)? Skip Whisper entirely:
python -m clipradar.cli --file podcast.mp4 --transcript transcript.json --num-clips 5
```

Output lands in `output/<video-slug>/`: `clip1.mp4` ... `clipN.mp4`, matching thumbnails, and `report.md`/`report.json`.

## Architecture

```
clipradar/
  textseg.py      word stream -> clean sentence boundaries (punctuation + pause detection)
  lexicons.py      hand-tuned word lists (hooks, emotion, filler, resolution markers)
  scoring.py       candidate generation + 8-factor explainable scoring + overlap suppression
  audio_energy.py  ffmpeg-decoded RMS envelope -> energy-spike scoring signal
  transcribe.py    faster-whisper wrapper + JSON transcript load/save
  download.py      yt-dlp wrapper
  captions.py      word-synced ASS karaoke-style caption generation
  clipper.py       ffmpeg vertical reframe (blurred-fill 9:16) + caption burn-in
  thumbnail.py     PIL-based thumbnail: clean frame + hook-text overlay + score badge
  metadata.py      title/description/hashtag generation (+ optional Claude polish)
  report.py        report.md / report.json assembly
  cli.py           orchestrates the whole pipeline
```

Design choices worth calling out:

- **Offline-first.** Everything except the optional Claude copy-polish and (obviously) the initial download runs locally with no API keys. That's a deliberate reliability bet: a hackathon demo (or a creator's actual workflow) shouldn't go down because a third-party API rate-limited you mid-demo.
- **Explainability is a first-class output, not a debug log.** `report.md` is designed to be read by a human deciding whether to trust the tool, not just a developer.
- **Sentence-aware cutting.** Candidates are built by combining whole sentences, never truncating mid-thought — a cheap decision that matters a lot for perceived quality.
- **Karaoke-style burned captions**, not a static subtitle bar — matches what actually performs on Shorts/Reels/TikTok today.

## Testing without live YouTube/Whisper access

`scripts/make_test_fixture.py` synthesizes a fully offline test case: it uses `espeak-ng` to narrate a scripted mini-"podcast" (deliberately including a strong hook, filler words, and an emotional beat) over a generated background video, and writes a matching word-level `transcript.json`. This lets the entire pipeline — scoring, clip rendering, captions, thumbnails, metadata, report — be exercised end-to-end without any network dependency. `sample/test_transcript.json` is the fixture output; regenerate the matching video with:

```bash
python scripts/make_test_fixture.py
python -m clipradar.cli --file sample/test_source.mp4 --transcript sample/test_transcript.json --num-clips 3
```

See `sample/report.md` for a real report generated by this exact pipeline — nothing hand-edited.

## How this maps to the judging criteria

- **Functionality:** Runs end-to-end today — transcription, scoring, vertical rendering, burned captions, thumbnails, metadata, and a report — verified against a real rendered test case (`sample/report.md`, `sample/clip1_thumb.jpg`).
- **Creativity:** The explainable multi-factor scorer is the actual novel piece — most "auto-clip" tools give you a black-box pick or an LLM guess. This gives you a defensible, inspectable reason for every choice, computed from real signal (transcript structure, TF-based novelty, timing/pacing, audio energy) — not vibes.
- **Technical execution :** Clean modular architecture, no unnecessary heavyweight dependencies, offline-first with graceful optional enhancement (Claude copy polish), single-pass ffmpeg filter graphs for the vertical composite + caption burn, synthetic test fixture for reproducible offline verification.
- **Real-world/User Pain Points usefulness:** Solves the actual bottleneck (clip *selection*, not just cutting) that every podcast/YouTube-to-Shorts workflow hits, and hands back something genuinely postable — vertical video, captions, thumbnail, title/description/hashtags — not just timestamps you still have to act on.

## Known limitations / next steps

- Scoring lexicons are English-only and hand-tuned, not learned — a natural v2 is calibrating weights against real engagement data.
- No face-tracking/auto-reframe within the vertical crop yet (current approach centers the full frame); for multi-speaker video, an active-speaker-aware crop would be the next investment.
- No comment/analytics loop-back yet — scoring is transcript+audio only, not "clips like this performed well for you before."
