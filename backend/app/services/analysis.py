import json
from .ai import chat, parse_json
from ..config import settings


SYSTEM = """You are an expert short-form video strategist and editor for TikTok, Instagram Reels and YouTube Shorts.
You analyze full video transcripts and identify the best self-contained moments to turn into vertical clips.
You never invent quotes or change meaning. You only select time ranges from the provided transcript.
You return STRICT JSON only, no prose, no markdown."""


def build_transcript_text(segments: list) -> str:
    lines = []
    for s in segments:
        lines.append(f"[{s['start']:.2f}-{s['end']:.2f}] {s['text']}")
    return "\n".join(lines)


async def analyze(cfg: dict, duration: float, segments: list, clip_count: int, clip_duration: int,
                 platform: str, priority: str, cut_aggressiveness: str) -> list[dict]:
    transcript = build_transcript_text(segments)
    auto = (clip_count == 0)
    n_instruction = "Choose the optimal number of clips (between 5 and 12)." if auto else f"Choose exactly {clip_count} clips."
    dur_instruction = f"Target clip length around {clip_duration} seconds (acceptable range {max(10, clip_duration-10)}-{clip_duration+15}s)."
    prompt = f"""Video duration: {duration:.1f}s
Platform: {platform}
Priority focus: {priority}
Cut aggressiveness: {cut_aggressiveness}
{n_instruction}
{dur_instruction}

Transcript with timestamps:
{transcript}

Task:
1. Identify the most engaging, self-contained moments suitable as short-form clips.
2. Each clip must start with a strong hook (no long intros), have enough context, a satisfying ending, no cut words.
3. Avoid overlapping clips (max 30% overlap). Avoid near-duplicate clips.
4. Score each clip 0-100 viral potential using the breakdown.

Return JSON:
{{
  "clips": [
    {{
      "start": 12.34,
      "end": 45.67,
      "viral_score": 82,
      "category": "humor|controversy|education|storytelling|entertainment|mixed",
      "hook": "the opening hook phrase",
      "titles": ["title 1", "title 2", "title 3"],
      "description": "short description",
      "hashtags": ["#tag1", "#tag2"],
      "explanation": "why this moment works",
      "score_breakdown": {{
        "hook": 0-10,
        "retention": 0-10,
        "interest": 0-10,
        "emotion": 0-10,
        "clarity": 0-10,
        "comments": 0-10,
        "shares": 0-10,
        "autonomy": 0-10,
        "closure": 0-10
      }}
    }}
  ]
}}
Ensure start/end are within [0,{duration:.1f}] and start<end.
"""
    raw = await chat(cfg, SYSTEM, prompt, max_tokens=6000)
    data = parse_json(raw)
    clips = data.get("clips", []) if isinstance(data, dict) else data
    # sanitize
    out = []
    for c in clips:
        try:
            s = float(c["start"]); e = float(c["end"])
        except Exception:
            continue
        s = max(0.0, min(duration, s))
        e = max(s + 1.0, min(duration, e))
        if e - s < 3:
            continue
        sb = c.get("score_breakdown") or {}
        # normalize score if breakdown present
        if not c.get("viral_score"):
            vals = [v for v in sb.values() if isinstance(v, (int, float))]
            if vals:
                c["viral_score"] = int(round(sum(vals) / len(vals) * 10))
        c["start"] = s
        c["end"] = e
        c["duration"] = e - s
        c.setdefault("titles", [])
        c.setdefault("title", (c["titles"][0] if c["titles"] else "Clip"))
        c.setdefault("description", "")
        c.setdefault("hashtags", [])
        c.setdefault("hook", "")
        c.setdefault("category", "mixed")
        c.setdefault("explanation", "")
        c.setdefault("score_breakdown", sb)
        out.append(c)
    # dedup overlaps: sort by score desc, keep non-overlapping-ish
    out.sort(key=lambda x: x.get("viral_score", 0), reverse=True)
    return out
