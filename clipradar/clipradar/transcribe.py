"""Transcription backends.

Primary path: faster-whisper (CPU-friendly CTranslate2 build of Whisper),
run locally, word-level timestamps. No API key, no per-minute cost.

Fallback / offline-testing path: load a pre-computed transcript JSON in the
shape produced by `dump_transcript_json`. This is also a legitimate feature
on its own — creators who already have captions (YouTube auto-captions,
Descript, Otter) can skip re-transcribing entirely.
"""

import json

from .textseg import Sentence, Word, group_into_sentences, words_from_dicts


def transcribe_with_whisper(media_path: str, model_size: str = "small.en", device: str = "cpu"):
    from faster_whisper import WhisperModel

    compute_type = "int8" if device == "cpu" else "float16"
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, info = model.transcribe(media_path, word_timestamps=True, vad_filter=True)
    segments = list(segments)  # generator -> list, forces full decode

    words = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append(Word(text=text, start=float(w.start), end=float(w.end)))
    return words, info


def load_transcript_json(path: str):
    with open(path) as f:
        data = json.load(f)
    return words_from_dicts(data["words"])


def dump_transcript_json(words, path: str):
    data = {"words": [{"text": w.text, "start": w.start, "end": w.end} for w in words]}
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_sentences(media_path: str = None, model_size: str = "small.en", device: str = "cpu",
                   transcript_json: str = None):
    if transcript_json:
        words = load_transcript_json(transcript_json)
    else:
        words, _info = transcribe_with_whisper(media_path, model_size=model_size, device=device)
    return group_into_sentences(words), words
