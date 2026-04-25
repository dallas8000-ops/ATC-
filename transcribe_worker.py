"""
Worker process for audio transcription.
Runs faster-whisper in a separate process so native library crashes
cannot terminate the PyQt UI process.
"""

import sys
import json
import os
import re


ATC_PROMPT = (
    "Air traffic control communication. Use ICAO/FAA phraseology, callsigns, runway, "
    "heading, altitude, flight level, descend, climb, maintain, contact, tower, approach, "
    "ground, center, VFR, IFR, squawk, cleared, hold short, line up and wait."
)

ATC_MARKERS = {
    "runway", "heading", "altitude", "flight", "level", "descend", "climb", "maintain",
    "contact", "tower", "approach", "center", "ground", "cleared", "hold", "short",
    "line", "wait", "taxi", "vfr", "ifr", "squawk", "november", "united", "american",
    "delta", "southwest", "jetblue", "frequency", "report"
}


def _collect_text_and_confidence(segments):
    parts = []
    total = 0.0
    count = 0
    for seg in segments:
        text = (seg.text or "").strip()
        if text:
            parts.append(text)
        if hasattr(seg, "avg_logprob") and seg.avg_logprob is not None:
            total += float(seg.avg_logprob)
            count += 1
    joined = " ".join(parts).strip()
    avg_logprob = (total / count) if count else -9.9
    return joined, avg_logprob


def _tokenize(text):
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _is_prompt_echo(text):
    """Detect cases where model echoes instruction/prompt instead of audio content."""
    normalized = (text or "").strip().lower()
    if not normalized:
        return False

    if normalized.startswith("air traffic control communication"):
        return True

    prompt_tokens = set(_tokenize(ATC_PROMPT))
    text_tokens = _tokenize(normalized)
    if not text_tokens:
        return False
    overlap = sum(1 for tok in text_tokens if tok in prompt_tokens)
    overlap_ratio = overlap / max(1, len(text_tokens))
    return overlap_ratio >= 0.75


def _is_numeric_loop_hallucination(text):
    """Detect common hallucination pattern: repetitive numeric tokens/phrases."""
    normalized = (text or "").lower()
    if not normalized:
        return False

    tokens = re.findall(r"[a-z0-9]+", normalized)
    if len(tokens) < 8:
        return False

    numeric_words = {
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "oh", "point"
    }
    numeric_like = [t for t in tokens if t.isdigit() or t in numeric_words]
    numeric_ratio = len(numeric_like) / max(1, len(tokens))

    # Repeated tiny vocabulary (e.g., only 3-2-0 tokens over and over)
    unique_ratio = len(set(tokens)) / len(tokens)

    # Repeated numeric trigram pattern
    trigrams = [" ".join(tokens[i:i + 3]) for i in range(len(tokens) - 2)]
    most_common_trigram_freq = 0
    if trigrams:
        counts = {}
        for tri in trigrams:
            counts[tri] = counts.get(tri, 0) + 1
        most_common_trigram_freq = max(counts.values()) / len(trigrams)

    return (
        numeric_ratio >= 0.8 and unique_ratio <= 0.35
    ) or (
        numeric_ratio >= 0.7 and most_common_trigram_freq >= 0.3
    )


def _has_atc_marker(text):
    tokens = _tokenize(text)
    return any(tok in ATC_MARKERS for tok in tokens)


def _filter_segments(segments, is_atc_mode):
    """Remove likely hallucinated segments while preserving ATC-relevant ones."""
    filtered = []
    for seg in segments:
        text = (getattr(seg, "text", "") or "").strip()
        if not text:
            continue

        if _is_numeric_loop_hallucination(text):
            continue

        avg_logprob = float(getattr(seg, "avg_logprob", -9.9) if getattr(seg, "avg_logprob", None) is not None else -9.9)
        token_count = len(_tokenize(text))

        if is_atc_mode:
            if avg_logprob < -1.25 and token_count >= 4 and not _has_atc_marker(text):
                continue
        else:
            if avg_logprob < -1.6 and token_count >= 6:
                continue

        filtered.append(seg)

    return filtered if filtered else segments


def _collapse_repeated_sequences(text):
    """Collapse repeated short token sequences (e.g., 'three two zero' loops)."""
    tokens = (text or "").split()
    if len(tokens) < 8:
        return text

    out = []
    i = 0
    while i < len(tokens):
        best_n = 0
        best_rep = 1
        for n in range(2, 7):
            if i + (2 * n) > len(tokens):
                break
            seq = tokens[i:i + n]
            rep = 1
            j = i + n
            while j + n <= len(tokens) and tokens[j:j + n] == seq:
                rep += 1
                j += n
            if rep > 1 and (n * rep) > (best_n * best_rep):
                best_n = n
                best_rep = rep

        if best_rep > 1:
            out.extend(tokens[i:i + best_n])
            i += best_n * best_rep
        else:
            out.append(tokens[i])
            i += 1

    return " ".join(out)


def main():
    if len(sys.argv) < 2:
        print("missing audio path", file=sys.stderr)
        raise SystemExit(2)

    audio_path = sys.argv[1]

    try:
        from faster_whisper import WhisperModel

        requested_model = os.getenv("ATC_WHISPER_MODEL", "small")
        mode = os.getenv("ATC_TRANSCRIPTION_MODE", "ATC Strict")
        is_atc_mode = mode == "ATC Strict"

        model = None
        model_load_errors = []
        for candidate in [requested_model, "base"]:
            if model is not None:
                break
            try:
                model = WhisperModel(candidate, device="cpu", compute_type="int8")
                requested_model = candidate
            except Exception as exc:
                model_load_errors.append(f"{candidate}: {exc}")

        if model is None:
            raise RuntimeError("; ".join(model_load_errors) or "Unable to load any Whisper model")

        print(f"[DEBUG-WORKER] Loaded Whisper model: {requested_model}", file=sys.stderr)

        decode_kwargs = {
            "language": "en",
            "condition_on_previous_text": False,
            "beam_size": 5,
            "best_of": 5,
            "temperature": 0.0,
        }
        if is_atc_mode:
            decode_kwargs["hotwords"] = (
                "runway heading altitude flight level squawk tower approach center "
                "ground cleared maintain descend climb"
            )

        # Primary pass with VAD enabled.
        segments, _ = model.transcribe(
            audio_path,
            vad_filter=True,
            **decode_kwargs,
        )
        segments = list(segments)
        segments = _filter_segments(segments, is_atc_mode)
        text, avg_logprob = _collect_text_and_confidence(segments)

        # Fallback for short or low-volume clips filtered out by VAD.
        if not text:
            segments, _ = model.transcribe(
                audio_path,
                vad_filter=False,
                **decode_kwargs,
            )
            segments = list(segments)
            segments = _filter_segments(segments, is_atc_mode)
            text, avg_logprob = _collect_text_and_confidence(segments)

        text = _collapse_repeated_sequences(text)

        prompt_echo = _is_prompt_echo(text)
        numeric_loop = _is_numeric_loop_hallucination(text)
        if prompt_echo or numeric_loop:
            text = ""

        payload = {
            "text": text,
            "avg_logprob": avg_logprob,
            "low_confidence": bool((text and avg_logprob < -1.2) or prompt_echo or numeric_loop),
            "prompt_echo": prompt_echo,
            "numeric_loop": numeric_loop,
            "model_used": requested_model,
        }
        print(json.dumps(payload))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
