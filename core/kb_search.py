import json, torch
from sentence_transformers import SentenceTransformer, util
from core.config import DATA

faq   = json.loads((DATA / "faq_ip.json").read_text(encoding="utf-8"))
questions = [q["question"] for q in faq]
answers   = [q["answer"] for q in faq]
model = SentenceTransformer("cointegrated/rubert-tiny2")
emb   = model.encode(questions, convert_to_tensor=True)

def find_answer(query: str, threshold=.3) -> str:
    scores = util.cos_sim(model.encode(query, convert_to_tensor=True), emb)[0]
    best = scores.argmax().item()
    return answers[best] if scores[best] > threshold else "Ничего не найдено, уточните вопрос."
