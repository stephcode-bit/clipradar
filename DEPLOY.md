# Deploying ClipRadar

This repo has two very different things in it, and they belong on two different hosts:

- **`clipradar/`** — the actual tool (transcription, scoring, video rendering). This does real work: downloads video, runs a local ML model, shells out to `ffmpeg`, writes large files. It needs a real machine with disk and no hard timeout.
- **`landing/`** — a static pitch page (HTML/CSS/JS, no build step, no backend). This is what belongs on Vercel.

## 1. Push the code to GitHub (do this first)

Judges will want to read the code — that's part of "technical execution." From inside this folder:

```bash
git init                     # skip if already a repo
git add .
git commit -m "ClipRadar: explainable auto-clipping for creators"
```

Then create an empty repo on GitHub (github.com/new — don't initialize it with a README), and:

```bash
git remote add origin https://github.com/YOUR-USERNAME/clipradar.git
git branch -M main
git push -u origin main
```

If you have the `gh` CLI installed and logged in, this replaces the "create an empty repo" step:

```bash
gh repo create clipradar --public --source=. --remote=origin --push
```

**After this, go update the placeholder GitHub links** in `landing/index.html` — search for `YOUR-USERNAME` (3 occurrences) and replace with your real repo URL:

```bash
sed -i 's#YOUR-USERNAME/clipradar#your-actual-username/clipradar#g' landing/index.html
```

## 2. Deploy the landing page to Vercel

The landing page is plain static HTML with no dependencies — this is exactly what Vercel is built for, and it's a genuinely good fit (unlike the tool itself).

**Easiest path — Vercel dashboard:**
1. Go to vercel.com → **Add New… → Project**.
2. Import the GitHub repo you just pushed.
3. Under **Root Directory**, click Edit and select `landing`.
4. Framework preset: **Other** (it's static — no build command needed).
5. Deploy. You'll get a `*.vercel.app` URL in under a minute.

**Or via CLI**, from the `landing/` folder:

```bash
npm i -g vercel        # if you don't have it
cd landing
vercel                 # follow the prompts, accept defaults
vercel --prod           # promote to your production URL
```

Either way, every future `git push` to `main` will auto-redeploy the site if you used the dashboard/GitHub integration.

## 3. A live, working demo, for free — `app.py`

The landing page shows real output but doesn't run the pipeline live.
`app.py` at the repo root is a Gradio front-end over the exact same
pipeline the CLI uses — paste a URL or upload a file, get clips back in
the browser.

**Correction:** an earlier version of this doc, and this repo's old
`SPACES.md`, recommended Hugging Face Spaces' "CPU Basic" free tier under
the Gradio SDK. That turned out to be wrong/outdated — as of Aug 2026,
Hugging Face only offers the **Static** and **ZeroGPU** SDKs for free;
Gradio and Docker Spaces both now require a paid plan for new accounts.
`SPACES.md` has been replaced with **`FREE_HOSTING.md`**, which covers
what's actually free right now:

- **Colab + Gradio's built-in tunnel** (recommended for the hackathon) —
  open `clipradar_colab.ipynb`, run it, get a live `*.gradio.live` link in
  a few minutes, zero deploy step. Temporary (tied to the Colab session),
  which is fine for a presentation window.
- **Streamlit Community Cloud** — genuinely free, permanent URL. Deploy
  `streamlit_app.py` (already in this repo, a Streamlit port of `app.py`
  that defaults to the lighter `tiny.en` Whisper model to fit the free
  tier's 1GB RAM ceiling — no porting work left to do).
- **Google Cloud Run** — a real, non-trial free quota (2M requests,
  180,000 vCPU-seconds/month, 60-minute request timeouts) using the
  `Dockerfile` already in this repo. Requires a GCP account with a card
  on file (not charged under quota).
- **Oracle Cloud Always Free** — most generous specs, most setup effort
  (bare VM, manual install).

Railway, Render, and Fly.io remain not viable for this workload's free
tiers (30-day trial credit only, 512MB/0.1 CPU, and no free tier for new
accounts, respectively) — that part of the earlier research still holds.
Vercel's serverless functions are still the wrong tool for the landing
page's neighbor reasons: no bundled `ffmpeg`, no room for the Whisper
model, hard timeout well under transcription+render time.

Full steps and honest trade-offs for every option above are in
`FREE_HOSTING.md`.

For the hackathon pitch itself, the safest fallback is still: run
`clipradar` locally on your laptop (fast, zero network dependency once the
Whisper model is cached) as backup in case a hosted link is cold or slow
live, with the hosted link as your primary "judges can actually try it"
artifact and the Vercel landing page as the pitch/proof artifact.
