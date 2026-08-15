"""Title / description / hashtag generation for a clip.

Default path is fully offline and deterministic: keyword extraction +
templated title patterns driven by which scoring factors actually fired
(so the copy reflects *why* the clip was picked). If ANTHROPIC_API_KEY is
set, `enhance_with_claude` will ask Claude for punchier alternatives and
falls back silently to the rule-based output on any error (no network,
no key, rate limit, etc.) — useful offline-first design for a live demo.
"""

import os
import re
from collections import Counter

from .lexicons import STOPWORDS

GENERIC_HASHTAGS = ["shorts", "reels", "fyp", "viral", "podcastclips", "contentcreator"]

TITLE_TEMPLATES_HOOK = [
    '"{hook}"',
    "{hook}",
    "This clip stops the scroll: {hook}",
]

TITLE_TEMPLATES_PLAIN = [
    "{keyword}: the moment nobody expected",
    "Wait for it... {keyword}",
    "The truth about {keyword}",
]


def _keywords(text: str, top_n: int = 6):
    words = re.findall(r"[a-z]+", text.lower())
    words = [w for w in words if w not in STOPWORDS and len(w) > 3]
    counts = Counter(words)
    return [w for w, _ in counts.most_common(top_n)]


def _clean_hook(sentence_text: str, max_len: int = 70) -> str:
    hook = sentence_text.strip()
    hook = hook[0].upper() + hook[1:] if hook else hook
    if len(hook) > max_len:
        hook = hook[:max_len].rsplit(" ", 1)[0] + "..."
    return hook


def generate_titles(candidate) -> list:
    hook_sentence = candidate.sentences[0].text.strip()
    if len(hook_sentence.split()) < 6 and len(candidate.sentences) > 1:
        # first sentence too short to stand alone as a title ("So what did I do.")
        hook_sentence = f"{hook_sentence} {candidate.sentences[1].text.strip()}"
    hook = _clean_hook(hook_sentence)
    keywords = _keywords(candidate.text)
    keyword = keywords[0] if keywords else "this"
    titles = []
    is_question = candidate.sentences[0].text.strip().endswith("?")
    if is_question or len(hook.split()) <= 14:
        titles.append(hook)
        titles.append(f"This clip stops the scroll: {hook}")
    else:
        titles.append(f"{keyword.capitalize()}: the moment nobody expected")
    titles.append(f"Wait for it... {keyword}")
    # de-dupe, keep order, cap at 3
    seen, out = set(), []
    for t in titles:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:3]


def generate_description(candidate, source_title: str = "") -> str:
    keywords = _keywords(candidate.text, top_n=4)
    lead = candidate.sentences[0].text.strip()
    tail = candidate.sentences[-1].text.strip()
    parts = [f'"{lead}"' if len(lead) < 90 else lead]
    if source_title:
        parts.append(f"Clipped from: {source_title}.")
    if keywords:
        parts.append(f"Topics: {', '.join(keywords)}.")
    parts.append("Full episode linked in bio.")
    return " ".join(parts)


def generate_hashtags(candidate, top_n: int = 8) -> list:
    keywords = _keywords(candidate.text, top_n=top_n)
    tags = [f"#{k}" for k in keywords]
    for g in GENERIC_HASHTAGS:
        if len(tags) >= top_n + len(GENERIC_HASHTAGS):
            break
        tag = f"#{g}"
        if tag not in tags:
            tags.append(tag)
    return tags[: top_n + 3]


def build_metadata(candidate, source_title: str = "") -> dict:
    return {
        "titles": generate_titles(candidate),
        "description": generate_description(candidate, source_title),
        "hashtags": generate_hashtags(candidate),
    }


def enhance_with_claude(candidate, base_metadata: dict) -> dict:
    """Optional: rewrite titles/description with Claude for extra polish.
    Silently returns base_metadata unchanged if no API key/network/error —
    this must never be the thing that breaks a live demo."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return base_metadata
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "You write punchy, non-clickbaity titles/descriptions/hashtags for "
            "short-form video clips (TikTok/Reels/Shorts). Given this clip transcript, "
            "return 3 title options (<70 chars each), a 2-sentence description, and 8 "
            "hashtags, as compact JSON with keys titles/description/hashtags.\n\n"
            f"Transcript: {candidate.text}"
        )
        resp = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        import json as _json

        text = resp.content[0].text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = _json.loads(match.group(0))
            if all(k in data for k in ("titles", "description", "hashtags")):
                return data
    except Exception:
        pass
    return base_metadata
