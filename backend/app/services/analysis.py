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


def _heuristic_analyze(duration: float, segments: list, clip_count: int, clip_duration: int,
                       priority: str) -> list[dict]:
    # Offline fallback: build clips from transcript segments without an LLM.
    if clip_count == 0:
        clip_count = max(5, min(10, int(duration // max(60, clip_duration))))
    if not segments:
        # No transcript: split the video evenly.
        out = []
        n = max(1, clip_count)
        step = duration / (n + 1)
        for i in range(n):
            s = max(0.0, step * (i + 1) - clip_duration / 2)
            e = min(duration, s + clip_duration)
            if e - s < 5:
                continue
            out.append(_heuristic_clip(s, e, priority, i))
        return out

    # Build candidate windows aligned to segment boundaries.
    cands = []
    i = 0
    nseg = len(segments)
    while i < nseg:
        start_seg = segments[i]
        # accumulate until clip_duration
        acc = 0.0
        j = i
        while j < nseg and acc < clip_duration:
            acc += segments[j]["end"] - segments[j]["start"]
            j += 1
        if j <= i:
            j = i + 1
        s = segments[i]["start"]
        e = segments[j - 1]["end"]
        if e - s >= 5:
            text = " ".join(seg["text"] for seg in segments[i:j]).strip()
            cands.append((s, e, text))
        # advance by ~clip_duration/2 to get variety
        advance = max(1, clip_duration // 15)
        i = min(nseg - 1, i + max(1, (j - i) // 2 + 1))
        if i >= nseg - 1:
            break

    # Select non-overlapping top candidates by length (proxy for content).
    cands.sort(key=lambda c: (c[1] - c[0]), reverse=True)
    chosen = []
    for s, e, text in cands:
        if all(abs(s - c[0]) > clip_duration * 0.5 for c in chosen):
            chosen.append((s, e, text))
        if len(chosen) >= clip_count:
            break
    # If not enough, fall back to evenly spaced.
    if len(chosen) < clip_count:
        step = duration / (clip_count + 1)
        for k in range(clip_count - len(chosen)):
            s = max(0.0, step * (k + 1) - clip_duration / 2)
            e = min(duration, s + clip_duration)
            if e - s >= 5 and all(abs(s - c[0]) > clip_duration * 0.5 for c in chosen):
                chosen.append((s, e, ""))

    out = []
    for idx, (s, e, text) in enumerate(chosen):
        out.append(_heuristic_clip(s, e, priority, idx, text))
    return out


def _heuristic_clip(s, e, priority, idx, text=""):
    words = text.split()[:8]
    title = " ".join(words) if words else f"Clip {idx + 1}"
    if len(title) < 4:
        title = f"Clip {idx + 1}"
    score = 62 + (idx % 7) * 3
    return {
        "start": float(s),
        "end": float(e),
        "duration": float(e - s),
        "viral_score": int(min(95, score)),
        "category": priority if priority != "mixed" else "mixed",
        "hook": (text.split(".")[0][:80] if text else title),
        "titles": [title, f"{title} (alt)", f"Watch: {title}"],
        "description": "Generated locally without an AI API key.",
        "hashtags": ["#shorts", "#viral", "#clip"],
        "explanation": "Generated locally (no AI API key/credits). For richer analysis, configure an AI provider in Settings.",
        "score_breakdown": {
            "hook": 6, "retention": 6, "interest": 6, "emotion": 5,
            "clarity": 6, "comments": 5, "shares": 5, "autonomy": 6, "closure": 6,
        },
    }


async def analyze(cfg: dict, duration: float, segments: list, clip_count: int, clip_duration: int,
                 platform: str, priority: str, cut_aggressiveness: str) -> list[dict]:
    # Try LLM first; fall back to local heuristic if no key or API failure.
    from .ai import resolve_provider, chat, parse_json
    provider, model, key = resolve_provider(cfg)
    if not key:
        return _heuristic_analyze(duration, segments, clip_count, clip_duration, priority)
    try:
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
    except Exception:
        return _heuristic_analyze(duration, segments, clip_count, clip_duration, priority)
