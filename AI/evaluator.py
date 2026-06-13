import os
import re

from AI.ocr_reader import extract_text
from AI.handwritten_checker import check_handwritten
from AI.prompts import PROMPT_TEMPLATE

from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

genai.configure(
        api_key=os.getenv("GEMINI_API_KEY")
    )

model = genai.GenerativeModel(
        "gemini-2.5-flash"
    )

def evaluate_assignment(question_pdf, student_pdf):

    try:

        question_text = extract_text(question_pdf)

        answer_text = extract_text(student_pdf)

        print("\n====================")
        print("QUESTION TEXT")
        print("====================")
        print(question_text)

        print("\n====================")
        print("ANSWER TEXT")
        print("====================")
        print(answer_text)

        handwritten = check_handwritten(student_pdf)

        if not handwritten:

            return {
                "ai_status": "rejected",
                "ai_score": 0,
                "ai_reason": "Not handwritten",
                "is_handwritten": 0
            }

        prompt = PROMPT_TEMPLATE.format(
            question=question_text,
            answer=answer_text
        )

        response = model.generate_content(prompt)

        result = response.text

        print("\n====================")
        print("GEMINI RESPONSE")
        print("====================")
        print(result)

        status_match = re.search(
            r"STATUS:\s*(approved|rejected)",
            result,
            re.IGNORECASE
        )

        score_match = re.search(
            r"SCORE:\s*(\d+)",
            result,
            re.IGNORECASE
        )

        reason_match = re.search(
            r"REASON:\s*(.*)",
            result,
            re.IGNORECASE
        )

        ai_status = (
            status_match.group(1).lower()
            if status_match
            else "rejected"
        )

        ai_score = (
            int(score_match.group(1))
            if score_match
            else 0
        )

        ai_reason = (
            reason_match.group(1)
            if reason_match
            else "No reason"
        )

        ai_reason = ai_reason[:80]

        return {
            "ai_status": ai_status,
            "ai_score": ai_score,
            "ai_reason": ai_reason,
            "is_handwritten": 1
        }

    except Exception as e:

        print("AI ERROR:", e)

        return {
            "ai_status": "pending",
            "ai_score": 0,
            "ai_reason": str(e),
            "is_handwritten": 1
        }