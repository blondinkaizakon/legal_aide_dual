from docxtpl import DocxTemplate
from core.config import TPL, GEN
from pathlib import Path

def build(data: dict, out_name="contract.docx") -> Path:
    tpl_path = TPL / "lease_ip_to_ip.docx"
    out_path = GEN / out_name
    tpl = DocxTemplate(tpl_path)
    tpl.render(data)
    tpl.save(out_path)
    return out_path
