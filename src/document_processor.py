import fitz
import os
from typing import List, Dict, Any

class DocumentProcessor:
    """
    PDF belgelerini okuyan, metinleri çıkaran ve LLM/Retrieval sistemleri için
    anlamlı parçalara (chunk) bölen ön işleme (pre-processing) sınıfı.
    """
    def __init__(self):
        # Varsayılan değerleri .env dosyasından okuyoruz
        self.chunk_size = int(os.getenv("CHUNK_SIZE", 1000))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", 200))

    def process_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Bir PDF dosyasını okur ve sayfalarındaki metni metadata ile birlikte döndürür.
        """
        try:
            doc = fitz.open(file_path)
            pages_data = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text").strip()
                
                if text:
                    # Gelecekte görsel (image) desteği eklemek istersek burayı genişletebiliriz
                    pages_data.append({
                        "page_content": text,
                        "metadata": {
                            "source": file_path,
                            "page": page_num + 1
                        }
                    })
                    
            print(f"✅ [DocumentProcessor]: '{file_path}' başarıyla okundu. Toplam {len(pages_data)} sayfa işlendi.")
            return pages_data
            
        except Exception as e:
            print(f"❌ [DocumentProcessor]: PDF okunurken hata oluştu: {str(e)}")
            return []

    def chunk_documents(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sayfa bazlı metinleri, Vektör veritabanına ve LLM'e uygun boyutta parçalara (chunks) böler.
        Basit karakter tabanlı bir chunking (sliding window) mekanizması kullanır.
        """
        chunks = []
        
        for page in pages:
            text = page["page_content"]
            metadata = page["metadata"]
            
            # Eğer metin chunk boyutundan küçükse doğrudan ekle
            if len(text) <= self.chunk_size:
                chunks.append({"page_content": text, "metadata": metadata})
                continue
                
            # Sliding window (Kayan pencere) mantığı ile parçalama
            start = 0
            while start < len(text):
                end = start + self.chunk_size
                chunk_text = text[start:end]
                
                chunks.append({
                    "page_content": chunk_text,
                    "metadata": metadata
                })
                
                # Overlap (örtüşme) kadar geri git ki bağlam kopmasın
                start += self.chunk_size - self.chunk_overlap
                
        print(f"✂️ [DocumentProcessor]: Belgeler toplam {len(chunks)} parçaya (chunk) bölündü.")
        return chunks