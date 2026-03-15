#!/usr/bin/env python3
"""YouTube Transcript Extractor using Supadata API.

Extract subtitles/transcripts from YouTube videos for free.
Supports plain text and timestamped output, language selection,
and both native captions and AI-generated transcripts.

Usage:
    python transcript.py <youtube_url_or_id> [options]

Examples:
    python transcript.py https://www.youtube.com/watch?v=dQw4w9WgXcQ
    python transcript.py dQw4w9WgXcQ --lang es --text
    python transcript.py dQw4w9WgXcQ --mode generate --output transcript.txt
"""

import argparse
import json
import os
import sys
import time

from supadata import Supadata
from supadata.errors import SupadataError


def get_api_key():
    """Get the Supadata API key from environment variable."""
    api_key = os.environ.get("SUPADATA_API_KEY")
    if not api_key:
        print("Error: SUPADATA_API_KEY environment variable is not set.", file=sys.stderr)
        print("Get your free API key at https://dash.supadata.ai", file=sys.stderr)
        sys.exit(1)
    return api_key


def extract_video_id(url_or_id):
    """Extract YouTube video ID from a URL or return the ID directly."""
    if len(url_or_id) == 11 and "/" not in url_or_id:
        return url_or_id
    return url_or_id


def format_timestamp(ms):
    """Convert milliseconds to HH:MM:SS.mmm format."""
    seconds, ms_remainder = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms_remainder:03d}"
    return f"{minutes:02d}:{seconds:02d}.{ms_remainder:03d}"


def poll_job(client, job_id, max_wait=300):
    """Poll for async job results. Polls every 1 second, up to max_wait seconds."""
    print(f"Processing async job {job_id}...", file=sys.stderr)
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(1)
        elapsed += 1
        try:
            result = client.transcript.get_results(job_id=job_id)
            if hasattr(result, "content") and result.content is not None:
                return result
        except SupadataError:
            continue
        if elapsed % 10 == 0:
            print(f"  Still processing... ({elapsed}s)", file=sys.stderr)
    print(f"Error: Job {job_id} did not complete within {max_wait}s.", file=sys.stderr)
    sys.exit(1)


def get_transcript(url_or_id, lang=None, text=False, mode=None):
    """Fetch a YouTube transcript using the Supadata API.

    Args:
        url_or_id: YouTube video URL or video ID.
        lang: Preferred language code (ISO 639-1), e.g. "en", "es".
        text: If True, return plain text. Otherwise return timestamped chunks.
        mode: "native" (captions only), "generate" (AI), or "auto" (try native first).

    Returns:
        The transcript result object from the Supadata SDK.
    """
    client = Supadata(api_key=get_api_key())
    input_value = extract_video_id(url_or_id)

    kwargs = {"text": text}
    if lang:
        kwargs["lang"] = lang
    if mode:
        kwargs["mode"] = mode

    # Use video_id if it looks like an ID, otherwise use url
    if len(input_value) == 11 and "/" not in input_value:
        result = client.youtube.transcript(video_id=input_value, **kwargs)
    else:
        result = client.transcript(url=input_value, **kwargs)

    # Handle async processing for long videos
    if hasattr(result, "job_id") and result.job_id and not hasattr(result, "content"):
        result = poll_job(client, result.job_id)

    return result


def format_output(result, text_mode, output_format="text"):
    """Format the transcript result for display.

    Args:
        result: Transcript result from Supadata.
        text_mode: Whether plain text was requested.
        output_format: "text" for human-readable, "json" for JSON output.
    """
    if output_format == "json":
        data = {"lang": getattr(result, "lang", None)}
        if text_mode:
            data["content"] = result.content
        else:
            data["content"] = [
                {
                    "text": chunk.text,
                    "offset": chunk.offset,
                    "duration": chunk.duration,
                    "lang": getattr(chunk, "lang", None),
                }
                for chunk in result.content
            ]
        available = getattr(result, "availableLangs", None) or getattr(
            result, "available_langs", None
        )
        if available:
            data["available_langs"] = available
        return json.dumps(data, indent=2, ensure_ascii=False)

    # Human-readable text format
    lines = []
    if text_mode:
        lines.append(result.content)
    else:
        for chunk in result.content:
            timestamp = format_timestamp(chunk.offset)
            lines.append(f"[{timestamp}] {chunk.text}")

    available = getattr(result, "availableLangs", None) or getattr(
        result, "available_langs", None
    )
    if available:
        lines.append(f"\nAvailable languages: {', '.join(available)}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Extract YouTube video transcripts using Supadata API."
    )
    parser.add_argument("video", help="YouTube video URL or video ID")
    parser.add_argument(
        "--lang", "-l", help="Preferred transcript language (ISO 639-1 code, e.g. en, es, fr)"
    )
    parser.add_argument(
        "--text", "-t", action="store_true", help="Return plain text instead of timestamped chunks"
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["native", "generate", "auto"],
        help="Transcript mode: native (captions only), generate (AI), auto (try native first)",
    )
    parser.add_argument("--json", "-j", action="store_true", help="Output in JSON format")
    parser.add_argument("--output", "-o", help="Write output to file instead of stdout")

    args = parser.parse_args()

    try:
        result = get_transcript(args.video, lang=args.lang, text=args.text, mode=args.mode)
    except SupadataError as e:
        print(f"Supadata API error: {e.message}", file=sys.stderr)
        if hasattr(e, "details") and e.details:
            print(f"Details: {e.details}", file=sys.stderr)
        sys.exit(1)

    output_format = "json" if args.json else "text"
    output = format_output(result, args.text, output_format)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Transcript saved to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
