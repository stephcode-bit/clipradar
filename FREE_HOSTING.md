# Running ClipRadar as a free hosted app

`app.py` wraps the exact same pipeline the CLI uses (`clipradar/`) in a
Gradio UI — paste a URL or upload a file, get clips, thumbnails, and a
report back in the browser.

**Correction (Aug 2026):** an earlier version of this doc pointed at
Hugging Face Spaces' "CPU Basic" hardware as a free option under the
Gradio SDK. That's no longer accurate — confirmed directly against the
Space-creation UI (Static is free; Gradio and Docker are both now
paid-plan-only for new/free accounts; the only free compute path left on
HF is ZeroGPU, which targets GPU inference workloads, not this pipeline).
That was wrong information; here's what's actually free right now.

## Recommended for the hackathon: Colab + Gradio's built-in tunnel

The fastest path to a live, working, public link, with **zero deploy
step** — `clipradar_colab.ipynb` in this repo does it in one notebook:

1. Open `clipradar_colab.ipynb` in Google Colab (upload it, or open
   directly from GitHub via Colab's "File → Open notebook → GitHub" tab).
2. Edit the `REPO_URL` in the clone cell to point at your repo.
3. Run all cells top to bottom.
4. The last cell prints a `https://xxxxx.gradio.live` link — that's your
   live demo, judges can open it in any browser.

How it works: `app.py` now reads a `CLIPRADAR_SHARE` env var — set it to
`1` and `demo.queue().launch(..., share=True)` spins up Gradio's built-in
public tunnel. No account, no card, no config beyond that one flag.

**The honest trade-off:** this link is tied to the Colab runtime that
created it. It stays up while that notebook cell keeps running and the
tab stays active — Colab free tier disconnects idle runtimes after
roughly 90 minutes of no interaction with the page, and enforces a hard
session ceiling on top of that (commonly cited around 12 hours on the
free tier, and it varies). Translation: start the notebook 5–10 minutes
before you present, keep the tab open, and don't expect the URL to still
resolve tomorrow. It is not a substitute for a permanently-hosted app —
it's the right tool for "I need a working public demo link for a specific
presentation window," which is exactly what a one-day hackathon is.

Bonus: if you select a GPU runtime in Colab (Runtime → Change runtime
type), Whisper transcription is noticeably faster than CPU-only hosts,
which matters if you're demoing live and don't want judges watching a
progress bar.

## If you want a permanent free URL instead

**Streamlit Community Cloud** is genuinely free and gives you a stable
`*.streamlit.app` URL that doesn't depend on a notebook staying open.
Signup is GitHub-account-only, no card. The catch, and it's a real one
for this workload: the guaranteed memory allocation is **1GB RAM**
(confirmed via Streamlit's own community forum — some headroom up to
~3GB exists opportunistically but isn't guaranteed). `faster-whisper`'s
`small.en` model plus Python overhead plus an `ffmpeg` subprocess is tight
against 1GB, so `streamlit_app.py` (already in this repo) defaults to the
lighter `tiny.en` model instead — some transcription-accuracy trade-off
for headroom. The pipeline modules in `clipradar/` are unchanged; only the
UI layer differs between `app.py` (Gradio) and `streamlit_app.py`
(Streamlit) — deploy steps below.

**Google Cloud Run** has a real, non-trial perpetual free quota: 2M
requests/month, 180,000 vCPU-seconds/month, 360,000 GiB-seconds of
memory/month, in `us-central1`/`us-east1`/`us-west1`, with request
timeouts configurable up to 60 minutes — long enough to run the whole
pipeline synchronously with no job queue. This repo's `Dockerfile` is
already set up for it. The catch: it requires a GCP account with a
billing card on file (you won't be charged while under quota, but the
card is required to create the account). This is the strongest "real,
permanent, actually free" option if you're willing to do the GCP signup —
see the steps below.

**Oracle Cloud "Always Free"** tier is the most generous of all of these
on paper (an ARM Ampere VM up to 4 OCPU / 24GB RAM, perpetually free, no
trial expiry) but it's a bare VM — you SSH in, install Docker or Python
yourself, and manage the process (systemd, or just `tmux` + `python
app.py` for a hackathon). Worth knowing about if the above options don't
fit, but budget real setup time for it; Oracle's signup flow also has a
reputation for occasional friction (card verification, capacity
availability in some regions).

## Streamlit Community Cloud — deploy steps

No terminal needed for any of this — it's entirely a web dashboard flow.

1. Make sure your GitHub repo is up to date and includes `streamlit_app.py`,
   `requirements.txt` (now includes `streamlit`), and `packages.txt`
   (already contains `ffmpeg` — Streamlit Cloud reads this file
   automatically for system-level dependencies, same mechanism Spaces
   used).
2. Go to **share.streamlit.io** and sign in with your GitHub account
   (this doubles as account creation if you don't have one — no card,
   no separate signup form).
3. Click **Create app** (sometimes labeled "New app").
4. Choose **"Deploy a public app from GitHub"**, then pick:
   - Repository: your `clipradar` repo
   - Branch: `main`
   - Main file path: `streamlit_app.py` ← this is the important one, it's
     what tells Streamlit Cloud which file to run (not `app.py`, that's
     the Gradio version)
5. (Optional) Click **Advanced settings** before deploying if you want to
   set `CLIPRADAR_WHISPER_MODEL` or any other env var as a "Secret" — not
   required, `tiny.en` is already the default in `streamlit_app.py`.
6. Click **Deploy**. First build takes a few minutes (installing
   `requirements.txt` + `packages.txt`); you'll land on a live
   `https://your-app-name.streamlit.app` URL that stays up permanently —
   no notebook, no session to keep open.
7. Every future `git push` to `main` auto-redeploys the app, same as the
   Vercel landing page.

**One real limitation to know before you rely on this for the demo:**
Community Cloud apps that get little traffic can go to sleep and need a
"wake up" click on first visit — budget a moment for that the first time
a judge opens the link, same idea as Cloud Run's cold start below.

## Google Cloud Run — deploy steps

Two paths: the CLI (fastest once set up) or the Cloud Run console
(zero local install, works from any browser via Google's Cloud Shell).

### Account setup (needed either way)

1. Go to **console.cloud.google.com** and sign in / create a Google
   account if needed.
2. You'll be prompted to create a project — accept the default name or
   pick your own (e.g. `clipradar`). Note the **Project ID** shown, you'll
   need it.
3. Set up billing: **Billing → Link a billing account**, add a card. This
   is required to use Cloud Run at all, even fully inside the free quota —
   Google won't charge you unless you exceed it, but the card has to be on
   file.
4. Enable the two APIs Cloud Run needs: search **"Cloud Run API"** and
   **"Cloud Build API"** in the top search bar, click into each, click
   **Enable**. (If you skip this, the deploy command in the next step
   prompts you to enable them automatically anyway.)

### Path A — no local install, using Cloud Shell

1. In the Cloud Console, click the **Cloud Shell** icon (the `>_` icon,
   top right) — this opens a free browser-based terminal with `gcloud`
   already installed and authenticated as you. No local setup at all.
2. Clone your repo into it:
   ```bash
   git clone https://github.com/YOUR-USERNAME/clipradar.git
   cd clipradar
   ```
3. Run the deploy command (see below) directly in that Cloud Shell tab.

### Path B — local terminal

1. Install the `gcloud` CLI (instructions at
   `cloud.google.com/sdk/docs/install` for your OS), then:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
2. `cd` into your local `clipradar` repo folder.

### The deploy command (same for both paths)

```bash
gcloud run deploy clipradar \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --timeout 3600 \
  --port 7860 \
  --set-env-vars CLIPRADAR_WHISPER_MODEL=tiny.en
```

This builds the `Dockerfile` already in this repo via Cloud Build and
deploys the resulting container — no separate `docker build`/`docker push`
step needed. It'll ask "Allow unauthenticated invocations?" — say yes, so
judges can open the URL without a Google login. First build takes a few
minutes.

`gcloud` prints a `*.run.app` URL when it finishes — that's your permanent
link.

### Path C — even more clicks-only: deploy from the Console UI

If you'd rather not touch a terminal at all:
1. Cloud Console → **Cloud Run → Create service**.
2. Choose **"Continuously deploy from a repository"**, click **Set up with
   Cloud Build**, and authorize/select your GitHub repo.
3. Build type: **Dockerfile** (it'll auto-detect the one in this repo).
4. Under **Container, networking, security → Container**, set memory to
   4 GiB, CPU to 2, request timeout to 3600, and add the env var
   `CLIPRADAR_WHISPER_MODEL=tiny.en`.
5. Under **Authentication**, choose **Allow unauthenticated invocations**.
6. Click **Create**. Same result as the CLI path — a `*.run.app` URL, and
   it auto-redeploys on every push to `main`, same as Vercel/Streamlit.

### After deploying

- Visit the `*.run.app` URL a few minutes before your demo to "pre-warm"
  it — Cloud Run scales to zero when idle, so the very first request after
  a quiet period pays a cold-start cost (container boot + first-time
  Whisper model download).
- Check **Cloud Run → your service → Metrics** if you want to keep an eye
  on usage against the free quota (2M requests / 180,000 vCPU-seconds /
  360,000 GiB-seconds per month) — for a one-day hackathon demo you will
  not come close to these numbers.

## Known constraints worth knowing before you demo (any of the above)

- **No persistent disk** on any of these free options — every request's
  output lives in a temp directory for the life of that request/session.
  Fine for a demo, not for a product with user accounts.
- **Cold starts.** Cloud Run scales to zero when idle — the first request
  after a quiet period pays a startup cost (container boot + first-time
  Whisper model download, cached after that). Pre-warm before you present
  by hitting the URL a few minutes ahead of time.
- **Shared/limited CPU** on all free tiers. A several-minute podcast will
  take real wall-clock time to transcribe anywhere on this list. For a
  live demo, either pre-warm, or demo against a short (2–5 minute) clip
  so the audience isn't watching a progress bar.

For the hackathon pitch itself, the safest fallback is still: run
`clipradar` locally on your laptop (fast, zero network dependency once
the Whisper model is cached) as backup in case a hosted link is cold or
slow live, with the hosted link as your primary "judges can actually try
it" artifact and the Vercel landing page as the pitch/proof artifact.
