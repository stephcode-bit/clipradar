# ClipRadar — container image for Fly.io / Render / Cloud Run / any Docker host.
# (Hugging Face Spaces does NOT use this file — it reads requirements.txt +
# packages.txt directly. This Dockerfile is for everywhere else.)

FROM python:3.11-slim

# ffmpeg (with libass for burned captions) + fonts for thumbnail/caption rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CLIPRADAR_WHISPER_MODEL=small.en
EXPOSE 7860

CMD ["python", "app.py"]
