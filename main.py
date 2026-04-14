"""
main.py — Çoklu Kaynak RAG Sistemi Giriş Noktası

İki çalışma modu sunar:
  1. Demo  → Hazır sorularla pipeline'ı adım adım gösterir
  2. İnteraktif → Kullanıcı kendi sorularını sorar

Kullanım:
    python main.py

Ön koşul: .env dosyasında geçerli bir OPENAI_API_KEY tanımlı olmalıdır.
"""

import os
from dotenv import load_dotenv

# ortam değişkenlerini yükle
load_dotenv()

# API key kontrolü
if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "buraya_kendi_keyinizi_yazin":
    print("HATA: Lütfen .env dosyasına geçerli bir OPENAI_API_KEY yazın.")
    print("Örnek: OPENAI_API_KEY=sk-...")
    exit(1)

from src.rag_engine import RAGMotoru


def interaktif_mod(motor: RAGMotoru):
    """Kullanıcıdan sürekli soru alan interaktif mod."""
    print("\n" + "=" * 60)
    print("  ÇOKLU KAYNAK RAG — MÜŞTERİ DESTEK SİSTEMİ")
    print("  Çıkmak için 'q' veya 'çıkış' yazın.")
    print("=" * 60)

    while True:
        soru = input("\n🧑 Sorunuz: ").strip()

        if soru.lower() in ["q", "çıkış", "exit", "quit"]:
            print("\nGörüşmek üzere! 👋")
            break

        if not soru:
            print("Lütfen bir soru yazın.")
            continue

        cevap = motor.soru_sor(soru)
        print(f"\n🤖 Cevap:\n{cevap}")


def demo_sorulari_calistir(motor: RAGMotoru):
    """Örnek sorularla sistemi test eder."""
    test_sorulari = [
        "Pro paketinin aylık fiyatı nedir?",
        "Aboneliğimi iptal edersem paramı geri alabilir miyim?",
        "Şu anki Pro paket fiyatı nedir ve iptal edersem paramı ne zaman alırım?",
        "Enterprise paket erken fesih bedeli ne kadar?",
        "Verilerim ne kadar süre saklanıyor?",
        "Paketler arasındaki farklar neler?",
    ]

    print("\n" + "=" * 60)
    print("  DEMO MODU — Örnek Sorular")
    print("=" * 60)

    for soru in test_sorulari:
        cevap = motor.soru_sor(soru)
        print(f"\n🤖 Cevap:\n{cevap}")
        print(f"\n{'—' * 60}")


if __name__ == "__main__":
    motor = RAGMotoru(veri_dizini="./data")

    print("\nMod seçin:")
    print("  1 — Demo (örnek sorularla test)")
    print("  2 — İnteraktif (kendi sorularınızı sorun)")

    secim = input("\nSeçiminiz (1/2): ").strip()

    if secim == "1":
        demo_sorulari_calistir(motor)
    else:
        interaktif_mod(motor)
