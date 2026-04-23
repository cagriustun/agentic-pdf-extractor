import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any

class VectorStoreManager:
    """
    Belge parçalarını (chunks) vektörlere dönüştüren ve ChromaDB üzerinde
    anlamsal arama (semantic search) yapılmasını sağlayan sınıf.
    """
    def __init__(self, collection_name: str = "agentic_pdf_collection"):
        # Yolu ve modeli env dosyasından alıyoruz
        self.db_path = os.getenv("CHROMA_PERSIST_DIR", "./.chroma")
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        self.openai_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_key:
            raise ValueError("❌ [VectorStore]: OPENAI_API_KEY ortam değişkeni bulunamadı.")

        embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.openai_key,
            model_name=embedding_model
        )
        
        # Koleksiyonu oluştur (varsa getir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )
        print(f"🗄️ [VectorStore]: '{collection_name}' koleksiyonu başarıyla yüklendi/oluşturuldu.")

    def add_documents(self, chunks: List[Dict[str, Any]]):
        """
        Metin parçalarını (chunks) ve metadatalarını veritabanına ekler.
        """
        if not chunks:
            print("⚠️ [VectorStore]: Eklenecek belge parçası bulunamadı.")
            return

        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            documents.append(chunk["page_content"])
            metadatas.append(chunk["metadata"])
            # Her bir chunk için benzersiz bir ID oluşturuyoruz
            ids.append(f"chunk_{i}")

        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"📥 [VectorStore]: {len(chunks)} adet belge parçası veritabanına eklendi.")
        except Exception as e:
            print(f"❌ [VectorStore]: Veritabanına ekleme sırasında hata oluştu: {str(e)}")

    def search(self, query: str) -> str:
        """
        Kullanıcının veya ajanın sorusuna en uygun 'top_k' adet metin parçasını getirir.
        Gelen sonuçları ajanların okuyabileceği tek bir string (bağlam) halinde birleştirir.
        """
        # RETRIEVAL_K değerini env dosyasından okuyoruz
        top_k = int(os.getenv("RETRIEVAL_K", 3))
        
        print(f"🔍 [VectorStore]: '{query}' için arama yapılıyor (Getirilecek Parça: {top_k})...")
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            # Gelen sonuçları LLM'e beslemek üzere formatlıyoruz
            formatted_context = ""
            for i in range(len(results['documents'][0])):
                doc = results['documents'][0][i]
                meta = results['metadatas'][0][i]
                
                # Ajanın hangi sayfaya baktığını bilmesi için metadata'yı da ekliyoruz
                formatted_context += f"\n--- Kaynak: Sayfa {meta.get('page', 'Bilinmiyor')} ---\n"
                formatted_context += f"{doc}\n"
                
            return formatted_context.strip()
            
        except Exception as e:
            print(f"❌ [VectorStore]: Arama sırasında hata oluştu: {str(e)}")
            return "Bağlam bulunamadı."
    
    def delete_collection(self):
        """Mevcut koleksiyondaki tüm verileri temizler."""
        try:
            # Koleksiyonu tamamen silip yeniden oluşturuyoruz
            self.client.delete_collection(self.collection.name)
            self.collection = self.client.create_collection(
                name=self.collection.name,
                embedding_function=self.embedding_fn
            )
            print("🗑️ [VectorStore]: Eski veriler temizlendi, yeni PDF için alan açıldı.")
        except Exception as e:
            print(f"⚠️ [VectorStore]: Temizleme sırasında bir hata oluştu (belki koleksiyon zaten boş): {str(e)}")