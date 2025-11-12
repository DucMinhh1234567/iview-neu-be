"""
Prompt templates for interview sessions.
"""
from typing import Any, Dict, List, Optional

from config import BATCH_SIZE


def prompt_generate_batch_questions(
    context_chunks: List[Dict[str, str]],
    difficulty: str,
    course_name: Optional[str] = None,
    additional_requirements: Optional[str] = None,
    num_questions: Optional[int] = None
) -> str:
    """Generate prompt for interview question batch creation."""
    chunks_text = "\n\n".join(
        f"[Chunk {idx + 1}]: {chunk.get('text', '')}"
        for idx, chunk in enumerate(context_chunks)
    )

    num_q = num_questions or BATCH_SIZE
    course_info = f"\nCourse: {course_name}" if course_name else ""
    requirements_text = (
        f"\n\nAdditional Requirements: {additional_requirements}"
        if additional_requirements
        else ""
    )

    return f"""You are an expert interviewer crafting behavioral and situational interview questions. Generate {num_q} high-quality questions based on the provided context.

Context Chunks:
{chunks_text}
{course_info}

Difficulty Level: {difficulty} (Bloom Taxonomy)
Question Style: Interview discussion (no multiple choice)

Requirements:
1. Generate exactly {num_q} questions
2. Questions must be grounded ONLY on the provided context chunks
3. Emphasize real-life scenarios, reasoning, and reflection suitable for interviews
4. Ensure each question explores a distinct competency or angle
5. Do NOT include reference answers (they will be generated separately)
6. Avoid multiple choice format
7. Keep questions clear, specific, and open-ended to spark conversation
8. Encourage candidates to explain decisions, experiences, or justifications
{requirements_text}

Output format (JSON):
{{
  "questions": [
    {{
      "question": "Question text here",
      "keywords": "keyword1, keyword2, keyword3",
      "difficulty": "EASY|MEDIUM|HARD"
    }}
  ]
}}

Generate the questions now:"""


def prompt_generate_reference_answers(
    questions: List[Dict[str, str]],
    context_chunks: List[Dict[str, str]],
    course_name: Optional[str] = None
) -> str:
    """Generate prompt for interview reference answers."""
    questions_text = "\n\n".join(
        f"Q{idx + 1}: {question.get('question', '')}\n"
        f"Keywords: {question.get('keywords', '')}\n"
        f"Difficulty: {question.get('difficulty', 'MEDIUM')}"
        for idx, question in enumerate(questions)
    )

    chunks_text = "\n\n".join(
        f"[Chunk {idx + 1}]: {chunk.get('text', '')}"
        for idx, chunk in enumerate(context_chunks)
    )

    course_info = f"\nCourse: {course_name}" if course_name else ""

    return f"""You are an expert interviewer designing model responses for interview questions. Create comprehensive, conversational reference answers using the provided questions and context.

Questions:
{questions_text}

Context Chunks:
{chunks_text}
{course_info}

Requirements:
1. Produce reference answers for ALL questions
2. Answers must be grounded on the provided context chunks
3. Responses should model strong interview storytelling (Situation-Task-Action-Result)
4. Highlight reasoning, decision-making, and personal insights
5. Align tone and depth with the difficulty level
6. Incorporate the supplied keywords naturally

Output format (JSON):
{{
  "answers": [
    {{
      "question_index": 0,
      "reference_answer": "Comprehensive reference answer here..."
    }}
  ]
}}

Generate the reference answers now:"""


def prompt_evaluate_answer(
    question: str,
    student_answer: str,
    reference_answer: str,
    difficulty: str = "MEDIUM"
) -> str:
    """Generate prompt for evaluating interview answers."""
    return f"""You are an expert interviewer assessing a candidate's response. Evaluate the answer using the criteria below, tailored for interview performance.

Question: {question}

Candidate Answer: {student_answer}

Reference Answer: {reference_answer}

Difficulty Level: {difficulty}

Evaluation Criteria (0-10 each):
1. Correctness: Does the answer address the prompt accurately and stay on topic?
2. Coverage: Does it provide sufficient depth, examples, or context from experience?
3. Reasoning: Are decisions and thought processes explained clearly?
4. Creativity: Does the candidate offer original insights or nuanced perspectives?
5. Communication: Is the delivery structured, confident, and easy to follow?
6. Attitude: Is the tone professional, collaborative, and growth-minded?

Requirements:
1. Score each criterion on a 0-10 scale
2. Provide detailed feedback highlighting interview strengths and growth areas
3. Mention notable examples or reasoning from the answer
4. Stay constructive and encouraging
5. Tailor feedback to the stated difficulty level

Output format (JSON):
{{
  "scores": {{
    "correctness": 8.0,
    "coverage": 7.5,
    "reasoning": 7.0,
    "creativity": 7.5,
    "communication": 8.0,
    "attitude": 8.5
  }},
  "overall_score": 7.9,
  "feedback": "Detailed feedback here...",
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1", "weakness 2"]
}}

Evaluate the answer now:"""


def prompt_generate_overall_feedback(
    qa_pairs: List[Dict[str, Any]],
    scores_summary: Dict[str, float]
) -> str:
    """Generate prompt for overall interview feedback."""
    qa_text = "\n\n".join(
        f"Q{idx + 1}: {pair.get('question', '')}\n"
        f"Answer: {pair.get('answer', '')}\n"
        f"Score: {pair.get('score', 0)}/10\n"
        f"Feedback: {pair.get('feedback', '')}"
        for idx, pair in enumerate(qa_pairs)
    )

    scores_text = "\n".join(
        f"{criterion}: {score}/10"
        for criterion, score in scores_summary.items()
    )

    return f"""You are summarizing a job interview performance. Provide holistic feedback that helps the candidate grow.

Question-Answer Pairs:
{qa_text}

Overall Scores Summary:
{scores_text}

Requirements:
1. Deliver an overall assessment of the candidate's interview performance
2. Highlight behavioral strengths and communication qualities
3. Identify key improvement areas with context
4. Offer practical recommendations for future interviews
5. Maintain a constructive, professional tone
6. Consider performance across all answers, not isolated moments

Output format (JSON):
{{
  "overall_feedback": "Comprehensive overall feedback here...",
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "recommendations": ["recommendation 1", "recommendation 2"]
}}

Generate the overall feedback now:"""

