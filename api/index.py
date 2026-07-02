"""
Vercel serverless entrypoint for the Medical Affairs AI FastAPI backend.

Vercel routes /api/* requests here. Set environment variables in the
Vercel project dashboard (Settings → Environment Variables):
  PUBMED_API_KEY
  OPENAI_API_KEY
"""

from __future__ import annotations

import os
import sys

# Ensure backend modules resolve on Vercel's serverless filesystem.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT_DIR, "sujeet", "poc", "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("VERCEL", "1")

from api_server import app  # noqa: E402  (import after path setup)
