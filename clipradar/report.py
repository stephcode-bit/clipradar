"""Assemble the human-facing report: one Markdown file + one JSON file
summarizing every selected clip, its score breakdown, its "why", and the
generated metadata/filenames."""

import json
import os

from .scoring import WEIGHTS

FACTOR_LABELS = {
    "hook": "Hook strength",
    "emotion": "Emotional density",
    "arc": "Setup/payoff arc",
    "filler": "Clean delivery",
    "duration_fit": "Duration fit",
    "novelty": "Topical novelty",
    "pacing": "Pacing dynamics",
    "energy": "Audio energy",
}


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def build_report(video_title: str, source: str, clips: list, out_dir: str):
    json_path = os.path.join(out_dir, "report.json")
    md_path = os.path.join(out_dir, "report.md")

    data = {
        "source": source,
        "video_title": video_title,
        "clips": clips,
    }
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)

    lines = [f"# ClipRadar report — {video_title or source}", "", f"Source: `{source}`", ""]
    for i, clip in enumerate(clips, 1):
        c = clip["candidate"]
        lines.append(f"## Clip {i} — score {c['total']}/100")
        lines.append("")
        lines.append(f"**Timecode:** {_fmt_time(c['start'])} - {_fmt_time(c['end'])} ({c['duration']:.0f}s)")
        lines.append("")
        lines.append(f"**Transcript:** \"{c['text']}\"")
        lines.append("")
        lines.append("**Why this clip:**")
        for reason in c["reasons"]:
            lines.append(f"- {reason}")
        lines.append("")
        lines.append("**Score breakdown:**")
        lines.append("")
        lines.append("| Factor | Weight | Score |")
        lines.append("|---|---|---|")
        for key, weight in WEIGHTS.items():
            lines.append(f"| {FACTOR_LABELS[key]} | {weight*100:.0f}% | {c['scores'][key]*100:.0f}/100 |")
        lines.append("")
        meta = clip["metadata"]
        lines.append("**Suggested titles:**")
        for t in meta["titles"]:
            lines.append(f"- {t}")
        lines.append("")
        lines.append(f"**Description:** {meta['description']}")
        lines.append("")
        lines.append(f"**Hashtags:** {' '.join(meta['hashtags'])}")
        lines.append("")
        lines.append(f"**Files:** `{clip['video_file']}`, `{clip['thumbnail_file']}`")
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(md_path, "w") as f:
        f.write("\n".join(lines))

    return json_path, md_path
