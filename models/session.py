"""
Session model and related types.
"""
from typing import Optional, Literal
from datetime import datetime


SessionType = Literal["EXAM", "PRACTICE", "INTERVIEW"]
BloomLevel = Literal["REMEMBER", "UNDERSTAND", "APPLY", "ANALYZE", "EVALUATE", "CREATE"]
SessionStatus = Literal[
    "created",
    "generating_questions",
    "reviewing_questions",
    "generating_answers",
    "reviewing_answers",
    "generating_script",
    "reviewing_script",
    "ready",
    "active",
    "ended"
]


class Session:
    """Session model"""
    
    def __init__(
        self,
        session_id: int,
        session_name: str,
        session_type: SessionType,
        course_name: Optional[str] = None,
        created_by: int = 0,
        material_id: Optional[int] = None,
        difficulty_level: Optional[BloomLevel] = None,
        follow_up_allowed: bool = False,
        password: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        status: SessionStatus = "created",
        opening_script: Optional[str] = None,
        closing_script: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        self.session_id = session_id
        self.session_name = session_name
        self.session_type = session_type
        self.course_name = course_name
        self.created_by = created_by
        self.material_id = material_id
        self.difficulty_level = difficulty_level
        self.follow_up_allowed = follow_up_allowed
        self.password = password
        self.start_time = start_time
        self.end_time = end_time
        self.status = status
        self.opening_script = opening_script
        self.closing_script = closing_script
        self.created_at = created_at or datetime.now()
    
    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Create Session from dictionary"""
        return cls(
            session_id=data.get("session_id"),
            session_name=data.get("session_name", ""),
            session_type=data.get("session_type", "EXAM"),
            course_name=data.get("course_name"),
            created_by=data.get("created_by", 0),
            material_id=data.get("material_id"),
            difficulty_level=data.get("difficulty_level"),
            follow_up_allowed=data.get("follow_up_allowed", False),
            password=data.get("password"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            status=data.get("status", "created"),
            opening_script=data.get("opening_script"),
            closing_script=data.get("closing_script"),
            created_at=data.get("created_at")
        )
    
    def to_dict(self) -> dict:
        """Convert Session to dictionary"""
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "session_type": self.session_type,
            "course_name": self.course_name,
            "created_by": self.created_by,
            "material_id": self.material_id,
            "difficulty_level": self.difficulty_level,
            "follow_up_allowed": self.follow_up_allowed,
            "password": self.password,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "opening_script": self.opening_script,
            "closing_script": self.closing_script,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


InterviewLevel = Literal["Intern", "Junior", "Mid", "Senior", "Lead"]


class InterviewConfig:
    """Interview configuration model"""
    
    def __init__(
        self,
        config_id: int,
        session_id: int,
        position: str,
        level: InterviewLevel,
        cv_url: str,
        jd_url: Optional[str] = None,
        time_limit: Optional[int] = None,
        num_questions: Optional[int] = None
    ):
        self.config_id = config_id
        self.session_id = session_id
        self.position = position
        self.level = level
        self.cv_url = cv_url
        self.jd_url = jd_url
        self.time_limit = time_limit
        self.num_questions = num_questions
    
    @classmethod
    def from_dict(cls, data: dict) -> "InterviewConfig":
        """Create InterviewConfig from dictionary"""
        return cls(
            config_id=data.get("config_id"),
            session_id=data.get("session_id"),
            position=data.get("position", ""),
            level=data.get("level", "Junior"),
            cv_url=data.get("cv_url", ""),
            jd_url=data.get("jd_url"),
            time_limit=data.get("time_limit"),
            num_questions=data.get("num_questions")
        )
    
    def to_dict(self) -> dict:
        """Convert InterviewConfig to dictionary"""
        return {
            "config_id": self.config_id,
            "session_id": self.session_id,
            "position": self.position,
            "level": self.level,
            "cv_url": self.cv_url,
            "jd_url": self.jd_url,
            "time_limit": self.time_limit,
            "num_questions": self.num_questions
        }

