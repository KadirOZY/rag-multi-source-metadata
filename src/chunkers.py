"""
chunkers.py — Kaynak-Bilinçli Chunking Stratejileri

Herkesin yaptığı: RecursiveCharacterTextSplitter ile her şeyi böl.
Bizim farkımız: Her kaynak kendi doğasına uygun şekilde parçalanıyor.

- TXT (Sözleşme)  → Madde bazlı bölme (her madde = 1 chunk)
- CSV (Fiyatlar)   → Satır bazlı bölme (başlıklar her chunk'a eklenir)
- JSON (Loglar)    → Her kayıt = 1 chunk (tarih + değişiklik bütün kalır)
"""

import re
from langchain.schema import Document


def _temiz_metadata(meta: dict) -> dict:
    """
    ChromaDB sadece str, int, float, bool kabul eder.
    None → boş string, list → virgüllü string'e çevirir.
    """
    temiz = {}
    for anahtar, deger in meta.items():
        if deger is None:
            temiz[anahtar] = ""
        elif isinstance(deger, list):
            temiz[anahtar] = ", ".join(str(d) for d in deger)
        else:
            temiz[anahtar] = deger
    return temiz


def chunk_sozlesme(metin: str) -> list[Document]:
    """
    Sözleşme metnini madde bazlı parçalar.

    Strateji: 'Madde X' pattern'ini yakala, aralarındaki metni
    tek bir chunk olarak tut. Böylece 'Madde 4 - İptal ve İade'
    başlığı altındaki tüm alt maddeler (4.1, 4.2, ...) tek chunk'ta kalır.
    """
    baslik_pattern = r"^(.*?)(?=Madde\s+1\s*[-–])"
    baslik_eslesme = re.search(baslik_pattern, metin, re.DOTALL)

    chunklar = []

    if baslik_eslesme:
        baslik_metni = baslik_eslesme.group(1).strip()
        if baslik_metni:
            chunklar.append(
                Document(
                    page_content=baslik_metni,
                    metadata=_temiz_metadata(
                        {"kaynak": "sozlesme.txt", "bolum": "baslik", "tip": "sozlesme"}
                    ),
                )
            )

    madde_pattern = r"(Madde\s+\d+\s*[-–].+?)(?=Madde\s+\d+\s*[-–]|$)"
    maddeler = re.findall(madde_pattern, metin, re.DOTALL)

    for madde in maddeler:
        madde_temiz = madde.strip()
        if not madde_temiz:
            continue

        madde_no_eslesme = re.match(
            r"Madde\s+(\d+)\s*[-–]\s*(.+?)(?:\n|$)", madde_temiz
        )
        madde_no = madde_no_eslesme.group(1) if madde_no_eslesme else "?"
        madde_baslik = madde_no_eslesme.group(2).strip() if madde_no_eslesme else ""

        chunklar.append(
            Document(
                page_content=madde_temiz,
                metadata=_temiz_metadata(
                    {
                        "kaynak": "sozlesme.txt",
                        "bolum": f"Madde {madde_no}",
                        "baslik": madde_baslik,
                        "tip": "sozlesme",
                    }
                ),
            )
        )

    return chunklar


def chunk_csv(satirlar: list[dict]) -> list[Document]:
    """
    CSV verisini satır bazlı chunk'lar.

    Fark: Her chunk'a sütun başlıkları da eklenir.
    Ek olarak, tüm tabloyu tek bir özet chunk olarak da ekliyoruz.
    """
    chunklar = []

    for satir in satirlar:
        paket = satir.get("paket_adi", "Bilinmeyen")

        icerik_parcalari = []
        for anahtar, deger in satir.items():
            icerik_parcalari.append(f"{anahtar}: {deger}")
        icerik = "\n".join(icerik_parcalari)

        chunklar.append(
            Document(
                page_content=icerik,
                metadata=_temiz_metadata(
                    {
                        "kaynak": "paket_fiyatlari.csv",
                        "paket": paket,
                        "tip": "fiyat_tablosu",
                        "sutunlar": ", ".join(satir.keys()),
                    }
                ),
            )
        )

    tablo_ozet_satirlar = []
    for satir in satirlar:
        paket = satir.get("paket_adi", "?")
        fiyat = satir.get("aylik_fiyat_tl", "?")
        depolama = satir.get("depolama_gb", "?")
        api = satir.get("api_limit_aylik", "?")
        tablo_ozet_satirlar.append(
            f"{paket}: Aylık {fiyat} TL, {depolama} GB depolama, {api} API çağrı/ay"
        )

    tablo_ozet = "TÜM PAKET KARŞILAŞTIRMASI:\n" + "\n".join(tablo_ozet_satirlar)
    chunklar.append(
        Document(
            page_content=tablo_ozet,
            metadata=_temiz_metadata(
                {
                    "kaynak": "paket_fiyatlari.csv",
                    "paket": "karsilastirma",
                    "tip": "fiyat_tablosu",
                    "sutunlar": ", ".join(satirlar[0].keys()) if satirlar else "",
                }
            ),
        )
    )

    return chunklar


def chunk_json(kayitlar: list[dict]) -> list[Document]:
    """
    JSON güncelleme loglarını kayıt bazlı chunk'lar.
    """
    chunklar = []

    for kayit in kayitlar:
        icerik_satirlari = [
            f"Güncelleme Tarihi: {kayit['tarih']}",
            f"Kategori: {kayit['kategori']}",
            f"Etkilenen Paket: {kayit['etkilenen_paket']}",
            f"Önceki Değer: {kayit['onceki_deger']}",
            f"Yeni Değer: {kayit['yeni_deger']}",
            f"Değişiklik Detayı: {kayit['degisiklik']}",
        ]
        if kayit.get("referans_madde"):
            icerik_satirlari.append(f"Referans: {kayit['referans_madde']}")

        icerik = "\n".join(icerik_satirlari)

        chunklar.append(
            Document(
                page_content=icerik,
                metadata=_temiz_metadata(
                    {
                        "kaynak": "guncellemeler.json",
                        "tarih": kayit["tarih"],
                        "kategori": kayit["kategori"],
                        "etkilenen_paket": kayit["etkilenen_paket"],
                        "tip": "guncelleme",
                        "referans_madde": kayit.get("referans_madde"),
                    }
                ),
            )
        )

    return chunklar
