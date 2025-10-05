
# core/doc_generator.py
from core.config import TPL, GEN
from docxtpl import DocxTemplate
from pathlib import Path

def build(data: dict, out_name: str = "contract.docx") -> Path:
    tpl_path = Path(TPL) / "lease_ip_to_ip.docx"
    out_path = Path(GEN) / out_name
    tpl = DocxTemplate(tpl_path)
    tpl.render(data)
    tpl.save(out_path)
    return out_path
