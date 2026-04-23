import os
from openai import OpenAI
from pydantic import BaseModel, Field
from .state import AgentState
from ..vector_store import VectorStoreManager

# OpenAI Client'ı başlatıyoruz
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
AI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- PYDANTIC MODELLERİ (LLM'i belirli bir JSON formatında cevap vermeye zorluyoruz) ---

class SupervisorDecision(BaseModel):
    next_action: str = Field(
        description="Eğer soru bir belge, PDF veya spesifik bir bilgi gerektiriyorsa 'search', sadece genel sohbet veya selamlama ise 'direct_answer' dön."
    )

class ValidationResult(BaseModel):
    is_valid: bool = Field(description="Üretilen cevap bağlama uyuyorsa ve halüsinasyon içermiyorsa true, aksi halde false.")
    reason: str = Field(description="Kararının kısa bir açıklaması.")

# --- AJAN FONKSİYONLARI ---

def supervisor_agent(state: AgentState) -> dict:
    """Kullanıcı niyetini anlar ve süreci yönlendirir."""
    question = state.get("question")
    prompt = f"""
    Soru/Komut: {question}
    
    Bu komut ne istiyor?
    1. Eğer belgenin "taslağını", "yapısını", "hiyerarşisini", "json formatını", "özet ağacını" veya "outline"ını istiyorsa sadece 'outline' dön.
    2. Eğer bir soru soruyor ve cevabın belgede olduğunu düşünüyorsan 'search' dön.
    3. Eğer merhaba, nasılsın gibi doğrudan sohbet ise 'direct_answer' dön.
    
    Sadece 'search', 'direct_answer' veya 'outline' kelimelerinden birini dön.
    """
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    decision = response.choices[0].message.content.strip().lower()
    
    # Hata durumunda varsayılan olarak search'e git
    if decision not in ["search", "direct_answer", "outline"]:
        decision = "search"
        
    return {"next_action": decision}


def retriever_agent(state: AgentState) -> dict:
    """
    Vektör veritabanında arama yapar ve bulunan bağlamı State'e yazar.
    """
    print("🔍 [Retriever]: Vektör veritabanında semantik arama yapılıyor...")
    question = state.get("question")
    
    # YENİ: Veritabanı bağlantısını her çağrıldığında taze olarak oluşturuyoruz
    vector_store = VectorStoreManager()
    
    # VectorStoreManager üzerinden arama yapıyoruz
    context = vector_store.search(query=question)
    
    if not context or context == "Bağlam bulunamadı.":
        print("   ↳ Uyarı: İlgili bağlam bulunamadı.")
    else:
        print("   ↳ Başarılı: İlgili parçalar bulundu.")
        
    return {"context": context}


def generator_agent(state: AgentState) -> dict:
    """
    Retriever'dan gelen bağlamı ve sohbet geçmişini kullanarak cevap üretir.
    """
    print("✍️ [Generator]: Bağlam ve sohbet geçmişi sentezleniyor...")
    context = state.get("context", "")
    question = state.get("question")
    next_action = state.get("next_action")
    
    # YENİ: Hafızadaki mesajları alıyoruz
    messages = state.get("messages", [])
    
    # LLM'e göndereceğimiz mesaj listesini hazırlıyoruz
    llm_messages = [
        {"role": "system", "content": "Sen yardımcı bir asistansın. Eğer bağlam (PDF) verildiyse ona sadık kal. Eğer kullanıcı geçmişle ilgili bir soru sorarsa aşağıdaki sohbet geçmişini kullanarak cevap ver."}
    ]
    
    # Geçmişteki mesajları listeye ekliyoruz (Son soru hariç)
    if len(messages) > 1:
        for msg in messages[:-1]:
            content = msg.content if hasattr(msg, 'content') else msg.get('content')
            role = "user" if (hasattr(msg, 'type') and msg.type == 'human') or msg.get('role') == 'user' else "assistant"
            llm_messages.append({"role": role, "content": content})

    # En son bağlamı ve asıl soruyu formatlayıp ekliyoruz
    if next_action == "search" and context:
        prompt = f"Bağlam (PDF Content):\n{context}\n\nSoru: {question}"
    else:
        prompt = question

    llm_messages.append({"role": "user", "content": prompt})

    # LLM Çağrısı
    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=llm_messages,
        temperature=0.3
    )
    
    draft = response.choices[0].message.content
    
    # YENİ: Üretilen cevabı hem taslak olarak dönüyoruz hem de hafızaya (messages) 'assistant' rolüyle ekliyoruz
    return {
        "draft_answer": draft,
        "messages": [{"role": "assistant", "content": draft}]
    }


def validator_agent(state: AgentState) -> dict:
    """
    Üretilen cevabı orijinal bağlamla karşılaştırır. Halüsinasyon kontrolü yapar.
    """
    print("⚖️ [Validator]: Üretilen taslak cevap doğrulanıyor (Halüsinasyon Testi)...")
    draft = state.get("draft_answer")
    context = state.get("context")
    question = state.get("question")
    revision_count = state.get("revision_count", 0)
    
    # Eğer doğrudan sohbetse (search yapılmadıysa) doğrulamaya gerek yok, geç.
    if state.get("next_action") != "search":
        print("   ↳ Not: Sohbet akışı, doğrulama atlandı.")
        return {"is_valid": True, "revision_count": revision_count + 1}

    completion = client.beta.chat.completions.parse(
        model=AI_MODEL,
        messages=[
            {"role": "system", "content": "Sen katı bir doğrulayıcısın. Üretilen cevabın verilen bağlama sadık kalıp kalmadığını kontrol et."},
            {"role": "user", "content": f"Bağlam: {context}\n\nSoru: {question}\n\nÜretilen Cevap: {draft}"}
        ],
        response_format=ValidationResult,
    )
    
    result = completion.choices[0].message.parsed
    print(f"   ↳ Sonuç: {'Geçerli' if result.is_valid else 'Geçersiz'} (Sebep: {result.reason})")
    
    return {
        "is_valid": result.is_valid,
        "revision_count": revision_count + 1
    }