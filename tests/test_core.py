import pytest
import os
from dotenv import load_dotenv

load_dotenv()

from src.document_processor import DocumentProcessor
from src.agents.graph import WorkflowManager

# --- TEST 1: Belge Ön İşleme (Chunking) Mantığı ---
def test_chunk_documents_logic():
    """
    DocumentProcessor sınıfının uzun metinleri doğru boyutta ve 
    doğru overlap (örtüşme) ile bölüp bölmediğini test eder.
    """
    processor = DocumentProcessor()
    # Test için env değişkenlerini eziyoruz ki standart ve hızlı çalışsın
    processor.chunk_size = 50
    processor.chunk_overlap = 10
    
    # 100 karakterlik sahte bir sayfa oluşturuyoruz
    dummy_text = "A" * 100
    dummy_pages = [{"page_content": dummy_text, "metadata": {"page": 1, "source": "test.pdf"}}]
    
    chunks = processor.chunk_documents(dummy_pages)
    
    # Beklentiler:
    # 1. chunk: 0-50
    # 2. chunk: 40-90 (10 overlap olduğu için 40'tan başlar)
    # 3. chunk: 80-100
    assert len(chunks) == 3, "Metin beklenen parça sayısına bölünemedi."
    assert len(chunks[0]["page_content"]) == 50, "İlk parçanın boyutu yanlış."
    assert chunks[0]["metadata"]["page"] == 1, "Metadata kayboldu."


# --- TEST 2: Validator ve Döngü (Routing) Mantığı ---
def test_graph_validation_routing():
    """
    WorkflowManager'ın Validator'dan gelen is_valid ve revision_count 
    değerlerine göre grafı doğru yönlendirip yönlendirmediğini test eder.
    """
    # Test için env değişkenini geçici olarak ayarlıyoruz
    os.environ["MAX_RETRIES"] = "2"
    manager = WorkflowManager()
    
    # Senaryo A: Cevap geçerli (Halüsinasyon yok) -> Süreç bitmeli ("valid")
    state_valid = {"is_valid": True, "revision_count": 1}
    assert manager._check_validation(state_valid) == "valid"
    
    # Senaryo B: Cevap geçersiz (Halüsinasyon var) -> Tekrar aranmalı ("invalid")
    state_invalid = {"is_valid": False, "revision_count": 1}
    assert manager._check_validation(state_invalid) == "invalid"
    
    # Senaryo C: Maksimum denemeye ulaşıldı -> Süreç bitmeli ("max_retries")
    state_max_retries = {"is_valid": False, "revision_count": 2}
    assert manager._check_validation(state_max_retries) == "max_retries"


# --- TEST 3: Supervisor Yönlendirme (Agentic Routing) Mantığı ---
def test_supervisor_routing():
    """
    WorkflowManager'ın Supervisor ajanından çıkan 'next_action' kararına
    göre süreci Retriever'a mı yoksa Generator'a mı yönlendirdiğini test eder.
    """
    manager = WorkflowManager()
    
    # Senaryo A: PDF'te arama yapılması gerekiyor
    state_search = {"next_action": "search"}
    assert manager._route_from_supervisor(state_search) == "search"
    
    # Senaryo B: Doğrudan sohbet edilecek
    state_direct = {"next_action": "direct_answer"}
    assert manager._route_from_supervisor(state_direct) == "direct_answer"
    
    # Senaryo C: Hatalı/Boş durumda varsayılan olarak "search" seçilmeli
    state_empty = {}
    assert manager._route_from_supervisor(state_empty) == "search"