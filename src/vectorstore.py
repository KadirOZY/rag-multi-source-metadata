"""
vectorstore.py — ChromaDB Vektör Mağazası

Tüm chunk'ları embed edip ChromaDB'ye yazar.
Metadata filtreleme desteği ile kaynak bazlı arama yapılabilir.
"""

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document

# ChromaDB telemetry uyarılarını kapat
import chromadb
from chromadb.config import Settings as ChromaSettings


# persist dizini — veritabanı burada tutulur
CHROMA_DIZIN = "./chroma_db"
KOLEKSIYON_ADI = "bulutforce_bilgi_bankasi"


def vektor_db_olustur(chunklar: list[Document]) -> Chroma:
    """
    Verilen chunk listesini embed edip ChromaDB'ye yazar.
    Her çalıştırmada sıfırdan oluşturur (veri güncelliği için).
    """
    embedding = OpenAIEmbeddings(model="text-embedding-3-small")

    # mevcut DB varsa temizle (dinamik güncelleme için)
    import shutil, os

    if os.path.exists(CHROMA_DIZIN):
        shutil.rmtree(CHROMA_DIZIN)

    vektor_db = Chroma.from_documents(
        documents=chunklar,
        embedding=embedding,
        collection_name=KOLEKSIYON_ADI,
        persist_directory=CHROMA_DIZIN,
        client_settings=ChromaSettings(anonymized_telemetry=False),
    )

    print(f"[VektörDB] {len(chunklar)} chunk başarıyla indexlendi.")
    return vektor_db


def arama_yap(
    vektor_db: Chroma, sorgu: str, k: int = 5, filtre: dict = None
) -> list[Document]:
    """
    Vektör veritabanında semantic arama yapar.

    Parametreler:
        sorgu   : Kullanıcının doğal dildeki sorusu
        k       : Döndürülecek en alakalı chunk sayısı
        filtre  : Metadata bazlı filtreleme (ör: {"tip": "fiyat_tablosu"})
    """
    if filtre:
        sonuclar = vektor_db.similarity_search(sorgu, k=k, filter=filtre)
    else:
        sonuclar = vektor_db.similarity_search(sorgu, k=k)

    return sonuclar
