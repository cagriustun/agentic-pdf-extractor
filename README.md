<<<<<<< HEAD
# agentic-pdf-extractor
=======
# Agentic PDF Extractor

Bu proje, gelişmiş RAG (Retrieval-Augmented Generation) tekniklerini ve "Agentic" iş akışlarını kullanarak PDF belgelerinden akıllıca bilgi çıkaran, sorgulayan ve doğrulayan interaktif bir yapay zeka asistanıdır. Standart RAG sistemlerinden farkı; kendi kararlarını verebilen, hatalarını denetleyen ve geçmişi hatırlayan bir ajan mimarisine sahip olmasıdır.

---

## Öne Çıkan Özellikler

* **Agentic Routing (Yönlendirme):** Sistem, gelen sorunun PDF bağlamına mı yoksa doğrudan sohbete mi ait olduğunu anlar ve gereksiz vektör aramalarını dinamik olarak atlar.

* **Halüsinasyon Koruması (Self-Correction):** Üretilen cevaplar kullanıcıya sunulmadan önce bir **Validator** ajanı tarafından kontrol edilir. Cevap bağlamla uyuşmuyorsa süreç otomatik olarak başa sarar.

* **Kısa Süreli Bellek (Memory):** LangGraph `MemorySaver` yapısı sayesinde asistan geçmiş soruları hatırlar ve bağlamsal sohbet sunar.

* **Zengin Terminal Arayüzü (TUI):** `Rich` kütüphanesi ile Markdown desteği, renkli paneller ve adım adım düşünce süreci takibi.

* **Modüler Yapı:** Tüm kritik parametreler (Model, Chunk Size, Retrieval K vb.) `.env` dosyası üzerinden yönetilir.

---

## ⚙️ Kurulum ve Hazırlık

1. **Sanal Ortamı Kurun:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows için: .\venv\Scripts\activate
    ```

2. **Bağımlılıkları Yükleyin:**
    ```bash
    pip install -r requirements.txt
    ```

3. **Çevresel Değişkenleri Ayarlayın:**
    Proje ana dizininde bir `.env` dosyası oluşturun:
    ```env
    OPENAI_API_KEY=sk-your-api-key-here
    OPENAI_MODEL=gpt-4o-mini
    EMBEDDING_MODEL=text-embedding-3-small
    CHROMA_PERSIST_DIR=./.chroma
    RETRIEVAL_K=4
    CHUNK_SIZE=1000
    CHUNK_OVERLAP=200
    MAX_RETRIES=2
    ```

---

## 🚀 Kullanım Kılavuzu

Sistemi iki farklı modda çalıştırabilirsiniz:

**1. İnteraktif Menü Modu (Önerilen):**

```bash
python main.py 
/pdf yazarak data/ klasöründeki dosyaları listeleyip seçebilirsiniz.

/q yazarak sistemden çıkabilirsiniz.
```

**2. CLI Parametre Modu:**

```bash
python main.py --pdf "data/dosya.pdf" --query "Bu belgenin özeti nedir?"
```

**Testleri Çalıştırma:**

```bash
pytest tests/ -v
```

# Mimari Tasarım Notu

1. Neden LangGraph?

Sistemin sadece doğrusal bir akışta değil, döngüsel (cyclic) bir yapıda çalışması gerekiyordu. LangGraph'ın state machine mimarisi, supervisor'ın yönlendirmesine, Validator'ın ise hata durumunda akışı Retriever'a geri göndermesine (Self-Correction) ayrıca talep edildiğinde ağaç formatı olarak çıktı verebilen outliner agent'ı çağırmaya olanak sağladığı için tercih edilmiştir.

2. Ajan Rolleri ve Karar Mekanizması

- Supervisor: Kullanıcı girdisini analiz eder. PDF araması gerekip gerekmediğine karar vererek "Agentic Routing" yapar.

- Retriever: ChromaDB üzerinde semantik arama yaparak en alakalı top_k parçayı getirir.

- Generator: Bağlamı ve sohbet geçmişini (Memory) harmanlayarak yanıt üretir.

- Validator: "Yanıt bağlamda mevcut mu?" kontrolü yapar. Halüsinasyon tespit edilirse MAX_RETRIES sınırına kadar süreci tekrarlatır.

- Outliner: Talep edildiğinde PDF için bir ağaç yapısı oluşturarak kullanıcıya sunar ve data klasörünün içerisine JSON olarak kaydeder.

3. Veri İşleme Stratejisi

PDF'ler fitz ile işlenir. CHUNK_SIZE=1000 ve CHUNK_OVERLAP=200 değerleri, metin bütünlüğünü korumak ve paragraf sonlarında bilgi kaybını önlemek amacıyla optimize edilmiştir. Vektör veritabanı olarak kalıcı (persistent) ChromaDB kullanılmış, her yeni PDF yüklemesinde koleksiyon temizleme mekanizması eklenmiştir.

4. Bellek (Memory) Yönetimi

LangGraph checkpointer yapısı kullanılarak her thread_id için özel bir hafıza alanı oluşturulmuştur. Bu sayede LLM, önceki mesajları takip ederek bağlamdan kopmadan cevap verebilir.
>>>>>>> 1d4cb42 (Initial commit: Agentic PDF Extraction System MVP)
