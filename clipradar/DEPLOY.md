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

## 3. A live, working demo, for free — `app.py` (Hugging Face Spaces)

The landing page shows real output but doesn't run the pipeline live. `app.py`
at the repo root is a Gradio front-end over the exact same pipeline the CLI
uses — paste a URL or upload a file, get clips back in the browser — built
specifically to run on **Hugging Face Spaces' free CPU Basic tier**: 16GB
RAM, 2 vCPU, $0/month, no credit card. Full deploy steps, and honest notes
on its limits (shared CPU, no persistent disk, cold-start after idle), are
in `SPACES.md`.

This correction is worth flagging: an earlier version of this doc pointed at
Railway, Render, and Fly.io as options. Checked against their current (Aug
2026) pricing, none of them actually offer a workable free tier for this
workload — Railway's free tier is a 30-day trial credit only, Render's free
tier is 512MB RAM / 0.1 CPU (too slow for Whisper), and Fly.io no longer
offers a free tier to new accounts at all. Vercel's serverless functions are
still the wrong tool for the same reasons as before (no bundled `ffmpeg`, no
room for the Whisper model, hard timeout well under transcription+render
time) — that part hasn't changed.

If you outgrow Hugging Face's shared free CPU, **Google Cloud Run** has a
genuine non-trial free quota and request timeouts up to 60 minutes (long
enough to run the pipeline synchronously, no job queue needed) — see
`SPACES.md` for specifics. That's a real Dockerfile + GCP account, so treat
it as the next step up, not the hackathon-day option.

For the hackathon pitch itself, the safest fallback is still: run `clipradar`
locally on your laptop (fast, zero network dependency once the Whisper model
is cached) as backup in case the Space is cold or slow live, with the Space
as your primary "judges can actually try it" link and the Vercel landing
page as the pitch/proof artifact.
