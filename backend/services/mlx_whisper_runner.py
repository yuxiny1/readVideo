import argparse
import re
from pathlib import Path


def transcript_text(result: dict) -> str:
    segments = result.get("segments") or []
    lines: list[str] = []
    previous = ""
    for segment in segments:
        text = re.sub(r"\s+", " ", str(segment.get("text", ""))).strip()
        comparable = re.sub(r"[^\w\u3400-\u9fff]+", "", text).casefold()
        if not text or comparable == previous:
            continue
        lines.append(text)
        previous = comparable
    if not lines:
        fallback = re.sub(r"\s+", " ", str(result.get("text", ""))).strip()
        if fallback:
            lines.append(fallback)
    return "\n".join(lines) + ("\n" if lines else "")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--language", default="auto")
    parser.add_argument("--prompt", default="")
    args = parser.parse_args()

    import mlx_whisper

    options = {
        "path_or_hf_repo": args.model,
        "verbose": False,
        "temperature": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
        "compression_ratio_threshold": 2.2,
        "logprob_threshold": -1.0,
        "no_speech_threshold": 0.6,
        "condition_on_previous_text": False,
        "task": "transcribe",
    }
    if args.language and args.language != "auto":
        options["language"] = args.language
    if args.prompt:
        options["initial_prompt"] = args.prompt

    result = mlx_whisper.transcribe(args.audio, **options)
    Path(args.output).write_text(transcript_text(result), encoding="utf-8")


if __name__ == "__main__":
    main()
