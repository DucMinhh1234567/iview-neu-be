"""
Question generation utilities using AI.
"""
from typing import Any, Dict, List, Optional, Protocol

from extensions import llm_interview, llm_qanda
from extensions.llm_core import call_llm_json
from utils.vector_search import search_for_question_generation
from utils.cv_ingest import load_and_extract, cleanup_temp
from extensions.supabase_client import supabase


class QuestionPromptModule(Protocol):
    """Protocol describing required prompt helpers."""

    def prompt_generate_batch_questions(
        self,
        context_chunks: List[Dict[str, str]],
        difficulty: str,
        course_name: Optional[str] = None,
        additional_requirements: Optional[str] = None,
        num_questions: Optional[int] = None,
    ) -> str:
        ...

    def prompt_generate_reference_answers(
        self,
        questions: List[Dict[str, str]],
        context_chunks: List[Dict[str, str]],
        course_name: Optional[str] = None,
    ) -> str:
        ...


def _select_prompt_module(session_type: Optional[str]) -> QuestionPromptModule:
    """Select appropriate prompt module based on session type."""
    if (session_type or "").upper() == "INTERVIEW":
        return llm_interview
    return llm_qanda


def generate_questions_for_session(
    session_id: int,
    material_id: Optional[int] = None,
    course_name: Optional[str] = None,
    difficulty_level: str = "APPLY",
    num_questions: Optional[int] = None,
    session_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Generate questions for a session using AI.
    
    Args:
        session_id: Session ID
        material_id: Material ID (optional, for EXAM/PRACTICE)
        course_name: Course name (for general knowledge if no material)
        difficulty_level: Bloom taxonomy level
        num_questions: Number of questions to generate
        session_type: Session context (INTERVIEW, PRACTICE, EXAM, ...)
        
    Returns:
        List of generated questions
    """
    try:
        prompt_module = _select_prompt_module(session_type)

        # Get context chunks if material is provided
        context_chunks = []
        if material_id:
            # Vector search for relevant chunks
            context_chunks = search_for_question_generation(
                material_id=material_id,
                query="general knowledge",
                k=10  # Get more chunks for context
            )
            
            if not context_chunks:
                raise Exception("No chunks found for material")
            
            # Format chunks for prompt
            chunks_for_prompt = [
                {"text": chunk["chunk_text"]}
                for chunk in context_chunks
            ]
        else:
            # No material - use course name for general knowledge
            chunks_for_prompt = []
        
        # Generate questions using AI
        prompt = prompt_module.prompt_generate_batch_questions(
            context_chunks=chunks_for_prompt,
            difficulty=difficulty_level,
            course_name=course_name,
            num_questions=num_questions
        )
        
        # Call LLM
        response = call_llm_json(prompt)
        
        if "questions" not in response:
            raise Exception("Invalid response format from AI")
        
        questions = response["questions"]
        
        # Format questions for database
        formatted_questions: List[Dict[str, Any]] = []
        for q in questions:
            # Với INTERVIEW: LLM trả về question_type; với vấn đáp/thi: dùng Bloom level của session
            question_type = q.get("question_type") or (
                difficulty_level if (session_type or "").upper() != "INTERVIEW" else ""
            )
            formatted_questions.append({
                "session_id": session_id,
                "content": q.get("question", ""),
                "keywords": q.get("keywords", ""),
                "question_type": question_type,
                "status": "draft",
                "reference_answer": None  # Will be generated later
            })
        
        return formatted_questions
        
    except Exception as e:  # noqa: BLE001 - bubble up handled error
        print(f"Question generation error: {e}")
        raise


def _chunk_text(text: str, max_chars: int = 4000) -> List[str]:
    """Simple text chunker to keep prompts bounded."""
    if not text:
        return []
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


def generate_interview_questions(
    session_id: int,
    job_title: str,
    cv_source: str,
    jd_source: Optional[str] = None,
    num_questions: int = 8,
) -> List[Dict[str, Any]]:
    """
    Generate interview questions using CV (and optional JD) text.

    Args:
        session_id: Session ID
        job_title: Target position
        cv_source: Path or URL to CV file
        jd_source: Path or URL to JD file (optional)
        num_questions: Number of questions to generate

    Returns:
        List of questions ready for insertion into question_interview
    """
    tmp_paths = []
    try:
        cv_text, cv_tmp = load_and_extract(cv_source)
        tmp_paths.append(cv_tmp)
        jd_text = ""
        jd_tmp = None
        if jd_source:
            jd_text, jd_tmp = load_and_extract(jd_source)
            tmp_paths.append(jd_tmp)

        # Build context chunks from CV and JD text (ephemeral, not persisted)
        combined_chunks = []
        for text in [cv_text, jd_text]:
            for chunk in _chunk_text(text):
                combined_chunks.append({"text": chunk})

        prompt = llm_interview.prompt_generate_batch_questions(
            context_chunks=combined_chunks,
            difficulty="MEDIUM",
            course_name=job_title,
            num_questions=num_questions,
        )

        response = call_llm_json(prompt)
        questions = response.get("questions", [])
        if not isinstance(questions, list):
            raise Exception("Invalid response format from AI")

        formatted_questions: List[Dict[str, Any]] = []
        for idx, q in enumerate(questions):
            formatted_questions.append(
                {
                    "session_id": session_id,
                    "content": q.get("question", ""),
                    "keywords": q.get("keywords", ""),
                    "question_type": q.get("question_type", ""),
                    "category": q.get("category", ""),
                    "purpose": q.get("purpose", ""),
                    "job_title": job_title,
                    "question_index": idx,
                    "status": "approved",
                    "reference_answer": None,
                }
            )

        return formatted_questions
    finally:
        for tmp in tmp_paths:
            cleanup_temp(tmp)


def generate_reference_answers_for_interview(
    question_interview_ids: List[int],
    cv_source: str,
    jd_source: Optional[str] = None,
    job_title: Optional[str] = None,
) -> Dict[int, str]:
    """
    Generate reference answers for interview questions using CV/JD text.

    Args:
        question_interview_ids: IDs of interview questions
        cv_source: Path or URL to CV file
        jd_source: Path or URL to JD file (optional)
        job_title: Target position (optional)

    Returns:
        Mapping question_interview_id -> reference_answer
    """
    tmp_paths = []
    try:
        cv_text, cv_tmp = load_and_extract(cv_source)
        tmp_paths.append(cv_tmp)
        jd_text = ""
        jd_tmp = None
        if jd_source:
            jd_text, jd_tmp = load_and_extract(jd_source)
            tmp_paths.append(jd_tmp)

        questions_response = (
            supabase.table("question_interview")
            .select("*")
            .in_("question_interview_id", question_interview_ids)
            .execute()
        )
        questions = questions_response.data or []
        if not questions:
            raise Exception("Interview questions not found")

        questions_for_prompt = [
            {
                "question": q.get("content", ""),
                "keywords": q.get("keywords", ""),
                "question_type": q.get("question_type", ""),
            }
            for q in questions
        ]

        combined_chunks = []
        for text in [cv_text, jd_text]:
            for chunk in _chunk_text(text):
                combined_chunks.append({"text": chunk})

        prompt = llm_interview.prompt_generate_reference_answers(
            questions=questions_for_prompt,
            context_chunks=combined_chunks,
            course_name=job_title,
        )

        response = call_llm_json(prompt)
        answers = response.get("answers", [])
        if not isinstance(answers, list):
            raise Exception("Invalid response format from AI")

        answer_map: Dict[int, str] = {}
        for i, answer_data in enumerate(answers):
            question_index = answer_data.get("question_index", i)
            if question_index < len(questions):
                question_id = questions[question_index]["question_interview_id"]
                answer_map[question_id] = answer_data.get("reference_answer", "")

        return answer_map
    finally:
        for tmp in tmp_paths:
            cleanup_temp(tmp)


def generate_reference_answers_for_questions(
    session_id: int,
    question_ids: List[int],
    material_id: Optional[int] = None,
    course_name: Optional[str] = None,
    session_type: Optional[str] = None,
) -> Dict[int, str]:
    """
    Generate reference answers for approved questions.
    
    Args:
        session_id: Session ID
        question_ids: List of question IDs
        material_id: Material ID (optional)
        course_name: Course name (optional)
        session_type: Session context (INTERVIEW, PRACTICE, EXAM, ...)
        
    Returns:
        Dictionary mapping question_id to reference_answer
    """
    try:
        prompt_module = _select_prompt_module(session_type)

        # Get questions
        questions_response = supabase.table("question").select("*").in_("question_id", question_ids).execute()
        
        if not questions_response.data:
            raise Exception("Questions not found")
        
        questions = questions_response.data
        
        # Get context chunks if material is provided
        context_chunks = []
        if material_id:
            chunks_response = supabase.table("material_chunks").select("chunk_text").eq("material_id", material_id).limit(10).execute()
            if chunks_response.data:
                context_chunks = [
                    {"text": chunk["chunk_text"]}
                    for chunk in chunks_response.data
                ]
        
        # Format questions for prompt
        questions_for_prompt = [
            {
                "question": q["content"],
                "keywords": q.get("keywords", ""),
                "question_type": q.get("question_type", "")
            }
            for q in questions
        ]
        
        # Generate reference answers using AI
        prompt = prompt_module.prompt_generate_reference_answers(
            questions=questions_for_prompt,
            context_chunks=context_chunks,
            course_name=course_name
        )
        
        # Call LLM
        response = call_llm_json(prompt)
        
        if "answers" not in response:
            raise Exception("Invalid response format from AI")
        
        answers = response["answers"]
        
        # Map answers to question IDs
        answer_map: Dict[int, str] = {}
        for i, answer_data in enumerate(answers):
            question_index = answer_data.get("question_index", i)
            if question_index < len(questions):
                question_id = questions[question_index]["question_id"]
                answer_map[question_id] = answer_data.get("reference_answer", "")
        
        return answer_map
        
    except Exception as e:  # noqa: BLE001 - bubble up handled error
        print(f"Reference answer generation error: {e}")
        raise

