import os
import json
import re
from pydantic import BaseModel, Field
from openai import OpenAI
from src.document_processor import DocumentProcessor
from .state import AgentState

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
AI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- Pydantic Şemaları ---
class SubSection(BaseModel):
    title: str = Field(description="Alt başlığın adı")
    summary: str = Field(description="Bu bölümün 1-2 cümlelik kısa özeti")

class MainSection(BaseModel):
    title: str = Field(description="Ana başlığın adı")
    subsections: list[SubSection] = Field(default_factory=list, description="Varsa alt başlıklar")

class DocumentOutline(BaseModel):
    document_title: str = Field(description="Belgenin genel adı veya konusu")
    sections: list[MainSection] = Field(description="Belgenin ana bölümleri")

# --- Temizleme ve Formatlama Yardımcıları ---
def _clean_title(title: str) -> str:
    return re.sub(r'^(\d+(\.\d+)?\s+)\1', r'\1', title).strip()

def _format_as_markdown_tree(outline: DocumentOutline, output_path: str) -> str:
    md = f"✅ **JSON dosyası başarıyla oluşturuldu:** `{output_path}`\n\n"
    md += f"## 📑 {_clean_title(outline.document_title)}\n\n"
    
    for section in outline.sections:
        clean_section_title = _clean_title(section.title)
        md += f"### {clean_section_title}\n"
        
        if not section.subsections:
            md += "*(Alt başlık bulunmuyor)*\n"
        
        for sub in section.subsections:
            clean_sub_title = _clean_title(sub.title)
            md += f"- **{clean_sub_title}**: *{sub.summary}*\n"
        md += "\n"
    
    return md

# --- Outline Agent Fonksiyonu ---
def outline_agent(state: AgentState) -> dict:
    """PDF'ten hiyerarşik JSON taslağı çıkarır ve PDF ismiyle data/ klasörüne kaydeder."""
    data_dir = "data"
    pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        msg = "⚠️ Hata: Taslak çıkarılacak PDF dosyası bulunamadı."
        return {"draft_answer": msg, "messages": [{"role": "assistant", "content": msg}]}
        
    original_pdf_name = pdf_files[0]
    pdf_path = os.path.join(data_dir, original_pdf_name)
    
    base_filename = os.path.splitext(original_pdf_name)[0]
    output_filename = f"{base_filename}.json"
    output_path = os.path.join(data_dir, output_filename)
    
    try:
        processor = DocumentProcessor()
        pages = processor.process_pdf(pdf_path)
        full_text = "\n".join([page["page_content"] for page in pages])
        text_sample = full_text[:15000] 
        
        completion = client.beta.chat.completions.parse(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "Sen uzman bir belge analistisin. Başlıklarda yer alan '3. 3.' gibi gereksiz numara tekrarlarını temizleyerek hiyerarşik bir taslak oluştur."},
                {"role": "user", "content": f"Aşağıdaki metnin hiyerarşik taslağını çıkar:\n\n{text_sample}"}
            ],
            response_format=DocumentOutline,
        )
        
        outline_data = completion.choices[0].message.parsed
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(outline_data.model_dump(), f, ensure_ascii=False, indent=4)
            
        rich_answer = _format_as_markdown_tree(outline_data, output_path)
        
        return {"draft_answer": rich_answer, "messages": [{"role": "assistant", "content": rich_answer}]}
        
    except Exception as e:
        error_msg = f"❌ Taslak çıkarılırken hata oluştu: {str(e)}"
        return {"draft_answer": error_msg, "messages": [{"role": "assistant", "content": error_msg}]}