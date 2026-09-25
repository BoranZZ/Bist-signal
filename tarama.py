# -*- coding: utf-8 -*-
"""
BIST sinyal taraması — BIST100, ~15 dk'da bir güncellenir.
Akış: fiyat çek -> sinyal + (günlük önbellekli) oran -> risk/lot -> AL+ -> yorum
-> index.html -> Telegram (tüm hisselerde yeni AL, portföyde yeni SAT).
"""
import json, math, os, time
import pandas as pd
import yfinance as yf
from sinyal import analiz_et
from pano import pano_uret, gecmis_uret

# ================== AYARLAR ==================
# BIST 100 bileşimi, 1 Ekim - 31 Aralık 2026 dönemi (Borsa İstanbul 3 ayda bir günceller)
BIST100 = [
 "AEFES","AGHOL","AHGAZ","AKBNK","AKCNS","AKFYE","AKSA","AKSEN","ALARK","ALBRK",
 "ALTNY","ANHYT","ANSGR","ARCLK","ASELS","ASTOR","AYGAZ","BERA","BIMAS","BINHO",
 "BRSAN","BRYAT","BSOKE","CANTE","CCOLA","CIMSA","CVKMD","CWENE","DOAS","DOHOL",
 "ECILC","ECZYT","EGEEN","EGGUB","EKGYO","ENERY","ENJSA","ENKAI","ENTRA","EREGL",
 "EUREN","FENER","FROTO","GARAN","GLRMK","GLYHO","GRSEL","GUBRF","GWIND","HALKB",
 "HEKTS","ISCTR","ISDMR","ISMEN","KARSN","KATMR","KCAER","KCHOL","KORDS","KRDMD",
 "LMKDC","MAVI","MGROS","MPARK","OBAMS","ODAS","OTKAR","OYAKC","PAHOL","PETKM",
 "PGSUS","RGYAS","RYSAS","SAHOL","SASA","SISE","SNGYO","SOKM","TABGD","TAVHL",
 "TCELL","TCKRC","THYAO","TKFEN","TOASO","TRALT","TRENJ","TRGYO","TRMET","TSKB",
 "TTKOM","TTRAK","TUKAS","TUPRS","TURSG","ULKER","VAKBN","VESTL","YKBNK","ZOREN",
]

# Endekste olmayan ama taramaya devam edilen hisseler (portföy/geçmiş kopmasın diye)
EK_HISSELER = [
 "AGROT","ALFAS","BUCIM","EUPWR","GENIL","GESAN","ISGYO","IZENR","KAYSE","KLKIM",
 "KLSER","KMPUR","KONTR","KONYA","MIATK","PAPIL","PENTA","QUAGR","REEDR","SDTTR",
 "SKBNK","SMRTG","TERA","ULUUN","VESBE","YEOTK",
]

PORTFOY_TL = 100_000
RISK_YUZDESI = 1.0
ASIRI_ISLEM_ESIGI = 8
PANO_URL = "https://boranzz.github.io/Bist-signal/"
# Telegram: tüm hisselerde yeni AL; SAT sadece portföydekiler (PORTFOY variable'ı, panodan otomatik yazılır).
# ============================================

KODLAR = sorted(set(BIST100 + EK_HISSELER))
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
    veri = {}
    try:
        with open(ORAN_CACHE, encoding="utf-8") as f:
            c = json.load(f)
        if c.get("tarih") == bugun:
            veri = c["veri"]
    except Exception:
        pass
    eksik = [k for k in kodlar if k not in veri]   # listeye yeni eklenen hisseler dahil
    if not eksik:
        print("Oranlar önbellekten.")
        return veri
    print(f"Oranlar güncelleniyor ({len(eksik)} hisse, günde 1 kez)...")
    for k in eksik:
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
    """Mesajı gönderir; başarılıysa True döner."""
    tok, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        print("Telegram bilgisi yok, atlandı. (GitHub > Settings > Secrets and variables > Actions: "
              "TELEGRAM_TOKEN ve TELEGRAM_CHAT_ID tanımlı mı?)")
        return False
    import urllib.request, urllib.parse, urllib.error
    u = f"https://api.telegram.org/bot{tok.strip()}/sendMessage"
    d = urllib.parse.urlencode({"chat_id": chat.strip(), "text": msg, "parse_mode": "HTML",
                                "disable_web_page_preview": "true"}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(u, data=d), timeout=20) as r:
            print("Telegram:", r.status)
            return True
    except urllib.error.HTTPError as e:
        # Telegram hatanın sebebini gövdede yazar (ör. "chat not found", "Unauthorized")
        print("Telegram hatası:", e.code, e.read().decode("utf-8", "replace"))
    except Exception as e:
        print("Telegram hatası:", e)
    return False


def durum_oku():
    try:
        with open(DURUM, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


GECMIS = "gecmis.json"


def portfoy_yukle():
    """Portföy GitHub variable'ından (PORTFOY) gelir; pano her değişiklikte bu
    metni üretir. Aynı hisse birden çok girildiyse adetler toplanır, maliyet ağırlıklı ortalama olur.
    DİKKAT: Actions logları herkese açık — portföy içeriğini asla print etme."""
    ham = os.environ.get("PORTFOY", "").strip()
    if not ham:
        print("Portföy tanımlı değil (panoda 'Telegram'a bağla' yapılmamış).")
        return {}
    try:
        liste = json.loads(ham)
    except Exception:
        print("PORTFOY variable'ı okunamadı: metin bozuk. Panoda portföyü bir kez kaydet.")
        return {}
    pf = {}
    for p in liste:
        try:
            kod = str(p["kod"]).strip().upper()
            adet, mal = float(p["adet"]), float(p["maliyet"])
        except Exception:
            continue
        if adet <= 0 or mal <= 0:
            continue
        if kod in pf:
            a0, m0 = pf[kod]["adet"], pf[kod]["maliyet"]
            pf[kod] = {"adet": a0 + adet, "maliyet": (a0 * m0 + adet * mal) / (a0 + adet)}
        else:
            pf[kod] = {"adet": adet, "maliyet": mal}
    print(f"Portföy: {len(pf)} hisse.")
    return pf


def sinyal_degisimleri(sonuclar, son):
    """son: kod -> son 'kesin' sinyal (AL/SAT). NÖTR ara geçişleri sayılmaz: AL→NÖTR→AL tekrar
    mesaj atmaz (15 dk'lık taramada gidip gelen hisse spam yapmasın), AL→SAT→AL atar.
    Listeye yeni giren hisse ilk görüldüğünde mesaj atmaz."""
    yeni_al, yeni_sat = [], []
    for s in sonuclar:
        k, sn = s["kod"], s["sinyal"]
        if k not in son:
            son[k] = sn
        elif sn != "NÖTR" and son[k] != sn:
            (yeni_al if sn == "AL" else yeni_sat).append(s)
            son[k] = sn
    return yeni_al, yeni_sat


def _tl(x):
    return f"{'+' if x >= 0 else '−'}{abs(round(x)):,.0f}".replace(",", ".") + " TL"


def portfoy_notu(s, p, stop_goster=True):
    f, m, a = s["fiyat"], p["maliyet"], p["adet"]
    t = f"Portföyünde {a:g} adet, maliyet {m:.2f} → şu an %{(f / m - 1) * 100:+.1f} ({_tl((f - m) * a)})"
    if stop_goster and s.get("stop"):
        sk = (s["stop"] - m) * a
        t += f"\n     Stop {s['stop']} TL'ye inerse: {_tl(sk)}" + (" (yine kârda çıkarsın)" if sk >= 0 else "")
    return t


MAX_AL_SATIR = 20  # Telegram mesajı 4096 karakterle sınırlı


def telegram_mesaji(yeni_al, yeni_sat, pf, uyari):
    tarih = pd.Timestamp.now(tz="Europe/Istanbul").strftime("%d.%m.%Y %H:%M")
    parca = [f"📊 <b>BIST Sinyal</b> — {tarih}"]
    if yeni_al:
        sirali = sorted(yeni_al, key=lambda x: (x["kod"] not in pf, not x["guclu"], -x["puan"]))
        gosterilen = [s for s in sirali if s["kod"] in pf] + [s for s in sirali if s["kod"] not in pf][:MAX_AL_SATIR]
        satir = []
        for s in gosterilen:
            isaret = "❗" if s["kod"] in pf else "🟢"
            y = " ★AL+" if s["guclu"] else ""
            fk = f"F/K {s['fk']}" if s.get("fk") else "F/K —"
            lot = f", öneri {s['lot']} lot" if s.get("lot") else ""
            t = f"{isaret} <b>{s['kod']}</b>{y}  {s['fiyat']} TL  ({fk}, RSI {s['rsi']})\n     stop {s['stop']} TL{lot}"
            if s["kod"] in pf:
                t += "\n     " + portfoy_notu(s, pf[s["kod"]])
            satir.append(t)
        kalan = len(sirali) - len(gosterilen)
        if kalan:
            satir.append(f"…ve {kalan} hisse daha (panoya bak)")
        parca.append(f"<b>Yeni AL ({len(yeni_al)})</b>\n" + "\n".join(satir))
    if yeni_sat:
        satir = []
        for s in yeni_sat:
            t = (f"❗ <b>{s['kod']}</b>  {s['fiyat']} TL  (RSI {s['rsi']})\n     "
                 + portfoy_notu(s, pf[s["kod"]], stop_goster=False)
                 + "\n     Sistemin çıkış kuralı: sinyal SAT'a dönünce çık — gözden geçir.")
            satir.append(t)
        parca.append("🔴 <b>Portföyünde SAT'a dönenler</b>\n" + "\n".join(satir))
    if uyari:
        parca.append(f"⚠️ {uyari}")
    parca.append(f"<a href=\"{PANO_URL}\">Panoyu aç</a>\n<i>Yatırım tavsiyesi değildir. Sinyal, karar değildir.</i>")
    return "\n\n".join(parca)


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
    if os.environ.get("TELEGRAM_TEST") == "true":   # Actions > Run workflow > "Telegram test" kutusu
        zaman = pd.Timestamp.now(tz="Europe/Istanbul").strftime("%d.%m.%Y %H:%M")
        if not tg_gonder(f"✅ BIST Sinyal: Telegram bağlantısı çalışıyor ({zaman})."):
            raise SystemExit("Telegram test mesajı gönderilemedi — yukarıdaki hataya bak.")

    pf = portfoy_yukle()
    disarida = [k for k in pf if k not in KODLAR]
    if disarida:   # kodları yazma: log herkese açık
        print(f"Portföyde tarama listesinde olmayan {len(disarida)} hisse var; takip için EK_HISSELER'e ekle.")

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
    durum = durum_oku()
    son = dict(durum.get("son", {}))
    yeni, yeni_sat = sinyal_degisimleri(sonuclar, son)
    yeni_sat = [s for s in yeni_sat if s["kod"] in pf]   # SAT mesajı sadece portföydekiler için

    uyari = None
    if len(yeni) > ASIRI_ISLEM_ESIGI:
        uyari = (f"Bu taramada {len(yeni)} yeni AL var — çok fazla. Hepsini alma; en yüksek puanlı/AL+ "
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

    if yeni or yeni_sat:
        print(f"Telegram: {len(yeni)} yeni AL, {len(yeni_sat)} portföy SAT.")
        tg_gonder(telegram_mesaji(yeni, yeni_sat, pf, uyari))
    else:
        print("Yeni AL / portföyde yeni SAT yok, Telegram sessiz.")

    with open(DURUM, "w", encoding="utf-8") as f:
        json.dump({"al": sorted(s["kod"] for s in bugun_al), "son": dict(sorted(son.items()))},
                  f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
