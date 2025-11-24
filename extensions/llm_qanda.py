"""
Prompt templates for vấn đáp / kiểm tra học thuật.
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
    """Generate prompt for vấn đáp question generation."""
    chunks_text = "\n\n".join(
        f"[Đoạn {idx + 1}]: {chunk.get('text', '')}"
        for idx, chunk in enumerate(context_chunks)
    )

    num_q = num_questions or BATCH_SIZE
    course_info = f"\nMôn học/Khoá học: {course_name}" if course_name else ""
    requirements_text = (
        f"\n\nYêu cầu bổ sung: {additional_requirements}"
        if additional_requirements
        else ""
    )

    return f"""Bạn là giảng viên đang chuẩn bị câu hỏi vấn đáp chuyên sâu. Hãy tạo {num_q} câu hỏi chất lượng dựa hoàn toàn trên nội dung cung cấp.

Ngữ cảnh:
{chunks_text}
{course_info}

Cấp độ nhận thức: {difficulty} (theo Bloom)
Dạng câu hỏi: Tự luận / vấn đáp (không trắc nghiệm)

Yêu cầu:
1. Xuất đúng {num_q} câu hỏi
2. Mỗi câu hỏi chỉ sử dụng kiến thức trong ngữ cảnh
3. Câu hỏi phải đánh giá được mức độ {difficulty}
4. Bao quát nhiều khía cạnh kiến thức, tránh lặp ý
5. Không kèm đáp án mẫu (sẽ tạo sau)
6. Không tạo đáp án trắc nghiệm
7. Diễn đạt rõ ràng, dễ hiểu, phù hợp vấn đáp học thuật
8. Khuyến khích người học phân tích, vận dụng và lý giải
9. QUAN TRỌNG - Trích dẫn nguyên văn khi cần:
   - Chỉ trích dẫn khi câu hỏi thực sự đòi hỏi dẫn chứng cụ thể (định nghĩa, khái niệm, phát biểu, dữ kiện). Nếu câu hỏi thiên về phân tích, vận dụng, đánh giá thì không cần trích dẫn.
   - Khi cần trích dẫn, phải chèn NGUYÊN VĂN nội dung vào trong câu hỏi (đặt trong dấu ngoặc kép hoặc khối trích) và ghi rõ nguồn đoạn. Ví dụ:
     "Tài liệu nêu: 'Đỉnh rẽ nhánh (branching vertex) là đỉnh có bậc lớn hơn 2 trong đồ thị' (Đoạn 7). Dựa trên định nghĩa này, hãy..."
   - Tránh các câu chung chung kiểu "Dựa vào tài liệu..." mà không có nội dung dẫn chứng.
   - Chỉ trích phần cần thiết; giữ trích dẫn ngắn gọn nhưng đủ thông tin.
{requirements_text}

Định dạng xuất (JSON):
{{
  "questions": [
    {{
      "question": "Nội dung câu hỏi...",
      "keywords": "từ khóa 1, từ khóa 2, ...",
      "difficulty": "EASY|MEDIUM|HARD"
    }}
  ]
}}

Bắt đầu tạo câu hỏi:"""


def prompt_generate_reference_answers(
    questions: List[Dict[str, str]],
    context_chunks: List[Dict[str, str]],
    course_name: Optional[str] = None
) -> str:
    """Generate prompt for vấn đáp reference answers."""
    questions_text = "\n\n".join(
        f"Câu {idx + 1}: {question.get('question', '')}\n"
        f"Từ khóa: {question.get('keywords', '')}\n"
        f"Độ khó: {question.get('difficulty', 'MEDIUM')}"
        for idx, question in enumerate(questions)
    )

    chunks_text = "\n\n".join(
        f"[Đoạn {idx + 1}]: {chunk.get('text', '')}"
        for idx, chunk in enumerate(context_chunks)
    )

    course_info = f"\nMôn học/Khoá học: {course_name}" if course_name else ""

    return f"""Bạn là giảng viên muốn chuẩn hóa đáp án mẫu dùng để đối chiếu khi chấm vấn đáp. Hãy tạo đáp án cô đọng, đúng trọng tâm cho từng câu hỏi dựa trên ngữ cảnh.

Câu hỏi:
{questions_text}

Ngữ cảnh:
{chunks_text}
{course_info}

Yêu cầu:
1. Tạo đáp án mẫu cho TẤT CẢ câu hỏi
2. Bám sát kiến thức trong ngữ cảnh, tránh suy diễn ngoài phạm vi
3. Trả lời đúng trọng tâm, độ dài gợi ý 4-7 câu cho EASY/MEDIUM và tối đa 10 câu cho HARD
4. Ưu tiên trình bày rõ ràng theo cấu trúc: Ý chính → Giải thích/luận cứ → Kết luận/khuyến nghị (nếu cần)
5. Nhấn mạnh luận điểm quan trọng bằng câu ngắn, tránh râu ria, hạn chế liệt kê lan man
6. Có thể dùng gạch đầu dòng khi liệt kê để dễ đọc, nhưng giữ tổng thể gọn gàng
7. Lồng ghép tự nhiên các từ khóa đã cung cấp

Định dạng xuất (JSON):
{{
  "answers": [
    {{
      "question_index": 0,
      "reference_answer": "Đáp án mẫu gọn gàng, đúng trọng tâm..."
    }}
  ]
}}

Hãy tạo đáp án ngay bây giờ:"""


def prompt_evaluate_answer(
    question: str,
    student_answer: str,
    reference_answer: str,
    difficulty: str = "MEDIUM"
) -> str:
    """Generate prompt for vấn đáp answer evaluation."""
    return f"""Bạn là giảng viên chấm vấn đáp. Hãy đánh giá câu trả lời của sinh viên theo các tiêu chí học thuật dưới đây.

Câu hỏi: {question}

Bài trả lời của sinh viên: {student_answer}

Đáp án mẫu: {reference_answer}

Cấp độ khó: {difficulty}

Tiêu chí chấm (0-10):
1. Correctness: mức độ chính xác so với kiến thức chuẩn
2. Coverage: độ đầy đủ, có nêu rõ ý chính và các luận điểm quan trọng
3. Reasoning: khả năng phân tích, lập luận, dẫn chứng
4. Creativity: mức độ vận dụng, liên hệ, mở rộng kiến thức
5. Communication: sự rõ ràng, mạch lạc, dùng thuật ngữ chuẩn xác
6. Attitude: thái độ, phong thái, sự tự tin khi trình bày

Yêu cầu:
1. Cho điểm từng tiêu chí theo thang 0-10
2. Viết nhận xét chi tiết nêu rõ điểm mạnh, điểm hạn chế
3. Gợi ý cải thiện cụ thể cho sinh viên
4. Thể hiện tinh thần khích lệ, xây dựng
5. Đánh giá phù hợp với cấp độ khó

Định dạng xuất (JSON):
{{
  "scores": {{
    "correctness": 8.0,
    "coverage": 7.5,
    "reasoning": 7.0,
    "creativity": 7.5,
    "communication": 8.0,
    "attitude": 8.5
  }},
  "overall_score": 7.8,
  "feedback": "Nhận xét chi tiết...",
  "strengths": ["điểm mạnh 1", "điểm mạnh 2"],
  "weaknesses": ["điểm cần cải thiện 1", "điểm cần cải thiện 2"]
}}

Hãy tiến hành chấm điểm:"""


def prompt_generate_overall_feedback(
    qa_pairs: List[Dict[str, Any]],
    scores_summary: Dict[str, float]
) -> str:
    """Generate prompt for overall oral exam feedback."""
    qa_text = "\n\n".join(
        f"Câu {idx + 1}: {pair.get('question', '')}\n"
        f"Trả lời: {pair.get('answer', '')}\n"
        f"Điểm: {pair.get('score', 0)}/10\n"
        f"Nhận xét: {pair.get('feedback', '')}"
        for idx, pair in enumerate(qa_pairs)
    )

    scores_text = "\n".join(
        f"{criterion}: {score}/10"
        for criterion, score in scores_summary.items()
    )

    return f"""Bạn đang tổng kết buổi vấn đáp/kiểm tra miệng. Hãy đưa ra đánh giá chung giúp sinh viên hiểu rõ năng lực hiện tại.

Danh sách câu hỏi và phản hồi:
{qa_text}

Tổng hợp điểm trung bình theo tiêu chí:
{scores_text}

Yêu cầu:
1. Đưa ra nhận xét tổng quan về kết quả vấn đáp
2. Tóm tắt những ưu điểm nổi bật
3. Chỉ ra hạn chế chính và lý do
4. Đề xuất định hướng/hoạt động cải thiện cụ thể
5. Giữ giọng văn tích cực, hỗ trợ người học
6. Dựa trên toàn bộ câu trả lời, tránh chỉ xét từng phần riêng lẻ

Định dạng xuất (JSON):
{{
  "overall_feedback": "Nhận xét tổng quan...",
  "strengths": ["ưu điểm 1", "ưu điểm 2"],
  "weaknesses": ["hạn chế 1", "hạn chế 2"],
  "recommendations": ["gợi ý 1", "gợi ý 2"]
}}

Hãy tạo đánh giá tổng quan:"""

