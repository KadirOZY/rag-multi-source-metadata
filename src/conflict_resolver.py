"""
conflict_resolver.py — Çelişki Çözümleme Motoru

RAG sistemlerinin en zayıf noktası: farklı kaynaklarda çelişen bilgi.
Örneğin sözleşmede iade süresi '14 gün' yazıyor ama JSON logunda
Pro paketi için '30 gün'e çıkarılmış.

Bu modül, çelişen bilgileri tespit edip en güncel olanı baz alır.
Ayrıca çelişki geçmişini de cevaba referans olarak ekler.
"""

from langchain.schema import Document
from datetime import datetime


def guncel_bilgileri_belirle(chunklar: list[Document]) -> dict:
    """
    Getirilen chunk'lar arasında çelişki varsa tespit eder.

    Mantık:
    1. Güncelleme loglarındaki (tip=guncelleme) kayıtları tarihlerine göre sırala
    2. Aynı konuda birden fazla bilgi varsa en yeni tarihli olanı işaretle
    3. Sonucu dict olarak döndür:
       {
         "celiski_var": True/False,
         "aciklama": "Pro paket iade süresi...",
         "guncel_chunklar": [...],
         "tarihce": [...]
       }
    """
    guncelleme_chunklari = []
    diger_chunklar = []

    for chunk in chunklar:
        if chunk.metadata.get("tip") == "guncelleme":
            guncelleme_chunklari.append(chunk)
        else:
            diger_chunklar.append(chunk)

    # güncelleme yoksa çelişki kontrolü gerekmez
    if not guncelleme_chunklari:
        return {
            "celiski_var": False,
            "aciklama": "",
            "guncel_chunklar": chunklar,
            "tarihce": []
        }

    # güncelleme kayıtlarını tarihe göre sırala (en yeni sonda)
    guncelleme_chunklari.sort(
        key=lambda c: datetime.strptime(c.metadata.get("tarih", "1900-01-01"), "%Y-%m-%d")
    )

    # aynı referans maddesine sahip güncellemeleri grupla
    madde_guncellemeleri = {}
    for chunk in guncelleme_chunklari:
        ref = chunk.metadata.get("referans_madde", "")
        paket = chunk.metadata.get("etkilenen_paket", "")
        anahtar = f"{ref}|{paket}" if ref else f"genel|{paket}"

        if anahtar not in madde_guncellemeleri:
            madde_guncellemeleri[anahtar] = []
        madde_guncellemeleri[anahtar].append(chunk)

    # çelişki tespiti: sözleşmede yazanla güncelleme logundaki farklıysa
    celiski_aciklamalari = []
    for anahtar, gunceller in madde_guncellemeleri.items():
        if len(gunceller) > 0:
            en_guncel = gunceller[-1]  # tarih sıralı, son eleman en yeni
            tarih = en_guncel.metadata.get("tarih", "?")
            celiski_aciklamalari.append(
                f"[{tarih}] {en_guncel.page_content.split('Değişiklik Detayı: ')[-1].split(chr(10))[0]}"
            )

    # tarihçe bilgisi
    tarihce = []
    for chunk in guncelleme_chunklari:
        tarihce.append({
            "tarih": chunk.metadata.get("tarih", "?"),
            "degisiklik": chunk.page_content.split("Değişiklik Detayı: ")[-1].split("\n")[0],
            "paket": chunk.metadata.get("etkilenen_paket", "?")
        })

    celiski_var = len(celiski_aciklamalari) > 0

    return {
        "celiski_var": celiski_var,
        "aciklama": "\n".join(celiski_aciklamalari) if celiski_var else "",
        "guncel_chunklar": chunklar,  # tüm chunk'ları gönder, LLM karar verecek
        "tarihce": tarihce
    }


def referans_metni_olustur(chunklar: list[Document]) -> str:
    """
    LLM'in cevabında gösterilecek kaynak referanslarını oluşturur.
    Hangi dosyadan, hangi bölümden, hangi tarihte bilgi alındığını gösterir.
    """
    referanslar = []
    gorulmus = set()

    for chunk in chunklar:
        kaynak = chunk.metadata.get("kaynak", "bilinmeyen")
        tip = chunk.metadata.get("tip", "")
        tarih = chunk.metadata.get("tarih", "")
        bolum = chunk.metadata.get("bolum", "")
        paket = chunk.metadata.get("paket", "")

        # tekrar etmesin
        ref_anahtar = f"{kaynak}|{bolum}|{tarih}|{paket}"
        if ref_anahtar in gorulmus:
            continue
        gorulmus.add(ref_anahtar)

        ref_parcalari = [f"📄 {kaynak}"]
        if bolum:
            ref_parcalari.append(f"({bolum})")
        if paket and paket != "karsilastirma":
            ref_parcalari.append(f"[{paket} paketi]")
        if tarih:
            ref_parcalari.append(f"— {tarih}")

        referanslar.append(" ".join(ref_parcalari))

    return "\n".join(referanslar) if referanslar else "Referans bilgisi bulunamadı."
