"""
Student sessions blueprint for student participation flow.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from extensions.supabase_client import supabase
from extensions.auth_middleware import require_auth, require_student
from utils.answer_evaluator import evaluate_answer, generate_overall_feedback

student_sessions_bp = Blueprint("student_sessions", __name__)


@student_sessions_bp.route("/join", methods=["POST"])
@require_student
def join_session():
    """Join a session (EXAM requires password)."""
    data = request.get_json()
    session_id = data.get("session_id")
    password = data.get("password", "")
    
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
    
    student_id = request.user_id
    
    try:
        # Get session details
        session_response = supabase.table("session").select("*").eq("session_id", session_id).single().execute()
        
        if not session_response.data:
            return jsonify({"error": "Session not found"}), 404
        
        session = session_response.data
        
        # Check session status and password based on session type
        if session["session_type"] == "EXAM":
            # EXAM sessions must be ready
            if session["status"] != "ready":
                return jsonify({"error": "Session is not ready yet"}), 400
            
            # Check password for EXAM sessions
            if session.get("password"):
                if password != session["password"]:
                    return jsonify({"error": "Invalid password"}), 401
        elif session["session_type"] in ["PRACTICE", "INTERVIEW"]:
            # PRACTICE/INTERVIEW sessions can be started immediately (status: created)
            # No password required
            if session["status"] not in ["created", "ready"]:
                return jsonify({"error": "Session is not available"}), 400
        
        # Check if student has already joined
        existing_response = supabase.table("studentsession").select("student_session_id").eq("session_id", session_id).eq("student_id", student_id).execute()
        
        if existing_response.data:
            student_session_id = existing_response.data[0]["student_session_id"]
            return jsonify({
                "student_session_id": student_session_id,
                "message": "Already joined this session"
            }), 200
        
        # Create student session
        student_session_data = {
            "session_id": session_id,
            "student_id": student_id
        }
        
        student_session_response = supabase.table("studentsession").insert(student_session_data).execute()
        
        if not student_session_response.data:
            return jsonify({"error": "Failed to join session"}), 500
        
        student_session_id = student_session_response.data[0]["student_session_id"]
        
        return jsonify({
            "student_session_id": student_session_id,
            "session_id": session_id,
            "message": "Joined session successfully"
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to join session: {str(e)}"}), 500


@student_sessions_bp.route("/<int:student_session_id>/start", methods=["POST"])
@require_student
def start_session(student_session_id):
    """Start a student session."""
    student_id = request.user_id
    
    try:
        # Verify student session exists and belongs to student
        student_session_response = supabase.table("studentsession").select("*").eq("student_session_id", student_session_id).single().execute()
        
        if not student_session_response.data:
            return jsonify({"error": "Student session not found"}), 404
        
        student_session = student_session_response.data
        
        if student_session["student_id"] != student_id:
            return jsonify({"error": "Access denied"}), 403
        
        # Get session details
        session_response = supabase.table("session").select("*").eq("session_id", student_session["session_id"]).single().execute()
        
        if not session_response.data:
            return jsonify({"error": "Session not found"}), 404
        
        session = session_response.data
        
        # Check if session is ready (for EXAM) or created (for PRACTICE/INTERVIEW)
        if session["session_type"] == "EXAM" and session["status"] != "ready":
            return jsonify({"error": "Session is not ready"}), 400
        elif session["session_type"] in ["PRACTICE", "INTERVIEW"] and session["status"] not in ["created", "ready"]:
            return jsonify({"error": "Session is not available"}), 400
        
        # For PRACTICE and INTERVIEW, generate questions if not already generated
        if session["session_type"] in ["PRACTICE", "INTERVIEW"]:
            # Check if questions exist
            questions_response = supabase.table("question").select("question_id").eq("session_id", session["session_id"]).execute()
            
            if not questions_response.data:
                # Generate questions on the fly
                from utils.question_generator import generate_questions_for_session
                
                try:
                    # Defaults for PRACTICE
                    gen_kwargs = {
                        "session_id": session["session_id"],
                        "material_id": session.get("material_id"),
                        "course_name": session.get("course_name"),
                        "difficulty_level": session.get("difficulty_level", "APPLY"),
                        "num_questions": None,
                    }

                    # For INTERVIEW sessions, pull config to guide generation
                    if session["session_type"] == "INTERVIEW":
                        try:
                            cfg = supabase.table("interviewconfig").select("*").eq("session_id", session["session_id"]).single().execute()
                            if cfg.data:
                                # Use position as course_name/topic for generation
                                gen_kwargs["course_name"] = cfg.data.get("position") or "interview"
                                # Map level to a sensible default difficulty if needed
                                gen_kwargs["difficulty_level"] = "APPLY"  # keep stable default
                                # Respect requested number of questions if provided
                                gen_kwargs["num_questions"] = cfg.data.get("num_questions")
                        except Exception as _e:
                            print(f"Warning: Failed to read interview config for session {session['session_id']}: {_e}")

                    questions = generate_questions_for_session(**gen_kwargs)
                    
                    # Insert questions
                    for question in questions:
                        question["status"] = "approved"  # Auto-approve for practice/interview
                        question["reference_answer"] = None  # Will be generated when answer is submitted
                        supabase.table("question").insert(question).execute()
                except Exception as e:
                    print(f"Warning: Failed to generate questions on-the-fly: {e}")
                    # Continue anyway - questions might be generated later
        
        # Get total questions count
        # Questions can have status "approved" or "answers_approved" - both are valid for students
        questions_response = supabase.table("question").select("question_id").eq("session_id", session["session_id"]).in_("status", ["approved", "answers_approved"]).execute()
        total_questions = len(questions_response.data or [])
        
        if total_questions == 0:
            return jsonify({"error": "No questions available for this session"}), 400
        
        return jsonify({
            "student_session_id": student_session_id,
            "session_started": True,
            "total_questions": total_questions,
            "time_limit": session.get("time_limit")
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to start session: {str(e)}"}), 500


@student_sessions_bp.route("/<int:student_session_id>/question", methods=["GET"])
@require_student
def get_next_question(student_session_id):
    """Get next question for student session."""
    student_id = request.user_id
    
    try:
        # Verify student session
        student_session_response = supabase.table("studentsession").select("*").eq("student_session_id", student_session_id).single().execute()
        
        if not student_session_response.data:
            return jsonify({"error": "Student session not found"}), 404
        
        student_session = student_session_response.data
        
        if student_session["student_id"] != student_id:
            return jsonify({"error": "Access denied"}), 403
        
        session_id = student_session["session_id"]
        
        # Get all answered question IDs
        answered_response = supabase.table("studentanswer").select("question_id").eq("student_session_id", student_session_id).execute()
        answered_question_ids = [a["question_id"] for a in (answered_response.data or [])]
        
        # Get all approved questions (both "approved" and "answers_approved" status)
        all_questions_response = supabase.table("question").select("*").eq("session_id", session_id).in_("status", ["approved", "answers_approved"]).execute()
        all_questions = all_questions_response.data or []
        
        # Filter out already answered questions
        if answered_question_ids:
            unanswered = [q for q in all_questions if q["question_id"] not in answered_question_ids]
        else:
            unanswered = all_questions
        
        if not unanswered:
            return jsonify({
                "message": "No more questions",
                "completed": True
            }), 200
        
        # Get first unanswered question
        question = unanswered[0]
        
        # Get total questions count
        total_questions = len(all_questions)
        
        return jsonify({
            "question_id": question["question_id"],
            "question": question["content"],
            "question_number": len(answered_question_ids) + 1,
            "total_questions": total_questions,
            "difficulty": question.get("difficulty", "MEDIUM")
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get question: {str(e)}"}), 500


@student_sessions_bp.route("/<int:student_session_id>/answer", methods=["POST"])
@require_student
def submit_answer(student_session_id):
    """Submit answer for a question (without AI evaluation - will be evaluated later)."""
    data = request.get_json()
    question_id = data.get("question_id")
    answer_text = data.get("answer")
    
    if not question_id or not answer_text:
        return jsonify({"error": "Question ID and answer are required"}), 400
    
    student_id = request.user_id
    
    try:
        # Verify student session
        student_session_response = supabase.table("studentsession").select("*").eq("student_session_id", student_session_id).single().execute()
        
        if not student_session_response.data:
            return jsonify({"error": "Student session not found"}), 404
        
        student_session = student_session_response.data
        
        if student_session["student_id"] != student_id:
            return jsonify({"error": "Access denied"}), 403
        
        # Get question
        question_response = supabase.table("question").select("*").eq("question_id", question_id).single().execute()
        
        if not question_response.data:
            return jsonify({"error": "Question not found"}), 404
        
        question = question_response.data
        
        # Check if already answered (idempotent handling)
        existing_answer_response = supabase.table("studentanswer").select("*").eq("student_session_id", student_session_id).eq("question_id", question_id).execute()
        
        if existing_answer_response.data:
            # Treat as success to avoid double-submit errors on network retry
            existing_answer = existing_answer_response.data[0]
            
            # Compute progress to mirror success payload
            answered_response = supabase.table("studentanswer").select("question_id").eq("student_session_id", student_session_id).execute()
            answered_count = len(answered_response.data or [])
            all_questions_response = supabase.table("question").select("question_id").eq("session_id", question["session_id"]).in_("status", ["approved", "answers_approved"]).execute()
            total_questions = len(all_questions_response.data or [])
            
            return jsonify({
                "answer_id": existing_answer.get("answer_id"),
                "ai_score": existing_answer.get("ai_score"),
                "ai_feedback": existing_answer.get("ai_feedback"),
                "next_question_available": answered_count < total_questions,
                "answered_count": answered_count,
                "total_questions": total_questions,
                "message": "Question already answered"
            }), 200
        
        # Get reference answer (if available)
        reference_answer = question.get("reference_answer", "")
        
        # For PRACTICE/INTERVIEW sessions, generate reference answer on-the-fly if not available
        if not reference_answer:
            session_response = supabase.table("session").select("session_type, material_id, course_name").eq("session_id", question["session_id"]).single().execute()
            session = session_response.data if session_response.data else {}
            
            if session.get("session_type") in ["PRACTICE", "INTERVIEW"]:
                # Generate reference answer on-the-fly
                try:
                    from utils.question_generator import generate_reference_answers_for_questions
                    answer_map = generate_reference_answers_for_questions(
                        session_id=question["session_id"],
                        question_ids=[question_id],
                        material_id=session.get("material_id"),
                        course_name=session.get("course_name")
                    )
                    reference_answer = answer_map.get(question_id, "")
                    
                    # Update question with reference answer
                    if reference_answer:
                        supabase.table("question").update({
                            "reference_answer": reference_answer
                        }).eq("question_id", question_id).execute()
                except Exception as e:
                    print(f"Warning: Failed to generate reference answer: {e}")
                    reference_answer = ""  # Continue without reference answer
        
        # Chỉ lưu câu trả lời, không có điểm và feedback
        safe_answer_text = answer_text if len(answer_text) <= 16000 else (answer_text[:16000])
        answer_data = {
            "student_session_id": student_session_id,
            "question_id": question_id,
            "answer_text": safe_answer_text,
            "ai_score": None,  # Sẽ được cập nhật sau
            "ai_feedback": None  # Sẽ được cập nhật sau
        }
        
        answer_response = supabase.table("studentanswer").insert(answer_data).execute()
        
        if not answer_response.data:
            return jsonify({"error": "Failed to save answer"}), 500
        
        answer_id = answer_response.data[0]["answer_id"]
        
        # Calculate progress
        answered_response = supabase.table("studentanswer").select("question_id").eq("student_session_id", student_session_id).execute()
        answered_count = len(answered_response.data or [])
        all_questions_response = supabase.table("question").select("question_id").eq("session_id", question["session_id"]).in_("status", ["approved", "answers_approved"]).execute()
        total_questions = len(all_questions_response.data or [])
        
        return jsonify({
            "answer_id": answer_id,
            "ai_score": None,  # Chưa có điểm
            "ai_feedback": None,  # Chưa có feedback
            "next_question_available": answered_count < total_questions,
            "answered_count": answered_count,
            "total_questions": total_questions,
            "message": "Answer saved. Evaluation will be done after completing all questions."
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to submit answer: {str(e)}"}), 500


@student_sessions_bp.route("/<int:student_session_id>/end", methods=["POST"])
@require_student
def end_session(student_session_id):
    """End student session, evaluate all answers, and generate overall feedback."""
    student_id = request.user_id
    
    try:
        # Verify student session
        student_session_response = supabase.table("studentsession").select("*").eq("student_session_id", student_session_id).single().execute()
        
        if not student_session_response.data:
            return jsonify({"error": "Student session not found"}), 404
        
        student_session = student_session_response.data
        
        if student_session["student_id"] != student_id:
            return jsonify({"error": "Access denied"}), 403
        
        session_id = student_session["session_id"]
        
        # Get all answers (chưa có điểm)
        try:
            answers_response = supabase.table("studentanswer").select("*").eq("student_session_id", student_session_id).execute()
            
            if not answers_response.data:
                return jsonify({"error": "No answers found"}), 400
            
            answers = answers_response.data
        except Exception as e:
            print(f"Error getting answers: {e}")
            return jsonify({"error": f"Failed to retrieve answers: {str(e)}"}), 500
        
        # Get questions for each answer
        try:
            question_ids = [a["question_id"] for a in answers if a.get("question_id")]
            if not question_ids:
                return jsonify({"error": "No valid question IDs found in answers"}), 400
            
            questions_response = supabase.table("question").select("*").in_("question_id", question_ids).execute()
            questions_dict = {q["question_id"]: q for q in (questions_response.data or [])}
        except Exception as e:
            print(f"Error getting questions: {e}")
            return jsonify({"error": f"Failed to retrieve questions: {str(e)}"}), 500
        
        # Get session info for reference answer generation
        try:
            session_response = supabase.table("session").select("session_type, material_id, course_name").eq("session_id", session_id).single().execute()
            session = session_response.data if session_response.data else {}
        except Exception as e:
            print(f"Warning: Failed to get session info: {e}")
            session = {}
        
        # Evaluate ALL answers in batch (with progress tracking)
        evaluated_answers = []
        evaluation_errors = []
        
        print(f"[end_session] Starting evaluation for {len(answers)} answers, student_session_id={student_session_id}")
        
        # Process answers sequentially to avoid overwhelming AI API
        for idx, answer in enumerate(answers):
            print(f"[end_session] Evaluating answer {idx + 1}/{len(answers)} (answer_id={answer.get('answer_id')})")
            
            try:
                question = questions_dict.get(answer["question_id"], {})
                if not question:
                    print(f"Warning: Question {answer['question_id']} not found for answer {answer['answer_id']}")
                    evaluated_answers.append({
                        "answer_id": answer["answer_id"],
                        "question_id": answer["question_id"],
                        "ai_score": None,
                        "ai_feedback": "Question not found"
                    })
                    continue
                
                # Get or generate reference answer
                reference_answer = question.get("reference_answer", "")
                if not reference_answer and session.get("session_type") in ["PRACTICE", "INTERVIEW"]:
                    try:
                        from utils.question_generator import generate_reference_answers_for_questions
                        answer_map = generate_reference_answers_for_questions(
                            session_id=session_id,
                            question_ids=[question["question_id"]],
                            material_id=session.get("material_id"),
                            course_name=session.get("course_name")
                        )
                        reference_answer = answer_map.get(question["question_id"], "")
                        if reference_answer:
                            try:
                                supabase.table("question").update({
                                    "reference_answer": reference_answer
                                }).eq("question_id", question["question_id"]).execute()
                            except Exception as update_e:
                                print(f"Warning: Failed to update reference answer: {update_e}")
                    except Exception as gen_e:
                        print(f"Warning: Failed to generate reference answer for question {question['question_id']}: {gen_e}")
                        reference_answer = ""
                
                # Evaluate answer
                try:
                    evaluation = evaluate_answer(
                        question=question.get("content", ""),
                        student_answer=answer.get("answer_text", ""),
                        reference_answer=reference_answer if reference_answer else "No reference answer available.",
                        difficulty=question.get("difficulty", "MEDIUM")
                    )
                    
                    # Safely extract score
                    try:
                        ai_score = evaluation.get("overall_score")
                        if ai_score is not None:
                            ai_score = float(ai_score)
                        else:
                            ai_score = None
                    except (ValueError, TypeError) as score_e:
                        print(f"Warning: Invalid score format: {score_e}")
                        ai_score = None
                    
                    # Update answer with evaluation
                    feedback_text = (evaluation.get("feedback") or "")
                    if isinstance(feedback_text, str) and len(feedback_text) > 8000:
                        feedback_text = feedback_text[:8000]
                    
                    try:
                        supabase.table("studentanswer").update({
                            "ai_score": ai_score,
                            "ai_feedback": feedback_text
                        }).eq("answer_id", answer["answer_id"]).execute()
                    except Exception as update_e:
                        print(f"Warning: Failed to update answer {answer['answer_id']}: {update_e}")
                        evaluation_errors.append(f"Failed to update answer {answer['answer_id']}: {str(update_e)}")
                    
                    evaluated_answers.append({
                        "answer_id": answer["answer_id"],
                        "question_id": answer["question_id"],
                        "ai_score": ai_score,
                        "ai_feedback": evaluation.get("feedback", "")
                    })
                except Exception as eval_e:
                    print(f"Warning: Failed to evaluate answer {answer['answer_id']}: {eval_e}")
                    import traceback
                    print(f"Traceback: {traceback.format_exc()}")
                    evaluation_errors.append(f"Failed to evaluate answer {answer['answer_id']}: {str(eval_e)}")
                    # Keep answer without score
                    evaluated_answers.append({
                        "answer_id": answer["answer_id"],
                        "question_id": answer["question_id"],
                        "ai_score": None,
                        "ai_feedback": f"Evaluation error: {str(eval_e)[:200]}"
                    })
            except Exception as answer_e:
                print(f"Error processing answer {answer.get('answer_id', 'unknown')}: {answer_e}")
                evaluation_errors.append(f"Error processing answer: {str(answer_e)}")
                evaluated_answers.append({
                    "answer_id": answer.get("answer_id"),
                    "question_id": answer.get("question_id"),
                    "ai_score": None,
                    "ai_feedback": f"Processing error: {str(answer_e)[:200]}"
                })
        
        # Calculate overall score from evaluated answers
        try:
            scores = [a["ai_score"] for a in evaluated_answers if a.get("ai_score") is not None]
            overall_score = sum(scores) / len(scores) if scores else 0.0
        except Exception as calc_e:
            print(f"Warning: Failed to calculate overall score: {calc_e}")
            overall_score = 0.0
        
        # Prepare Q&A pairs for overall feedback
        qa_pairs = []
        scores_summary = {
            "correctness": 0.0,
            "coverage": 0.0,
            "reasoning": 0.0,
            "creativity": 0.0,
            "communication": 0.0,
            "attitude": 0.0
        }
        
        try:
            for answer in answers:
                question = questions_dict.get(answer["question_id"], {})
                eval_data = next((e for e in evaluated_answers if e["answer_id"] == answer["answer_id"]), {})
                qa_pairs.append({
                    "question": question.get("content", ""),
                    "answer": answer.get("answer_text", ""),
                    "score": eval_data.get("ai_score", 0.0),
                    "feedback": eval_data.get("ai_feedback", "")
                })
        except Exception as pairs_e:
            print(f"Warning: Failed to prepare Q&A pairs: {pairs_e}")
        
        # Generate overall feedback (skip if too many questions to avoid timeout)
        overall_feedback = "Đã hoàn thành đánh giá."
        if len(qa_pairs) <= 20:  # Only generate overall feedback if reasonable number of questions
            try:
                print(f"[end_session] Generating overall feedback for {len(qa_pairs)} Q&A pairs")
                overall_feedback_data = generate_overall_feedback(qa_pairs, scores_summary)
                overall_feedback = overall_feedback_data.get("overall_feedback", overall_feedback)
                print(f"[end_session] Overall feedback generated successfully")
            except Exception as feedback_e:
                print(f"Warning: Failed to generate overall feedback: {feedback_e}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                overall_feedback = f"Đã hoàn thành đánh giá. Một số câu hỏi có thể chưa được chấm điểm do lỗi kỹ thuật."
        else:
            print(f"[end_session] Skipping overall feedback generation (too many questions: {len(qa_pairs)})")
            overall_feedback = f"Đã hoàn thành đánh giá {len(qa_pairs)} câu hỏi."
        
        # Update student session (best-effort with multiple attempts)
        update_success = False
        update_attempts = [
            # Try full update first
            {
                "score_total": overall_score,
                "ai_overall_feedback": overall_feedback
            },
            # Try without ai_overall_feedback if it fails
            {
                "score_total": overall_score
            },
            # Try with just a simple message
            {
                "score_total": overall_score,
                "ai_overall_feedback": "Đã hoàn thành đánh giá."
            }
        ]
        
        for attempt_idx, update_data in enumerate(update_attempts):
            try:
                supabase.table("studentsession").update(update_data).eq("student_session_id", student_session_id).execute()
                update_success = True
                print(f"Successfully updated studentsession with attempt {attempt_idx + 1}")
                break
            except Exception as update_e:
                print(f"Warning: Failed to update studentsession (attempt {attempt_idx + 1}): {update_e}")
                if attempt_idx == len(update_attempts) - 1:
                    # Last attempt failed, log full error
                    import traceback
                    print(f"All update attempts failed. Traceback: {traceback.format_exc()}")
                # Continue to next attempt
        
        # Prepare response
        response_data = {
            "student_session_id": student_session_id,
            "score_total": overall_score,
            "ai_overall_feedback": overall_feedback,
            "evaluated_count": len([a for a in evaluated_answers if a.get("ai_score") is not None]),
            "total_answers": len(answers),
            "completed_at": datetime.now().isoformat()
        }
        
        # Add warnings if there were errors (but don't fail the request)
        if evaluation_errors:
            response_data["warnings"] = evaluation_errors[:5]  # Limit to first 5 errors
            print(f"Evaluation completed with {len(evaluation_errors)} errors for session {student_session_id}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"CRITICAL ERROR in end_session for student_session_id={student_session_id}: {e}")
        print(f"Traceback: {error_trace}")
        
        # Try to save partial results and mark as completed
        try:
            if 'evaluated_answers' in locals() and evaluated_answers:
                scores = [a["ai_score"] for a in evaluated_answers if a.get("ai_score") is not None]
                overall_score = sum(scores) / len(scores) if scores else 0.0
                
                # Try to update studentsession with partial results
                try:
                    supabase.table("studentsession").update({
                        "score_total": overall_score,
                        "ai_overall_feedback": f"Đã hoàn thành một phần đánh giá. Có lỗi xảy ra: {str(e)[:200]}"
                    }).eq("student_session_id", student_session_id).execute()
                except:
                    # If that fails, try just score_total
                    try:
                        supabase.table("studentsession").update({
                            "score_total": overall_score
                        }).eq("student_session_id", student_session_id).execute()
                    except:
                        pass
                
                return jsonify({
                    "student_session_id": student_session_id,
                    "score_total": overall_score,
                    "ai_overall_feedback": f"Đã hoàn thành một phần đánh giá. Có lỗi xảy ra: {str(e)[:200]}",
                    "evaluated_count": len([a for a in evaluated_answers if a.get("ai_score") is not None]),
                    "total_answers": len(answers) if 'answers' in locals() else 0,
                    "completed_at": datetime.now().isoformat(),
                    "warning": f"Partial evaluation completed with error: {str(e)[:200]}"
                }), 200
        except Exception as recovery_e:
            print(f"Failed to recover partial results: {recovery_e}")
        
        # If we can't return partial results, still try to mark as completed
        try:
            # Calculate score from evaluated_answers if available
            if 'evaluated_answers' in locals() and evaluated_answers:
                scores = [a["ai_score"] for a in evaluated_answers if a.get("ai_score") is not None]
                calculated_score = sum(scores) / len(scores) if scores else 0.0
                supabase.table("studentsession").update({
                    "score_total": calculated_score
                }).eq("student_session_id", student_session_id).execute()
        except:
            pass
        
        # Return error but with 200 status to allow frontend to proceed
        return jsonify({
            "student_session_id": student_session_id,
            "error": f"Failed to end session: {str(e)[:500]}",
            "score_total": overall_score if 'overall_score' in locals() else None,
            "completed_at": datetime.now().isoformat()
        }), 200  # Return 200 instead of 500 to allow frontend to redirect


@student_sessions_bp.route("/<int:student_session_id>", methods=["GET"])
@require_student
def get_student_session(student_session_id):
    """Get student session results."""
    student_id = request.user_id
    
    try:
        # Verify student session
        student_session_response = supabase.table("studentsession").select("*").eq("student_session_id", student_session_id).single().execute()
        
        if not student_session_response.data:
            return jsonify({"error": "Student session not found"}), 404
        
        student_session = student_session_response.data
        
        if student_session["student_id"] != student_id:
            return jsonify({"error": "Access denied"}), 403
        
        # Get session details
        session_response = supabase.table("session").select("*").eq("session_id", student_session["session_id"]).single().execute()
        session = session_response.data if session_response.data else {}
        
        # Get all answers
        answers_response = supabase.table("studentanswer").select("*").eq("student_session_id", student_session_id).execute()
        answers = answers_response.data or []
        
        # Get questions
        question_ids = [a["question_id"] for a in answers]
        questions_response = supabase.table("question").select("*").in_("question_id", question_ids).execute()
        questions_dict = {q["question_id"]: q for q in (questions_response.data or [])}
        
        # Format answers
        formatted_answers = []
        for answer in answers:
            question = questions_dict.get(answer["question_id"], {})
            formatted_answers.append({
                "answer_id": answer["answer_id"],
                "question_id": answer["question_id"],
                "question": question.get("content", ""),
                "answer": answer.get("answer_text", ""),
                "ai_score": answer.get("ai_score"),
                "ai_feedback": answer.get("ai_feedback"),
                "lecturer_score": answer.get("lecturer_score"),
                "lecturer_feedback": answer.get("lecturer_feedback")
            })
        
        return jsonify({
            "student_session_id": student_session_id,
            "session_id": student_session["session_id"],
            "session_name": session.get("session_name", ""),
            "session_type": session.get("session_type", ""),
            "score_total": student_session.get("score_total"),
            "ai_overall_feedback": student_session.get("ai_overall_feedback"),
            "answers": formatted_answers,
            "join_time": student_session.get("join_time")
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get student session: {str(e)}"}), 500


@student_sessions_bp.route("/history", methods=["GET"])
@require_student
def get_history():
    """Get student's session history."""
    student_id = request.user_id
    
    try:
        # Get all student sessions
        student_sessions_response = supabase.table("studentsession").select("*").eq("student_id", student_id).order("join_time", desc=True).execute()
        
        if not student_sessions_response.data:
            return jsonify([]), 200
        
        # Format response with session details
        history = []
        for ss in student_sessions_response.data:
            # Get session details
            session_response = supabase.table("session").select("*").eq("session_id", ss["session_id"]).single().execute()
            session = session_response.data if session_response.data else {}
            
            history.append({
                "student_session_id": ss["student_session_id"],
                "session_id": ss["session_id"],
                "session_name": session.get("session_name", ""),
                "session_type": session.get("session_type", ""),
                "course_name": session.get("course_name", ""),
                "score_total": ss.get("score_total"),
                "join_time": ss.get("join_time")
            })
        
        return jsonify(history), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get history: {str(e)}"}), 500

