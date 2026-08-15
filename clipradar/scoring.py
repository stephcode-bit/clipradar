"""Explainable "viral moment" scoring engine.

Every candidate clip gets scored on eight independent, human-readable
signals. Nothing here is a black box — each factor is a small function you
can read top to bottom, and every clip ships with the exact reasons it
scored the way it did. That's the whole pitch of ClipRadar: not just "here
are 5 clips" but "here's *why* these 5 and not the other 40 minutes."

Weights sum to 1.0 and were tuned by hand against the intuition of what
makes a short-form clip work: a strong open, a complete arc, energy, and a
topic that stands on its own without the rest of the video for context.
"""

import re
from dataclasses import dataclass, field

from .lexicons import EMOTION_WORDS, FILLER_WORDS, HOOK_OPENERS, RESOLUTION_MARKERS, STOPWORDS

WEIGHTS = {
    "hook": 0.20,
    "emotion": 0.13,
    "arc": 0.15,
    "filler": 0.10,
    "duration_fit": 0.10,
    "novelty": 0.15,
    "pacing": 0.10,
    "energy": 0.07,
}

IDEAL_DURATION = 32.0  # seconds — sweet spot for Shorts/Reels/TikTok


@dataclass
class Candidate:
    sentences: list
    start: float
    end: float
    text: str = ""
    scores: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)
    total: float = 0.0

    @property
    def duration(self):
        return self.end - self.start


def _norm_words(text: str):
    return re.findall(r"[a-z']+", text.lower())


def _contains_phrase(text_lower: str, phrases) -> int:
    return sum(1 for p in phrases if p in text_lower)


def score_hook(candidate: Candidate) -> tuple:
    first_sentence = candidate.sentences[0].text.strip().lower()
    hits = _contains_phrase(first_sentence, HOOK_OPENERS)
    is_question = first_sentence.rstrip().endswith("?")
    score = min(1.0, hits * 0.45 + (0.45 if is_question else 0))
    reason = None
    if is_question and hits:
        reason = f'Opens with a direct question and a hook phrase ("{candidate.sentences[0].text.strip()[:60]}")'
    elif is_question:
        reason = "Opens with a question — a classic scroll-stopping hook"
    elif hits:
        reason = "Opens with a proven hook pattern (contrarian/curiosity phrasing)"
    return score, reason


def score_emotion(candidate: Candidate) -> tuple:
    words = _norm_words(candidate.text)
    if not words:
        return 0.0, None
    hits = sum(1 for w in words if w in EMOTION_WORDS)
    density = hits / max(len(words), 1)
    score = min(1.0, density * 12)
    reason = f"High emotional/superlative word density ({hits} charged words)" if hits >= 2 else None
    return score, reason


def score_arc(candidate: Candidate) -> tuple:
    text_lower = candidate.text.lower()
    ends_clean = candidate.sentences[-1].text.strip().endswith((".", "!", "?"))
    has_setup = candidate.sentences[0].text.strip().endswith("?") or _contains_phrase(
        candidate.sentences[0].text.lower(), HOOK_OPENERS
    )
    has_payoff = _contains_phrase(text_lower, RESOLUTION_MARKERS)
    score = 0.0
    reasons = []
    if ends_clean:
        score += 0.3
    if has_setup and has_payoff:
        score += 0.7
        reasons.append("Complete setup-and-payoff arc (opens with a question/hook, lands on a resolution)")
    elif ends_clean and len(candidate.sentences) >= 2:
        score += 0.2
    reason = reasons[0] if reasons else ("Ends on a complete thought" if ends_clean else None)
    return min(1.0, score), reason


def score_filler(candidate: Candidate) -> tuple:
    words = _norm_words(candidate.text)
    if not words:
        return 1.0, None
    hits = sum(1 for w in words if w in FILLER_WORDS)
    ratio = hits / len(words)
    score = max(0.0, 1.0 - ratio * 8)
    reason = "Clean delivery, almost no filler words" if ratio < 0.01 else None
    return score, reason


def score_duration_fit(candidate: Candidate) -> tuple:
    d = candidate.duration
    dist = abs(d - IDEAL_DURATION)
    score = max(0.0, 1.0 - dist / IDEAL_DURATION)
    reason = f"Runs {d:.0f}s — right in the sweet spot for Shorts/Reels/TikTok" if 20 <= d <= 45 else None
    return score, reason


def score_novelty(candidate: Candidate, full_text_terms: dict) -> tuple:
    """TF-based distinctiveness vs. the rest of the video: does this moment
    stand on its own topically, or is it interchangeable with any other
    minute of the video?"""
    words = [w for w in _norm_words(candidate.text) if w not in STOPWORDS and len(w) > 2]
    if not words:
        return 0.0, None
    from collections import Counter

    local = Counter(words)
    total_terms = sum(full_text_terms.values()) or 1
    distinct_score = 0.0
    top_terms = []
    for term, count in local.most_common(6):
        global_freq = full_text_terms.get(term, count) / total_terms
        local_freq = count / len(words)
        # terms that are locally common but globally rare score highest
        distinct_score += local_freq * (1 - min(global_freq * len(words), 1))
        if global_freq * total_terms <= max(2, count):
            top_terms.append(term)
    score = min(1.0, distinct_score * 3)
    reason = None
    if top_terms:
        reason = f"Distinct topic vs. rest of the video (\"{', '.join(top_terms[:3])}\") — works without context"
    return score, reason


def score_pacing(candidate: Candidate) -> tuple:
    """Reward bursts of speaking-rate change — a common signature of
    excitement, punchlines, or a speaker leaning into a moment."""
    sentences = candidate.sentences
    if len(sentences) < 2:
        return 0.0, None
    rates = []
    for s in sentences:
        if s.duration > 0.05:
            rates.append(s.word_count / s.duration)
    if len(rates) < 2:
        return 0.0, None
    mean_rate = sum(rates) / len(rates)
    variance = sum((r - mean_rate) ** 2 for r in rates) / len(rates)
    score = min(1.0, (variance ** 0.5) / max(mean_rate, 0.1))
    reason = "Noticeable speech-pace shifts — reads as energetic/animated" if score > 0.4 else None
    return score, reason


def score_energy(candidate: Candidate, energy_fn) -> tuple:
    if energy_fn is None:
        return 0.0, None
    peak_z = energy_fn(candidate.start, candidate.end)
    score = max(0.0, min(1.0, peak_z / 2.5))
    reason = "Audio energy spikes in this window (raised voice, laughter, or emphasis)" if score > 0.5 else None
    return score, reason


def build_candidates(sentences, min_dur: float, max_dur: float) -> list:
    candidates = []
    n = len(sentences)
    for i in range(n):
        acc = []
        for j in range(i, n):
            acc.append(sentences[j])
            start, end = acc[0].start, acc[-1].end
            dur = end - start
            if dur < min_dur:
                continue
            if dur > max_dur:
                break
            text = " ".join(s.text for s in acc)
            candidates.append(Candidate(sentences=list(acc), start=start, end=end, text=text))
    return candidates


def _global_term_freq(sentences):
    from collections import Counter

    counter = Counter()
    for s in sentences:
        for w in _norm_words(s.text):
            if w not in STOPWORDS and len(w) > 2:
                counter[w] += 1
    return counter


def score_candidate(candidate: Candidate, full_text_terms: dict, energy_fn=None) -> Candidate:
    factor_fns = {
        "hook": lambda c: score_hook(c),
        "emotion": lambda c: score_emotion(c),
        "arc": lambda c: score_arc(c),
        "filler": lambda c: score_filler(c),
        "duration_fit": lambda c: score_duration_fit(c),
        "novelty": lambda c: score_novelty(c, full_text_terms),
        "pacing": lambda c: score_pacing(c),
        "energy": lambda c: score_energy(c, energy_fn),
    }
    total = 0.0
    reasons = []
    for key, fn in factor_fns.items():
        s, reason = fn(candidate)
        s = max(0.0, min(1.0, s))
        candidate.scores[key] = s
        total += s * WEIGHTS[key]
        if reason:
            reasons.append(reason)
    candidate.total = round(total * 100, 1)
    candidate.reasons = reasons
    return candidate


def select_top_clips(candidates: list, num_clips: int, min_gap_ratio: float = 0.5) -> list:
    """Greedy non-max suppression: pick the highest scoring candidates while
    avoiding heavily overlapping picks so we don't return five versions of
    the same moment."""
    ranked = sorted(candidates, key=lambda c: c.total, reverse=True)
    chosen = []
    for cand in ranked:
        overlap = False
        for picked in chosen:
            latest_start = max(cand.start, picked.start)
            earliest_end = min(cand.end, picked.end)
            inter = max(0.0, earliest_end - latest_start)
            shorter = min(cand.duration, picked.duration)
            if shorter > 0 and inter / shorter > min_gap_ratio:
                overlap = True
                break
        if not overlap:
            chosen.append(cand)
        if len(chosen) >= num_clips:
            break
    return chosen


def rank_transcript(sentences, min_dur: float, max_dur: float, num_clips: int, energy_fn=None) -> list:
    full_terms = _global_term_freq(sentences)
    candidates = build_candidates(sentences, min_dur, max_dur)
    for c in candidates:
        score_candidate(c, full_terms, energy_fn)
    return select_top_clips(candidates, num_clips)
