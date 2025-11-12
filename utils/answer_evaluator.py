"""
Answer evaluation utilities using AI.
"""
from typing import Dict, Any
from extensions.llm import call_llm_json, prompt_evaluate_answer, prompt_generate_overall_feedback


def evaluate_answer(
    question: str,
    student_answer: str,
    reference_answer: str,
    difficulty: str = "MEDIUM"
) -> Dict[str, Any]:
    """
    Evaluate a student's answer using AI.
    
    Args:
        question: Question text
        student_answer: Student's answer
        reference_answer: Reference answer
        difficulty: Question difficulty
        
    Returns:
        Evaluation result with scores and feedback
    """
    try:
        # Generate evaluation prompt
        prompt = prompt_evaluate_answer(
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
        
    except Exception as e:
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
    qa_pairs: list,
    scores_summary: Dict[str, float]
) -> Dict[str, Any]:
    """
    Generate overall feedback for a complete session.
    
    Args:
        qa_pairs: List of Q&A pairs with scores and feedback
        scores_summary: Summary of scores across all criteria
        
    Returns:
        Overall feedback with strengths, weaknesses, and recommendations
    """
    try:
        # Generate feedback prompt
        prompt = prompt_generate_overall_feedback(
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
        
    except Exception as e:
        print(f"Overall feedback generation error: {e}")
        return {
            "overall_feedback": f"Feedback generation error: {str(e)}",
            "strengths": [],
            "weaknesses": [],
            "recommendations": []
        }

