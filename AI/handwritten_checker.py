import os
from PIL import Image
import fitz
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel("gemini-2.5-flash")


def check_handwritten(file_path):

    try:

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":

            pdf = fitz.open(file_path)

            page = pdf[0]

            pix = page.get_pixmap()

            temp_image = "temp_handwriting_check.png"

            pix.save(temp_image)

            image = Image.open(temp_image)

        else:

            image = Image.open(file_path)

        prompt = """
Check whether this submission is handwritten.

Rules:
- Handwritten notebook pages = YES
- Pen/pencil writing = YES
- Printed document = NO
- MS Word document = NO
- Typed text = NO

Return only:
YES
or
NO
"""

        response = model.generate_content(
            [prompt, image]
        )

        result = response.text.strip().upper()

        if ext == ".pdf":
            os.remove(temp_image)

        return result == "YES"

    except Exception as e:

        print("Handwriting Error:", e)

        return False