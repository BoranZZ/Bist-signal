"""
BIST günlük sinyal taraması.
Akış: veri çek -> sinyal + oran -> risk/lot hesapla -> AL+ işaretle
-> index.html üret -> (yeni AL) izleme listesi için Telegram.
"""
import json
import math
import os
import time

import pandas as pd
import yfinance as yf

from sinyal import analiz_et
from pano import pano_uret

# ================== AYARLAR ==================
IZLEME_LISTEM = [
    "TUPRS", "THYAO", "ASELS", "PGSUS", "SASA", "FROTO", "KONTR", "ASTOR",
    # "TERA", "TEHOL",  # kodlarını teyit edip aç
]
BIST30 = [
    "AKBNK", "ASELS", "ASTOR", "BIMAS", "EKGYO", "ENKAI", "EREGL", "FROTO",
    "GARAN", "GUBRF", "HEKTS", "ISCTR", "KCHOL", "KOZAL", "KRDMD", "PETKM",
    "PGSUS", "SAHOL", "SASA", "SISE", "TCELL", "THYAO", "TOASO", "TTKOM",
    "TUPRS", "YKBNK", "MGROS", "OYAKC", "KONTR",
]

PORTFOY_TL = 100_000      # toplam portföyün (lot önerisi için) — kendi rakamını yaz
RISK_YUZDESI = 1.0        # bir işlemde riske atacağın portföy yüzdesi
ASIRI_ISLEM_ESIGI = 6     # bir günde bundan çok yeni AL çıkarsa "seçici ol" uyarısı
SADECE_IZLEME_ALARM = True  # Telegram sadece IZLEME_LISTEM için; pano yine hepsini gösterir
# ============================================

KODLAR = sorted(set(IZLEME_LISTEM + BIST30))
DURUM_DOSYASI = "durum.json"


def veri_cek(kodlar):
    tickers = [k + ".IS" for k in kodlar]
    print(f"{len(tickers)} hisse indiriliyor...")
    return yf.download(tickers, period="2y", interval="1d", group_by="ticker",
                       auto_adjust=True, progress=False, threads=True)


def oran_cek(kod):
    try:
        info = yf.Ticker(kod + ".IS").info
        fk, pddd = info.get("trailingPE"), info.get("priceToBook")
        return (round(fk, 1) if isinstance(fk, (int, float)) and fk > 0 else None,
                round(pddd, 2) if isinstance(pddd, (int, float)) and pddd > 0 else None)
    except Exception as e:
        print(f"  oran alınamadı {kod}: {e}")
        return (None, None)


def lot_oner(fiyat, stop):
    if not fiyat or not stop or fiyat <= stop:
        return None
    risk_tl = PORTFOY_TL * RISK_YUZDESI / 100
    return int(max(0, math.floor(risk_tl / (fiyat - stop))))


def telegram_gonder(mesaj):
    token, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("Telegram bilgisi yok, bildirim atlandı.")
        return
    import urllib.request, urllib.parse
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    veri = urllib.parse.urlencode({"chat_id": chat, "text": mesaj,
                                   "parse_mode": "HTML", "disable_web_page_preview": "true"}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=veri), timeout=20) as r:
            print("Telegram gönderildi:", r.status)
    except Exception as e:
        print("Telegram hatası:", e)


def onceki_al():
    try:
        with open(DURUM_DOSYASI, encoding="utf-8") as f:
            return set(json.load(f).get("al", []))
    except Exception:
        return set()


def main():
    data = veri_cek(KODLAR)
    sonuclar = []
    for kod in KODLAR:
        try:
            df = data[kod + ".IS"] if len(KODLAR) > 1 else data
            df = df.dropna(subset=["Close"])
            if df.empty:
                continue
            a = analiz_et(df)
            if not a:
                continue
            a["kod"] = kod
            a["fk"], a["pddd"] = oran_cek(kod)
            a["lot"] = lot_oner(a["fiyat"], a["stop"])
            sonuclar.append(a)
            time.sleep(0.4)
        except Exception as e:
            print(f"Atlandı {kod}: {e}")

    if not sonuclar:
        print("Hiç sonuç yok.")
        return

    # --- Teknik + temel birlikte: AL+ (güçlü) işaretle ---
    fk_list = sorted(s["fk"] for s in sonuclar if s.get("fk"))
    pddd_list = sorted(s["pddd"] for s in sonuclar if s.get("pddd"))
    fk_med = fk_list[len(fk_list) // 2] if fk_list else None
    pddd_med = pddd_list[len(pddd_list) // 2] if pddd_list else None
    for s in sonuclar:
        s["guclu"] = bool(
            s["sinyal"] == "AL" and s.get("fk") and s.get("pddd")
            and fk_med and pddd_med and s["fk"] <= fk_med and s["pddd"] <= pddd_med
        )

    # --- Yeni AL sinyalleri ---
    bugun_al = [s for s in sonuclar if s["sinyal"] == "AL"]
    bugun_kod = {s["kod"] for s in bugun_al}
    onceki = onceki_al()
    yeni_al = [s for s in bugun_al if s["kod"] not in onceki]

    # --- Aşırı işlem uyarısı ---
    uyari = None
    if len(yeni_al) > ASIRI_ISLEM_ESIGI:
        uyari = (f"Bugün {len(yeni_al)} yeni AL sinyali var — bu çok. Hepsini almaya çalışma; "
                 f"en yüksek puanlı / AL+ olan birkaçına odaklan, aşırı işlem komisyonda eritir.")

    # --- Pano ---
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(pano_uret(sonuclar, ornek=False, uyari=uyari))
    print(f"index.html yazıldı ({len(sonuclar)} hisse, {len(bugun_al)} AL).")

    # --- Telegram: sadece izleme listesi (ayar açıksa) ---
    telegram_al = yeni_al
    if SADECE_IZLEME_ALARM:
        telegram_al = [s for s in yeni_al if s["kod"] in IZLEME_LISTEM]

    if telegram_al:
        tarih = pd.Timestamp.now(tz="Europe/Istanbul").strftime("%d.%m.%Y")
        satir = []
        for s in sorted(telegram_al, key=lambda x: (not x["guclu"], -x["puan"])):
            yildiz = " ★AL+" if s["guclu"] else ""
            fk = f"F/K {s['fk']}" if s.get("fk") else "F/K —"
            lot = f", öneri {s['lot']} lot" if s.get("lot") else ""
            satir.append(f"🟢 <b>{s['kod']}</b>{yildiz}  {s['fiyat']} TL  ({fk}, RSI {s['rsi']})\n"
                         f"     stop {s['stop']} TL{lot}")
        mesaj = (f"📊 <b>Yeni AL sinyali (izleme listen)</b> — {tarih}\n\n" + "\n".join(satir))
        if uyari:
            mesaj += f"\n\n⚠️ {uyari}"
        mesaj += "\n\n<i>Yatırım tavsiyesi değildir. Sinyal, karar değildir.</i>"
        telegram_gonder(mesaj)
    else:
        print("İzleme listende yeni AL yok, Telegram sessiz.")

    with open(DURUM_DOSYASI, "w", encoding="utf-8") as f:
        json.dump({"al": sorted(bugun_kod)}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
