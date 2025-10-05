import fitz

def extract_text(pdf_path: str) -> str:
    with fitz.open(pdf_path) as doc:
        return "\n".join(page.get_text() for page in doc)
TPL = "templates"  # путь к папки с шаблонами документов
GEN = "generated"  # путь для сгенерированных документов
TOKEN = "8440749347:AAFeXggvdBjedsTHI9cOHrHvG6vUrBnka4Y"
