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

Cấp độ nhận thức (Bloom): {difficulty}
Dạng câu hỏi: Tự luận / vấn đáp

Yêu cầu bắt buộc:
1. Tạo đúng {num_q} câu hỏi
2. Mỗi câu hỏi CHỈ sử dụng kiến thức trong ngữ cảnh, không dùng kiến thức bên ngoài
3. Câu hỏi phải đánh giá được mức độ {difficulty} theo Bloom Taxonomy
4. Bao quát nhiều khía cạnh kiến thức, tránh lặp ý
5. KHÔNG kèm đáp án mẫu (sẽ tạo riêng sau)
6. Diễn đạt rõ ràng, dễ hiểu, phù hợp với vấn đáp học thuật
7. Khuyến khích người học phân tích, vận dụng và lý giải

Quy tắc quan trọng:
- KHÔNG tạo các câu hỏi kiểu "Theo tài liệu nhận được", "Dựa trên ví dụ", "Được đề cập trong tài liệu", "Theo nội dung đã đọc" hoặc tương tự
- Ngôn ngữ thân thiện, tự nhiên, giống như giảng viên đang nói trực tiếp với sinh viên trong buổi vấn đáp
- Giảng viên KHÔNG được tham chiếu rằng họ đã đọc tài liệu - câu hỏi phải cảm giác tự nhiên như đang kiểm tra kiến thức
- Câu hỏi phải hỏi về kiến thức/áp dụng/lý giải, có thể tạo các câu hỏi tính toán dựa trên lý thuyết nhận được
- Tránh tạo câu hỏi dựa trên ví dụ cụ thể nếu đoạn văn không đề cập rõ ràng đến ví dụ đó
- Câu hỏi phải kiểm tra khả năng hiểu, vận dụng và phân tích, không chỉ nhớ lại thông tin
- Nếu ngữ cảnh không nhắc đến một khái niệm, KHÔNG tạo câu hỏi về khái niệm đó
{requirements_text}

Định dạng xuất (JSON):
{{
  "questions": [
    {{
      "question": "Nội dung câu hỏi...",
      "keywords": "từ khóa 1, từ khóa 2, ...",
      "question_type": "REMEMBER|UNDERSTAND|APPLY|ANALYZE|EVALUATE|CREATE"
    }}
  ]
}}

Lưu ý: Chỉ trả JSON thuần, không thêm markdown code block (```json ... ```), không sử dụng LaTeX.

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
        f"Bloom level: {question.get('question_type', '')}"
        for idx, question in enumerate(questions)
    )

    chunks_text = "\n\n".join(
        f"[Đoạn {idx + 1}]: {chunk.get('text', '')}"
        for idx, chunk in enumerate(context_chunks)
    )

    course_info = f"\nMôn học/Khoá học: {course_name}" if course_name else ""

    return f"""Bạn là giảng viên muốn chuẩn hóa đáp án mẫu dùng để đối chiếu khi chấm vấn đáp. Hãy tạo đáp án đầy đủ cho từng câu hỏi dựa trên ngữ cảnh.

Danh sách câu hỏi:
{questions_text}

Ngữ cảnh:
{chunks_text}
{course_info}

Yêu cầu:
1. Tạo đáp án mẫu cho TẤT CẢ câu hỏi
2. Bám sát kiến thức trong ngữ cảnh, tránh suy diễn ngoài phạm vi
3. Diễn đạt mạch lạc, đi từ ý chính tới chi tiết quan trọng
4. Làm rõ lập luận, khái niệm và điểm cần nhấn mạnh
5. Liên hệ độ khó tương ứng với Bloom Taxonomy
6. Lồng ghép tự nhiên các từ khóa đã cung cấp
7. Đáp án phải đầy đủ, chi tiết nhưng không quá dài dòng (khoảng 100-200 từ mỗi câu)
8. Cấu trúc rõ ràng: ý chính → giải thích → ví dụ (nếu cần)

Định dạng xuất (JSON):
{{
  "answers": [
    {{
      "question_index": 0,
      "reference_answer": "Đáp án mẫu chi tiết..."
    }}
  ]
}}

Lưu ý: Chỉ trả JSON thuần, không thêm markdown code block. Đảm bảo số lượng answers bằng số lượng questions.

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

Tiêu chí chấm (0-10 mỗi tiêu chí):
1. Correctness (Tính chính xác): Mức độ chính xác so với kiến thức chuẩn, có đúng với nội dung trong đáp án mẫu không?
2. Coverage (Độ bao phủ): Độ đầy đủ, có nêu rõ ý chính và các luận điểm quan trọng không?
3. Reasoning (Lý luận): Khả năng phân tích, lập luận, dẫn chứng có rõ ràng và logic không?
4. Creativity (Sáng tạo): Mức độ vận dụng, liên hệ, mở rộng kiến thức có tốt không?
5. Communication (Giao tiếp): Sự rõ ràng, mạch lạc, dùng thuật ngữ chuẩn xác có đúng không?
6. Attitude (Thái độ): Thái độ, phong thái, sự tự tin khi trình bày có tốt không?

Yêu cầu:
1. Cho điểm từng tiêu chí theo thang 0-10 (có thể dùng số thập phân)
2. Viết nhận xét chi tiết nêu rõ điểm mạnh, điểm hạn chế
3. Gợi ý cải thiện cụ thể cho sinh viên
4. Thể hiện tinh thần khích lệ, xây dựng
5. Đánh giá phù hợp với cấp độ khó
6. Điểm tổng thể (overall_score) nên là trung bình có trọng số của các tiêu chí

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

Lưu ý: Chỉ trả JSON thuần, không thêm markdown code block. Đảm bảo tất cả điểm số là số thực từ 0.0 đến 10.0. Strengths và weaknesses nên có 2-4 mục.

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

    return f"""Bạn đang tổng kết buổi vấn đáp/kiểm tra miệng. Hãy đưa ra đánh giá chung giúp sinh viên hiểu rõ năng lực hiện tại và cách cải thiện.

Danh sách câu hỏi và phản hồi:
{qa_text}

Tổng hợp điểm trung bình theo tiêu chí:
{scores_text}

Yêu cầu:
1. Đưa ra nhận xét tổng quan về kết quả vấn đáp
2. Tóm tắt những ưu điểm nổi bật của sinh viên
3. Chỉ ra hạn chế chính và lý do
4. Đề xuất định hướng/hoạt động cải thiện cụ thể
5. Giữ giọng văn tích cực, hỗ trợ người học
6. Dựa trên toàn bộ câu trả lời, tránh chỉ xét từng phần riêng lẻ
7. Phản hồi phải cụ thể, có thể hành động được (150-300 từ)

Định dạng xuất (JSON):
{{
  "overall_feedback": "Nhận xét tổng quan...",
  "strengths": ["ưu điểm 1", "ưu điểm 2"],
  "weaknesses": ["hạn chế 1", "hạn chế 2"],
  "recommendations": ["gợi ý 1", "gợi ý 2"]
}}

Lưu ý: Chỉ trả JSON thuần, không thêm markdown code block. Strengths và weaknesses nên có 2-4 mục mỗi loại. Recommendations phải cụ thể và có thể thực hiện được.

Hãy tạo đánh giá tổng quan:"""

