"""
LLM integration for Google Gemini.
Handles API calls, JSON parsing, and prompt templates.
"""
import json
import re
import time
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from config import GEMINI_API_KEY, GEMINI_MODEL, BATCH_SIZE

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

LLM = genai.GenerativeModel(
    GEMINI_MODEL,
    generation_config=GenerationConfig(response_mime_type="application/json")
)


def safe_parse_llm_output(raw: str) -> Dict[str, Any]:
    """
    Safely parse LLM output as JSON.
    Removes code blocks and fixes escape characters.
    
    Args:
        raw: Raw LLM output string
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        ValueError: If JSON parsing fails
    """
    # Remove markdown code blocks
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    
    # Fix unescaped backslashes
    cleaned = re.sub(r'(?<!\\)\\(?![\\"])', r'\\\\', cleaned)
    
    # Parse JSON
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Cannot parse LLM output as JSON: {e}\nRaw output: {raw}")


def call_llm_json(prompt: str, max_retries: int = 3, retry_delay: float = 1.0) -> Dict[str, Any]:
    """
    Call LLM with JSON mode and parse response safely.
    Includes retry logic with exponential backoff.
    
    Args:
        prompt: Prompt text
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries (exponential backoff)
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        Exception: If all retries fail
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            response = LLM.generate_content(prompt)
            raw = (response.text or "").strip()
            if not raw:
                raise ValueError("Empty response from LLM")
            return safe_parse_llm_output(raw)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = retry_delay * (2 ** attempt)  # Exponential backoff
                time.sleep(delay)
            else:
                raise last_error
    
    raise last_error


def prompt_generate_batch_questions(
    context_chunks: List[Dict[str, str]],
    difficulty: str,
    course_name: Optional[str] = None,
    additional_requirements: Optional[str] = None,
    num_questions: Optional[int] = None
) -> str:
    """
    Generate prompt for batch question generation.
    
    Args:
        context_chunks: List of chunks with 'text'
        difficulty: Difficulty level (Bloom taxonomy)
        course_name: Course name (optional)
        additional_requirements: Additional requirements for questions
        num_questions: Number of questions to generate (default: BATCH_SIZE)
        
    Returns:
        Formatted prompt string
    """
    chunks_text = "\n\n".join([
        f"[Chunk {i+1}]: {chunk.get('text', '')}"
        for i, chunk in enumerate(context_chunks)
    ])
    
    num_q = num_questions or BATCH_SIZE
    course_info = f"\nCourse: {course_name}" if course_name else ""
    requirements_text = f"\n\nAdditional Requirements: {additional_requirements}" if additional_requirements else ""
    
    prompt = f"""You are an expert educator creating interview questions. Generate {num_q} high-quality questions based on the provided context.

Context Chunks:
{chunks_text}
{course_info}

Difficulty Level: {difficulty} (Bloom Taxonomy)
Question Type: Short answer / Essay (Q&A only, NO multiple choice)

Requirements:
1. Generate exactly {num_q} questions
2. Questions must be based ONLY on the provided context chunks
3. Questions should test understanding at the {difficulty} level according to Bloom's Taxonomy
4. Each question should be unique and cover different aspects
5. Do NOT include reference answers (they will be generated separately)
6. Do NOT include multiple choice options
7. Questions should be clear, specific, and answerable from the context
8. Avoid questions that simply ask "what does the text say" - focus on understanding and application
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
    
    return prompt


def prompt_generate_reference_answers(
    questions: List[Dict[str, str]],
    context_chunks: List[Dict[str, str]],
    course_name: Optional[str] = None
) -> str:
    """
    Generate prompt for reference answer generation.
    
    Args:
        questions: List of questions with 'question', 'keywords', 'difficulty'
        context_chunks: List of context chunks
        course_name: Course name (optional)
        
    Returns:
        Formatted prompt string
    """
    questions_text = "\n\n".join([
        f"Q{i+1}: {q.get('question', '')}\nKeywords: {q.get('keywords', '')}\nDifficulty: {q.get('difficulty', 'MEDIUM')}"
        for i, q in enumerate(questions)
    ])
    
    chunks_text = "\n\n".join([
        f"[Chunk {i+1}]: {chunk.get('text', '')}"
        for i, chunk in enumerate(context_chunks)
    ])
    
    course_info = f"\nCourse: {course_name}" if course_name else ""
    
    prompt = f"""You are an expert educator creating reference answers for interview questions. Generate comprehensive reference answers based on the provided questions and context.

Questions:
{questions_text}

Context Chunks:
{chunks_text}
{course_info}

Requirements:
1. Generate reference answers for ALL questions
2. Answers must be based on the provided context chunks
3. Answers should be comprehensive and detailed
4. Answers should demonstrate deep understanding of the topic
5. Answers should align with the difficulty level of each question
6. Answers should use the keywords provided for each question

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
    
    return prompt


def prompt_generate_script(
    session_name: str,
    course_name: Optional[str] = None,
    difficulty_level: Optional[str] = None,
    session_type: str = "EXAM"
) -> str:
    """
    Generate prompt for opening and closing script generation.
    
    Args:
        session_name: Session name
        course_name: Course name (optional)
        difficulty_level: Difficulty level (optional)
        session_type: Session type (EXAM, PRACTICE, INTERVIEW)
        
    Returns:
        Formatted prompt string
    """
    course_info = f"\nCourse: {course_name}" if course_name else ""
    difficulty_info = f"\nDifficulty Level: {difficulty_level}" if difficulty_level else ""
    
    prompt = f"""You are creating a script for an {session_type} session. Generate professional opening and closing scripts.

Session Name: {session_name}
{course_info}
{difficulty_info}

Requirements:
1. Opening script should:
   - Welcome students/participants warmly
   - Explain the session purpose and format
   - Provide clear instructions
   - Set expectations
   - Be professional and encouraging

2. Closing script should:
   - Thank participants for their participation
   - Provide next steps or information
   - Be encouraging and supportive
   - Be professional and warm

3. Scripts should be in Vietnamese (unless specified otherwise)
4. Scripts should be appropriate for the session type: {session_type}

Output format (JSON):
{{
  "opening_script": "Opening script text here...",
  "closing_script": "Closing script text here..."
}}

Generate the scripts now:"""
    
    return prompt


def prompt_evaluate_answer(
    question: str,
    student_answer: str,
    reference_answer: str,
    difficulty: str = "MEDIUM"
) -> str:
    """
    Generate prompt for answer evaluation.
    
    Args:
        question: Question text
        student_answer: Student's answer
        reference_answer: Reference answer
        difficulty: Question difficulty
        
    Returns:
        Formatted prompt string
    """
    prompt = f"""You are an expert evaluator assessing a student's answer. Evaluate the answer based on multiple criteria.

Question: {question}

Student Answer: {student_answer}

Reference Answer: {reference_answer}

Difficulty Level: {difficulty}

Evaluation Criteria:
1. Correctness (0-10): How accurate is the answer?
2. Coverage (0-10): How well does it cover the topic?
3. Reasoning (0-10): How logical and well-reasoned is the answer?
4. Creativity (0-10): How creative and original is the approach?
5. Communication (0-10): How clear and well-communicated is the answer?
6. Attitude (0-10): How professional and positive is the tone?

Requirements:
1. Provide scores for each criterion (0-10 scale)
2. Provide detailed feedback for the student
3. Highlight strengths and weaknesses
4. Be constructive and encouraging
5. Consider the difficulty level when scoring

Output format (JSON):
{{
  "scores": {{
    "correctness": 8.0,
    "coverage": 7.5,
    "reasoning": 7.5,
    "creativity": 7.0,
    "communication": 8.5,
    "attitude": 8.0
  }},
  "overall_score": 7.8,
  "feedback": "Detailed feedback here...",
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1", "weakness 2"]
}}

Evaluate the answer now:"""
    
    return prompt


def prompt_generate_overall_feedback(
    qa_pairs: List[Dict[str, Any]],
    scores_summary: Dict[str, float]
) -> str:
    """
    Generate prompt for overall feedback generation.
    
    Args:
        qa_pairs: List of Q&A pairs with scores and feedback
        scores_summary: Summary of scores across all criteria
        
    Returns:
        Formatted prompt string
    """
    qa_text = "\n\n".join([
        f"Q{i+1}: {pair.get('question', '')}\n"
        f"Answer: {pair.get('answer', '')}\n"
        f"Score: {pair.get('score', 0)}/10\n"
        f"Feedback: {pair.get('feedback', '')}"
        for i, pair in enumerate(qa_pairs)
    ])
    
    scores_text = "\n".join([
        f"{criterion}: {score}/10"
        for criterion, score in scores_summary.items()
    ])
    
    prompt = f"""You are providing overall feedback for a complete interview session. Generate comprehensive overall feedback.

Question-Answer Pairs:
{qa_text}

Overall Scores Summary:
{scores_text}

Requirements:
1. Provide overall assessment of performance
2. Highlight main strengths across all answers
3. Identify main weaknesses and areas for improvement
4. Provide specific recommendations for improvement
5. Be constructive and encouraging
6. Consider the overall performance, not just individual answers

Output format (JSON):
{{
  "overall_feedback": "Comprehensive overall feedback here...",
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "recommendations": ["recommendation 1", "recommendation 2"]
}}

Generate the overall feedback now:"""
    
    return prompt

