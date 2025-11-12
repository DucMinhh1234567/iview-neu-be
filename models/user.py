"""
User model and related types.
"""
from typing import Optional, Literal
from datetime import datetime


UserRole = Literal["LECTURER", "STUDENT"]


class User:
    """User model"""
    
    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        full_name: str,
        role: UserRole,
        password_hash: str = "",
        created_at: Optional[datetime] = None
    ):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.role = role
        self.password_hash = password_hash
        self.created_at = created_at or datetime.now()
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create User from dictionary"""
        return cls(
            user_id=data.get("user_id"),
            username=data.get("username", ""),
            email=data.get("email", ""),
            full_name=data.get("full_name", ""),
            role=data.get("role", "STUDENT"),
            password_hash=data.get("password_hash", ""),
            created_at=data.get("created_at")
        )
    
    def to_dict(self) -> dict:
        """Convert User to dictionary"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Lecturer:
    """Lecturer model"""
    
    def __init__(
        self,
        lecturer_id: int,
        lecturer_code: str,
        department: Optional[str] = None,
        bio: Optional[str] = None
    ):
        self.lecturer_id = lecturer_id
        self.lecturer_code = lecturer_code
        self.department = department
        self.bio = bio
    
    @classmethod
    def from_dict(cls, data: dict) -> "Lecturer":
        """Create Lecturer from dictionary"""
        return cls(
            lecturer_id=data.get("lecturer_id"),
            lecturer_code=data.get("lecturer_code", ""),
            department=data.get("department"),
            bio=data.get("bio")
        )
    
    def to_dict(self) -> dict:
        """Convert Lecturer to dictionary"""
        return {
            "lecturer_id": self.lecturer_id,
            "lecturer_code": self.lecturer_code,
            "department": self.department,
            "bio": self.bio
        }


class Student:
    """Student model"""
    
    def __init__(
        self,
        student_id: int,
        student_code: str,
        class_name: Optional[str] = None,
        course_year: Optional[int] = None
    ):
        self.student_id = student_id
        self.student_code = student_code
        self.class_name = class_name
        self.course_year = course_year
    
    @classmethod
    def from_dict(cls, data: dict) -> "Student":
        """Create Student from dictionary"""
        return cls(
            student_id=data.get("student_id"),
            student_code=data.get("student_code", ""),
            class_name=data.get("class_name"),
            course_year=data.get("course_year")
        )
    
    def to_dict(self) -> dict:
        """Convert Student to dictionary"""
        return {
            "student_id": self.student_id,
            "student_code": self.student_code,
            "class_name": self.class_name,
            "course_year": self.course_year
        }

