"""
loaders.py — Kaynak Bazlı Veri Yükleyiciler

Her dosya formatı için özelleştirilmiş yükleme mantığı.
Klasik RAG'den farkımız: dosya tipine göre farklı okuma stratejisi.
"""

import csv
import json
from pathlib import Path
from datetime import datetime


def yukle_sozlesme(dosya_yolu: str) -> str:
    """
    Sözleşme metnini düz metin olarak okur.
    Encoding sorunlarına karşı utf-8 zorlanır.
    """
    yol = Path(dosya_yolu)
    if not yol.exists():
        raise FileNotFoundError(f"Sözleşme dosyası bulunamadı: {dosya_yolu}")

    with open(yol, "r", encoding="utf-8") as f:
        icerik = f.read()

    return icerik


def yukle_csv(dosya_yolu: str) -> list[dict]:
    """
    CSV dosyasını satır satır okur ve her satırı
    sütun başlıklarıyla eşleştirilmiş dict olarak döndürür.

    Neden dict listesi? → Chunk'lama aşamasında her satırın
    hangi sütuna ait olduğu bilgisi korunmuş oluyor.
    """
    yol = Path(dosya_yolu)
    if not yol.exists():
        raise FileNotFoundError(f"CSV dosyası bulunamadı: {dosya_yolu}")

    satirlar = []
    with open(yol, "r", encoding="utf-8") as f:
        okuyucu = csv.DictReader(f)
        for satir in okuyucu:
            satirlar.append(dict(satir))

    return satirlar


def yukle_json(dosya_yolu: str) -> list[dict]:
    """
    JSON güncelleme loglarını okur ve tarihe göre sıralar.
    En eski kayıt başta, en yeni sonda.
    """
    yol = Path(dosya_yolu)
    if not yol.exists():
        raise FileNotFoundError(f"JSON dosyası bulunamadı: {dosya_yolu}")

    with open(yol, "r", encoding="utf-8") as f:
        kayitlar = json.load(f)

    # tarihe göre sırala (kronolojik)
    kayitlar.sort(key=lambda k: datetime.strptime(k["tarih"], "%Y-%m-%d"))

    return kayitlar
