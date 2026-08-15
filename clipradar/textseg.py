"""Turn word-level transcript timestamps into sentence-level segments.

faster-whisper (and most ASR engines) give you a stream of words with
start/end times. Sentence boundaries matter a lot for clip quality: we
never want a clip to start or end mid-sentence. This module re-segments
the raw word stream into clean sentences using punctuation as the primary
signal and long pauses as a fallback for transcripts with sparse
punctuation.
"""

from dataclasses import dataclass, field

SENTENCE_END_CHARS = (".", "?", "!")
PAUSE_BREAK_SECONDS = 0.9  # a silence this long is treated as a sentence break
MIN_SENTENCE_WORDS = 2


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class Sentence:
    text: str
    start: float
    end: float
    words: list = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def word_count(self) -> int:
        return len(self.words)


def words_from_whisper_segments(segments) -> list:
    """Flatten faster-whisper's segment/word structure into a flat Word list."""
    words = []
    for seg in segments:
        seg_words = getattr(seg, "words", None) or []
        for w in seg_words:
            text = w.word.strip()
            if not text:
                continue
            words.append(Word(text=text, start=float(w.start), end=float(w.end)))
    return words


def words_from_dicts(word_dicts) -> list:
    """Build Word objects from plain dicts, e.g. loaded from a JSON transcript."""
    return [Word(text=w["text"], start=float(w["start"]), end=float(w["end"])) for w in word_dicts]


def group_into_sentences(words) -> list:
    """Group a flat word stream into Sentence objects."""
    sentences = []
    current = []

    def flush():
        if not current:
            return
        text = " ".join(w.text for w in current).strip()
        sentences.append(Sentence(text=text, start=current[0].start, end=current[-1].end, words=list(current)))

    for i, w in enumerate(words):
        current.append(w)
        ends_sentence = w.text.rstrip().endswith(SENTENCE_END_CHARS)
        pause_break = False
        if i + 1 < len(words):
            gap = words[i + 1].start - w.end
            if gap >= PAUSE_BREAK_SECONDS and len(current) >= MIN_SENTENCE_WORDS:
                pause_break = True
        if ends_sentence or pause_break:
            flush()
            current = []
    flush()

    # Merge stray 1-word "sentences" (usually punctuation artifacts) into neighbors.
    merged = []
    for s in sentences:
        if merged and s.word_count < MIN_SENTENCE_WORDS:
            prev = merged[-1]
            prev.text = f"{prev.text} {s.text}".strip()
            prev.end = s.end
            prev.words.extend(s.words)
        else:
            merged.append(s)
    return merged
