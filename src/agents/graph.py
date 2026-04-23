import os
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict
from .state import AgentState
from .nodes import supervisor_agent, retriever_agent, generator_agent, validator_agent
from .outline import outline_agent

class WorkflowManager:
    """
    Ajanların birbirleriyle nasıl etkileşime gireceğini (Execution Graph) tanımlayan sınıf.
    """
    def __init__(self):
        # 1. State nesnesini vererek grafı başlatıyoruz
        self.workflow = StateGraph(AgentState)
        self.memory = MemorySaver()  # Hafıza modülü
        self._build_graph()

    def _build_graph(self):
        # 2. Düğümleri (Nodes) ekliyoruz. Her bir düğüm bizim bir ajanımız.
        self.workflow.add_node("supervisor", supervisor_agent)
        self.workflow.add_node("retriever", retriever_agent)
        self.workflow.add_node("generator", generator_agent)
        self.workflow.add_node("validator", validator_agent)
        self.workflow.add_node("outliner", outline_agent)

        # 3. Kenarları (Edges) ve Akışı (Flow) tanımlıyoruz.
        
        # Giriş noktası (Entry point) Supervisor'dır. Soruyu ilk o görür.
        self.workflow.set_entry_point("supervisor")
        
        # Supervisor'dan sonra araştırmacıya (Retriever) gidiyoruz.
        self.workflow.add_conditional_edges(
            "supervisor",
            self._route_from_supervisor,
            {
                "search": "retriever",        # Eğer karar search ise Retriever'a git
                "direct_answer": "generator",  # Eğer karar direct_answer ise Generator'a git
                "outline": "outliner"
            }
        )
        
        # Araştırmacı bağlamı bulunca taslak cevap üreticisine (Generator) gidiyor.
        self.workflow.add_edge("retriever", "generator")
        
        # Taslak cevap üretildikten sonra onaya (Validator) gidiyor.
        self.workflow.add_edge("generator", "validator")

        # Outliner işini bitirince doğrudan akışı sonlandırır
        self.workflow.add_edge("outliner", END)

        # 4. Koşullu Yönlendirme (Conditional Edges)
        # Validator'ın kararına göre ya süreci bitireceğiz ya da döngüye sokacağız.
        self.workflow.add_conditional_edges(
            "validator",
            self._check_validation,
            {
                "valid": END,                 # Eğer cevap doğruysa (is_valid=True), süreci bitir.
                "invalid": "retriever",       # Halüsinasyon varsa veya bağlam yetersizse yeni arama yap.
                "max_retries": END            # Sonsuz döngüyü engellemek için limite ulaşıldıysa bitir.
            }
        )

        # Grafı derleyip çalıştırılabilir hale getiriyoruz
        self.app = self.workflow.compile(checkpointer=self.memory)

    # YENİ EKLENEN METOT
    def _route_from_supervisor(self, state: AgentState) -> str:
        """
        Supervisor'ın 'next_action' kararına göre grafın makasını değiştirir.
        """
        return state.get("next_action", "search") # Eğer boşsa varsayılan olarak ara
    
    def _check_validation(self, state: AgentState) -> str:
        """
        Validator ajanından çıkan sonuca göre grafın nereye akacağına karar veren yönlendirici fonksiyon.
        """
        is_valid = state.get("is_valid", False)
        revision_count = state.get("revision_count", 0)

        max_retries = int(os.getenv("MAX_RETRIES", 2))
        if revision_count >= max_retries:
            print(f"⚠️ [Graph]: Maksimum deneme sayısına ({max_retries}) ulaşıldı. Mevcut en iyi cevapla çıkılıyor.")
            return "max_retries"
            
        if is_valid:
            print("✅ [Graph]: Cevap doğrulandı. Süreç tamamlanıyor.")
            return "valid"
        else:
            print("🔄 [Graph]: Cevap reddedildi (Halüsinasyon / Yetersiz Bağlam). Retriever tekrar tetikleniyor...")
            return "invalid"

    def run(self, question: str, thread_id: str = "sabit_oturum_1") -> dict:
        initial_state = {
            "question": question,
            "revision_count": 0,
            "messages": [{"role": "user", "content": question}] # Soruyu hafızaya yazıyoruz
        }
        
        print("🚀 [Graph]: Ajan iş akışı başlatılıyor...\n" + "-"*40)
        config = {"configurable": {"thread_id": thread_id}}
        final_state = self.app.invoke(initial_state, config=config)
        return final_state