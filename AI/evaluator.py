from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def extract_text(pdf_path):
    text = ""

    try:
        reader = PdfReader(pdf_path)

        for page in reader.pages:
            content = page.extract_text()

            if content:
                text += content

    except Exception as e:
        print("PDF Error:", e)

    return text


def evaluate_assignment(pdf_path, expected_keywords=None):

    if expected_keywords is None:
        expected_keywords = [
            "docker",
            "container",
            "image",
            "linux",
            "deployment"
        ]

    text = extract_text(pdf_path)

    if not text:
        return {
            "marks": 0,
            "feedback": "No readable content found."
        }

    text_lower = text.lower()

    # Keyword Score
    keyword_matches = 0

    for word in expected_keywords:
        if word.lower() in text_lower:
            keyword_matches += 1

    keyword_score = (keyword_matches / len(expected_keywords)) * 10

    # Word Count
    word_count = len(text.split())

    # Final Marks
    final_marks = round(min(keyword_score + (word_count / 100), 10), 2)

    # Feedback
    if final_marks >= 8:
        feedback = "Excellent assignment submission."
    elif final_marks >= 5:
        feedback = "Good work, but improvements are needed."
    else:
        feedback = "Poor assignment quality."

    return {
        "marks": final_marks,
        "feedback": feedback,
        "word_count": word_count,
        "keywords_found": keyword_matches
    }