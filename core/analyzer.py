import re

def analyze(text: str) -> list[str]:
    risks = []
    if "предмет договора" not in text.lower():
        risks.append("⚠ Не указан предмет договора (ст. 432 ГК РФ)")
    if "срок действия" not in text.lower():
        risks.append("⚠ Отсутствует срок действия договора")
    if re.search(r"ИНН|ОГРН|паспорт", text, re.I) is None:
        risks.append("⚠ Нет реквизитов сторон")
    return risks or ["✅ Критических рисков не обнаружено"]
