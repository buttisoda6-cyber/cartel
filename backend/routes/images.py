"""Image proxy route to fetch external images with permissive CORS headers.

This lets the frontend load images through our backend so they are canvas-safe
when generating posters (avoids tainted canvas from remote images).
"""

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
import requests

router = APIRouter()


@router.get("/api/images/fetch")
def fetch_image(url: str = Query(..., description="Remote image URL to proxy")):
    # Basic validation
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")

    try:
        # Provide a common browser User-Agent to improve upstream compatibility
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"}
        resp = requests.get(url, stream=True, timeout=10, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch image: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Upstream image fetch failed")

    content_type = resp.headers.get("content-type", "application/octet-stream")

    headers = {
        # Allow any origin to read this resource in browsers
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=3600",
    }

    return StreamingResponse(resp.raw, media_type=content_type, headers=headers)
