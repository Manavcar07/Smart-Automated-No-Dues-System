import fitz
import pytesseract
from PIL import Image
import os

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def extract_text(file_path):

    text = ""

    ext = os.path.splitext(file_path)[1].lower()

    # PDF
    if ext == ".pdf":

        pdf = fitz.open(file_path)

        for page in pdf:

            page_text = page.get_text()

            # text pdf
            if page_text.strip():
                text += page_text

            # scanned pdf
            else:

                pix = page.get_pixmap()

                temp_img = "temp_page.png"

                pix.save(temp_img)

                text += pytesseract.image_to_string(
                    Image.open(temp_img)
                )

                os.remove(temp_img)

        pdf.close()

    # image
    elif ext in [".png", ".jpg", ".jpeg"]:

        text = pytesseract.image_to_string(
            Image.open(file_path)
        )

    return text