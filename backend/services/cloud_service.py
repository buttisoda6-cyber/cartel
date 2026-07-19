import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


def upload_poster_bytes(file_path: str) -> str:
    """
    Upload a poster file to Cloudinary.
    
    Args:
        file_path: Temporary file path of the PNG
        
    Returns:
        Secure URL of the uploaded image
    """
    result = cloudinary.uploader.upload(
        file_path,
        folder="cartel_posters"
    )
    os.remove(file_path)
    return result["secure_url"]


def upload_poster(file_path: str) -> str:
    """Deprecated: Use upload_poster_bytes instead."""
    return upload_poster_bytes(file_path)