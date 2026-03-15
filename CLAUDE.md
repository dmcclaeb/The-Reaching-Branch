# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

YouTube Transcript Extractor built on the Supadata API. Extracts subtitles/transcripts from YouTube videos using the Supadata Python SDK (`supadata>=1.6.0`).

## Setup

```bash
pip install -r requirements.txt
export SUPADATA_API_KEY=your_key_here  # Get from https://dash.supadata.ai
```

## Usage

```bash
# Basic usage with URL or video ID
python transcript.py <youtube_url_or_id>

# With options
python transcript.py dQw4w9WgXcQ --lang es --text --json --output out.txt
```

Key flags: `--lang` (ISO 639-1), `--text` (plain text vs timestamped), `--mode` (native|generate|auto), `--json`, `--output`.

## Architecture

Single-file CLI tool (`transcript.py`) using the `supadata` Python SDK. Handles both synchronous responses and async job polling for long videos (>20 min). API key is read from `SUPADATA_API_KEY` env var.
