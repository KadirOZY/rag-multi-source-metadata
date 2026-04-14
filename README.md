# Çoklu Kaynak ve Metadata Destekli RAG Sistemi

Farklı formatlardaki şirket dokümanlarını (TXT, CSV, JSON) kullanarak müşteri sorularını doğru ve güncel şekilde yanıtlayan bir **Retrieval-Augmented Generation** pipeline'ı.

## Sorun Tanımı

Şirketlerin bilgisi tek bir yerde değil — sözleşmeler TXT'de, fiyatlar CSV'de, değişiklik logları JSON'da tutulur. Klasik RAG sistemleri her şeyi aynı şekilde parçalayıp vektör veritabanına atar, bu da tablo yapısının bozulmasına ve çelişen bilgilerin gözden kaçmasına yol açar.

Bu proje, her kaynağı kendi doğasına uygun şekilde işleyen ve çelişkileri tarih bazlı çözen bir mimari sunar.

## Mimari

```
Kullanıcı Sorusu
       │
       ▼
┌──────────────────┐
│   Smart Router   │  Sorudaki anahtar kelimelere göre
│  (router.py)     │  hangi kaynakların gerektiğine karar verir
└──────────────────┘
       │
       ├──────────────────────────────────┐
       ▼                                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Sözleşme    │  │  Fiyat       │  │  Güncelleme  │
│  (TXT)       │  │  Tablosu     │  │  Logları     │
│  Madde bazlı │  │  (CSV)       │  │  (JSON)      │
│  chunking    │  │  Satır bazlı │  │  Kayıt bazlı │
│              │  │  chunking    │  │  chunking    │
└──────────────┘  └──────────────┘  └──────────────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────────────────────────────────────┐
│           ChromaDB Vektör Veritabanı        │
│         Semantic Search + Metadata Filtre   │
└─────────────────────────────────────────────┘
       │
       ▼
┌──────────────────┐
│    Conflict      │  Aynı konuda farklı bilgi varsa
│    Resolver      │  en güncel tarihli kaydı baz alır
│ (conflict_       │
│  resolver.py)    │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│   LLM (GPT-4o   │  Bağlam + çelişki bilgisi + referanslar
│   -mini)         │  ile doğal dilde cevap üretir
└──────────────────┘
       │
       ▼
   Cevap + Kaynak Referansları
```

## Klasik RAG'den Farkları

| Özellik | Klasik Yaklaşım | Bu Proje |
|---------|-----------------|----------|
| Chunking | Tüm kaynaklar aynı boyutta bölünür | Her kaynak kendi formatına uygun bölünür |
| CSV İşleme | Satırlar parçalanır, sütun bağlamı kaybolur | Her satır başlık bilgisiyle birlikte tek chunk |
| Çelişki | Fark edilmez, rastgele bilgi döner | Tarih bazlı çelişki tespiti ve çözümleme |
| Yönlendirme | Her soru tüm veritabanını tarar | Router ilgili kaynakları belirler, güncelleme logları her zaman dahil |
| Kaynak Referansı | Yok | Hangi dosyadan, hangi tarihte bilgi alındığı gösterilir |

## Proje Yapısı

```
├── data/                          # Veri kaynakları
│   ├── sozlesme.txt               # Müşteri sözleşmesi (hukuki metin, madde bazlı)
│   ├── paket_fiyatlari.csv        # Paket fiyat ve limit tablosu (Basic, Pro, Enterprise)
│   └── guncellemeler.json         # Tarihsel değişiklik logları (fiyat, sözleşme, özellik)
│
├── src/                           # Kaynak kodları
│   ├── __init__.py
│   ├── loaders.py                 # Dosya formatına özel yükleyiciler (TXT, CSV, JSON)
│   ├── chunkers.py                # Kaynak-bilinçli chunking stratejileri
│   ├── vectorstore.py             # ChromaDB vektör veritabanı yönetimi
│   ├── router.py                  # Soru analizi ve kaynak yönlendirme
│   ├── conflict_resolver.py       # Çelişki tespiti ve tarih bazlı çözümleme
│   └── rag_engine.py              # Ana RAG pipeline (orkestratör)
│
├── main.py                        # Çalıştırma noktası (demo + interaktif mod)
├── requirements.txt               # Python bağımlılıkları
├── .env                           # API anahtarı (git'e eklenmemeli)
└── .gitignore                     # Git dışında tutulacak dosyalar
```

## Teknoloji Yığını

| Teknoloji | Versiyon | Kullanım Amacı |
|-----------|----------|----------------|
| Python | 3.10+ | Ana programlama dili |
| LangChain | 0.3.x | RAG pipeline framework'ü |
| ChromaDB | 1.0.x | Vektör veritabanı (embedding saklama ve semantic search) |
| OpenAI API | - | Embedding üretimi (text-embedding-3-small) ve cevap üretimi (gpt-4o-mini) |
| python-dotenv | - | Ortam değişkenleri yönetimi |

## Kurulum

```bash
# 1. Repoyu klonlayın
git clone https://github.com/KadirOZY/rag-multi-source.git
cd rag-multi-source

# 2. Sanal ortam oluşturun
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# 3. Bağımlılıkları yükleyin
pip install -r requirements.txt

# 4. API anahtarınızı ayarlayın
# .env dosyasını açıp OPENAI_API_KEY değerini yazın

# 5. Çalıştırın
python main.py
```

## Kullanım

Sistem iki modda çalışır:

**Demo Modu (1)** — Hazır sorularla sistemi test eder. Çıktıda Router kararları, getirilen chunk'lar, çelişki tespiti ve son cevap adım adım görünür.

**İnteraktif Mod (2)** — Kendi sorularınızı yazarak sistemi test edebilirsiniz.

### Örnek Sorular

```
Şu anki Pro paket fiyatı nedir ve iptal edersem paramı ne zaman alırım?
Enterprise paket erken fesih bedeli ne kadar?
Verilerim ne kadar süre saklanıyor?
Paketler arasındaki farklar neler?
```

## Dinamik Test Senaryoları

Sistem, veri dosyalarını her başlatıldığında sıfırdan okur. Statik değildir. Aşağıdaki senaryolarla doğrulayabilirsiniz:

### Senaryo 1 — Fiyat Değişikliği

`data/paket_fiyatlari.csv` dosyasında Pro paketinin aylık fiyatını `599` yerine `699` yapın. Sistemi yeniden başlatıp "Pro paket fiyatı nedir?" sorusunu sorun. Cevap **699 TL** olmalıdır.

### Senaryo 2 — Yeni Güncelleme Kaydı

`data/guncellemeler.json` dosyasının sonuna aşağıdaki kaydı ekleyin:

```json
,
  {
    "tarih": "2025-03-01",
    "kategori": "sozlesme",
    "etkilenen_paket": "Basic",
    "onceki_deger": "14 gün",
    "yeni_deger": "7 gün",
    "degisiklik": "Basic paket iade süresi 14 günden 7 güne düşürülmüştür.",
    "referans_madde": "Madde 4.1"
  }
```

"Basic paket iade süresi nedir?" sorusunu sorun. Sözleşmede 14 gün yazmasına rağmen sistem güncelleme logundaki **7 gün** bilgisini esas almalıdır.

### Senaryo 3 — Çelişki Tespiti

Pro paket iade süresi sözleşmede 14 gün olarak geçer, ancak güncelleme logunda (2024-06-01 tarihli) 30 güne çıkarılmıştır. Sistem bu çelişkiyi tespit eder ve **30 gün** cevabını verir.
