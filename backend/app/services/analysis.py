"""Analysis service: LLM-based + local heuristic fallback."""
import json
from .ai import chat, parse_json


SYSTEM = """You are an expert short-form video strategist and editor for TikTok, Instagram Reels and YouTube Shorts.
You analyze full video transcripts and identify the best self-contained moments to turn into vertical clips.
You never invent quotes or change meaning. You only select time ranges from the provided transcript.
You return STRICT JSON only, no prose, no markdown."""


def build_transcript_text(segments: list) -> str:
    lines = []
    for s in segments:
        lines.append(f"[{s['start']:.2f}-{s['end']:.2f}] {s['text']}")
    return "\n".join(lines)


def _first_sentence(text: str) -> str:
    text = text.strip()
    for sep in (". ", "! ", "? ", "\n"):
        idx = text.find(sep)
        if idx != -1 and idx < 120:
            return text[:idx + 1].strip()
    return text[:80].strip()


def _heuristic_analyze(duration: float, segments: list, clip_count: int, clip_duration: int,
                       priority: str) -> list[dict]:
    """Offline fallback that respects sentence/segment boundaries so clips make sense."""
    if clip_count == 0:
        clip_count = max(3, min(8, int(duration // max(60, clip_duration))))

    if not segments:
        # No transcript: split evenly but keep whole chunks.
        out = []
        n = max(1, clip_count)
        step = duration / (n + 1)
        for i in range(n):
            s = max(0.0, step * (i + 1) - clip_duration / 2)
            e = min(duration, s + clip_duration)
            if e - s < 5:
                continue
            out.append(_heuristic_clip(s, e, priority, i, ""))
        return out

    # Build candidate windows aligned to segment boundaries (complete phrases).
    cands = []
    i = 0
    nseg = len(segments)
    while i < nseg:
        start_idx = i
        acc = 0.0
        j = i
        while j < nseg and acc < clip_duration:
            acc += segments[j]["end"] - segments[j]["start"]
            j += 1
        if j <= i:
            j = i + 1
        s = segments[start_idx]["start"]
        e = segments[j - 1]["end"]
        text = " ".join(seg["text"] for seg in segments[start_idx:j]).strip()
        if e - s >= 8 and text:
            cands.append((s, e, text, start_idx, j))
        # advance: move forward by roughly half the clip to get variety
        step_seg = max(1, (j - start_idx) // 2)
        i = min(nseg - 1, start_idx + step_seg)
        if i <= start_idx:
            i = start_idx + 1
        if i >= nseg:
            break

    # Score candidates: prefer denser speech (more words per second) and earlier hooks.
    def score(c):
        s, e, text, a, b = c
        dur = max(1, e - s)
        wps = len(text.split()) / dur
        # slight preference for content-rich (higher wps) and not too long
        return wps * 10 + (1 if dur <= clip_duration + 5 else 0)

    cands.sort(key=score, reverse=True)

    chosen = []
    for c in cands:
        s, e, text, a, b = c
        if all(abs(s - ch[0]) > clip_duration * 0.4 for ch in chosen):
            chosen.append(c)
        if len(chosen) >= clip_count:
            break

    # If not enough, fall back to evenly spaced segment-aligned windows.
    if len(chosen) < clip_count:
        step = duration / (clip_count + 1)
        for k in range(clip_count - len(chosen)):
            # find segment nearest to target start
            target = step * (k + 1) - clip_duration / 2
            idx = min(nseg - 1, max(0, next((x for x in range(nseg) if segments[x]["start"] >= target), nseg - 1)))
            # build window
            s = segments[idx]["start"]
            acc = 0.0
            j = idx
            while j < nseg and acc < clip_duration:
                acc += segments[j]["end"] - segments[j]["start"]
                j += 1
            if j <= idx:
                j = idx + 1
            e = segments[j - 1]["end"]
            text = " ".join(seg["text"] for seg in segments[idx:j]).strip()
            if e - s >= 8 and all(abs(s - ch[0]) > clip_duration * 0.4 for ch in chosen):
                chosen.append((s, e, text, idx, j))

    out = []
    for idx, (s, e, text, a, b) in enumerate(chosen):
        out.append(_heuristic_clip(s, e, priority, idx, text))
    return out


def _heuristic_clip(s, e, priority, idx, text=""):
    title = _first_sentence(text) if text else f"Clip {idx + 1}"
    if len(title) < 4:
        title = f"Clip {idx + 1}"
    # Cap title length
    if len(title) > 70:
        title = title[:67] + "..."
    score = 60 + (idx % 5) * 4
    return {
        "start": float(s),
        "end": float(e),
        "duration": float(e - s),
        "viral_score": int(min(90, score)),
        "category": priority if priority not in ("mixed",) else "mixed",
        "hook": _first_sentence(text)[:90] if text else title,
        "titles": [title, f"{title} (alt)", f"Watch: {title}"],
        "description": "Generated locally. Configure an AI provider in Settings for richer, viral-optimized clips.",
        "hashtags": ["#shorts", "#viral", "#clip"],
        "explanation": "Generated locally (no AI API key/credits). Clip boundaries follow complete phrases from the transcript.",
        "score_breakdown": {
            "hook": 6, "retention": 6, "interest": 6, "emotion": 5,
            "clarity": 7, "comments": 5, "shares": 5, "autonomy": 7, "closure": 6,
        },
    }


async def analyze(cfg: dict, duration: float, segments: list, clip_count: int, clip_duration: int,
                 platform: str, priority: str, cut_aggressiveness: str) -> list[dict]:
    # Try LLM first; fall back to local heuristic if no key or API failure.
    from .ai import resolve_provider
    provider, model, key = resolve_provider(cfg)
    if not key or provider == "ollama":
        # Ollama handled below; if no key and not ollama, heuristic
        if provider != "ollama" or not key:
            if provider != "ollama":
                return _heuristic_analyze(duration, segments, clip_count, clip_duration, priority)
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
5. Prefer moments with a clear hook, a complete thought, and a satisfying ending. Never cut mid-sentence.

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
Ensure start/end are within [0,{duration:.1f}] and start<end. Align start/end to sentence boundaries from the transcript.
"""
    try:
        from .ai import chat, parse_json
        raw = await chat(cfg, SYSTEM, prompt, max_tokens=6000)
        data = parse_json(raw)
        clips = data.get("clips", []) if isinstance(data, dict) else data
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
            # Snap to nearest segment boundaries to avoid cutting sentences
            s, e = _snap_to_segments(s, e, segments)
            if e - s < 3:
                continue
            sb = c.get("score_breakdown") or {}
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
        out.sort(key=lambda x: x.get("viral_score", 0), reverse=True)
        if out:
            return out
    except Exception:
        pass
    return _heuristic_analyze(duration, segments, clip_count, clip_duration, priority)


def _snap_to_segments(s, e, segments):
    if not segments:
        return s, e
    # snap start to nearest segment start <= s
    best_s = s
    for seg in segments:
        if seg["start"] <= s <= seg["end"]:
            best_s = seg["start"]
            break
        if seg["start"] <= s:
            best_s = seg["start"]
    # snap end to nearest segment end >= e
    best_e = e
    for seg in reversed(segments):
        if seg["start"] <= e <= seg["end"]:
            best_e = seg["end"]
            break
        if seg["end"] >= e:
            best_e = seg["end"]
    if best_e - best_s < 3:
        return s, e
    return best_s, best_e