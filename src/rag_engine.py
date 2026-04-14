"""
rag_engine.py — Ana RAG Pipeline

Tüm bileşenleri bir araya getiren orkestratör.
Akış: Soru → Router → Retrieval → Conflict Resolution → LLM → Cevap
"""

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import Document

from src.loaders import yukle_sozlesme, yukle_csv, yukle_json
from src.chunkers import chunk_sozlesme, chunk_csv, chunk_json
from src.vectorstore import vektor_db_olustur, arama_yap
from src.router import kaynak_belirle, metadata_filtresi_olustur
from src.conflict_resolver import guncel_bilgileri_belirle, referans_metni_olustur


# cevap üretme şablonu — LLM'e verilen talimat
CEVAP_SABLONU = ChatPromptTemplate.from_messages([
    ("system", """Sen bir şirketin müşteri destek asistanısın.

Görevin: Müşteri sorularını yalnızca sana verilen kaynaklara dayanarak cevaplamak.

Kurallar:
1. SADECE verilen bağlam bilgisini kullan. Bağlamda olmayan bilgiyi uydurma.
2. Birden fazla kaynaktan bilgi geliyorsa hepsini sentezleyerek tutarlı bir cevap ver.
3. Eğer çelişki bilgisi verilmişse, güncelleme logundaki EN SON tarihli bilgiyi esas al.
4. Cevabın sonunda hangi kaynaklardan yararlandığını belirt.
5. Emin olmadığın konularda "Bu konuda kesin bilgi bulamadım, müşteri hizmetleriyle iletişime geçmenizi öneririm." de.
6. Türkçe ve samimi bir dille cevap ver, teknik jargondan kaçın.

Çelişki Durumu:
{celiski_bilgisi}

Değişiklik Tarihçesi:
{tarihce}"""),
    ("human", """Müşteri Sorusu: {soru}

Kaynaklardan Getirilen Bilgi:
{baglam}

Kaynak Referansları:
{referanslar}

Lütfen yukarıdaki bilgilere dayanarak müşterinin sorusunu cevapla.""")
])


class RAGMotoru:
    """
    Çoklu Kaynak RAG Motoru.

    Veri dosyalarını her başlatılışta sıfırdan okur — böylece
    dosyalar değiştirildiğinde sistem otomatik olarak güncellenir.
    Statik cache kullanmaz, her zaman güncel veriyle çalışır.
    """

    def __init__(self, veri_dizini: str = "./data"):
        self.veri_dizini = veri_dizini
        self.vektor_db = None
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self._sistemi_hazirla()

    def _sistemi_hazirla(self):
        """Veri dosyalarını oku, chunk'la ve vektör DB'ye yaz."""
        print("[RAG] Sistem başlatılıyor...")

        # 1. verileri yükle
        print("[RAG] Veriler yükleniyor...")
        sozlesme_metni = yukle_sozlesme(f"{self.veri_dizini}/sozlesme.txt")
        csv_satirlari = yukle_csv(f"{self.veri_dizini}/paket_fiyatlari.csv")
        json_kayitlari = yukle_json(f"{self.veri_dizini}/guncellemeler.json")

        # 2. akıllı chunking
        print("[RAG] Chunk'lama yapılıyor...")
        tum_chunklar = []
        tum_chunklar.extend(chunk_sozlesme(sozlesme_metni))
        tum_chunklar.extend(chunk_csv(csv_satirlari))
        tum_chunklar.extend(chunk_json(json_kayitlari))

        print(f"[RAG] Toplam {len(tum_chunklar)} chunk oluşturuldu:")
        tip_sayilari = {}
        for c in tum_chunklar:
            t = c.metadata.get("tip", "?")
            tip_sayilari[t] = tip_sayilari.get(t, 0) + 1
        for t, s in tip_sayilari.items():
            print(f"       - {t}: {s} chunk")

        # 3. vektör DB oluştur
        print("[RAG] Vektör veritabanı oluşturuluyor...")
        self.vektor_db = vektor_db_olustur(tum_chunklar)

        print("[RAG] Sistem hazır!\n")

    def soru_sor(self, soru: str) -> str:
        """
        Kullanıcının sorusunu işleyip cevap üretir.

        Akış:
        1. Router ile ilgili kaynakları belirle
        2. Metadata filtresi oluştur
        3. Vektör DB'de arama yap
        4. Çelişki kontrolü yap
        5. LLM ile cevap üret
        """
        print(f"\n{'='*60}")
        print(f"Soru: {soru}")
        print(f"{'='*60}")

        # 1 — hangi kaynaklara bakmamız gerekiyor?
        kaynaklar = kaynak_belirle(soru)
        print(f"[Router] Belirlenen kaynaklar: {kaynaklar}")

        # 2 — metadata filtresi
        filtre = metadata_filtresi_olustur(kaynaklar)
        if filtre:
            print(f"[Router] Uygulanan filtre: {filtre}")
        else:
            print("[Router] Filtre yok — tüm kaynaklar taranacak.")

        # 3 — vektör araması
        getirilen_chunklar = arama_yap(self.vektor_db, soru, k=6, filtre=filtre)
        print(f"[Retrieval] {len(getirilen_chunklar)} chunk getirildi:")
        for i, chunk in enumerate(getirilen_chunklar):
            kaynak = chunk.metadata.get("kaynak", "?")
            tip = chunk.metadata.get("tip", "?")
            print(f"  [{i+1}] {kaynak} (tip: {tip})")

        # 4 — çelişki kontrolü
        celiski_sonucu = guncel_bilgileri_belirle(getirilen_chunklar)
        if celiski_sonucu["celiski_var"]:
            print(f"[Çelişki] Çelişki tespit edildi!")
            print(f"  {celiski_sonucu['aciklama']}")
        else:
            print("[Çelişki] Çelişki bulunamadı.")

        # 5 — referans metni
        referanslar = referans_metni_olustur(getirilen_chunklar)

        # bağlam metnini oluştur
        baglam = "\n\n---\n\n".join(
            [chunk.page_content for chunk in getirilen_chunklar]
        )

        # tarihçe metni
        tarihce_metni = ""
        if celiski_sonucu["tarihce"]:
            tarihce_satirlari = []
            for t in celiski_sonucu["tarihce"]:
                tarihce_satirlari.append(f"• [{t['tarih']}] {t['paket']}: {t['degisiklik']}")
            tarihce_metni = "\n".join(tarihce_satirlari)

        # çelişki bilgisi
        celiski_bilgisi = ""
        if celiski_sonucu["celiski_var"]:
            celiski_bilgisi = (
                "DİKKAT: Kaynaklarda çelişen bilgiler tespit edilmiştir. "
                "En güncel tarihli güncelleme logundaki bilgiyi esas al.\n"
                f"{celiski_sonucu['aciklama']}"
            )
        else:
            celiski_bilgisi = "Çelişki tespit edilmedi."

        # 6 — LLM ile cevap üret
        print("[LLM] Cevap üretiliyor...")
        zincir = CEVAP_SABLONU | self.llm

        cevap = zincir.invoke({
            "soru": soru,
            "baglam": baglam,
            "celiski_bilgisi": celiski_bilgisi,
            "tarihce": tarihce_metni if tarihce_metni else "Tarihçe bilgisi yok.",
            "referanslar": referanslar
        })

        return cevap.content
