"""
File storage service with hybrid support (Local/Supabase Storage).
"""
import os
from werkzeug.utils import secure_filename
from flask import send_file, redirect
from extensions.supabase_client import supabase
from config import USE_SUPABASE_STORAGE, UPLOAD_FOLDER, SUPABASE_STORAGE_BUCKETS


class StorageService:
    """Unified storage service - handles both local and Supabase storage"""
    
    @staticmethod
    def upload_file(file, resource_id, file_type="material"):
        """
        Upload file - automatically chooses storage method based on config
        
        Args:
            file: File object from request
            resource_id: ID of resource (material_id, session_id, etc.)
            file_type: Type of file ('material', 'cv', 'jd')
        
        Returns:
            dict: File information including path and URL
        """
        if USE_SUPABASE_STORAGE:
            return StorageService._upload_to_supabase(file, resource_id, file_type)
        else:
            return StorageService._upload_local(file, resource_id, file_type)
    
    @staticmethod
    def _upload_local(file, resource_id, file_type):
        """Upload to local filesystem"""
        # Create directory structure
        base_path = os.path.join(UPLOAD_FOLDER, f"{file_type}s")
        resource_path = os.path.join(base_path, str(resource_id))
        os.makedirs(resource_path, exist_ok=True)
        
        # Generate filename
        filename = secure_filename(file.filename)
        file_path = os.path.join(resource_path, filename)
        
        # Save file
        file.save(file_path)
        
        # Return file info
        relative_path = os.path.relpath(file_path, UPLOAD_FOLDER)
        return {
            "storage_type": "local",
            "file_path": relative_path,
            "filename": filename,
            "url": f"/api/files/{file_type}s/{resource_id}/{filename}",
            "size": os.path.getsize(file_path)
        }
    
    @staticmethod
    def _upload_to_supabase(file, resource_id, file_type):
        """Upload to Supabase Storage"""
        # Determine bucket
        bucket_name = SUPABASE_STORAGE_BUCKETS.get(file_type, "materials")
        
        # Generate file path
        filename = secure_filename(file.filename)
        file_path = f"{resource_id}/{filename}"
        
        # Read file data
        file_data = file.read()
        file.seek(0)
        
        # Upload to Supabase
        try:
            response = supabase.storage.from_(bucket_name).upload(
                path=file_path,
                file=file_data,
                file_options={
                    "content-type": file.content_type or "application/pdf",
                    "cache-control": "3600",
                    "upsert": "false"
                }
            )
            
            # Get URL
            if bucket_name == "materials":
                # Public bucket
                file_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
            else:
                # Private bucket - signed URL
                signed_url = supabase.storage.from_(bucket_name).create_signed_url(
                    file_path,
                    expires_in=86400  # 24 hours
                )
                file_url = signed_url.get("signedURL") if isinstance(signed_url, dict) else signed_url
            
            return {
                "storage_type": "supabase",
                "file_path": file_path,
                "filename": filename,
                "bucket": bucket_name,
                "url": file_url,
                "size": len(file_data)
            }
        except Exception as e:
            raise Exception(f"Failed to upload to Supabase: {str(e)}")
    
    @staticmethod
    def download_file(file_path, storage_type, file_type="material", bucket=None):
        """
        Download file - handles both storage types
        
        Returns:
            Flask response (send_file or redirect)
        """
        if storage_type == "local":
            return StorageService._download_local(file_path)
        else:
            return StorageService._download_from_supabase(file_path, bucket or SUPABASE_STORAGE_BUCKETS.get(file_type))
    
    @staticmethod
    def _download_local(file_path):
        """Download from local filesystem"""
        full_path = os.path.join(UPLOAD_FOLDER, file_path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        filename = os.path.basename(full_path)
        return send_file(
            full_path,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf"
        )
    
    @staticmethod
    def _download_from_supabase(file_path, bucket_name):
        """Download from Supabase Storage"""
        try:
            if bucket_name == "materials":
                # Public bucket - redirect to public URL
                url = supabase.storage.from_(bucket_name).get_public_url(file_path)
                return redirect(url)
            else:
                # Private bucket - generate signed URL
                signed_url = supabase.storage.from_(bucket_name).create_signed_url(
                    file_path,
                    expires_in=3600
                )
                url = signed_url.get("signedURL") if isinstance(signed_url, dict) else signed_url
                return redirect(url)
        except Exception as e:
            raise Exception(f"Failed to download from Supabase: {str(e)}")
    
    @staticmethod
    def delete_file(file_path, storage_type, bucket=None):
        """Delete file from storage"""
        if storage_type == "local":
            return StorageService._delete_local(file_path)
        else:
            return StorageService._delete_from_supabase(file_path, bucket)
    
    @staticmethod
    def _delete_local(file_path):
        """Delete from local filesystem"""
        full_path = os.path.join(UPLOAD_FOLDER, file_path)
        
        if os.path.exists(full_path):
            os.remove(full_path)
            # Remove empty directory
            folder = os.path.dirname(full_path)
            if not os.listdir(folder):
                os.rmdir(folder)
        return True
    
    @staticmethod
    def _delete_from_supabase(file_path, bucket_name):
        """Delete from Supabase Storage"""
        try:
            supabase.storage.from_(bucket_name).remove([file_path])
            return True
        except Exception as e:
            raise Exception(f"Failed to delete from Supabase: {str(e)}")

