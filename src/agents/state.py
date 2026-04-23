# src/agents/state.py
from typing import TypedDict, List, Annotated
import operator

class AgentState(TypedDict):
    """
    Sistemdeki tüm ajanların okuyup yazabileceği ortak state nesnesi.
    """
    # Mesaj geçmişini tutar (Annotated ve operator.add sayesinde listeye sürekli ekleme yapılır, üzerine yazılmaz)
    messages: Annotated[List[dict], operator.add]
    
    question: str           # Kullanıcının sorduğu orijinal soru
    context: str            # Retriever'ın PDF'ten bulup getirdiği metin
    draft_answer: str       # Ajanın ürettiği taslak cevap
    is_valid: bool          # Validator'ın onayı (True ise işlem biter, False ise döngüye girer)
    revision_count: int     # Sonsuz döngüyü engellemek için deneme sayısı
    next_action: str