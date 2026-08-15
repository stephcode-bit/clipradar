"""Small, hand-tuned word lists used by the scoring engine.

These are intentionally simple (no heavyweight NLP model) so the scorer
stays fast, dependency-light, and — crucially — *inspectable*: anyone can
open this file and see exactly why a moment scored the way it did.
"""

HOOK_OPENERS = {
    "why", "how", "what", "the truth", "nobody", "no one", "everyone thinks",
    "the biggest mistake", "the reason", "here's why", "here's the thing",
    "you won't believe", "stop", "never", "always", "the secret", "warning",
    "unpopular opinion", "the problem is", "i used to think", "turns out",
    "plot twist", "wait", "listen", "the real reason", "most people",
}

EMOTION_WORDS = {
    "amazing", "insane", "crazy", "shocking", "shocked", "terrifying",
    "unbelievable", "incredible", "wild", "brutal", "devastating", "furious",
    "heartbreaking", "hilarious", "obsessed", "love", "hate", "worst", "best",
    "huge", "massive", "tiny", "genius", "stupid", "ridiculous", "insanely",
    "literally", "actually", "genuinely", "terrified", "petrified", "thrilled",
    "nightmare", "dream", "explode", "exploded", "disaster", "miracle",
}

RESOLUTION_MARKERS = {
    "so", "that's why", "which means", "turns out", "and that's how",
    "the result was", "in the end", "eventually", "so what happened was",
    "and that's when", "long story short", "bottom line",
}

FILLER_WORDS = {
    "um", "uh", "uhh", "umm", "like", "you know", "sort of", "kind of",
    "basically", "actually", "i mean", "right", "so yeah", "just", "literally",
}

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for",
    "is", "it", "this", "that", "with", "as", "at", "by", "be", "was",
    "are", "were", "i", "you", "we", "they", "he", "she", "them", "his",
    "her", "its", "my", "your", "our", "their", "so", "if", "then", "than",
    "from", "not", "have", "has", "had", "do", "does", "did", "just",
    "about", "there", "here", "what", "which", "who", "when", "how", "why",
    "s", "t", "re", "ve", "ll", "d", "m",
}
