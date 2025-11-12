"""
Question generation utilities using AI.
"""
from typing import List, Dict, Any, Optional
from extensions.llm import call_llm_json, prompt_generate_batch_questions, prompt_generate_reference_answers
from utils.vector_search import search_for_question_generation
from utils.bloom_taxonomy import bloom_to_difficulty, get_included_levels
from extensions.supabase_client import supabase


def generate_questions_for_session(
    session_id: int,
    material_id: Optional[int] = None,
    course_name: Optional[str] = None,
    difficulty_level: str = "APPLY",
    num_questions: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Generate questions for a session using AI.
    
    Args:
        session_id: Session ID
        material_id: Material ID (optional, for EXAM/PRACTICE)
        course_name: Course name (for general knowledge if no material)
        difficulty_level: Bloom taxonomy level
        num_questions: Number of questions to generate
        
    Returns:
        List of generated questions
    """
    try:
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
        prompt = prompt_generate_batch_questions(
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
        
        # Map difficulty from Bloom to question difficulty
        question_difficulty = bloom_to_difficulty(difficulty_level)
        
        # Format questions for database
        formatted_questions = []
        for q in questions:
            formatted_questions.append({
                "session_id": session_id,
                "content": q.get("question", ""),
                "keywords": q.get("keywords", ""),
                "difficulty": q.get("difficulty", question_difficulty),
                "status": "draft",
                "reference_answer": None  # Will be generated later
            })
        
        return formatted_questions
        
    except Exception as e:
        print(f"Question generation error: {e}")
        raise


def generate_reference_answers_for_questions(
    session_id: int,
    question_ids: List[int],
    material_id: Optional[int] = None,
    course_name: Optional[str] = None
) -> Dict[int, str]:
    """
    Generate reference answers for approved questions.
    
    Args:
        session_id: Session ID
        question_ids: List of question IDs
        material_id: Material ID (optional)
        course_name: Course name (optional)
        
    Returns:
        Dictionary mapping question_id to reference_answer
    """
    try:
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
                "difficulty": q.get("difficulty", "MEDIUM")
            }
            for q in questions
        ]
        
        # Generate reference answers using AI
        prompt = prompt_generate_reference_answers(
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
        answer_map = {}
        for i, answer_data in enumerate(answers):
            question_index = answer_data.get("question_index", i)
            if question_index < len(questions):
                question_id = questions[question_index]["question_id"]
                answer_map[question_id] = answer_data.get("reference_answer", "")
        
        return answer_map
        
    except Exception as e:
        print(f"Reference answer generation error: {e}")
        raise

