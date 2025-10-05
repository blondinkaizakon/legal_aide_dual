from docxtpl import DocxTemplate
from core.config import TPL, GEN  # Импортируются правильно
from pathlib import Path

def build(data: dict, out_name: str = "contract.docx") -> Path:
    tpl_path = Path(TPL) / "lease_ip_to_ip.docx"  # Используем Path для корректов пути
    out_path = Path(GEN) / out_name  # Используем Path для корректов пути
    tpl = DocxTemplate(tpl_path)
    tpl.render(data)
    tpl.save(out_path)
    return out_path
