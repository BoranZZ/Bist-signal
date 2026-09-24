# -*- coding: utf-8 -*-
"""
BIST sinyal taraması — BIST100, ~15 dk'da bir güncellenir.
Akış: fiyat çek -> sinyal + (günlük önbellekli) oran -> risk/lot -> AL+ -> yorum
-> index.html -> (yeni AL, izleme listesi) Telegram.
"""
import json, math, os, time
import pandas as pd
import yfinance as yf
from sinyal import analiz_et
from pano import pano_uret, gecmis_uret

# ================== AYARLAR ==================
IZLEME_LISTEM = ["TUPRS","THYAO","ASELS","PGSUS","SASA","FROTO","KONTR","ASTOR"]

BIST100 = [
 "AEFES","AGHOL","AKBNK","AKSA","AKSEN","ALARK","ALFAS","ARCLK","ASELS","ASTOR",
 "BERA","BIMAS","BRSAN","BRYAT","BUCIM","CCOLA","CIMSA","DOAS","DOHOL","ECILC",
 "EGEEN","EKGYO","ENJSA","ENKAI","EREGL","EUPWR","FROTO","GARAN","GESAN","GUBRF",
 "HALKB","HEKTS","ISCTR","ISMEN","ISGYO","KARSN","KCHOL","KLSER","KONTR","KONYA",
 "KORDS","KOZAA","KOZAL","KRDMD","MAVI","MGROS","MIATK","ODAS","OTKAR","OYAKC",
 "PETKM","PGSUS","QUAGR","SAHOL","SASA","SISE","SKBNK","SMRTG","SOKM","TAVHL",
 "TCELL","THYAO","TKFEN","TOASO","TSKB","TTKOM","TTRAK","TUKAS","TUPRS","ULKER",
 "VAKBN","VESTL","YKBNK","ZOREN","AGROT","CANTE","CWENE","GENIL","IPEKE","KAYSE",
 "KLKIM","PAPIL","REEDR","TABGD","YEOTK","BINHO","CVKMD","EUREN","GWIND","IZENR",
 "KMPUR","MPARK","OBAMS","PENTA","RGYAS","SDTTR","TERA","ULUUN","VESBE","ANSGR",
]

PORTFOY_TL = 100_000
RISK_YUZDESI = 1.0
ASIRI_ISLEM_ESIGI = 8
SADECE_IZLEME_ALARM = True
# ============================================

KODLAR = sorted(set(IZLEME_LISTEM + BIST100))
DURUM = "durum.json"
ORAN_CACHE = "oranlar.json"


def veri_cek(kodlar):
    tickers = [k + ".IS" for k in kodlar]
    print(f"{len(tickers)} hisse indiriliyor...")
    return yf.download(tickers, period="1y", interval="1d", group_by="ticker",
                       auto_adjust=True, progress=False, threads=True)


def oran_cek_tek(kod):
    try:
        info = yf.Ticker(kod + ".IS").info
        fk, pddd, fav = info.get("trailingPE"), info.get("priceToBook"), info.get("enterpriseToEbitda")
        return [round(fk, 1) if isinstance(fk, (int, float)) and fk > 0 else None,
                round(pddd, 2) if isinstance(pddd, (int, float)) and pddd > 0 else None,
                round(fav, 1) if isinstance(fav, (int, float)) and fav > 0 else None]
    except Exception:
        return [None, None, None]


def oranlari_al(kodlar):
    """Oranlar yavaş değişir; günde bir kez çekip önbelleğe alırız (intraday hızlı kalsın)."""
    bugun = pd.Timestamp.now(tz="Europe/Istanbul").strftime("%Y-%m-%d")
    try:
        with open(ORAN_CACHE, encoding="utf-8") as f:
            c = json.load(f)
        if c.get("tarih") == bugun:
            print("Oranlar önbellekten.")
            return c["veri"]
    except Exception:
        pass
    print("Oranlar güncelleniyor (günde 1 kez)...")
    veri = {}
    for k in kodlar:
        veri[k] = oran_cek_tek(k)
        time.sleep(0.2)
    with open(ORAN_CACHE, "w", encoding="utf-8") as f:
        json.dump({"tarih": bugun, "veri": veri}, f, ensure_ascii=False)
    return veri


def lot_oner(fiyat, stop):
    if not fiyat or not stop or fiyat <= stop:
        return None
    return int(max(0, math.floor((PORTFOY_TL * RISK_YUZDESI / 100) / (fiyat - stop))))


def yorum_uret(s, fk_med, pddd_med):
    p = []
    sn = s["sinyal"]
    if sn == "AL":
        p.append("Teknik tablo olumlu: " + ", ".join(s["gerekce"][:2]).lower() + ".")
    elif sn == "SAT":
        p.append("Teknik tablo zayıf; trend ve momentum aşağı yönlü, alım için acele etme.")
    else:
        p.append("Kararsız bölge: bazı göstergeler olumlu ama AL eşiğine ulaşmıyor; net sinyal yok.")
    if s.get("rsi") is not None:
        r = s["rsi"]
        if r > 75:
            p.append(f"RSI {r:.0f} ile aşırı alımda — kısa vadede geri çekilme riski var.")
        elif r < 30:
            p.append(f"RSI {r:.0f} ile aşırı satımda — tepki gelebilir ama trend teyidi ister.")
    if s.get("fk") and fk_med:
        p.append(f"F/K {s['fk']} " + ("grup medyanının altında, görece ucuz." if s["fk"] < fk_med
                 else "grup medyanının üstünde, görece pahalı.") + " (Enflasyonda yanıltıcı olabilir.)")
    if sn == "AL" and s.get("stop"):
        p.append(f"Alırsan stop olarak {s['stop']} TL mantıklı bir başlangıç; altına inerse çık.")
    if s.get("guclu"):
        p.insert(0, "★ AL+: hem grafik hem değerleme olumlu — listenin öne çıkanı.")
    return " ".join(p)


def tg_gonder(msg):
    tok, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        print("Telegram bilgisi yok, atlandı.")
        return
    import urllib.request, urllib.parse
    u = f"https://api.telegram.org/bot{tok}/sendMessage"
    d = urllib.parse.urlencode({"chat_id": chat, "text": msg, "parse_mode": "HTML",
                                "disable_web_page_preview": "true"}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(u, data=d), timeout=20) as r:
            print("Telegram:", r.status)
    except Exception as e:
        print("Telegram hatası:", e)


def onceki_al():
    try:
        with open(DURUM, encoding="utf-8") as f:
            return set(json.load(f).get("al", []))
    except Exception:
        return set()


GECMIS = "gecmis.json"
PORTFOY = "portoy.json"


def portfoy_yukle():
    try:
        with open(PORTFOY, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def portfoy_hesapla(portfoy, by_kod):
    cikti = []
    for p in portfoy:
        kod = p.get("kod")
        s = by_kod.get(kod, {})
        fiyat = s.get("fiyat")
        maliyet = p.get("maliyet")
        adet = p.get("adet")
        kar_y = round((fiyat / maliyet - 1) * 100, 1) if (fiyat and maliyet) else None
        kar_tl = round((fiyat - maliyet) * adet, 0) if (fiyat and maliyet and adet) else None
        cikti.append({"kod": kod, "adet": adet, "maliyet": maliyet, "fiyat": fiyat,
                      "kar_yuzde": kar_y, "kar_tl": kar_tl,
                      "sinyal": s.get("sinyal", "—"), "stop": s.get("stop")})
    return cikti


def _kapa(r, fiyat, sebep, bugun):
    r["durum"] = "kapalı"
    r["cikis_tarih"] = bugun
    r["cikis_fiyat"] = fiyat
    r["sonuc"] = round((fiyat / r["giris_fiyat"] - 1) * 100, 1)
    r["sebep"] = sebep


def gecmis_guncelle(by_kod, bugun):
    try:
        with open(GECMIS, encoding="utf-8") as f:
            kayitlar = json.load(f).get("kayitlar", [])
    except Exception:
        kayitlar = []

    acik_basta = {r["kod"] for r in kayitlar if r["durum"] == "açık"}
    for r in kayitlar:
        if r["durum"] != "açık":
            continue
        s = by_kod.get(r["kod"])
        if not s or not s.get("fiyat"):
            continue
        r["guncel"] = s["fiyat"]
        r["anlik"] = round((s["fiyat"] / r["giris_fiyat"] - 1) * 100, 1)
        if s["fiyat"] <= r["stop"]:
            _kapa(r, s["fiyat"], "stop", bugun)
        elif s["sinyal"] == "SAT":
            _kapa(r, s["fiyat"], "sinyal", bugun)

    for kod, s in by_kod.items():
        if s["sinyal"] == "AL" and kod not in acik_basta and s.get("fiyat"):
            kayitlar.append({"kod": kod, "giris_tarih": bugun, "giris_fiyat": s["fiyat"],
                             "stop": s["stop"], "durum": "açık",
                             "guncel": s["fiyat"], "anlik": 0.0})

    with open(GECMIS, "w", encoding="utf-8") as f:
        json.dump({"kayitlar": kayitlar}, f, ensure_ascii=False, indent=2)

    acik = [r for r in kayitlar if r["durum"] == "açık"]
    kapali = [r for r in kayitlar if r["durum"] == "kapalı"]
    if kapali:
        sonuclar_ = [r["sonuc"] for r in kapali if r.get("sonuc") is not None]
        isabet = round(sum(1 for x in sonuclar_ if x > 0) / len(sonuclar_) * 100, 1) if sonuclar_ else 0
        ort = round(sum(sonuclar_) / len(sonuclar_), 1) if sonuclar_ else 0
    else:
        isabet = ort = 0
    ozet = {"isabet": isabet, "kapanan": len(kapali), "ort": ort, "acik": len(acik)}
    return acik, kapali, ozet


def main():
    data = veri_cek(KODLAR)
    oranlar = oranlari_al(KODLAR)
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
            o = oranlar.get(kod, [None, None, None])
            a["fk"] = o[0] if len(o) > 0 else None
            a["pddd"] = o[1] if len(o) > 1 else None
            a["favok"] = o[2] if len(o) > 2 else None
            a["lot"] = lot_oner(a["fiyat"], a["giris_stop"])
            sonuclar.append(a)
        except Exception as e:
            print(f"Atlandı {kod}: {e}")

    if not sonuclar:
        print("Sonuç yok.")
        return

    fk_l = sorted(s["fk"] for s in sonuclar if s.get("fk"))
    pd_l = sorted(s["pddd"] for s in sonuclar if s.get("pddd"))
    fk_med = fk_l[len(fk_l) // 2] if fk_l else None
    pd_med = pd_l[len(pd_l) // 2] if pd_l else None
    for s in sonuclar:
        s["guclu"] = bool(s["sinyal"] == "AL" and s.get("fk") and s.get("pddd")
                          and fk_med and pd_med and s["fk"] <= fk_med and s["pddd"] <= pd_med)
        s["yorum"] = yorum_uret(s, fk_med, pd_med)

    bugun_al = [s for s in sonuclar if s["sinyal"] == "AL"]
    onceki = onceki_al()
    yeni = [s for s in bugun_al if s["kod"] not in onceki]

    uyari = None
    if len(yeni) > ASIRI_ISLEM_ESIGI:
        uyari = (f"Bugün {len(yeni)} yeni AL var — çok fazla. Hepsini alma; en yüksek puanlı/AL+ "
                 f"birkaçına odaklan, aşırı işlem komisyonda eritir.")

    by_kod = {s["kod"]: s for s in sonuclar}
    bugun_iso = pd.Timestamp.now(tz="Europe/Istanbul").strftime("%Y-%m-%d")

    # Sinyal geçmişi (canlı karne): yeni AL'leri kaydet, açıkları stop/SAT ile kapat
    acik, kapali, karne = gecmis_guncelle(by_kod, bugun_iso)
    with open("gecmis.html", "w", encoding="utf-8") as f:
        f.write(gecmis_uret(acik, kapali, karne))

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(pano_uret(sonuclar, ornek=False, uyari=uyari))
    print(f"index.html: {len(sonuclar)} hisse, {len(bugun_al)} AL, {len(yeni)} yeni | "
          f"karne: {karne['kapanan']} kapanan, {karne['acik']} açık.")

    tg = [s for s in yeni if (not SADECE_IZLEME_ALARM or s["kod"] in IZLEME_LISTEM)]
    if tg:
        tarih = pd.Timestamp.now(tz="Europe/Istanbul").strftime("%d.%m.%Y %H:%M")
        satir = []
        for s in sorted(tg, key=lambda x: (not x["guclu"], -x["puan"])):
            y = " ★AL+" if s["guclu"] else ""
            fk = f"F/K {s['fk']}" if s.get("fk") else "F/K —"
            lot = f", öneri {s['lot']} lot" if s.get("lot") else ""
            satir.append(f"🟢 <b>{s['kod']}</b>{y}  {s['fiyat']} TL  ({fk}, RSI {s['rsi']})\n     stop {s['stop']} TL{lot}")
        msg = f"📊 <b>Yeni AL (izleme listen)</b> — {tarih}\n\n" + "\n".join(satir)
        if uyari:
            msg += f"\n\n⚠️ {uyari}"
        msg += "\n\n<i>Yatırım tavsiyesi değildir. Sinyal, karar değildir.</i>"
        tg_gonder(msg)
    else:
        print("İzleme listende yeni AL yok, Telegram sessiz.")

    with open(DURUM, "w", encoding="utf-8") as f:
        json.dump({"al": sorted(s["kod"] for s in bugun_al)}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
