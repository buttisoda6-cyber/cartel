"""Poster upload route for handling PNG uploads from frontend."""

from fastapi import APIRouter, UploadFile, File
from services.cloud_service import upload_poster_bytes
import tempfile
import os

router = APIRouter()


@router.post("/api/posters/upload")
async def upload_poster(file: UploadFile = File(...)):
    """
    Upload a poster PNG to Cloudinary.
    
    Args:
        file: PNG file from frontend
        
    Returns:
        JSON with poster_url from Cloudinary
    """
    contents = await file.read()
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".png"
    ) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    
    try:
        url = upload_poster_bytes(tmp_path)
        return {"poster_url": url}
    except Exception as e:
        raise Exception(f"Failed to upload poster: {str(e)}")
