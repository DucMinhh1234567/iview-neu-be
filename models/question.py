"""
Question model and related types.
"""
from typing import Optional, Literal


QuestionDifficulty = Literal["EASY", "MEDIUM", "HARD"]
QuestionStatus = Literal[
    "draft",
    "approved",
    "answers_generated",
    "answers_approved",
    "finalized"
]


class Question:
    """Question model"""
    
    def __init__(
        self,
        question_id: int,
        session_id: int,
        content: str,
        keywords: Optional[str] = None,
        difficulty: Optional[QuestionDifficulty] = None,
        follow_up: bool = False,
        reference_answer: Optional[str] = None,
        status: QuestionStatus = "draft",
        created_by: Optional[int] = None
    ):
        self.question_id = question_id
        self.session_id = session_id
        self.content = content
        self.keywords = keywords
        self.difficulty = difficulty
        self.follow_up = follow_up
        self.reference_answer = reference_answer
        self.status = status
        self.created_by = created_by
    
    @classmethod
    def from_dict(cls, data: dict) -> "Question":
        """Create Question from dictionary"""
        return cls(
            question_id=data.get("question_id"),
            session_id=data.get("session_id"),
            content=data.get("content", ""),
            keywords=data.get("keywords"),
            difficulty=data.get("difficulty"),
            follow_up=data.get("follow_up", False),
            reference_answer=data.get("reference_answer"),
            status=data.get("status", "draft"),
            created_by=data.get("created_by")
        )
    
    def to_dict(self) -> dict:
        """Convert Question to dictionary"""
        return {
            "question_id": self.question_id,
            "session_id": self.session_id,
            "content": self.content,
            "keywords": self.keywords,
            "difficulty": self.difficulty,
            "follow_up": self.follow_up,
            "reference_answer": self.reference_answer,
            "status": self.status,
            "created_by": self.created_by
        }

