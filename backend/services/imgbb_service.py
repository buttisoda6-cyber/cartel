import os
import requests
from typing import Optional

def upload_to_imgbb(image_url: str) -> Optional[str]:
    """
    Uploads an image (via URL or local path) to ImgBB and returns its public URL.
    Returns None if IMGBB_API_KEY is not configured or the upload fails.
    """
    api_key = os.getenv("IMGBB_API_KEY")
    if not api_key:
        return None

    try:
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            params={"key": api_key},
            data={"image": image_url},
            timeout=10
        )
        if response.status_code == 200:
            res_data = response.json()
            return res_data.get("data", {}).get("url")
        else:
            print(f"[WARN] ImgBB API error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[WARN] Error uploading to ImgBB: {e}")

    return None
