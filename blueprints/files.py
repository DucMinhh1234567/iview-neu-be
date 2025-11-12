"""
Files blueprint for serving uploaded files.
"""
from flask import Blueprint
from utils.storage import StorageService
from extensions.supabase_client import supabase

files_bp = Blueprint("files", __name__)


@files_bp.route("/<file_type>s/<resource_id>/<filename>", methods=["GET"])
def download_file(file_type, resource_id, filename):
    """Download file from local storage."""
    try:
        # Construct file path
        file_path = f"{file_type}s/{resource_id}/{filename}"
        
        # For local storage, serve file directly
        # For Supabase storage, this route won't be used (redirect to Supabase URL)
        return StorageService.download_file(
            file_path=file_path,
            storage_type="local",  # This route is only for local files
            file_type=file_type
        )
        
    except FileNotFoundError:
        return {"error": "File not found"}, 404
    except Exception as e:
        return {"error": f"Failed to download file: {str(e)}"}, 500

