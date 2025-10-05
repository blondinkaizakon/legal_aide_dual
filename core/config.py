# core/config.py
import os

# Путь к папке с шаблонами DOCX
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TPL = os.path.join(BASE_DIR, "templates")      # папка с шаблонами
GEN = os.path.join(BASE_DIR, "generated")      # папка для сгенерированных документов
