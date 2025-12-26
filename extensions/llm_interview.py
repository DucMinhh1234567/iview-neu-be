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
        f"[Đoạn {idx + 1}]: {chunk.get('text', '')}"
        for idx, chunk in enumerate(context_chunks)
    )

    num_q = num_questions or BATCH_SIZE
    course_info = f"\nVị trí/Công việc: {course_name}" if course_name else ""
    requirements_text = (
        f"\n\nAdditional Requirements: {additional_requirements}"
        if additional_requirements
        else ""
    )

    return f"""Bạn là chuyên gia phỏng vấn tuyển dụng, đang soạn các câu hỏi phỏng vấn hành vi và tình huống. Hãy tạo {num_q} câu hỏi chất lượng cao dựa hoàn toàn trên ngữ cảnh được cung cấp.

Ngữ cảnh:
{chunks_text}
{course_info}

Cấp độ nhận thức (Bloom): {difficulty}
Phong cách câu hỏi: Phỏng vấn việc làm

Yêu cầu bắt buộc:
1. Tạo đúng {num_q} câu hỏi
2. Mỗi câu hỏi PHẢI dựa HOÀN TOÀN trên ngữ cảnh được cung cấp, không dùng kiến thức bên ngoài
3. Tập trung vào các tình huống thực tế, lý luận và phản ánh phù hợp với phỏng vấn
4. Mỗi câu hỏi phải khám phá một năng lực hoặc góc độ khác biệt
5. KHÔNG bao gồm đáp án mẫu (sẽ tạo riêng sau)
6. Câu hỏi phải rõ ràng, cụ thể và mở để khuyến khích cuộc trò chuyện
7. Khuyến khích ứng viên giải thích quyết định, kinh nghiệm hoặc lý do

Quy tắc quan trọng:
- KHÔNG tạo các câu hỏi kiểu "Theo tài liệu nhận được", "Dựa trên ví dụ", "Được đề cập trong tài liệu" hoặc tương tự
- Ngôn ngữ thân thiện, tự nhiên, giống như người phỏng vấn đang nói trực tiếp với ứng viên
- Người phỏng vấn KHÔNG được tham chiếu rằng họ đã đọc tài liệu - câu hỏi phải cảm giác tự nhiên
- Câu hỏi phải kiểm tra kiến thức/ứng dụng/phân tích, có thể tạo câu hỏi tính toán dựa trên lý thuyết
- Tránh tạo câu hỏi dựa trên ví dụ cụ thể nếu đoạn văn không đề cập rõ ràng
- Câu hỏi phải hỏi về kiến thức/áp dụng/lý giải, không chỉ nhớ lại thông tin
- Nếu ngữ cảnh không nhắc đến một khái niệm, KHÔNG tạo câu hỏi về khái niệm đó
{requirements_text}

Output format (JSON):
{{
  "questions": [
    {{
      "question": "Question text here",
      "keywords": "keyword1, keyword2, keyword3",
      "question_type": "behavioral|situational|technical|case|coding|competency"
    }}
  ]
}}

Lưu ý: Chỉ trả JSON thuần, không thêm markdown code block (```json ... ```), không sử dụng LaTeX.

Tạo các câu hỏi ngay bây giờ:"""


def prompt_generate_reference_answers(
    questions: List[Dict[str, str]],
    context_chunks: List[Dict[str, str]],
    course_name: Optional[str] = None
) -> str:
    """Generate prompt for interview reference answers."""
    questions_text = "\n\n".join(
        f"Câu {idx + 1}: {question.get('question', '')}\n"
        f"Từ khóa: {question.get('keywords', '')}\n"
        f"Loại câu hỏi: {question.get('question_type', '')}"
        for idx, question in enumerate(questions)
    )

    chunks_text = "\n\n".join(
        f"[Đoạn {idx + 1}]: {chunk.get('text', '')}"
        for idx, chunk in enumerate(context_chunks)
    )

    course_info = f"\nVị trí/Công việc: {course_name}" if course_name else ""

    return f"""Bạn là chuyên gia phỏng vấn thiết kế câu trả lời mẫu cho các câu hỏi phỏng vấn. Hãy tạo đáp án mẫu toàn diện, mang tính đàm thoại sử dụng các câu hỏi và ngữ cảnh được cung cấp.

Danh sách câu hỏi:
{questions_text}

Ngữ cảnh:
{chunks_text}
{course_info}

Yêu cầu:
1. Tạo đáp án mẫu cho TẤT CẢ các câu hỏi
2. Đáp án PHẢI dựa trên ngữ cảnh được cung cấp, không suy diễn ngoài phạm vi
3. Câu trả lời nên mô hình hóa cách kể chuyện phỏng vấn mạnh mẽ (Tình huống-Nhiệm vụ-Hành động-Kết quả)
4. Làm nổi bật lý luận, quyết định và những hiểu biết cá nhân
5. Điều chỉnh giọng điệu và độ sâu phù hợp với loại câu hỏi
6. Lồng ghép tự nhiên các từ khóa đã cung cấp
7. Đáp án phải đầy đủ, chi tiết nhưng không quá dài dòng (khoảng 100-200 từ mỗi câu hỏi)

Output format (JSON):
{{
  "answers": [
    {{
      "question_index": 0,
      "reference_answer": "Comprehensive reference answer here..."
    }}
  ]
}}

Lưu ý: Chỉ trả JSON thuần, không thêm markdown code block. Đảm bảo số lượng answers bằng số lượng questions.

Tạo đáp án mẫu ngay bây giờ:"""


def prompt_evaluate_answer(
    question: str,
    student_answer: str,
    reference_answer: str,
    difficulty: str = "MEDIUM"
) -> str:
    """Generate prompt for evaluating interview answers."""
    return f"""Bạn là chuyên gia phỏng vấn đang đánh giá phản hồi của ứng viên. Hãy đánh giá câu trả lời theo các tiêu chí dưới đây, được điều chỉnh cho hiệu suất phỏng vấn.

Câu hỏi: {question}

Câu trả lời của ứng viên: {student_answer}

Đáp án mẫu: {reference_answer}

Cấp độ khó: {difficulty}

Tiêu chí đánh giá (0-10 mỗi tiêu chí):
1. Correctness (Tính chính xác): Câu trả lời có giải quyết chính xác câu hỏi và giữ đúng chủ đề không?
2. Coverage (Độ bao phủ): Có cung cấp đủ độ sâu, ví dụ hoặc ngữ cảnh từ kinh nghiệm không?
3. Reasoning (Lý luận): Quyết định và quá trình suy nghĩ có được giải thích rõ ràng không?
4. Creativity (Sáng tạo): Ứng viên có đưa ra những hiểu biết độc đáo hoặc quan điểm tinh tế không?
5. Communication (Giao tiếp): Cách trình bày có cấu trúc, tự tin và dễ theo dõi không?
6. Attitude (Thái độ): Giọng điệu có chuyên nghiệp, hợp tác và hướng tới phát triển không?

Yêu cầu:
1. Không cần chào hỏi hay tương tác, hãy trả lời như một báo cáo, đi thẳng vào nhận xét
2. Cho điểm từng tiêu chí theo thang 0-10 (có thể dùng số thập phân như 7.5, 8.5)
3. Viết nhận xét chi tiết nêu rõ điểm mạnh và lĩnh vực cần phát triển trong phỏng vấn
4. Đề cập đến các ví dụ hoặc lý luận đáng chú ý từ câu trả lời
5. Giữ tinh thần xây dựng và khuyến khích
6. Điều chỉnh phản hồi phù hợp với cấp độ khó đã nêu
7. Điểm tổng thể (overall_score) nên là trung bình có trọng số của các tiêu chí
8. Phản hồi phải cụ thể, có thể hành động được (250-500 từ)

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

Lưu ý: Chỉ trả JSON thuần, không thêm markdown code block (```json ... ```), không sử dụng LaTeX. Đảm bảo tất cả điểm số là số thực từ 0.0 đến 10.0.

Evaluate the answer now:"""


def prompt_generate_overall_feedback(
    qa_pairs: List[Dict[str, Any]],
    scores_summary: Dict[str, float]
) -> str:
    """Generate prompt for overall interview feedback."""
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

    return f"""Bạn đang tổng kết hiệu suất phỏng vấn tuyển dụng. Hãy cung cấp phản hồi tổng thể giúp ứng viên phát triển.

Các cặp Câu hỏi-Trả lời:
{qa_text}

Tổng hợp điểm số:
{scores_text}

Yêu cầu:
1. Không cần chào hỏi hay tương tác, hãy trả lời như một báo cáo, đi thẳng vào nhận xét
2. Đưa ra đánh giá tổng thể về hiệu suất phỏng vấn của ứng viên
3. Làm nổi bật điểm mạnh về hành vi và phẩm chất giao tiếp
4. Xác định các lĩnh vực cải thiện chính với ngữ cảnh
5. Đưa ra các khuyến nghị thực tế cho các cuộc phỏng vấn trong tương lai
6. Duy trì giọng điệu xây dựng, chuyên nghiệp
7. Xem xét hiệu suất trên tất cả các câu trả lời, không chỉ những khoảnh khắc riêng lẻ
8. Phản hồi phải cụ thể, có thể hành động được (150-300 từ)

Output format (JSON):
{{
  "overall_feedback": "Comprehensive overall feedback here...",
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "recommendations": ["recommendation 1", "recommendation 2"]
}}

Lưu ý: Chỉ trả JSON thuần, không thêm markdown code block (```json ... ```), không sử dụng LaTeX. Recommendations phải cụ thể và có thể thực hiện được.

Generate the overall feedback now:"""

