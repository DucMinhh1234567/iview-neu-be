"""
Student session and answer models.
"""
from typing import Optional
from datetime import datetime


class StudentSession:
    """Student session model"""
    
    def __init__(
        self,
        student_session_id: int,
        session_id: int,
        student_id: int,
        join_time: Optional[datetime] = None,
        score_total: Optional[float] = None,
        ai_overall_feedback: Optional[str] = None,
        reviewed_by: Optional[int] = None,
        reviewed_at: Optional[datetime] = None
    ):
        self.student_session_id = student_session_id
        self.session_id = session_id
        self.student_id = student_id
        self.join_time = join_time or datetime.now()
        self.score_total = score_total
        self.ai_overall_feedback = ai_overall_feedback
        self.reviewed_by = reviewed_by
        self.reviewed_at = reviewed_at
    
    @classmethod
    def from_dict(cls, data: dict) -> "StudentSession":
        """Create StudentSession from dictionary"""
        return cls(
            student_session_id=data.get("student_session_id"),
            session_id=data.get("session_id"),
            student_id=data.get("student_id"),
            join_time=data.get("join_time"),
            score_total=data.get("score_total"),
            ai_overall_feedback=data.get("ai_overall_feedback"),
            reviewed_by=data.get("reviewed_by"),
            reviewed_at=data.get("reviewed_at")
        )
    
    def to_dict(self) -> dict:
        """Convert StudentSession to dictionary"""
        return {
            "student_session_id": self.student_session_id,
            "session_id": self.session_id,
            "student_id": self.student_id,
            "join_time": self.join_time.isoformat() if self.join_time else None,
            "score_total": self.score_total,
            "ai_overall_feedback": self.ai_overall_feedback,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None
        }


class StudentAnswer:
    """Student answer model"""
    
    def __init__(
        self,
        answer_id: int,
        student_session_id: int,
        question_id: int,
        answer_text: str,
        ai_score: Optional[float] = None,
        ai_feedback: Optional[str] = None,
        lecturer_score: Optional[float] = None,
        lecturer_feedback: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        self.answer_id = answer_id
        self.student_session_id = student_session_id
        self.question_id = question_id
        self.answer_text = answer_text
        self.ai_score = ai_score
        self.ai_feedback = ai_feedback
        self.lecturer_score = lecturer_score
        self.lecturer_feedback = lecturer_feedback
        self.created_at = created_at or datetime.now()
    
    @classmethod
    def from_dict(cls, data: dict) -> "StudentAnswer":
        """Create StudentAnswer from dictionary"""
        return cls(
            answer_id=data.get("answer_id"),
            student_session_id=data.get("student_session_id"),
            question_id=data.get("question_id"),
            answer_text=data.get("answer_text", ""),
            ai_score=data.get("ai_score"),
            ai_feedback=data.get("ai_feedback"),
            lecturer_score=data.get("lecturer_score"),
            lecturer_feedback=data.get("lecturer_feedback"),
            created_at=data.get("created_at")
        )
    
    def to_dict(self) -> dict:
        """Convert StudentAnswer to dictionary"""
        return {
            "answer_id": self.answer_id,
            "student_session_id": self.student_session_id,
            "question_id": self.question_id,
            "answer_text": self.answer_text,
            "ai_score": self.ai_score,
            "ai_feedback": self.ai_feedback,
            "lecturer_score": self.lecturer_score,
            "lecturer_feedback": self.lecturer_feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

