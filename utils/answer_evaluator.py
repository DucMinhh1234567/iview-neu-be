"""
Answer evaluation utilities using AI.
"""
from typing import Any, Dict, List, Optional, Protocol

from extensions import llm_interview, llm_vandap
from extensions.llm_core import call_llm_json


class EvaluationPromptModule(Protocol):
    """Protocol describing evaluation prompt helpers."""

    def prompt_evaluate_answer(
        self,
        question: str,
        student_answer: str,
        reference_answer: str,
        difficulty: str = "MEDIUM",
    ) -> str:
        ...

    def prompt_generate_overall_feedback(
        self,
        qa_pairs: List[Dict[str, Any]],
        scores_summary: Dict[str, float],
    ) -> str:
        ...


def _select_prompt_module(session_type: Optional[str]) -> EvaluationPromptModule:
    """Pick interview or vấn đáp prompt module based on session type."""
    if (session_type or "").upper() == "INTERVIEW":
        return llm_interview
    return llm_vandap


def evaluate_answer(
    question: str,
    student_answer: str,
    reference_answer: str,
    difficulty: str = "MEDIUM",
    session_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate a student's answer using AI.
    
    Args:
        question: Question text
        student_answer: Student's answer
        reference_answer: Reference answer
        difficulty: Question difficulty
        session_type: Session context (INTERVIEW, PRACTICE, EXAM, ...)
        
    Returns:
        Evaluation result with scores and feedback
    """
    try:
        prompt_module = _select_prompt_module(session_type)

        # Generate evaluation prompt
        prompt = prompt_module.prompt_evaluate_answer(
            question=question,
            student_answer=student_answer,
            reference_answer=reference_answer,
            difficulty=difficulty
        )
        
        # Call LLM
        response = call_llm_json(prompt)
        
        # Extract scores
        scores = response.get("scores", {})
        overall_score = response.get("overall_score", 0.0)
        feedback = response.get("feedback", "")
        strengths = response.get("strengths", [])
        weaknesses = response.get("weaknesses", [])
        
        return {
            "scores": scores,
            "overall_score": float(overall_score),
            "feedback": feedback,
            "strengths": strengths,
            "weaknesses": weaknesses
        }
        
    except Exception as e:  # noqa: BLE001 - default fallback values
        print(f"Answer evaluation error: {e}")
        # Return default evaluation on error
        return {
            "scores": {
                "correctness": 5.0,
                "coverage": 5.0,
                "reasoning": 5.0,
                "creativity": 5.0,
                "communication": 5.0,
                "attitude": 5.0
            },
            "overall_score": 5.0,
            "feedback": f"Evaluation error: {str(e)}",
            "strengths": [],
            "weaknesses": []
        }


def generate_overall_feedback(
    qa_pairs: List[Dict[str, Any]],
    scores_summary: Dict[str, float],
    session_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate overall feedback for a complete session.
    
    Args:
        qa_pairs: List of Q&A pairs with scores and feedback
        scores_summary: Summary of scores across all criteria
        session_type: Session context (INTERVIEW, PRACTICE, EXAM, ...)
        
    Returns:
        Overall feedback with strengths, weaknesses, and recommendations
    """
    try:
        prompt_module = _select_prompt_module(session_type)

        # Generate feedback prompt
        prompt = prompt_module.prompt_generate_overall_feedback(
            qa_pairs=qa_pairs,
            scores_summary=scores_summary
        )
        
        # Call LLM
        response = call_llm_json(prompt)
        
        return {
            "overall_feedback": response.get("overall_feedback", ""),
            "strengths": response.get("strengths", []),
            "weaknesses": response.get("weaknesses", []),
            "recommendations": response.get("recommendations", [])
        }
        
    except Exception as e:  # noqa: BLE001 - default fallback values
        print(f"Overall feedback generation error: {e}")
        return {
            "overall_feedback": f"Feedback generation error: {str(e)}",
            "strengths": [],
            "weaknesses": [],
            "recommendations": []
        }

