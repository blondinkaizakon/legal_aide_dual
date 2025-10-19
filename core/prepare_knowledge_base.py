# prepare_knowledge_base.py
import os
import pickle
import json
import re
import pdfplumber
# ... другие импорты ...
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
CODECS_DIR = "data/codecs"
INDEX_FILE = "data/faiss_index.bin"
METADATA_FILE = "data/kb_metadata.pkl"

# --- Функции из предыдущего примера (extract_text_from_file, split_by_articles и т.д.) ---
def extract_text_from_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    text = ""
    if ext == '.pdf':
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    # elif ext == '.docx':
    #     import docx
    #     doc = docx.Document(filepath)
    #     text = "\n".join([p.text for p in doc.paragraphs])
    # elif ext == '.txt':
    #     with open(filepath, 'r', encoding='utf-8') as f:
    #         text = f.read()
    return text

def split_by_articles(text):
    # Пример: разбиение по "Статья N."
    chunks = re.split(r'(Статья\s+\d+\..*?)(?=(Статья\s+\d+\.|$))', text, flags=re.DOTALL)
    articles = []
    for i in range(1, len(chunks), 2):
        if i + 1 < len(chunks):
            article_text = chunks[i] + chunks[i+1]
        else:
            article_text = chunks[i]
        article_text = article_text.strip()
        if article_text:
            articles.append(article_text)
    return articles
# --- Конец функций ---

def main():
    all_texts = []
    all_metadata = []

    model = SentenceTransformer(MODEL_NAME)

    for filename in os.listdir(CODECS_DIR):
        filepath = os.path.join(CODECS_DIR, filename)
        if os.path.isfile(filepath):
            print(f"Обработка {filename}...")
            raw_text = extract_text_from_file(filepath)
            chunks = split_by_articles(raw_text)

            for chunk in chunks:
                all_texts.append(chunk)
                all_metadata.append({
                    "source_file": filename,
                    "original_chunk": chunk,
                    # ... возможно, другие метаданные ...
                })

    print(f"Всего фрагментов: {len(all_texts)}")

    if not all_texts:
        print("Не найдено текста для векторизации.")
        return

    print("Векторизация...")
    embeddings = model.encode(all_texts, show_progress_bar=True)

    print("Создание индекса...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    faiss.normalize_L2(embeddings.astype('float32'))
    index.add(embeddings.astype('float32'))

    print(f"Сохранение индекса в {INDEX_FILE}...")
    faiss.write_index(index, INDEX_FILE)

    print(f"Сохранение метаданных в {METADATA_FILE}...")
    with open(METADATA_FILE, "wb") as f:
        pickle.dump(all_metadata, f)

    print("Подготовка базы знаний завершена!")

if __name__ == "__main__":
    main()
