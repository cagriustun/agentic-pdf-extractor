# Mimari Tasarım Dokümanı: Agentic Bilgi Çıkarımı Sistemi

# Proje Klasör Yapısı

agentic-pdf-extractor/
│
├── data/                   # Test edilecek PDF dosyaları
├── src/                    # Ana kaynak kodları
│   ├── __init__.py
│   ├── document_processor.py # PDF okuma, chunking (PyMuPDF - fitz)
│   ├── vector_store.py       # ChromaDB entegrasyonu ve retrieval
│   └── agents/               
│       ├── __init__.py
│       ├── state.py          # LangGraph state tanımları
│       ├── outline.py        # PDF Ağacını (Json) veren agent
│       ├── nodes.py          # Agentların yapacağı işler (araştır, doğrula vs.)
│       └── graph.py          # Agentların birbirine bağlanması
│
├── tests/                  # Pytest unit testleri
│   ├── __init__.py
│   └── test_processor.py
│
├── DESIGN.md               # Mimari tasarım doküman (Aşağıdaki içerik)
├── requirements.txt        # Bağımlılıklar
├── .env                    # API anahtarları ve configler (OpenAI API Key vb.)
├── main.py                 # CLI arayüzü ve giriş noktası
└── README.md               # Kurulum ve çalıştırma talimatları

# Proje Özeti

Bu doküman, uzun ve karmaşık belgelerden (PDF) bilgi çıkarmak amacıyla tasarlanan ajan tabanlı (agentic) sistemin mimari kararlarını, bileşenlerini ve veri akışını detaylandırmaktadır.

## 1. Sistem Mimarisinin Temel Bileşenleri

Sistem, "Kara Kutu" (Black Box) RAG çözümleri yerine, durum yönetimi (state management) yapılabilen yönlendirmeli bir graf mimarisi üzerine inşa edilmiştir.

### 1.1 Belge Ön İşleme (Document Pre-processing)

* **Araç:** `PyMuPDF` (fitz).

* **Ayrıştırma Stratejisi:** PDF içerisindeki metinler sayfa sayfa okunur. PyMuPDF'in seçilme nedeni, karakter koordinatlarını ve metin bloklarını hızlı bir şekilde vererek yapısal navigasyona olanak tanımasıdır. 

* **Chunking (Parçalama):** Metinler anlamsal bütünlüğü korumak adına belirli token limitlerine göre (örn. 1000 chunk size, 200 overlap) bölünerek vektör uzayına hazırlanır.

* **Görsel Ayrıştırma (Opsiyonel Vizyon):** PyMuPDF ile sayfalar görüntü (image) olarak da dışa aktarılabilir. Gerekirse bu görüntüler çok-modlu (multi-modal) bir modele (örn. gpt-4o) gönderilerek görsel içerik analizi yapılabilir.

### 1.2 Yapısal Navigasyon ve Retrieval Stratejisi

* **Araçlar:** `ChromaDB` (Vektör Veritabanı) ve `OpenAI text-embedding-3-small`.

* **Navigasyon:** Belge yapısı, her bir chunk'ın metadatasında (Sayfa numarası, belge adı) tutulur. Ajan, bir bilgi aradığında sadece ilgili sayfalara veya bölüm metadatalarına filtreleme (metadata filtering) uygulayarak uzun belgelerde kaybolmadan hedef bölüme odaklanabilir.

* **Arama (Retrieval):** Dense Retrieval (Vektör benzerliği) kullanılmaktadır. Sistem, sadece semantic arama yapmakla kalmaz; ajan tabanlı yapı sayesinde ajan, "Bu chunk'lar soruyu cevaplamak için yeterli mi?" diye sorarak yetersiz bulduğunda arama sorgusunu (query) kendi kendine revize ederek vektör veritabanında tekrar arama yapabilir.

## 2. Ajan (Agent) Mimarisi

Sistem, LangChain/LlamaIndex gibi üst düzey soyutlamalar yerine, kontrol edilebilirliği artırmak için durum tabanlı bir yapı olan LangGraph kullanır. 

**Roller ve İletişim:**

1.  **Supervisor (Yönlendirici):** Kullanıcıdan gelen soruyu analiz eder. Sorunun doğrudan cevaplanıp cevaplanamayacağına veya PDF'ten bilgi çekilmesi (retrieval) gerekip gerekmediğine karar verir.

2.  **Retriever (Araştırmacı):** Supervisor'dan gelen talimatla vektör veritabanına sorgu atar. Gerektiğinde "Tool Calling" kullanarak arama parametrelerini değiştirir.

3.  **Validator (Doğrulayıcı):** Çıkarılan bağlamı (context) ve üretilen taslak cevabı alır. "Bu cevap bağlamla uyuşuyor mu? Halüsinasyon var mı?" sorusunu değerlendirir.

4.  **Outline Agent (Ağaç Oluşturucu):** Belgenin hiyerarşik haritasını çıkarmakla görevli uzman ajandır. OpenAI'ın Structured Outputs (Pydantic) özelliğini kullanarak ham metni analiz eder ve dokümanı başlık/alt başlık/özet hiyerarşisinde yapılandırılmış bir JSON ağacına dönüştürür. Bu ajan, büyük belgelerin hızlıca taranabilmesi için stratejik olarak belgenin ilk bölümlerine odaklanan bir örnekleme stratejisi kullanır.

## 3. Doğrulama, Güvenilirlik ve Bellek

* **Doğrulama (Self-Correction):** Validator ajanı, üretilen cevabı orijinal bağlamla karşılaştırır. Eğer cevapta bağlam dışı bir bilgi (halüsinasyon) tespit ederse, Retriever ajanı geri tetikleyerek yeni bir sorgu yapmasını veya cevabı düzeltmesini ister. Çıktıların formatı `Pydantic` ile yapısal olarak (JSON) doğrulanır.

* **Bellek Yönetimi:** Görevler arası (soru-cevap seansında) öğrenme, State objesi üzerinden sağlanır. Sistemdeki "Message History" listesi sayesinde ajan, kullanıcının önceki sorularını ve sistemin verdiği önceki yanıtları bellekte tutarak bağlamsal süreklilik sağlar (Short-term memory).

* **Döngü Sınırlama ve Hata Toleransı:** Validator ajanı, halüsinasyon tespiti durumunda süreci sonsuz döngüye sokmamak adına MAX_RETRIES (varsayılan: 2) parametresi ile kısıtlanmıştır. Eğer sistem belirlenen deneme sayısında doğru bilgiye ulaşamazsa, mevcut en iyi cevabı "belgede tam olarak bulunamadı" uyarısıyla kullanıcıya sunar.

## 4. Tasarım Kararları ve Trade-off'lar

* **LangGraph vs Standard LangChain:** Standart zincirler (chains) deterministiktir ve hata durumunda kolayca çöker. Graf yapısı ise ajanların döngüye girmesine (örneğin cevabı beğenmeyip tekrar arama yapmasına) izin verir. Geliştirme süresi biraz daha uzundur ancak sistem çok daha dayanıklıdır.

* **Recursive vs. Karakter Bazlı Parçalama (Chunking):** Belge parçalama stratejisinde RecursiveCharacterTextSplitter tercih edilmiştir. Metni sadece sabit karakter sınırlarına göre bölmek yerine; paragraf, cümle ve kelime hiyerarşisini koruyarak anlamsal bütünlüğü önceler. Bu yöntem, arama sonuçlarının kalitesini artırarak ajanın doğru bağlama ulaşmasını sağlar.

* **Agentic Routing (Dinamik Yönlendirme):** Sistemin giriş noktasında statik bir akış yerine Supervisor ajanı tarafından yönetilen bir "Routing" mekanizması kurgulanmıştır. Her kullanıcı sorusu (örneğin selamlaşmalar veya geçmişe dair sorular) pahalı ve zaman alan vektör araması gerektirmez. Supervisor, sorunun niyetini analiz ederek gereksiz adımları atlar, böylece hem API maliyetlerini düşürür hem de kullanıcıya daha hızlı yanıt verilmesini sağlar. Karar verme aşamasında küçük bir model gecikmesi eklese de, sistemin genel verimliliğine katkısı çok daha yüksektir.

* **Lokal ChromaDB vs Cloud DB (Pinecone vs):** Sistem MVP aşamasında olduğu için kurulum kolaylığı ve ek maliyet/ağ gecikmesi (latency) yaratmaması adına in-memory çalışabilen lokal ChromaDB tercih edilmiştir. Mimari, ileride farklı bir veritabanının kolayca entegre edilebileceği modülerlikte tasarlanmıştır.

## 5. Dosya ve Çıktı Yönetimi

* **Dinamik İsimlendirme:** Taslak çıkarma işlemi sonrasında üretilen JSON dosyaları, data/ klasörü altında ilgili PDF dosyasıyla aynı isimde (örn: rapor.pdf -> rapor.json) otomatik olarak kaydedilir. Bu, veri tutarlılığını sağlar.

* **Zengin Terminal Arayüzü:** Kullanıcı etkileşimi Rich kütüphanesiyle güçlendirilmiştir. Ajanların düşünce süreçleri, hata ayıklama logları ve hiyerarşik belge ağaçları terminalde Markdown formatında, renkli ve okunabilir panellerle sunulur.

## 6. Mühendislik Yaklaşımı ve Hata Yönetimi

### 6.1 Tasarım Öncelikli Geliştirme (Design-First)
Kodlama aşamasına geçilmeden önce sistemin State Graph tasarlanmıştır. Bu sayede ajanlar arası veri akışı deterministik bir yapıya kavuşturulmuş, geliştirme sırasında oluşabilecek problemleri engellenmiştir.

### 6.2 Retrieval Başarı Faktörleri
Sistemin bilgi geri getirme kalitesi; recursive chunking, regex tabanlı veri temizlemeye ve yüksek boyutlu vektör uzayı (text-embedding-3-small) kullanımına dayanmaktadır. Verinin ham PDF metninden saf bilgiye dönüştürülmesi önceliklendirilmiştir.

### 6.3 Exception Handling ve Resilience
* **Dosya Katmanı:** Bozuk PDF veya hatalı dosya yolları `DocumentProcessor` seviyesinde yakalanarak kullanıcıya raporlanır.
* **API Katmanı:** LLM ve Vektör Veritabanı servislerinde yaşanabilecek kesintiler `try-except` blokları ile yönetilir, sistemin çalışma durumu korunarak çökme engellenir.