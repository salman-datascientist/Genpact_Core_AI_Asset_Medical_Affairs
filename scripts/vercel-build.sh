#!/usr/bin/env bash
# Copy POC frontend assets into Vercel's public/ output directory.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/public"
cp -r "$ROOT/sujeet/poc/frontend/." "$ROOT/public/"
echo "Vercel build: copied frontend to public/"
