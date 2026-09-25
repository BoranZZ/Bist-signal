# -*- coding: utf-8 -*-
"""
BIST sinyal taraması — BIST100, ~15 dk'da bir güncellenir.
Akış: fiyat çek -> sinyal + (günlük önbellekli) oran -> risk/lot -> AL+ -> yorum
-> index.html -> Telegram (tüm hisselerde yeni AL, portföyde yeni SAT).
"""
import json, math, os, time
import pandas as pd
import yfinance as yf
from sinyal import analiz_et, TABAN_GETIRI, TABAN_GUN
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

# Endekste olmayan ama taramaya devam edilen hisseler (portföy/geçmiş kopmasın diye).
# 2026-09: fon krizinde çöken şişirilmiş hisseler (TERA, SMRTG, GENIL, MIATK — son 3 haftada
# 5+ kez taban) çıkarıldı. Faiz yüzünden düşen eski büyükler (ör. KONTR) bilerek listede.
EK_HISSELER = [
 "AGROT","ALFAS","BUCIM","EUPWR","GESAN","ISGYO","IZENR","KAYSE","KLKIM",
 "KLSER","KMPUR","KONTR","KONYA","PAPIL","PENTA","QUAGR","REEDR","SDTTR",
 "SKBNK","ULUUN","VESBE","YEOTK",
]

# Son 12 ayın halka arzları: kod -> (borsada işlem başlangıcı, halka arz fiyatı TL). Kaynak: halkarz.com
# (ENPRA kısmi bölünmeyle geldi, arz fiyatı yok). Yeni arzlar sinyal için ~60 işlem günü geçmiş ister.
HALKA_ARZ = {
 "ECOGR": ("2025-11-03", 10.40), "VAKFA": ("2025-11-20", 14.20), "PAHOL": ("2025-11-21", 1.50),
 "ZERGY": ("2025-12-18", 13.00), "ARFYE": ("2026-01-05", 19.50), "MEYSU": ("2026-01-13", 7.50),
 "FRMPL": ("2026-01-15", 30.24), "ZGYO": ("2026-01-16", 9.77), "UCAYM": ("2026-01-22", 18.00),
 "NETCD": ("2026-02-05", 46.00), "AKHAN": ("2026-02-06", 21.50), "BESTE": ("2026-02-11", 14.70),
 "ATATR": ("2026-02-19", 11.20), "EMPAE": ("2026-02-26", 22.00), "SVGYO": ("2026-03-06", 3.64),
 "GENKM": ("2026-03-06", 11.00), "LXGYO": ("2026-03-10", 12.05), "MCARD": ("2026-03-11", 80.00),
 "AAGYO": ("2026-04-09", 21.10), "ENPRA": ("2026-04-07", None), "EKDMR": ("2026-05-22", 45.00),
 "BETAE": ("2026-07-01", 40.00), "SOHOE": ("2026-07-06", 15.00), "ORZAX": ("2026-07-07", 69.00),
 "GOLDA": ("2026-07-08", 9.20), "EKIM": ("2026-07-09", 30.26), "ISVEA": ("2026-07-10", 20.90),
 "SSAAT": ("2026-07-16", 56.00), "SARAE": ("2026-07-17", 70.00), "METEN": ("2026-07-28", 20.00),
 "ALBTN": ("2026-07-29", 38.60), "MASFN": ("2026-07-30", 45.68), "KARCL": ("2026-07-31", 35.00),
 "QUICK": ("2026-08-06", 76.60), "CITAS": ("2026-08-18", 73.70), "VEYAS": ("2026-08-20", 136.00),
 "TKNKA": ("2026-08-20", 85.40), "KPEKS": ("2026-08-21", 94.00), "INTET": ("2026-09-01", 53.60),
 "BKRGY": ("2026-09-02", 12.93), "NETGL": ("2026-09-17", 25.52),
}

PORTFOY_TL = 100_000
RISK_YUZDESI = 1.0
ASIRI_ISLEM_ESIGI = 8
PANO_URL = "https://boranzz.github.io/Bist-signal/"
# Telegram: tüm hisselerde yeni AL; SAT sadece portföydekiler (PORTFOY variable'ı, panodan otomatik yazılır).
# ============================================

KODLAR = sorted(set(BIST100 + EK_HISSELER + list(HALKA_ARZ)))
DURUM = "durum.json"
ORAN_CACHE = "oranlar.json"
ENDEKS = "XU100"
# Kapanış: sürekli işlem 18:00'de biter, kapanış seansı ~18:10; Yahoo verisi ~15 dk gecikmeli -> kesin kapanış
# fiyatı ~18:25'te gelir. Kapanış sonrası işler (AL/SAT mesajları, günlük özet) 18:30'dan sonraki ilk taramada.
KAPANIS_DAKIKA = 18 * 60 + 30
# Gün içi yeni AL/SAT'ların ~%22'si kapanışta geçersiz oluyor (saatlik veriyle ölçüldü, 2026-09) ve backtest
# kapanış sinyali + ertesi gün açılış girişi varsayıyor: AL/SAT mesajları sadece kapanış sonrası taramada gider.
SADECE_KAPANIS_MESAJI = True
MIN_GUN = 60      # sinyal için gereken en az işlem günü (sinyal.analiz_et)


def veri_cek(kodlar):
    tickers = [k + ".IS" for k in kodlar] + [ENDEKS + ".IS"]
    print(f"{len(tickers)} hisse indiriliyor...")
    return yf.download(tickers, period="1y", interval="1d", group_by="ticker",
                       auto_adjust=True, progress=False, threads=True)


def piyasa_durumu(data):
    """Piyasa filtresi: BIST 100 50 günlük ortalamasının altındaysa 'zayıf' (backtest: bu dönemdeki AL'ler kötü)."""
    try:
        xu = data[ENDEKS + ".IS"]["Close"].dropna()
        ort = float(xu.rolling(50).mean().iloc[-1])
        son = float(xu.iloc[-1])
        return {"endeks": round(son), "ort50": round(ort), "zayif": son < ort, "fark": round((son / ort - 1) * 100, 1)}
    except Exception:
        return None


def arz_bilgisi(kod, df):
    """Son 12 ayın halka arzı ise: arz tarihi/fiyatı, arzdan beri getiri, taban serisi."""
    if kod not in HALKA_ARZ:
        return None
    tarih, arz_fiyat = HALKA_ARZ[kod]
    c = df["Close"]
    son = float(c.iloc[-1])
    return {"kod": kod, "tarih": tarih, "arz_fiyat": arz_fiyat, "fiyat": round(son, 2),
            "getiri": round((son / arz_fiyat - 1) * 100, 1) if arz_fiyat else None,
            "degisim": round((son / float(c.iloc[-2]) - 1) * 100, 2) if len(c) > 1 else None,
            "gun": len(c), "eksik_gun": max(0, MIN_GUN - len(c)),
            "taban15": int((c.pct_change().tail(TABAN_GUN) <= TABAN_GETIRI).sum())}


SEKTOR_TR = {
    "Industrials": "Sanayi", "Financial Services": "Finans", "Basic Materials": "Temel malzeme",
    "Consumer Defensive": "Temel tüketim", "Consumer Cyclical": "Döngüsel tüketim", "Utilities": "Enerji dağıtım/üretim",
    "Real Estate": "Gayrimenkul", "Technology": "Teknoloji", "Healthcare": "Sağlık",
    "Communication Services": "İletişim", "Energy": "Enerji (petrol/gaz)",
}
ENDUSTRI_TR = {
    "Banks - Regional": "Banka", "Conglomerates": "Holding", "Building Materials": "Çimento/yapı malz.",
    "Utilities - Renewable": "Yenilenebilir enerji", "Packaged Foods": "Gıda", "Steel": "Çelik/demir",
    "Engineering & Construction": "İnşaat/taahhüt", "Textile Manufacturing": "Tekstil", "REIT - Residential": "GYO (konut)",
    "REIT - Diversified": "GYO", "Building Products & Equipment": "Yapı ürünleri", "Utilities - Regulated Gas": "Doğalgaz dağıtım",
    "Utilities - Independent Power Producers": "Elektrik üretim", "Utilities - Regulated Electric": "Elektrik dağıtım",
    "Beverages - Non-Alcoholic": "İçecek", "Aerospace & Defense": "Savunma", "Furnishings, Fixtures & Appliances": "Beyaz eşya/mobilya",
    "Electrical Equipment & Parts": "Elektrik ekipmanı", "Specialty Chemicals": "Kimya", "Chemicals": "Kimya",
    "Agricultural Inputs": "Gübre/tarım girdisi", "Auto Manufacturers": "Otomotiv", "Auto Parts": "Otomotiv yan sanayi",
    "Farm & Heavy Construction Machinery": "Traktör/iş makinesi", "Airlines": "Havayolu", "Airports & Air Services": "Havalimanı",
    "Solar": "Güneş enerjisi", "Grocery Stores": "Perakende (market)", "Insurance - Diversified": "Sigorta",
    "Insurance - Life": "Hayat sigortası/emeklilik", "Insurance - Property & Casualty": "Sigorta", "Confectioners": "Şekerleme",
    "Other Industrial Metals & Mining": "Madencilik", "Gold": "Altın madenciliği", "Electronics & Computer Distribution": "Elektronik dağıtım",
    "Real Estate - Development": "Gayrimenkul geliştirme", "Telecom Services": "Telekom", "Travel Services": "Turizm",
    "Auto & Truck Dealerships": "Otomotiv bayi", "Drug Manufacturers - Specialty & Generic": "İlaç", "Marine Shipping": "Denizcilik",
    "Staffing & Employment Services": "İnsan kaynakları hizmet", "Railroads": "Demiryolu", "Information Technology Services": "BT hizmetleri",
    "Capital Markets": "Aracı kurum", "Apparel Retail": "Giyim perakende", "Software - Infrastructure": "Yazılım",
    "Software - Application": "Yazılım", "Medical Care Facilities": "Hastane", "Consumer Electronics": "Tüketici elektroniği",
    "Integrated Freight & Logistics": "Lojistik", "Department Stores": "Mağazacılık", "Luxury Goods": "Lüks ürün",
    "Restaurants": "Restoran", "Metal Fabrication": "Metal işleme", "Packaging & Containers": "Ambalaj",
    "Oil & Gas Refining & Marketing": "Rafineri", "Credit Services": "Finansman/faktoring", "Entertainment": "Spor/eğlence",
    "Real Estate Services": "Gayrimenkul hizmet",
}


def oran_cek_tek(kod):
    try:
        info = yf.Ticker(kod + ".IS").info
        fk, pddd, fav = info.get("trailingPE"), info.get("priceToBook"), info.get("enterpriseToEbitda")
        sek, end = info.get("sector"), info.get("industry")
        return [round(fk, 1) if isinstance(fk, (int, float)) and fk > 0 else None,
                round(pddd, 2) if isinstance(pddd, (int, float)) and pddd > 0 else None,
                round(fav, 1) if isinstance(fav, (int, float)) and fav > 0 else None,
                SEKTOR_TR.get(sek, sek), ENDUSTRI_TR.get(end, end)]
    except Exception:
        return [None, None, None, None, None]


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
    eksik = [k for k in kodlar if len(veri.get(k) or []) < 5]   # yeni hisseler + sektör bilgisi olmayan eski kayıtlar
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


TG_SINIR = 3900   # Telegram mesaj sınırı 4096 karakter; HTML etiketleri için pay bırak


def _parcala(msg, sinir=TG_SINIR):
    """Uzun mesajı paragraf (boş satır), gerekirse satır sınırlarından böler; etiketler satır içinde kapandığı için bozulmaz."""
    parcalar, cur = [], ""
    for blok in msg.split("\n\n"):
        satirlar = [blok] if len(blok) <= sinir else blok.split("\n")
        for s in satirlar:
            ayrac = "\n\n" if s is blok else "\n"
            if cur and len(cur) + len(ayrac) + len(s) > sinir:
                parcalar.append(cur)
                cur = s
            else:
                cur = cur + ayrac + s if cur else s
    if cur:
        parcalar.append(cur)
    return parcalar


def tg_gonder(msg):
    """Mesajı gönderir (4096 sınırını aşarsa parçalara böler); hepsi gittiyse True döner."""
    parcalar = _parcala(msg)
    if len(parcalar) > 1:
        return all([_tg_tek(p + f"\n\n<i>({i}/{len(parcalar)})</i>") for i, p in enumerate(parcalar, 1)])
    return _tg_tek(msg)


def _tg_tek(msg):
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
        uzun = bool(p.get("uzun"))
        if kod in pf:
            a0, m0 = pf[kod]["adet"], pf[kod]["maliyet"]
            pf[kod] = {"adet": a0 + adet, "maliyet": (a0 * m0 + adet * mal) / (a0 + adet),
                       "uzun": pf[kod]["uzun"] or uzun}
        else:
            pf[kod] = {"adet": adet, "maliyet": mal, "uzun": uzun}
    print(f"Portföy: {len(pf)} hisse.")
    return pf


def alarmlari_yukle():
    """Fiyat alarmları GitHub variable'ından (ALARMLAR) gelir; panoda hisse penceresinden kurulur.
    DİKKAT: loglar herkese açık — alarm içeriğini print etme."""
    try:
        liste = json.loads(os.environ.get("ALARMLAR", "").strip() or "[]")
    except Exception:
        print("ALARMLAR okunamadı.")
        return []
    temiz = []
    for a in liste if isinstance(liste, list) else []:
        try:
            kod, yon, fiyat = str(a["kod"]).strip().upper(), a["yon"], float(a["fiyat"])
        except Exception:
            continue
        if yon in ("ust", "alt") and fiyat > 0:
            temiz.append({"kod": kod, "yon": yon, "fiyat": fiyat})
    if temiz:
        print(f"Alarm: {len(temiz)} adet.")
    return temiz


def _alarm_anahtar(a):
    # durum.json herkese açık: alarmın kendisi değil, özeti (hash) saklanır
    import hashlib
    return hashlib.sha1(f"{a['kod']}|{a['yon']}|{a['fiyat']}".encode()).hexdigest()[:12]


def alarm_kontrol(alarmlar, by_kod, tetiklenen):
    """Koşulu sağlanan ve daha önce bildirilmemiş alarmlar. Silinen alarmların kaydı temizlenir (yeniden kurulursa tekrar çalışır)."""
    aktif = {_alarm_anahtar(a) for a in alarmlar}
    tetiklenen &= aktif
    yeni = []
    for a in alarmlar:
        s = by_kod.get(a["kod"])
        if not s or not s.get("fiyat"):
            continue
        tuttu = s["fiyat"] >= a["fiyat"] if a["yon"] == "ust" else s["fiyat"] <= a["fiyat"]
        k = _alarm_anahtar(a)
        if tuttu and k not in tetiklenen:
            tetiklenen.add(k)
            yeni.append((a, s))
    return yeni


def alarm_mesaji(liste):
    satir = [f"🔔 <b>{a['kod']}</b> {a['fiyat']:g} TL {'üstüne çıktı' if a['yon'] == 'ust' else 'altına indi'} — şu an {s['fiyat']} TL ({s['sinyal']})"
             for a, s in liste]
    return ("🔔 <b>Fiyat alarmı</b>\n" + "\n".join(satir) +
            f"\n\n<a href=\"{PANO_URL}\">Panoyu aç</a> · Alarm bir kez çalar; panodan silebilir ya da yenisini kurabilirsin.")


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


def _yz(x):
    return f"%{x:+.1f}".replace("+-", "-").replace("-", "−")


def karar_cizgisi(s):
    """Uzun vade pozisyon için karar çizgisi: fiyatın altındaki en yakın ana destek, tolerans kadar aşağısı."""
    sd = s.get("sd") or {}
    if not sd.get("destek"):
        return None
    return round(sd["destek"]["fiyat"] * (1 - sd["tol"] / 100), 2)


def pozisyon_plani(s, p):
    """Portföydeki pozisyon için çıkış (stop) ve hedefler. pano.py'deki pozPlan() ile aynı mantık.
    SAT'ta çıkış sebebi sinyalin kendisi: stop ve hedef verilmez. Uzun vade pozisyonda stop yerine
    karar çizgisi (ana destek) kullanılır; kısa vadeli sinyaller bilgi amaçlıdır."""
    f, m, a = s["fiyat"], p["maliyet"], p["adet"]
    plan = {"fiyat": f, "maliyet": m, "adet": a, "kz": (f - m) * a, "kz_y": (f / m - 1) * 100,
            "sat": s["sinyal"] == "SAT", "stop": None, "hedefler": [], "uzun": bool(p.get("uzun"))}
    if plan["uzun"]:
        plan["karar"] = karar_cizgisi(s)
        if plan["karar"]:
            plan["karar_uzak"] = (plan["karar"] / f - 1) * 100
            plan["karar_asildi"] = f < plan["karar"]
        dr = (s.get("sd") or {}).get("direnc")
        if dr and dr["fiyat"] > f:
            plan["hedefler"].append((dr["fiyat"], f"en yakın direnç ({dr['tarih']} tepesi)"))
        return plan
    if plan["sat"]:
        return plan
    # çıkış seviyesi: son AL'in başındaki sabit stop (backtest'teki kural); AL hiç yoksa güncel stop
    stop = s.get("al_stop") or s.get("stop")
    plan["stop"] = stop
    if stop:
        plan["stop_uzak"] = (stop / f - 1) * 100
        plan["stop_kz"] = (stop - m) * a
        plan["stop_asildi"] = f <= stop
    dr = (s.get("sd") or {}).get("direnc")
    if dr and dr["fiyat"] > f:
        plan["hedefler"].append((dr["fiyat"], f"en yakın direnç ({dr['tarih']} tepesi)"))
    if stop and stop < f:
        baz = m if stop < m else f            # stop maliyetin üstündeyse kâr kilitli; hedefi güncelden say
        h2 = round(baz + 2 * (baz - stop), 2)
        if h2 > f:
            plan["hedefler"].append((h2, "risk/ödül 2:1 referansı"))
    plan["hedefler"].sort()
    return plan


def plan_metni(s, p, girinti="     "):
    """Telegram için sade pozisyon açıklaması."""
    pl = pozisyon_plani(s, p)
    t = [f"Senin pozisyonun{' (uzun vade)' if pl['uzun'] else ''}: {pl['adet']:g} adet, maliyet {pl['maliyet']:.2f} → "
         f"şu an {_yz(pl['kz_y'])} ({_tl(pl['kz'])})"]
    if pl["uzun"]:
        if pl["sat"]:
            t.append("ℹ️ Kısa vadede trend aşağı (SAT) — uzun vade pozisyonun için bilgi.")
        if pl.get("karar"):
            if pl["karar_asildi"]:
                t.append(f"🧭 Fiyat karar çizgisinin ({pl['karar']} TL) ALTINDA — ana destek kırıldı, pozisyonu gözden geçirme noktası.")
            else:
                t.append(f"🧭 Karar çizgisi: {pl['karar']} TL — {_yz(pl['karar_uzak'])} aşağıda. "
                         f"Ana destek ({s['sd']['destek']['fiyat']} TL) bunun altında kapanışla kırılmış sayılır.")
        else:
            t.append("🧭 Fiyatın altında belirgin bir destek yok (son 120 günün dibinde).")
        for h, ne in pl["hedefler"]:
            t.append(f"🎯 İzleme: {h} TL — {ne}, {_yz((h / pl['fiyat'] - 1) * 100)} yukarıda")
        return ("\n" + girinti).join(t)
    if pl["sat"]:
        t.append("📍 Çıkış: SAT sinyali — kural SAT 2 gün üst üste gelince çıkmak.")
        sd = s.get("sd") or {}
        if sd.get("tepki") and sd.get("destek"):
            karar = round(sd["destek"]["fiyat"] * (1 - sd["tol"] / 100), 2)
            t.append(f"⚠️ Destekte ({sd['destek']['fiyat']} TL) tepki var, ama backtest'te SAT sürerken destekler "
                     f"~%68 oranında 20 günde kırıldı. Karar çizgisi: {karar} TL — altında kapanış = destek kırıldı.")
        return ("\n" + girinti).join(t)
    if pl.get("stop"):
        if pl["stop_asildi"]:
            t.append(f"📍 Fiyat çıkış seviyesinin ({pl['stop']} TL) ALTINDA — sistemin kuralına göre çıkış zamanı.")
        else:
            t.append(f"📍 Çıkış (stop): {pl['stop']} TL — {_yz(pl['stop_uzak'])} aşağıda. Buraya inerse: {_tl(pl['stop_kz'])}"
                     + (" (yine kârda)" if pl["stop_kz"] >= 0 else ""))
    for i, (h, ne) in enumerate(pl["hedefler"], 1):
        t.append(f"🎯 {i}. hedef: {h} TL — {ne}, {_yz((h / pl['fiyat'] - 1) * 100)} yukarıda")
    return ("\n" + girinti).join(t)


MAX_AL_SATIR = 20  # Telegram mesajı 4096 karakterle sınırlı


def _al_satiri(s, pf):
    isaret = "❗" if s["kod"] in pf else "🟢"
    y = " ★AL+" if s["guclu"] else ""
    h = f" 📈hacim {s['hacim_kat']}x" if s.get("hacim_teyit") else ""
    fk = f"F/K {s['fk']}" if s.get("fk") else "F/K —"
    lot = f", öneri {s['lot']} lot" if s.get("lot") else ""
    t = f"{isaret} <b>{s['kod']}</b>{y}{h}  {s['fiyat']} TL  ({fk}, RSI {s['rsi']})\n     stop {s['giris_stop']} TL{lot}"
    if s["kod"] in pf:
        t += "\n     " + plan_metni(s, pf[s["kod"]])
    return t


def telegram_mesaji(yeni_al, yeni_sat, sat_teyit, pf, uyari, piyasa=None, karar_kirilan=None):
    tarih = pd.Timestamp.now(tz="Europe/Istanbul").strftime("%d.%m.%Y %H:%M")
    parca = [f"📊 <b>BIST Sinyal</b> — {tarih}"]
    if yeni_al:
        sirali = sorted(yeni_al, key=lambda x: (x["kod"] not in pf, not x.get("hacim_teyit"), not x["guclu"], -x["puan"]))
        gosterilen = [s for s in sirali if s["kod"] in pf] + [s for s in sirali if s["kod"] not in pf][:MAX_AL_SATIR]
        satir = [_al_satiri(s, pf) for s in gosterilen]
        kalan = len(sirali) - len(gosterilen)
        if kalan:
            satir.append(f"…ve {kalan} hisse daha (panoya bak)")
        bas = f"<b>Yeni AL ({len(yeni_al)})</b>"
        if piyasa and piyasa.get("zayif"):
            bas += ("\n⚠️ <i>Piyasa zayıf: BIST 100 50 günlük ortalamasının altında. Backtest'te bu dönemlerde "
                    "gelen AL'ler belirgin şekilde daha kötü sonuç verdi — temkinli ol.</i>")
        parca.append(bas + "\n" + "\n".join(satir))
    if yeni_sat:
        satir = []
        for s in yeni_sat:
            if pf[s["kod"]].get("uzun"):
                satir.append(f"ℹ️ <b>{s['kod']}</b> (uzun vade)  {s['fiyat']} TL  (RSI {s['rsi']})\n     "
                             + plan_metni(s, pf[s["kod"]]))
                continue
            gun1 = (s.get("sinyal_gun") or 1) <= 1
            durum = ("⏳ <b>1. gün</b> — teyit için yarını bekle: yarın da SAT kalırsa çık." if gun1
                     else f"✅ <b>{s['sinyal_gun']} gündür SAT</b> — teyitli, kurala göre çıkış zamanı.")
            satir.append(f"❗ <b>{s['kod']}</b>  {s['fiyat']} TL  (RSI {s['rsi']})\n     {durum}\n     "
                         + plan_metni(s, pf[s["kod"]]))
        parca.append("🔴 <b>Portföyünde SAT'a dönenler</b>\n" + "\n".join(satir))
    if sat_teyit:
        satir = [f"❗ <b>{s['kod']}</b>  {s['fiyat']} TL — 2. gün de SAT: <b>teyitlendi</b>, kurala göre çıkış zamanı.\n     "
                 + plan_metni(s, pf[s["kod"]]) for s in sat_teyit]
        parca.append("✅ <b>SAT teyidi (2. gün)</b>\n" + "\n".join(satir))
    if karar_kirilan:
        satir = [f"🧭 <b>{s['kod']}</b> (uzun vade): kapanış {s['fiyat']} TL, karar çizgin <b>{seviye} TL</b>'nin altında — "
                 f"ana destek kırıldı, pozisyonu gözden geçirme noktası.\n     " + plan_metni(s, pf[s["kod"]])
                 for s, seviye in karar_kirilan]
        parca.append("🧭 <b>Karar çizgisi kırıldı</b>\n" + "\n".join(satir))
    if uyari:
        parca.append(f"⚠️ {uyari}")
    parca.append(f"<a href=\"{PANO_URL}\">Panoyu aç</a>\n<i>Yatırım tavsiyesi değildir. Sinyal, karar değildir.</i>")
    return "\n\n".join(parca)


YOGUNLASMA_ESIGI = 40   # portföy değerinin %'si tek endüstrideyse uyar


def sektor_dagilimi(pf, by):
    """Portföyün güncel değerine göre endüstri payları: [(ad, yüzde), ...] büyükten küçüğe. pano.py pfDagilim() ile aynı."""
    top, pay = 0.0, {}
    for kod, p in pf.items():
        s = by.get(kod)
        if not s or not s.get("fiyat"):
            continue
        deger = p["adet"] * s["fiyat"]
        ad = s.get("endustri") or s.get("sektor") or "Bilinmiyor"
        pay[ad] = pay.get(ad, 0) + deger
        top += deger
    return sorted(((a, v / top * 100) for a, v in pay.items()), key=lambda x: -x[1]) if top else []


def haftalik_ozet(sonuclar, pf, acik, kapali, simdi):
    """Cuma kapanıştan sonra: haftanın AL'leri, canlı karnenin haftası, portföyün haftalık değişimi."""
    pazartesi = (simdi - pd.Timedelta(days=simdi.weekday())).strftime("%Y-%m-%d")
    parca = [f"🗓 <b>Haftalık özet</b> — {pazartesi} haftası"]
    al = sorted((s for s in sonuclar if s["sinyal"] == "AL" and (s.get("sinyal_tarih") or "") >= pazartesi),
                key=lambda s: -(s.get("sinyal_degisim") or 0))
    if al:
        parca.append(f"<b>Bu hafta AL'e dönen ({len(al)})</b>: " + ", ".join(
            f"{s['kod']} ({_yz(s['sinyal_degisim'] or 0)})" for s in al[:10]) + (" …" if len(al) > 10 else ""))
    else:
        parca.append("Bu hafta AL'e dönen hisse yok.")
    kap = [r for r in kapali if (r.get("cikis_tarih") or "") >= pazartesi and r.get("sonuc") is not None]
    if kap:
        kazanan = sum(1 for r in kap if r["sonuc"] > 0)
        parca.append(f"<b>Canlı karne</b>: bu hafta {len(kap)} sinyal kapandı — {kazanan} kârda, ortalama "
                     f"{_yz(sum(r['sonuc'] for r in kap) / len(kap))}. Açık takip: {len(acik)}.")
    else:
        parca.append(f"<b>Canlı karne</b>: bu hafta kapanan sinyal yok. Açık takip: {len(acik)}.")
    if pf:
        by = {s["kod"]: s for s in sonuclar}
        satir, top = [], 0.0
        for kod, p in pf.items():
            c = [x for x in ((by.get(kod) or {}).get("spark") or {}).get("c", []) if x is not None]
            if len(c) >= 6:
                deg = p["adet"] * (c[-1] - c[-6])
                top += deg
                satir.append((kod, (c[-1] / c[-6] - 1) * 100))
        if satir:
            satir.sort(key=lambda x: -x[1])
            parca.append(f"<b>Portföyün bu hafta</b>: {_tl(top)} · " + ", ".join(f"{k} {_yz(x)}" for k, x in satir))
    parca.append(f"<a href=\"{PANO_URL}\">Panoyu aç</a> · <a href=\"{PANO_URL}gecmis.html\">Karne</a>\n"
                 f"<i>Yatırım tavsiyesi değildir.</i>")
    return "\n\n".join(parca)


def portfoy_ozeti(sonuclar, pf, piyasa=None):
    """Günde bir kez (kapanıştan sonra) portföyün tamamı: sinyal, K/Z, çıkış ve hedefler, dikkat notları."""
    by = {s["kod"]: s for s in sonuclar}
    tarih = pd.Timestamp.now(tz="Europe/Istanbul").strftime("%d.%m.%Y")
    parca = [f"💼 <b>Portföy özeti</b> — {tarih}"]
    toplam = 0.0
    for kod in sorted(pf, key=lambda k: (by.get(k, {}).get("sinyal") != "SAT", k)):
        s, p = by.get(kod), pf[kod]
        if not s:
            parca.append(f"❔ <b>{kod}</b>: taranan listede yok — takip için listeye eklenmeli.")
            continue
        toplam += (s["fiyat"] - p["maliyet"]) * p["adet"]
        sn = s["sinyal"]
        if sn == "NÖTR":
            sn = "NÖTR (AL'den)" if s.get("notr_kaynak") == "AL" else ("NÖTR (SAT'tan)" if s.get("notr_kaynak") == "SAT" else "NÖTR")
        if s["sinyal"] == "SAT" and not p.get("uzun"):
            sn += " ⏳1. gün" if (s.get("sinyal_gun") or 1) <= 1 else f" ✅{s['sinyal_gun']}. gün"
        notlar = []
        pl = pozisyon_plani(s, p)
        if pl.get("stop") and not pl.get("stop_asildi") and pl["stop_uzak"] > -3:
            notlar.append("⚠️ stop'a %3'ten yakın")
        if pl.get("karar") and not pl.get("karar_asildi") and pl["karar_uzak"] > -3:
            notlar.append("⚠️ karar çizgisine %3'ten yakın")
        if pl["uzun"]:
            sn += " · uzun vade"
        if s.get("direnc_yakin"):
            notlar.append("⚠️ dirence yaklaşıyor")
        if s.get("patlak"):
            notlar.append(f"⚠️ taban serisi ({s['taban15']} kez/15 gün)")
        ikon = "🔴" if s["sinyal"] == "SAT" else ("🟢" if s["sinyal"] == "AL" else "🟡")
        parca.append(f"{ikon} <b>{kod}</b> {s['fiyat']} TL — {sn}" + (" · " + " · ".join(notlar) if notlar else "")
                     + "\n     " + plan_metni(s, p))
    parca.insert(1, f"Toplam K/Z: <b>{_tl(toplam)}</b>")
    dag = sektor_dagilimi(pf, by)
    if dag:
        metin = ", ".join(f"{ad} %{pay:.0f}" for ad, pay in dag[:4])
        if len(pf) >= 2 and dag[0][1] > YOGUNLASMA_ESIGI:
            metin = f"⚠️ Portföyünün <b>%{dag[0][1]:.0f}</b>'i tek sektörde ({dag[0][0]}) — o sektördeki bir haber hepsini birlikte etkiler.\n     " + metin
        parca.insert(2, "Dağılım: " + metin)
    if piyasa and piyasa.get("zayif"):
        parca.append("⚠️ Piyasa zayıf (BIST 100 50 günlük ortalamasının altında).")
    parca.append(f"<a href=\"{PANO_URL}\">Panoyu aç</a>\n<i>Hedefler satış emri değil, izleme noktası (backtest: hedefte satmak, SAT/stop'a kadar tutmaktan kötüydü). Yatırım tavsiyesi değildir.</i>")
    return "\n\n".join(parca)


def _kapa(r, fiyat, sebep, bugun):
    r["durum"] = "kapalı"
    r["cikis_tarih"] = bugun
    r["cikis_fiyat"] = fiyat
    r["sonuc"] = round((fiyat / r["giris_fiyat"] - 1) * 100, 1)
    r["sebep"] = sebep


def gecmis_guncelle(by_kod, bugun, piyasa=None):
    """Canlı karne, canlıdaki kuralların aynısını ölçer: AL'e dönüşte gir (taban serisi hariç), giriş stopu
    sabit; stop ya da 2 gün üst üste SAT'ta çık. Aynı AL dalgası bir kez kaydedilir (stop sonrası yeniden açılmaz)."""
    try:
        with open(GECMIS, encoding="utf-8") as f:
            kayitlar = json.load(f).get("kayitlar", [])
    except Exception:
        kayitlar = []

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
        elif s["sinyal"] == "SAT" and (s.get("sinyal_gun") or 1) >= 2:
            _kapa(r, s["fiyat"], "sinyal", bugun)

    acik = {r["kod"] for r in kayitlar if r["durum"] == "açık"}
    kayitli = {(r["kod"], r.get("sinyal_tarih")) for r in kayitlar}
    for kod, s in by_kod.items():
        if (s["sinyal"] == "AL" and (s.get("sinyal_gun") or 99) <= 2 and not s.get("patlak") and s.get("fiyat")
                and kod not in acik and (kod, s.get("sinyal_tarih")) not in kayitli):
            kayitlar.append({"kod": kod, "giris_tarih": bugun, "giris_fiyat": s["fiyat"],
                             "stop": s["giris_stop"], "durum": "açık", "guncel": s["fiyat"], "anlik": 0.0,
                             "sinyal_tarih": s.get("sinyal_tarih"),
                             "piyasa": "zayıf" if (piyasa and piyasa.get("zayif")) else "normal",
                             "hacim": bool(s.get("hacim_teyit"))})

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
    piyasa = piyasa_durumu(data)
    oranlar = oranlari_al(KODLAR)
    sonuclar, yeni_arzlar = [], []
    for kod in KODLAR:
        try:
            df = data[kod + ".IS"].dropna(subset=["Close"])
            if df.empty:
                continue
            arz = arz_bilgisi(kod, df)
            a = analiz_et(df)
            if not a:
                if arz:
                    yeni_arzlar.append(arz)   # sinyal için geçmiş henüz yetersiz
                continue
            a["kod"] = kod
            a["arz"] = arz
            o = oranlar.get(kod, [None, None, None])
            a["fk"] = o[0] if len(o) > 0 else None
            a["pddd"] = o[1] if len(o) > 1 else None
            a["favok"] = o[2] if len(o) > 2 else None
            a["sektor"] = o[3] if len(o) > 3 else None
            a["endustri"] = o[4] if len(o) > 4 else None
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
    simdi = pd.Timestamp.now(tz="Europe/Istanbul")
    kapanis_zamani = simdi.hour * 60 + simdi.minute >= KAPANIS_DAKIKA   # kesin kapanış fiyatı geldi
    kapanis_sonrasi = kapanis_zamani or not SADECE_KAPANIS_MESAJI
    durum = durum_oku()
    son = dict(durum.get("son", {}))
    if kapanis_sonrasi:
        yeni, yeni_sat = sinyal_degisimleri(sonuclar, son)
    else:
        yeni, yeni_sat = [], []   # 'son' değişmez: geçişler kapanışta, kesinleşmiş sinyalle değerlendirilir
    patlak_al = [s for s in yeni if s.get("patlak")]
    yeni = [s for s in yeni if not s.get("patlak")]      # taban serisindeki hisseden AL mesajı gitmez
    yeni_sat = [s for s in yeni_sat if s["kod"] in pf]   # SAT mesajı sadece portföydekiler için

    # SAT 2. gün teyidi (portföy): her SAT dalgası için bir kez. İlk çalışmada sessizce başlangıç kaydı.
    ilk_kez = "sat_teyit" not in durum
    teyit = dict(durum.get("sat_teyit", {}))
    sat_teyit = []
    for s in (sonuclar if kapanis_sonrasi else []):
        if (s["kod"] in pf and s["sinyal"] == "SAT" and (s.get("sinyal_gun") or 1) >= 2
                and teyit.get(s["kod"]) != s["sinyal_tarih"]):
            teyit[s["kod"]] = s["sinyal_tarih"]
            if not ilk_kez and s not in yeni_sat and not pf[s["kod"]].get("uzun"):   # uzun vadede "çık" teyidi yok
                sat_teyit.append(s)

    # Uzun vade: karar çizgisi (ana destek) KAPANIŞLA kırılınca bir kez uyar. Karar çizgisi hep fiyatın altındaki
    # en yakın destekten hesaplandığı için, bir önceki kapanışta kaydedilen çizgiyle kıyaslanır. Gün içi iğneler
    # sayılmasın diye hem kontrol hem kayıt sadece kapanış sonrası taramalarda (KAPANIS_DAKIKA+) yapılır.
    karar_kayit = dict(durum.get("karar_cizgisi", {}))
    kirilim = dict(durum.get("karar_kirilim", {}))
    karar_kirilan = []
    if kapanis_zamani:
        for s in sonuclar:
            p = pf.get(s["kod"])
            if not (p and p.get("uzun")):
                continue
            onceki = karar_kayit.get(s["kod"])
            if onceki and s["fiyat"] < onceki and kirilim.get(s["kod"]) != onceki:
                kirilim[s["kod"]] = onceki
                karar_kirilan.append((s, onceki))
            yeni_karar = karar_cizgisi(s)
            if yeni_karar:
                karar_kayit[s["kod"]] = yeni_karar

    uyari = None
    if len(yeni) > ASIRI_ISLEM_ESIGI:
        uyari = (f"Bu taramada {len(yeni)} yeni AL var — çok fazla. Hepsini alma; en yüksek puanlı/AL+ "
                 f"birkaçına odaklan, aşırı işlem komisyonda eritir.")

    by_kod = {s["kod"]: s for s in sonuclar}
    bugun_iso = simdi.strftime("%Y-%m-%d")

    # Sinyal geçmişi (canlı karne): yeni AL'leri kaydet, açıkları stop/SAT ile kapat
    acik, kapali, karne = gecmis_guncelle(by_kod, bugun_iso, piyasa)
    with open("gecmis.html", "w", encoding="utf-8") as f:
        f.write(gecmis_uret(acik, kapali, karne))

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(pano_uret(sonuclar, ornek=False, uyari=uyari, piyasa=piyasa, yeni_arzlar=yeni_arzlar))
    print(f"index.html: {len(sonuclar)} hisse (+{len(yeni_arzlar)} yeni arz), {len(bugun_al)} AL, {len(yeni)} yeni | "
          f"taban serisi: {sum(1 for s in sonuclar if s.get('patlak'))} | "
          f"piyasa: {'zayıf' if piyasa and piyasa['zayif'] else 'normal'} | "
          f"karne: {karne['kapanan']} kapanan, {karne['acik']} açık.")
    if patlak_al:
        print(f"Taban serisindeki {len(patlak_al)} hissenin AL mesajı gönderilmedi.")

    if yeni or yeni_sat or sat_teyit or karar_kirilan:
        print(f"Telegram: {len(yeni)} yeni AL, {len(yeni_sat)} portföy SAT, {len(sat_teyit)} SAT teyidi, "
              f"{len(karar_kirilan)} karar çizgisi kırılımı.")
        tg_gonder(telegram_mesaji(yeni, yeni_sat, sat_teyit, pf, uyari, piyasa, karar_kirilan))
    else:
        print("Yeni AL / portföyde SAT yok, Telegram sessiz." if kapanis_sonrasi
              else "Gün içi tarama: AL/SAT mesajları kapanış sonrası taramada gönderilir.")

    # Fiyat alarmları: her taramada (gün içi de) kontrol edilir, her alarm bir kez çalar
    tetiklenen = set(durum.get("alarm_tetik", []))
    alarm_yeni = alarm_kontrol(alarmlari_yukle(), by_kod, tetiklenen)
    if alarm_yeni:
        print(f"Telegram: {len(alarm_yeni)} fiyat alarmı.")
        if not tg_gonder(alarm_mesaji(alarm_yeni)):
            for a, _ in alarm_yeni:
                tetiklenen.discard(_alarm_anahtar(a))   # gönderilemediyse sonraki taramada yeniden dene

    # Günlük portföy özeti: hafta içi, kapanıştan sonraki ilk taramada bir kez
    ozet_tarih = durum.get("ozet_tarih")
    if pf and simdi.weekday() < 5 and kapanis_zamani and ozet_tarih != bugun_iso:
        if tg_gonder(portfoy_ozeti(sonuclar, pf, piyasa)):
            ozet_tarih = bugun_iso
            print("Günlük portföy özeti gönderildi.")

    # Haftalık özet: cuma kapanıştan sonraki ilk taramada bir kez
    hafta_tarih = durum.get("hafta_tarih")
    if simdi.weekday() == 4 and kapanis_zamani and hafta_tarih != bugun_iso:
        if tg_gonder(haftalik_ozet(sonuclar, pf, acik, kapali, simdi)):
            hafta_tarih = bugun_iso
            print("Haftalık özet gönderildi.")

    with open(DURUM, "w", encoding="utf-8") as f:
        json.dump({"al": sorted(s["kod"] for s in bugun_al), "son": dict(sorted(son.items())),
                   "sat_teyit": dict(sorted(teyit.items())), "ozet_tarih": ozet_tarih, "hafta_tarih": hafta_tarih,
                   "karar_kirilim": dict(sorted(kirilim.items())), "karar_cizgisi": dict(sorted(karar_kayit.items())),
                   "alarm_tetik": sorted(tetiklenen)},
                  f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
