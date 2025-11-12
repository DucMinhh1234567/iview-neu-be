"""
Materials blueprint for managing PDF materials.
Handles upload, processing, and retrieval of materials (Lecturer only).
"""
import os
from flask import Blueprint, request, jsonify
from pdfminer.high_level import extract_text
from extensions.supabase_client import supabase
from extensions.auth_middleware import require_lecturer
from utils.storage import StorageService
from utils.semantic_chunking import process_material_semantic
from config import MAX_UPLOAD_SIZE

materials_bp = Blueprint("materials", __name__)


@materials_bp.route("/upload", methods=["POST"])
@require_lecturer
def upload_material():
    """Upload and process PDF material with semantic chunking (Lecturer only)."""
    file = request.files.get("file")
    title = request.form.get("title")
    description = request.form.get("description", "")
    is_public = request.form.get("is_public", "true").lower() == "true"  # Default to True
    user_id = request.user_id
    
    if not file:
        return jsonify({"error": "PDF file is required"}), 400
    
    if not title:
        return jsonify({"error": "Title is required"}), 400
    
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are allowed"}), 400
    
    # Validate file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_UPLOAD_SIZE:
        return jsonify({
            "error": f"File size exceeds maximum size of {MAX_UPLOAD_SIZE / (1024*1024)}MB"
        }), 400
    
    try:
        # Create material record first
        material_data = {
            "title": title,
            "source_type": "UPLOAD",
            "uploaded_by": user_id,
            "is_public": is_public  # Add is_public field
        }
        
        material_response = supabase.table("material").insert(material_data).execute()
        
        if not material_response.data:
            return jsonify({"error": "Failed to create material record"}), 500
        
        material_id = material_response.data[0]["material_id"]
        
        # Upload file
        file_info = StorageService.upload_file(file, material_id, file_type="material")
        
        # Update material with file info
        supabase.table("material").update({
            "file_path": file_info["file_path"],
            "file_url": file_info["url"],
            "storage_type": file_info["storage_type"],
            "bucket_name": file_info.get("bucket")
        }).eq("material_id", material_id).execute()
        
        # Extract text from PDF
        if file_info["storage_type"] == "local":
            file_path = os.path.join("uploads", file_info["file_path"])
        else:
            # For Supabase storage, download temporarily or use a different approach
            # For now, we'll need to read from the uploaded file
            file.seek(0)
            file_path = None
        
        # Extract text
        if file_path and os.path.exists(file_path):
            text = extract_text(file_path)
        else:
            # Read from file object directly
            file.seek(0)
            # Save temporarily for extraction
            temp_path = f"temp_{material_id}.pdf"
            file.save(temp_path)
            text = extract_text(temp_path)
            os.remove(temp_path)
        
        if not text or len(text.strip()) < 100:
            # Delete material if text extraction fails
            supabase.table("material").delete().eq("material_id", material_id).execute()
            return jsonify({"error": "PDF appears to be empty or unreadable"}), 400
        
        # Process with semantic chunking and embeddings
        chunks = process_material_semantic(text, material_id)
        
        # Store chunks in database with embeddings
        chunks_to_insert = []
        for chunk in chunks:
            chunk_data = {
                "material_id": material_id,
                "chunk_text": chunk["text"],
                "chunk_index": chunk["chunk_index"],
                "embedding": chunk.get("embedding"),  # This is a list of floats
                "metadata": chunk.get("metadata", {})
            }
            chunks_to_insert.append(chunk_data)
        
        # Insert chunks in batches
        batch_size = 50
        for i in range(0, len(chunks_to_insert), batch_size):
            batch = chunks_to_insert[i:i + batch_size]
            supabase.table("material_chunks").insert(batch).execute()
        
        # Update material with chunk count
        supabase.table("material").update({
            "num_chunks": len(chunks)
        }).eq("material_id", material_id).execute()
        
        return jsonify({
            "material_id": material_id,
            "title": title,
            "num_chunks": len(chunks),
            "file_url": file_info["url"],
            "storage_type": file_info["storage_type"],
            "is_public": is_public  # Return is_public in response
        }), 200
        
    except Exception as e:
        error_msg = str(e)
        print(f"Material upload error: {error_msg}")
        return jsonify({"error": f"Failed to upload material: {error_msg}"}), 500


@materials_bp.route("", methods=["GET"])
def get_materials():
    """Get all materials. Students can view list, but only lecturers can download."""
    try:
        materials_response = supabase.table("material").select("*").order("created_at", desc=True).execute()
        
        if not materials_response.data:
            return jsonify([]), 200
        
        # Remove sensitive file info for non-lecturers
        # This will be handled by auth middleware if needed
        materials = materials_response.data
        
        return jsonify(materials), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get materials: {str(e)}"}), 500


@materials_bp.route("/<int:material_id>", methods=["GET"])
@require_lecturer
def get_material(material_id):
    """Get material details (Lecturer only)."""
    try:
        material_response = supabase.table("material").select("*").eq("material_id", material_id).single().execute()
        
        if not material_response.data:
            return jsonify({"error": "Material not found"}), 404
        
        return jsonify(material_response.data), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get material: {str(e)}"}), 500


@materials_bp.route("/<int:material_id>/download", methods=["GET"])
@require_lecturer
def download_material(material_id):
    """Download material PDF file (Lecturer only)."""
    try:
        material_response = supabase.table("material").select("*").eq("material_id", material_id).single().execute()
        
        if not material_response.data:
            return jsonify({"error": "Material not found"}), 404
        
        material = material_response.data
        
        # Download file using storage service
        return StorageService.download_file(
            file_path=material["file_path"],
            storage_type=material.get("storage_type", "local"),
            file_type="material",
            bucket=material.get("bucket_name")
        )
        
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to download material: {str(e)}"}), 500


@materials_bp.route("/<int:material_id>", methods=["DELETE"])
@require_lecturer
def delete_material(material_id):
    """Delete material (Lecturer only)."""
    try:
        # Get material info
        material_response = supabase.table("material").select("*").eq("material_id", material_id).single().execute()
        
        if not material_response.data:
            return jsonify({"error": "Material not found"}), 404
        
        material = material_response.data
        
        # Delete file from storage
        try:
            StorageService.delete_file(
                file_path=material["file_path"],
                storage_type=material.get("storage_type", "local"),
                bucket=material.get("bucket_name")
            )
        except Exception as e:
            print(f"Warning: Failed to delete file: {e}")
        
        # Delete chunks (cascade should handle this, but we'll do it explicitly)
        supabase.table("material_chunks").delete().eq("material_id", material_id).execute()
        
        # Delete material
        supabase.table("material").delete().eq("material_id", material_id).execute()
        
        return jsonify({"message": "Material deleted successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to delete material: {str(e)}"}), 500

