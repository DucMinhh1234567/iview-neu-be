"""
Material model.
"""
from typing import Optional, Literal
from datetime import datetime


MaterialSource = Literal["UPLOAD", "NEUREADER", "EXTERNAL"]
StorageType = Literal["local", "supabase"]


class Material:
    """Material model"""
    
    def __init__(
        self,
        material_id: int,
        title: str,
        source_type: MaterialSource,
        file_url: Optional[str] = None,
        file_path: Optional[str] = None,
        storage_type: StorageType = "local",
        bucket_name: Optional[str] = None,
        uploaded_by: Optional[int] = None,
        num_chunks: int = 0,
        is_public: bool = True,  # Add is_public parameter with default True
        created_at: Optional[datetime] = None
    ):
        self.material_id = material_id
        self.title = title
        self.source_type = source_type
        self.file_url = file_url
        self.file_path = file_path
        self.storage_type = storage_type
        self.bucket_name = bucket_name
        self.uploaded_by = uploaded_by
        self.num_chunks = num_chunks
        self.is_public = is_public  # Add is_public attribute
        self.created_at = created_at or datetime.now()
    
    @classmethod
    def from_dict(cls, data: dict) -> "Material":
        """Create Material from dictionary"""
        return cls(
            material_id=data.get("material_id"),
            title=data.get("title", ""),
            source_type=data.get("source_type", "UPLOAD"),
            file_url=data.get("file_url"),
            file_path=data.get("file_path"),
            storage_type=data.get("storage_type", "local"),
            bucket_name=data.get("bucket_name"),
            uploaded_by=data.get("uploaded_by"),
            num_chunks=data.get("num_chunks", 0),
            is_public=data.get("is_public", True),  # Add is_public with default True
            created_at=data.get("created_at")
        )
    
    def to_dict(self) -> dict:
        """Convert Material to dictionary"""
        return {
            "material_id": self.material_id,
            "title": self.title,
            "source_type": self.source_type,
            "file_url": self.file_url,
            "file_path": self.file_path,
            "storage_type": self.storage_type,
            "bucket_name": self.bucket_name,
            "uploaded_by": self.uploaded_by,
            "num_chunks": self.num_chunks,
            "is_public": self.is_public,  # Add is_public to dictionary
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

