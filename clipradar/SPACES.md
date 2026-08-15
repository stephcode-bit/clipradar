# Running ClipRadar as a free hosted app (Hugging Face Spaces)

`app.py` wraps the exact same pipeline the CLI uses (`clipradar/`) in a Gradio
UI — paste a URL or upload a file, get clips, thumbnails, and a report back
in the browser. This is the genuinely free option, verified as of August 2026:

- **Hugging Face Spaces, CPU Basic hardware, Gradio SDK**: 16GB RAM, 2 vCPU,
  $0/month, no credit card. Sleeps after a period of inactivity and wakes
  automatically on the next visit.
- The catch: raw **Docker SDK** Spaces now require a paid plan. The **Gradio
  SDK** free tier does not — which is exactly why `app.py` is a Gradio app
  and not a bare FastAPI service. Gradio is a normal Python web framework
  under the hood, so it can shell out to `ffmpeg` and call `faster-whisper`
  just fine; the SDK label just controls which free hardware you're eligible
  for.

## Deploy steps

1. Create a free account at huggingface.co if you don't have one.
2. Create a new Space: **New → Space**. Pick the **Gradio** SDK and **CPU
   basic** hardware (free tier).
3. Push this repo's contents to the Space. Two ways to do it:

   **Via git** (a Space is just a git repo):
   ```bash
   git remote add space https://huggingface.co/spaces/YOUR-USERNAME/clipradar
   git push space main
   ```

   **Via the `huggingface_hub` CLI**:
   ```bash
   pip install huggingface_hub
   huggingface-cli login
   huggingface-cli upload YOUR-USERNAME/clipradar . --repo-type=space
   ```

4. The Space reads `requirements.txt` (Python deps, already includes
   `gradio`) and `packages.txt` (system deps — just `ffmpeg`) automatically.
   No Dockerfile needed.
5. First launch will download the Whisper model (`small.en` by default,
   ~500MB) — that happens once per Space restart, not per request, but the
   very first request after a cold start will be slow. Set
   `CLIPRADAR_WHISPER_MODEL=tiny.en` as a Space secret/variable if you want
   a smaller, faster model at some accuracy cost — good tradeoff for a
   hackathon demo where judges are trying it live and won't wait 90 seconds.

## Known constraints worth knowing before you demo

- **No persistent disk.** Every request's output lives in a temp directory
  for the life of that request/session; nothing survives a Space restart.
  Fine for a demo, not for a product with user accounts.
- **Shared free CPU.** 2 vCPU is workable but not fast — a several-minute
  podcast will take real wall-clock time to transcribe. For a live demo,
  either pre-warm the Space (visit it a few minutes before you go on) or
  demo against a short (2-5 minute) clip so the audience isn't watching a
  progress bar for two minutes.
- **Concurrent users share that same 2 vCPU / 16GB box.** If several judges
  hit "Generate" at once, requests queue rather than running in true
  parallel. Gradio's `.queue()` (already enabled in `app.py`) handles this
  gracefully — it won't crash, it'll just process one at a time.

## If you outgrow the free tier

Google Cloud Run has a genuine, non-trial free quota (2M requests, 180,000
vCPU-seconds, 360,000 GiB-seconds of memory per month, in `us-central1`/
`us-east1`/`us-west1`) and supports request timeouts up to 60 minutes — long
enough to run the whole pipeline synchronously without building a job queue.
It needs a real Dockerfile and a GCP account with billing enabled (you won't
be charged while under quota, but a card is required on file). That's the
natural next step if HF Spaces' shared CPU becomes the bottleneck.

**Railway, Render, and Fly.io are not realistic free options for this
workload** as of August 2026 — worth knowing before you sink time into any
of them:
- Railway's "free" tier is a 30-day, $5 one-time trial credit; afterward
  it's a paid $1/month minimum plan capped at 0.5GB RAM / 1 vCPU, too small
  to reliably run Whisper + ffmpeg together.
- Render's free web service tier is 512MB RAM / 0.1 CPU — the CPU
  allocation alone makes transcription impractically slow, separate from
  the RAM being tight.
- Fly.io stopped offering a free tier to new accounts entirely.
