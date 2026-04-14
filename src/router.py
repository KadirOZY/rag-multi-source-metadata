"""
router.py — Akıllı Soru Yönlendirici

Kullanıcının sorusunu analiz eder ve hangi kaynaklardan
bilgi çekilmesi gerektiğine karar verir.

İki aşamalı çalışır:
1. Anahtar kelime tespiti (hızlı, LLM gerektirmez)
2. Gerekirse LLM ile soru niyetini anlama (karmaşık sorular için)
"""

# kaynak bazlı anahtar kelime haritası
KAYNAK_ANAHTAR_KELIMELER = {
    "fiyat_tablosu": [
        "fiyat",
        "ücret",
        "maliyet",
        "paket",
        "plan",
        "abonelik",
        "kaç tl",
        "ne kadar",
        "basic",
        "pro",
        "enterprise",
        "depolama",
        "api limit",
        "kullanıcı sayısı",
        "gb",
        "indirim",
        "yıllık",
        "aylık",
        "karşılaştır",
        "fark",
        "en ucuz",
        "en pahalı",
        "özellik",
    ],
    "sozlesme": [
        "madde",
        "sözleşme",
        "hüküm",
        "koşul",
        "şart",
        "iade",
        "iptal",
        "fesih",
        "cayma",
        "para iadesi",
        "ödeme",
        "fatura",
        "gecikme",
        "faiz",
        "destek",
        "sla",
        "güvenlik",
        "veri",
        "gizlilik",
        "limit",
        "aşım",
        "yükseltme",
        "değişiklik",
        "uyuşmazlık",
        "tahkim",
        "hak",
        "yükümlülük",
    ],
    "guncelleme": [
        "güncel",
        "son",
        "değişiklik",
        "güncelleme",
        "yeni",
        "ne zaman değişti",
        "eski",
        "önceki",
        "tarih",
        "şu anki",
        "mevcut",
        "son durum",
        "güncellenmiş",
        "artış",
        "azalma",
        "değişti mi",
        "yeni fiyat",
    ],
}


def kaynak_belirle(soru: str) -> list[str]:
    """
    Sorudaki anahtar kelimelere göre hangi kaynakların
    sorgulanması gerektiğini belirler.

    Döndürür: ["fiyat_tablosu", "sozlesme", "guncelleme"]
    gibi bir liste. Birden fazla kaynak dönebilir.

    ÖNEMLİ: Güncelleme logları her zaman dahil edilir.
    Çünkü sözleşmedeki veya fiyat tablosundaki bir bilgi,
    sonradan güncellenmiş olabilir. Bunu atlamak çelişki
    tespitini imkansız hale getirir.
    """
    soru_kucuk = soru.lower()
    ilgili_kaynaklar = set()

    for kaynak, kelimeler in KAYNAK_ANAHTAR_KELIMELER.items():
        for kelime in kelimeler:
            if kelime in soru_kucuk:
                ilgili_kaynaklar.add(kaynak)
                break

    # hiçbir kaynak bulunamazsa hepsini tara
    if not ilgili_kaynaklar:
        ilgili_kaynaklar = {"fiyat_tablosu", "sozlesme", "guncelleme"}

    # güncelleme loglarını HER ZAMAN dahil et
    # sözleşme veya fiyat bilgisi sorulsa bile, o bilgi
    # sonradan değişmiş olabilir — çelişki tespiti için şart
    ilgili_kaynaklar.add("guncelleme")

    return list(ilgili_kaynaklar)


def metadata_filtresi_olustur(kaynaklar: list[str]) -> dict | None:
    """
    Belirlenen kaynaklara göre ChromaDB metadata filtresi oluşturur.

    Tek kaynak varsa basit filtre, birden fazla varsa $or operatörü kullanılır.
    Tüm kaynaklar seçildiyse filtre None döner (filtre yok = hepsini tara).
    """
    tip_haritasi = {
        "fiyat_tablosu": "fiyat_tablosu",
        "sozlesme": "sozlesme",
        "guncelleme": "guncelleme",
    }

    if len(kaynaklar) >= 3:
        return None  # hepsini tara

    tipler = [tip_haritasi[k] for k in kaynaklar if k in tip_haritasi]

    if len(tipler) == 1:
        return {"tip": tipler[0]}
    elif len(tipler) > 1:
        return {"$or": [{"tip": t} for t in tipler]}

    return None
