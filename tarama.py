# -*- coding: utf-8 -*-
"""
BIST sinyal taraması — BIST100, ~15 dk'da bir güncellenir.
Akış: fiyat çek -> sinyal + (günlük önbellekli) oran -> risk/lot -> AL+ -> yorum
-> index.html -> Telegram (tüm hisselerde yeni AL, portföyde yeni SAT).
"""
import bisect, json, math, os, time
from html import escape
import pandas as pd
import yfinance as yf
from kap import kap_guncelle, kap_mesaji
from bilanco import bilancolari_al, bilanco_ozet, bilanco_metni, bilanco_yakin, tarih_tr, temettu_ozet
from sinyal import analiz_et, destek_direnc, bolunme_duzelt, tahta_riski, TABAN_GETIRI, TABAN_GUN, IZ_STOP_ORAN, KILIT_ARALIK
from pano import pano_uret, gecmis_uret
import gunici
try:
    import oda   # 🏢 İşlem Odası (sanal para); yoksa/bozuksa tarama etkilenmez
except Exception as _e:
    oda = None
    print(f"İşlem odası yüklenemedi ({type(_e).__name__}).")

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
_REPO = (os.environ.get("GITHUB_REPOSITORY") or "BoranZZ/Bist-signal").split("/")
PANO_URL = f"https://{_REPO[0].lower()}.github.io/{_REPO[1]}/"   # arkadaşın kopyasında onun sitesi
# Telegram: tüm hisselerde yeni AL; SAT sadece portföydekiler (PORTFOY variable'ı, panodan otomatik yazılır).
# ============================================

# Küçük/orta hisseler (2026-09): BIST100/EK dışında, son 60 gün medyan günlük işlem ≥ 50 milyon TL (KAP kod listesi +
# yfinance). Tahtacı uyarıları (🎈 ⚠️ 🪤) bunlarda da görünsün diye. 3 ayda bir güncelle.
KUCUK_HISSELER = [
    "A1CAP", "ADEL", "ADESE", "AKENR", "AKFIS", "AKGRT", "AKSUE", "ALCTL", "ALGYO", "ALKLC", "ALVES", "ANELE", "ARDYZ",
    "ARMGD", "ARSAN", "ATATP", "AVHOL", "AYDEM", "BAHKM", "BALSU", "BIGEN", "BIGTK", "BIOEN", "BJKAS", "BLUME", "BMSTL",
    "BOBET", "BORLS", "BRLSM", "BTCIM", "BULGS", "BURCE", "BVSAN", "CATES", "CELHA", "CEMZY", "CGCAM", "CRDFA", "CRFSA",
    "DAGI", "DAPGM", "DCTTR", "DITAS", "DMRGD", "DSTKF", "EDATA", "EFOR", "EGEGY", "EGEPO", "EMKEL", "ENDAE", "ENSRI",
    "ESCAR", "ESCOM", "ESEN", "FONET", "FORTE", "FRIGO", "FZLGY", "GENIL", "GEREL", "GIPTA", "GMTAS", "GOKNR", "GRTHO",
    "GSDDE", "GSDHO", "GSRAY", "GUNDG", "GZNMI", "HATSN", "HDFGS", "HEDEF", "HKTM", "HLGYO", "HOROZ", "HRKET", "HUNER",
    "HURGZ", "ICUGS", "IEYHO", "IHAAS", "IHLAS", "INDES", "INFO", "ISGSY", "ISKPL", "IZFAS", "IZMDC", "KAREL", "KARTN",
    "KBORU", "KGYO", "KLRHO", "KLYPV", "KOCMT", "KOPOL", "KRDMA", "KRDMB", "KTLEV", "KUYAS", "KZBGY", "LIDER", "LILAK",
    "LINK", "LOGO", "LYDHO", "MAGEN", "MANAS", "MARTI", "MEGMT", "MERCN", "METRO", "MIATK", "MOBTL", "MOGAN", "MOPAS",
    "MRGYO", "MRSHL", "NTHOL", "ODINE", "OFSYM", "ONCSM", "ONRYT", "ORGE", "OZATD", "OZSUB", "PASEU", "PATEK", "PCILT",
    "PEKGY", "PKART", "PRZMA", "PSGYO", "RALYH", "RTALB", "RUBNS", "RYGYO", "SAFKR", "SANFM", "SARKY", "SAYAS", "SEGMN",
    "SELEC", "SMRTG", "SMRVA", "SUNTK", "SURGY", "TARKM", "TATEN", "TEHOL", "TERA", "TGSAS", "TMPOL", "TNZTP", "TRHOL",
    "TSPOR", "TUREX", "ULUSE", "USAK", "VBTYZ", "VSNMD", "YIGIT",
]

KODLAR = sorted(set(BIST100 + EK_HISSELER + KUCUK_HISSELER + list(HALKA_ARZ)))
DURUM = "durum.json"
ORAN_CACHE = "oranlar.json"
ENDEKS = "XU100"
# Kapanış: sürekli işlem 18:00'de biter, kapanış seansı ~18:10; Yahoo verisi ~15 dk gecikmeli -> kesin kapanış
# fiyatı ~18:25'te gelir. Kapanış sonrası işler (AL/SAT mesajları, günlük özet) 18:30'dan sonraki ilk taramada.
KAPANIS_DAKIKA = 18 * 60 + 30
# AL/SAT mesajları kapanıştan ~30 dk önce (17:30+, Yahoo gecikmesiyle ~17:15 fiyatı) değerlendirilir: kullanıcı
# isterse o gün alabilsin. Saatlik veriyle ölçüldü (2026-09): bu saatte görülen yeni AL'lerin ~%88'i kapanışta
# tutuyor (gün içi erken saatlerde ~%75); 17:00 fiyatından almak ile ertesi açılıştan almak arasında belirgin
# fark yok. Kapanışta tutmayanlar için KAPANIS_DAKIKA'dan sonra "iptal" mesajı gider ve durum geri alınır.
SINYAL_DAKIKA = 17 * 60 + 30
SADECE_KAPANIS_MESAJI = True   # False: gün içi her taramada (eski davranış)
MIN_GUN = 60      # sinyal için gereken en az işlem günü (sinyal.analiz_et)

# 🚀 gün içi kırılım (kesin kapanıştan önce görünen): o saatte saatlik kapanışı 20 günlük zirvenin üstünde olan şablondaki
# hisselerin kaçı gün sonunda da üstünde kapattı (scratchpad vade_gunici/v3_yanlis.py, 2023-11 → 2026-10, 611 aday gün).
# Saat = saatlik mumun bitişi; Yahoo ~15 dk gecikmeli olduğu için verinin saati (şimdi − 15 dk) kullanılır.
GK_ORAN = ((10 * 60 + 30, 67), (11 * 60 + 30, 71), (12 * 60 + 30, 74), (13 * 60 + 30, 77), (14 * 60 + 30, 76),
           (15 * 60 + 30, 79), (16 * 60 + 30, 85), (17 * 60 + 30, 88))
GK_EK = {67: "'si", 71: "'i", 74: "'ü", 77: "'si", 76: "'sı", 79: "'u", 85: "'i", 88: "'i"}   # Türkçe ek (JS gkMetin ile aynı)
GK_NOT = ("Geçmişte kapanışta tutan kırılımda kapanış seansında almak ertesi sabaha göre ort. +0,8 puan iyiydi; ertesi gün "
          "geri çekilme ya da limit emirle beklemek belirgin kötüydü (en güçlüler kaçtı).")   # v3_analiz.py B) — JS GK_NOT


def gk_oran(simdi):
    """Verinin saatine (şimdi − 15 dk) göre kapanışta tutma oranı (%); 10:30 öncesi için ilk değer."""
    dk = simdi.hour * 60 + simdi.minute - gunici.GECIKME
    o = GK_ORAN[0][1]
    for d, p in GK_ORAN:
        if dk >= d:
            o = p
    return o


def gk_metni(oran):
    return f"Gün içi kırılım: geçmişte bu saatte görünen kırılımların ~%{oran}{GK_EK.get(oran, '')} kapanışta tuttu."


KAPANIS_DUZELT_GUN = 3     # son kaç günün günlük kapanışı saatlik veriyle düzeltilir
KAPANIS_DUZELT_SINIR = 0.02  # günlük ile saatlik arasında bundan büyük fark: temettü düzeltmesi/veri hatası, dokunma


def _son_fiyat(tk):
    try:
        x = yf.Ticker(tk).fast_info.last_price
        return float(x) if x and x == x else None
    except Exception:
        return None


def _gun_ici_indir(tickers, gun):
    """Yahoo 15 dk verisi: gun verilirse son 'gun' takvim günü (`start=`, gün içi görünüm için), yoksa son 7 gün."""
    kw = dict(interval="15m", group_by="ticker", auto_adjust=True, progress=False, threads=True)
    if gun:
        bas = (pd.Timestamp.now(tz="Europe/Istanbul") - pd.Timedelta(days=gun)).date()
        s = yf.download(tickers, start=str(bas), **kw)
    else:
        s = yf.download(tickers, period="7d", **kw)
    if s is None or s.empty:
        raise ValueError("boş veri")
    return s


def veri_cek(kodlar, kesin_kapanis=False, gunici_gun=None, ara=None):
    """Günlük veri (2 yıl: SMA200 tabanlı sinyaller için) + kapanış düzeltmesi. Yahoo'nun BIST günlük barlarında kapanış
    çoğu zaman resmi kapanıştan farklı (Eylül 2026 kontrolü: günlerin ~%30'unda >%0,3; THYAO 24.09 günlük 288,5, resmi
    289,5) ve son günün kapanışı boş geliyor. Gün içi verinin gün sonu fiyatı resmi kapanışla birebir tuttu (16/16).
    Bu yüzden son KAPANIS_DUZELT_GUN günün kapanışı gün içi veriden alınır; kesin kapanıştan sonra son gün Yahoo'nun anlık
    son fiyatından (kapanış seansı fiyatı, TradingView ile aynı).
    Gün içi veri 15 dk'lık (2026-10: 6 günde 326 hissenin 1.956 gün sonu kapanışı saatlikle birebir aynı); aynı indirme
    📊 gün içi görünümde de kullanılır (gunici_gun: kaç günlük, ara: {"15m": veri} buraya yazılır). Alınamazsa eski
    saatlik indirmeye düşülür (gün içi görünüm o taramada boş kalır)."""
    tickers = [k + ".IS" for k in kodlar] + [ENDEKS + ".IS"]
    print(f"{len(tickers)} hisse indiriliyor...")
    g = yf.download(tickers, period="2y", interval="1d", group_by="ticker", auto_adjust=True, progress=False, threads=True)
    try:
        s = _gun_ici_indir(tickers, gunici_gun)
        if ara is not None:
            ara["15m"] = s
    except Exception as e:
        print(f"15 dk veri alınamadı ({type(e).__name__}); saatlik deneniyor.")
        try:
            s = yf.download(tickers, period="7d", interval="1h", group_by="ticker", auto_adjust=True, progress=False, threads=True)
        except Exception as e:
            print(f"Saatlik veri alınamadı ({type(e).__name__}); günlük veri düzeltmesiz kullanılıyor.")
            return g
    son = {}
    if kesin_kapanis:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=12) as ex:
            son = dict(zip(tickers, ex.map(_son_fiyat, tickers)))
    parca, duzeltilen, eklenen = {}, 0, 0
    for tk in tickers:
        try:
            d = g[tk].copy()
        except KeyError:
            continue
        try:
            hh = s[tk].dropna(subset=["Close"])
        except KeyError:
            hh = None
        if hh is not None and not hh.empty:
            ix = hh.index.tz_convert("Europe/Istanbul") if hh.index.tz is not None else hh.index
            agg = hh.groupby(ix.date).agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
            gunler = sorted(agg.index)[-KAPANIS_DUZELT_GUN:]
            tarih = pd.Series(d.index.date, index=d.index)
            for gd in gunler:
                x = float(agg.at[gd, "Close"])
                if gd == gunler[-1] and son.get(tk) and abs(son[tk] / x - 1) <= KAPANIS_DUZELT_SINIR:
                    x = son[tk]
                satir = tarih.index[tarih.values == gd]
                if len(satir):
                    t = satir[-1]
                    eski = d.at[t, "Close"]
                    if pd.notna(eski) and abs(x / eski - 1) > KAPANIS_DUZELT_SINIR:
                        continue
                    for k_, v_ in (("Open", agg.at[gd, "Open"]), ("High", agg.at[gd, "High"]), ("Low", agg.at[gd, "Low"])):
                        if pd.isna(d.at[t, k_]):
                            d.at[t, k_] = v_
                    d.at[t, "Close"] = x
                    d.at[t, "High"] = max(d.at[t, "High"], x)
                    d.at[t, "Low"] = min(d.at[t, "Low"], x)
                    duzeltilen += int(pd.isna(eski) or abs(x - eski) > 1e-9)
                else:
                    yeni = pd.Timestamp(gd).tz_localize(d.index.tz) if d.index.tz is not None else pd.Timestamp(gd)
                    d.loc[yeni] = pd.Series({"Open": agg.at[gd, "Open"], "High": max(agg.at[gd, "High"], x),
                                             "Low": min(agg.at[gd, "Low"], x), "Close": x,
                                             "Volume": agg.at[gd, "Volume"]}).reindex(d.columns)
                    eklenen += 1
            d = d.sort_index()
        parca[tk] = d
    print(f"Kapanış düzeltmesi: {duzeltilen} gün-hisse düzeltildi, {eklenen} eksik gün eklendi"
          + (f", son fiyat {sum(1 for v in son.values() if v)} hisse için anlık kapanıştan." if son else "."))
    return pd.concat(parca, axis=1)


def piyasa_durumu(data):
    """Piyasa filtresi: BIST 100 50 günlük ortalamasının altındaysa 'zayıf' (backtest: bu dönemdeki AL'ler kötü)."""
    try:
        xu = data[ENDEKS + ".IS"]["Close"].dropna()
        ort = float(xu.rolling(50).mean().iloc[-1])
        son = float(xu.iloc[-1])
        return {"endeks": round(son), "ort50": round(ort), "zayif": son < ort, "fark": round((son / ort - 1) * 100, 1)}
    except Exception:
        return None


def endeks_serisi(data=None):
    """Portföy-endeks kıyası için BIST 100 kapanışları: son 2 yıl günlük (taramanın indirdiği güncel veri), öncesi
    (10 yıla kadar) haftalık. {"t": ["YYYY-MM-DD", ...], "c": [kapanış, ...]} ya da None."""
    try:
        xu = yf.download(ENDEKS + ".IS", period="10y", interval="1d", auto_adjust=True, progress=False)["Close"]
        if isinstance(xu, pd.DataFrame):
            xu = xu.iloc[:, 0]
        xu = xu.dropna()
        yakin = None
        if data is not None:
            try:
                yakin = data[ENDEKS + ".IS"]["Close"].dropna()
            except Exception:
                yakin = None
        if yakin is None or yakin.empty:
            yakin = xu[xu.index >= xu.index[-1] - pd.DateOffset(years=2)]
        eski = xu[xu.index < yakin.index[0]]
        eski = eski.groupby(eski.index.to_period("W")).tail(1)   # haftanın son kapanışı
        xu = pd.concat([eski, yakin])
        return {"t": [str(t.date()) for t in xu.index], "c": [round(float(v), 2) for v in xu.values]}
    except Exception as e:
        print(f"Endeks serisi alınamadı: {e}")
        return None


def endeks_deger(seri, tarih):
    """Serideki tarih'e eşit ya da ondan önceki son kapanış (yoksa None)."""
    if not seri or not tarih:
        return None
    i = bisect.bisect_right(seri["t"], str(tarih)[:10]) - 1
    return seri["c"][i] if i >= 0 else None


def _yzd(x):
    return f"+%{x:.1f}" if x >= 0 else f"−%{-x:.1f}"


def endeks_kiyas(pf, by, seri):
    """Alış tarihi girilmiş pozisyonlar (xu_birim) için: portföy getirisi vs aynı para aynı günlerde BIST 100.
    {"n", "toplam_n", "pf_yuzde", "xu_yuzde", "fark"} ya da None."""
    if not seri:
        return None
    xu_son = seri["c"][-1]
    maliyet = deger = xu_deger = 0.0
    n = 0
    for kod, p in pf.items():
        s = by.get(kod)
        if not p.get("xu_birim") or not s:
            continue
        n += 1
        maliyet += p["adet"] * p["maliyet"]
        deger += p["adet"] * s["fiyat"]
        xu_deger += p["xu_birim"] * xu_son
    if not n or maliyet <= 0:
        return None
    pfy, xuy = (deger / maliyet - 1) * 100, (xu_deger / maliyet - 1) * 100
    return {"n": n, "toplam_n": len(pf), "pf_yuzde": round(pfy, 1), "xu_yuzde": round(xuy, 1), "fark": round(pfy - xuy, 1)}


# --- 🔎 Hareket açıklaması (pano.py 'hareket' JS fonksiyonuyla AYNI mantık ve eşikler; birini değiştirirsen ikisini de) ---
# bt/hareket: BIST 100'den ayrışma 1/5/20 günde ≥ 4/10/20 puan → günlerin ~%12-13'ü; hacim ≥1,5x → ~%12,5'i.
HR_ESIK = {1: 4, 5: 10, 20: 20}
HR_HACIM = 1.5
# Sektör kıyası: Yahoo endüstrileri çoğu hissede çok küçük (2-3 hisse); ana sektör ise çok geniş ('Sanayi' 77 hisse: holding,
# havayolu, savunma...). Küçük ama benzer endüstriler bu ara gruplarda birleşir; grupta (kendisi dahil) en az KIYAS_MIN hisse
# yoksa sektör kıyası yapılmaz ("yeterli benzer hisse yok"). Eşlemede olmayan endüstri kendi adıyla grup olur.
KIYAS_MIN = 4
KIYAS_GRUP = {
    "Elektrik üretim": "Elektrik/doğalgaz", "Elektrik dağıtım": "Elektrik/doğalgaz", "Doğalgaz dağıtım": "Elektrik/doğalgaz",
    "Finansman/faktoring": "Sigorta/finansman", "Sigorta": "Sigorta/finansman", "Hayat sigortası/emeklilik": "Sigorta/finansman",
    "Gıda": "Gıda/içecek", "İçecek": "Gıda/içecek", "Şekerleme": "Gıda/içecek", "Farm Products": "Gıda/içecek",
    "Perakende (market)": "Perakende", "Mağazacılık": "Perakende", "Giyim perakende": "Perakende", "Specialty Retail": "Perakende",
    "Otomotiv bayi": "Perakende",
    "Otomotiv": "Otomotiv", "Otomotiv yan sanayi": "Otomotiv",
    "Tekstil": "Tekstil/giyim", "Apparel Manufacturing": "Tekstil/giyim",
    "Turizm": "Turizm/yeme-içme", "Lodging": "Turizm/yeme-içme", "Restoran": "Turizm/yeme-içme",
    "Beyaz eşya/mobilya": "Dayanıklı tüketim", "Tüketici elektroniği": "Dayanıklı tüketim",
    "Denizcilik": "Ulaştırma", "Lojistik": "Ulaştırma", "Demiryolu": "Ulaştırma", "Havayolu": "Ulaştırma", "Havalimanı": "Ulaştırma",
    "Traktör/iş makinesi": "Makine/metal", "Specialty Industrial Machinery": "Makine/metal", "Metal işleme": "Makine/metal",
    "Specialty Business Services": "Ticari hizmet/kiralama", "Business Equipment & Supplies": "Ticari hizmet/kiralama",
    "İnsan kaynakları hizmet": "Ticari hizmet/kiralama", "Industrial Distribution": "Ticari hizmet/kiralama",
    "Rental & Leasing Services": "Ticari hizmet/kiralama",
    "Madencilik": "Madencilik", "Altın madenciliği": "Madencilik", "Copper": "Madencilik",
    "GYO": "GYO", "GYO (konut)": "GYO", "REIT - Industrial": "GYO", "REIT - Hotel & Motel": "GYO", "Real Estate - Diversified": "GYO",
    "Gayrimenkul geliştirme": "Gayrimenkul geliştirme/hizmet", "Gayrimenkul hizmet": "Gayrimenkul geliştirme/hizmet",
    "Yazılım": "Yazılım/BT", "BT hizmetleri": "Yazılım/BT",
    "Telekom": "Medya/telekom", "Publishing": "Medya/telekom", "Broadcasting": "Medya/telekom", "Advertising Agencies": "Medya/telekom",
    "Hastane": "Sağlık", "İlaç": "Sağlık", "Biotechnology": "Sağlık", "Medical Devices": "Sağlık",
    "Health Information Services": "Sağlık", "Medical Distribution": "Sağlık",
}


def kiyas_gruplari(sonuclar):
    """Her sonuca 'kg' (sektör kıyas grubu) yazar; grupta en az KIYAS_MIN hisse yoksa None. Pano da bunu kullanır."""
    ad = {s["kod"]: (KIYAS_GRUP.get(s.get("endustri"), s.get("endustri")) or None) for s in sonuclar}
    say = {}
    for g in ad.values():
        if g:
            say[g] = say.get(g, 0) + 1
    for s in sonuclar:
        g = ad[s["kod"]]
        s["kg"] = g if g and say[g] >= KIYAS_MIN else None


def hareket_hepsi(sonuclar, seri):
    """kod -> [{u, t0, r, xu, fark, sek, sn, hk, tavan, taban, tur, dikkat}, ...] (1/5/20 gün). Veri: panodaki grafik
    serisi (spark) ve BIST 100 serisi — JS 'hareket' ile birebir aynı girdiler."""
    idx = {}
    for s in sonuclar:
        sp = s.get("spark") or {}
        idx[s["kod"]] = dict(zip(sp.get("t") or [], sp.get("c") or []))

    def getiri(kod, t0, t1):
        m = idx.get(kod) or {}
        c0, c1 = m.get(t0), m.get(t1)
        if c0 is None or c1 is None or not c0:
            return None
        return (c1 / c0 - 1) * 100

    gruplar = {}
    for s in sonuclar:
        if s.get("kg"):
            gruplar.setdefault(s["kg"], []).append(s["kod"])
    out = {}
    for s in sonuclar:
        sp = s.get("spark") or {}
        c, t = sp.get("c") or [], sp.get("t") or []
        n = len(c)
        if n < 2:
            continue
        kod, t1 = s["kod"], t[-1]
        xu_tamam = bool(seri and seri.get("t") and seri["t"][-1] >= t1)
        hv = s.get("hv") or [None, None, None]
        liste = []
        for j, u in enumerate((1, 5, 20)):
            if n <= u:
                continue
            t0 = t[n - 1 - u]
            r = getiri(kod, t0, t1)
            if r is None:
                continue
            x0 = endeks_deger(seri, t0) if xu_tamam else None
            x1 = endeks_deger(seri, t1) if xu_tamam else None
            xu = (x1 / x0 - 1) * 100 if (x0 and x1) else None
            top, sn = 0.0, 0
            for k2 in gruplar.get(s.get("kg"), []):
                if k2 == kod:
                    continue
                rr = getiri(k2, t0, t1)
                if rr is not None:
                    top += rr
                    sn += 1
            sek = top / sn if sn >= 2 else None
            hk = hv[j] if j < len(hv) else None
            tavan = taban = 0
            for i in range(n - u, n):
                if c[i] is None or c[i - 1] is None or not c[i - 1]:
                    continue
                ch = c[i] / c[i - 1] - 1
                tavan += ch >= 0.095
                taban += ch <= -0.095
            T = HR_ESIK[u]
            fark = None if xu is None else r - xu
            if fark is None:
                tur = "?"
            elif abs(fark) < T:
                tur = "piyasa"
            elif sek is not None and abs(r - sek) < T / 2 and abs(sek - xu) >= T / 2 and (sek - xu) * fark > 0:
                tur = "sektor"
            else:
                tur = "ozel"
            dikkat = (fark is not None and abs(fark) >= T) or abs(r) >= T or (hk is not None and hk >= HR_HACIM)
            liste.append({"u": u, "t0": t0, "r": r, "xu": xu, "fark": fark, "sek": sek, "sn": sn, "hk": hk,
                          "tavan": tavan, "taban": taban, "tur": tur, "dikkat": bool(dikkat)})
        out[kod] = liste
    return out


def ozel_dusus(hr):
    """🔻 Hisseye özel hacimli düşüş (bilgi uyarısı, sinyal değil): 5 ya da 20 günde hem kendisi hem endeksten farkı ≤ −eşik
    (10 / 20 puan), sektörü bunu açıklamıyor (tur 'ozel') ve hacim ≥1,5x. bt/hareket/olay2.py (299 hisse, 2021-26): sonraki 20
    günde endeksi yenme %38 (tüm günler %46), çökenler hariç %39 / %45; düşük faiz 2022-09/2023-06'da fark yok (%46-48 / %47). Döner: en uzun ufuk {u, r, xu, hk} ya da None."""
    bul = [x for x in (hr or []) if x["u"] in (5, 20) and x["tur"] == "ozel" and x["fark"] is not None
           and x["fark"] <= -HR_ESIK[x["u"]] and x["r"] <= -HR_ESIK[x["u"]] and x["hk"] is not None and x["hk"] >= HR_HACIM]
    if not bul:
        return None
    x = bul[-1]
    return {"u": x["u"], "r": round(x["r"], 1), "xu": round(x["xu"], 1), "hk": x["hk"]}


def hareket_satiri(hr):
    """Akşam portföy özeti: bugün (1 gün) hisseye özel hareket — eşiği geçmiyorsa None."""
    x = next((y for y in (hr or []) if y["u"] == 1), None)
    if not x or not x["dikkat"] or x["tur"] != "ozel":
        return None
    m = f"{_yzd(x['r'])} (BIST 100 {_yzd(x['xu'])}"
    if x["sek"] is not None:
        m += f", benzer {x['sn']} hisse {_yzd(x['sek'])}"
    if x["hk"] is not None and x["hk"] >= HR_HACIM:
        m += f", hacim {x['hk']:.1f}x".replace(".", ",")
    return m + ")"


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
        p.append(f"Alırsan çıkış kuralı iz stop: şimdilik {round(s['fiyat'] * (1 - IZ_STOP_ORAN), 2)} TL; fiyat yükseldikçe "
                 f"tepe kapanışın %20 altına taşınır, kapanış altına inerse çık.")
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
        try:   # endeks kıyası: alış tarihindeki BIST 100 ile "aynı parayla alınabilecek endeks birimi" (panoda hesaplanır)
            xub = float(p["xu_birim"]) if p.get("xu_birim") else None
        except Exception:
            xub = None
        if kod in pf:
            a0, m0 = pf[kod]["adet"], pf[kod]["maliyet"]
            x0 = pf[kod]["xu_birim"]
            pf[kod] = {"adet": a0 + adet, "maliyet": (a0 * m0 + adet * mal) / (a0 + adet),
                       "uzun": pf[kod]["uzun"] or uzun, "xu_birim": (x0 + xub) if (x0 and xub) else None}
        else:
            pf[kod] = {"adet": adet, "maliyet": mal, "uzun": uzun, "xu_birim": xub}
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
            x = {"kod": kod, "yon": yon, "fiyat": fiyat}
            notu = str(a.get("not") or "").strip()[:40]   # isteğe bağlı: 'destek', 'iz stop'... (anahtara girmez)
            if notu:
                x["not"] = notu
            temiz.append(x)
    if temiz:
        print(f"Alarm: {len(temiz)} adet.")
    return temiz


def _gizli(metin):
    """durum.json herkese açık: portföyü ele verebilecek anahtarlar gizli bir anahtarla (TELEGRAM_TOKEN, Actions
    secret'ı) HMAC'lenir. Anahtar bilinmeden 160 hisseyi deneyerek geri çözülemez."""
    import hmac, hashlib
    anahtar = (os.environ.get("TELEGRAM_TOKEN") or "yerel-test").encode()
    return hmac.new(anahtar, metin.encode(), hashlib.sha256).hexdigest()[:16]


def _alarm_anahtar(a):
    # durum.json herkese açık: alarmın kendisi değil, gizli özeti saklanır
    return _gizli(f"alarm|{a['kod']}|{a['yon']}|{a['fiyat']}")


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
    satir = [f"🔔 <b>{a['kod']}</b> {a['fiyat']:g} TL{' (' + escape(a['not']) + ')' if a.get('not') else ''} "
             f"{'üstüne çıktı' if a['yon'] == 'ust' else 'altına indi'} — şu an {s['fiyat']} TL ({s['sinyal']})"
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
    """Portföydeki pozisyon için çıkış ve izleme seviyeleri. pano.py'deki pozPlan() ile aynı mantık.
    v2: çıkış iz stop (AL'den beri tepe kapanışın %20 altı); SAT bilgi amaçlı. Uzun vade pozisyonda stop yerine
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
    # v2: çıkış kuralı iz stop (AL'den beri tepe kapanışın %20 altı); SAT sinyali tek başına "çık" demek değil
    iz = s.get("iz")
    if iz and iz.get("cikti"):
        plan["iz_cikti"] = iz["cikis_tarih"]
        stop = None
    elif iz:
        stop, plan["iz"], plan["tepe"] = iz["stop"], True, iz["tepe"]
    else:
        stop = s.get("al_stop") or s.get("stop")
    plan["stop"] = stop
    if stop:
        plan["stop_uzak"] = (stop / f - 1) * 100
        plan["stop_kz"] = (stop - m) * a
        plan["stop_asildi"] = f <= stop
    dr = (s.get("sd") or {}).get("direnc")
    if dr and dr["fiyat"] > f:
        plan["hedefler"].append((dr["fiyat"], f"en yakın direnç ({dr['tarih']} tepesi)"))
    return plan


def plan_metni(s, p, girinti="     "):
    """Telegram için sade pozisyon açıklaması."""
    pl = pozisyon_plani(s, p)
    t = [f"Senin pozisyonun{' (uzun vade)' if pl['uzun'] else ''}: {pl['adet']:g} adet, maliyet {pl['maliyet']:.2f} → "
         f"şu an {_yz(pl['kz_y'])} ({_tl(pl['kz'])})"]
    if pl["uzun"]:
        uv = s.get("uv") or {}
        if uv.get("durum") == "AL":
            t.append(f"🌱 Uzun vade sinyali: AL ({uv['tarih']}'den beri {_yz(uv['degisim'])}) — trend sağlam.")
        elif uv.get("durum") == "SAT":
            t.append(f"🌱 Uzun vade sinyali: SAT ({uv['tarih']}) — fiyat 200 günlük ortalamanın ({uv['sma200']} TL) altında; uzun vadeli trend bozuk.")
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
        t.append("ℹ️ Kısa vadeli SAT sinyali — çıkış kuralı iz stop; SAT tek başına \"çık\" demek değil.")
    if pl.get("iz_cikti"):
        sp = s.get("spark") or {}
        o_gun = sp.get("c", [None])[sp.get("t", []).index(pl["iz_cikti"])] if pl["iz_cikti"] in sp.get("t", []) else None
        fark = f" O günkü kapanış {o_gun:g} TL, o günden beri {_yz((pl['fiyat'] / o_gun - 1) * 100)}." if o_gun else ""
        t.append(f"📍 İz stop {pl['iz_cikti']} tarihinde kırıldı — kurala göre çıkış zamanı geçti.{fark}")
    elif pl.get("stop"):
        if pl.get("iz"):
            t.append(f"📍 İz stop: {pl['stop']} TL (AL'den beri tepe {pl['tepe']} TL'nin %20 altı) — {_yz(pl['stop_uzak'])} aşağıda. "
                     f"Kapanış bunun altına inerse çık; buraya inerse: {_tl(pl['stop_kz'])}" + (" (yine kârda)" if pl["stop_kz"] >= 0 else ""))
        elif pl["stop_asildi"]:
            t.append(f"📍 Fiyat çıkış seviyesinin ({pl['stop']} TL) ALTINDA — sistemin kuralına göre çıkış zamanı.")
        else:
            t.append(f"📍 Çıkış (stop): {pl['stop']} TL — {_yz(pl['stop_uzak'])} aşağıda. Buraya inerse: {_tl(pl['stop_kz'])}"
                     + (" (yine kârda)" if pl["stop_kz"] >= 0 else ""))
    for i, (h, ne) in enumerate(pl["hedefler"], 1):
        t.append(f"🎯 İzleme: {h} TL — {ne}, {_yz((h / pl['fiyat'] - 1) * 100)} yukarıda")
    return ("\n" + girinti).join(t)


# 📍 Portföy gün içi mesajları (destek/direnç, iz stop, taban/tavan). Yahoo ~15 dk gecikmeli: 10:00 açılış ~10:15'te gelir.
GUNICI_BAS = 10 * 60 + 15
GUNICI_SON = 18 * 60 + 10       # sürekli işlem 18:00'de biter; sonrası kapanış teyidi (KAPANIS_DAKIKA)
GUNICI_VERI_FARK = 0.01         # tablodaki fiyat ile anlık fiyat bundan fazla farklıysa veri şüpheli: o hisse için mesaj yok
IZ_YAKIN = 0.02                 # iz stop'a bu kadar yaklaşınca gün içi uyarı
SERT_DUSUS, TABAN_ESIK, TAVAN_ESIK = -0.05, -0.095, 0.095
# Açık gün içi olaylar. d_sarkti (desteğin altına sarktı, hisse-günlerin ~%14'ü) ve d_yakin (~%7) gürültülü ve bir
# şey söylemiyor (sarkmaların %41'i kapanışta geri alındı) → kapalı; yakınlık sabah mesajında 👉, sarkma sonucu kapanış
# mesajında. Açmak için buraya ekle. (bt/mesajsay*.py, 125 hisse 2022-26: 5 hisselik portföyde tümü açık ve geniş dönüş
# tanımıyla günlerin %82'sinde mesaj; bu set + dönüşte gün içi tepenin dirence değmesi şartıyla %41, günde ~0,6 hisse.)
GUNICI_OLAYLAR = {"kilitli", "taban", "tavan", "sert", "sisme", "dagitim", "iz_yakin", "iz_alti", "d_kirildi", "r_kirdi", "r_dondu"}
PIYASA_SERT = 0.025             # BIST 100 gün içinde bu kadar (±) oynarsa portföyün günlük K/Z'si tek satır
# Olay çalışması (2022-26, 125 hisse, seviyeler bir önceki kapanışa göre; scratchpad bt/sd1-2.py): gün içi desteğin
# altına sarkmaların ~%41'i kapanışta geri alındı, ~%40'ı desteğin hafif altında (tolerans içinde) kapadı, ~%19'u
# kırıldı. Kırılım / dönüş sonrası 20 gün, aynı trenddeki rastgele günden en fazla ±1-2 puan farklı ve yönü faiz
# dönemine göre değişiyor → destek/direnç mesajları BİLGİ; çıkış kuralı iz stop / karar çizgisi (test edilen).
# v3 pozisyonları (bt/izgunici.py, 125 hisse): gün içi iz stop altına ilk sarkmaların %44'ü (düşük faiz %47, yüksek %43)
# kapanışta geri alındı; kapanışa bakan kural, sarkma anında stop'tan satmaya göre ort. +%3 (medyan hafif eksi, birkaç büyük
# kazanç taşıyor) → iz_alti mesajı "kapanışı bekle" der.
SD_NOT = ("Geçmiş testte (2022-26) gün içi desteğin altına sarkmaların ~%40'ı kapanışta geri alındı; destek kırılımı ya da "
          "dirençten dönüş sonrası 20 gün rastgele bir günden belirgin farklı değildi. Bunlar bilgi; çıkış kuralı iz stop / karar çizgisi.")


# 🔒 kilitli taban (sinyal.kilitli_taban; bt/korn 2026-10, 587 hisse 2021-26): metin panodaki JS ktMetin ile aynı
KILIT_NOT = ("Geçmişte benzerlerinin ~%60'ı 4+ tabana uzadı (normalde ~%9). Kilitli tabanda satış emri çoğu zaman "
             "gerçekleşmez. Kesin değil.")
# Aşırı uzamış 🚀 girişi (sinyal.asiri_uzama; bt/korn s1_kuyruk): BİLGİ notu, AL engellenmez
UZAMA_NOT = ("geçmişte bu tür 🚀 girişlerinin ~%13'ü %30+ kayıpla kapandı (diğerlerinde ~%1; taban günlerinde satılamadığı "
             "varsayımıyla), en büyük kazananların bir kısmı da bu grupta. Pozisyon büyüklüğüne dikkat.")


def kilit_metni(kt):
    """🔒 tek cümle (Telegram + pano aynı): '2 gündür taban, bugün gün boyu işlem neredeyse yok (kilitli). ...'"""
    if not kt:
        return ""
    if kt.get("kilitli_bugun"):
        m = f"{kt['seri']} gündür taban, bugün gün boyu işlem neredeyse yok (kilitli)"
        if not kt.get("kesin", True):
            m += " — gün içi veri, kapanışta kesinleşir"
    else:
        m = f"{kt['seri']} gündür taban, dün gün boyu işlem neredeyse yoktu (kilitli)"
    return "🔒 kilitli taban: " + m + ". " + KILIT_NOT


def uzama_metni(u):
    """Aşırı uzamış 🚀 girişi notu (JS uzamaMetin ile aynı)."""
    if not u:
        return ""
    ne = [f"52 hafta dibinin {('%g' % u['dipkat']).replace('.', ',')} katı"] if u.get("dipkat") and u["dipkat"] >= 5 else []
    if u.get("r6") is not None and u["r6"] >= 200:
        ne.append(f"6 ayda +%{u['r6']}")
    return "⚠️ Çok yükselmiş hisse (" + ", ".join(ne) + "): " + UZAMA_NOT


# 📏 Sıkı çizgi (sinyal.siki_cizgi; scratchpad cikis/c12, 2022-09…2026-10, aşırı uzamış 306 v3 pozisyonunda ilk kijun-altı kapanıştan
# sonraki 20 gün: %5'inde 4+ taban, %11'inde %25+ düşüş, %20'sinde %25+ yükseliş). BİLGİ notu: v3 kuralı/iz stop değişmez.
SIKI_NOT = ("Çok yükselmiş hissede bu seviyenin altında kapanış geçmişte bazen çöküşün habercisi oldu: benzer durumlarda sonraki "
            "20 günde ~%5'inde taban serisi (4+ taban) geldi, ~%11'inde fiyat %25+ düştü; ama ~%20'sinde %25+ yükselmeye devam etti. "
            "Kural değil, bilgi; asıl çıkış iz stop.")


def _sayi_tr(x):
    """4542.5 → '4.542,5' (en çok 2 ondalık; JS sayiTr ile aynı)."""
    t = f"{abs(x):,.2f}".rstrip("0").rstrip(".")
    return ("−" if x < 0 else "") + t.replace(",", "_").replace(".", ",").replace("_", ".")


def _gun_ay(t):
    """'2026-09-10' → '10.09'"""
    return f"{t[8:10]}.{t[5:7]}"


def siki_alt(sc):
    """Kesinleşmiş kijun-altı kapanış tarihleri (son 5 işlem günü): kapanış kesin değilse bugünkü sayılmaz (JS scAlt ile aynı)."""
    if not sc:
        return []
    a = list(sc.get("alt") or [])
    if a and sc.get("bugun") and sc.get("kesin") is False:
        a = a[:-1]
    return a


def siki_metni(sc):
    """📏 Sıkı çizgi notu (hisse penceresi 🚀 kutusu; JS scMetin ile aynı)."""
    if not sc:
        return ""
    sv = _sayi_tr(sc["s"]) + " TL"
    a = siki_alt(sc)
    simdi = bool(sc.get("bugun") and sc.get("kesin") is False)
    if a:
        m = f"📏 Sıkı çizginin altında kapandı ({', '.join(_gun_ay(x) for x in a)}). Sıkı çizgi şu an {sv} (kijun)."
    else:
        m = f"📏 Sıkı çizgi: {sv} (kijun)."
    if simdi:
        m += f" Fiyat şu an{' da' if a else ''} çizginin altında (gün içi; kapanışta kesinleşir)."
    if sc.get("ilk") and sc["ilk"] not in a and not (simdi and sc["ilk"] == (sc.get("alt") or [None])[-1]):
        m += f" Daha önce{' de' if (a or simdi) else ''} altında kapanmıştı (ilk kez {_gun_ay(sc['ilk'])})."
    if sc.get("u"):
        m += f" Hisse 🚀 girişinden sonra aşırı yükseldi (ilk kez {_gun_ay(sc['u'])}: 52 hafta dibinin 5+ katı ya da 6 ayda 3+ kat)."
    return m + " " + SIKI_NOT


def _sisme_ad(th, ad):
    """🎈 tetiklendi ama 20 günde hâlâ eksi: çöküş sonrası tepki tavanları — 'şişme' yanıltıcı (panodaki thDalga ile aynı)."""
    if (th.get("yuk20") or 0) < 0:
        return f"🎈 sert tavan-taban dalgalanması (düşüş sonrası, 20 günde %{th['yuk20']:.0f}): "
    return f"🎈 {ad}: "


def _bugun_tarih():
    return pd.Timestamp.now(tz="Europe/Istanbul").date()


def sd_dun(df, bugun_bari=True):
    """Portföy mesajları için destek/direnç DÜNKÜ kapanışa kadarki veriyle: fiyat desteği kırınca yeniden hesaplanan
    destek bir alttaki dibe kayar, kırılım görünmez olur (karar çizgisiyle aynı mantık). bugun_bari=True: son bar
    bugünün olmalı (yoksa hisse bugün henüz işlem görmedi → None; dünün olayları tekrar 'bugün' sayılmasın).
    bugun_bari=False (sabah): bugünden önceki son kapanışa kadarki veri. Bugünden önceki barlarla birlikte döner."""
    d = bolunme_duzelt(df)
    son_bugun = d.index[-1].date() == _bugun_tarih() if len(d) else False
    if bugun_bari and not son_bugun:
        return None, None
    gecmis = d.iloc[:-1] if son_bugun else d
    if len(gecmis) < 30:
        return None, None
    return destek_direnc(gecmis), d


def gunici_olaylar(s, df, pozisyon, fiyat=None):
    """Portföydeki bir hisse için o anki fiyatla olaylar: [(olay, seviye, bastırdığı hafif olaylar, metin)].
    fiyat: kontrol edilecek fiyat (varsayılan tablodaki son fiyat). Her olay+seviye günde bir kez gönderilir."""
    sd, d = sd_dun(df)
    if d is None:
        return []
    f = float(fiyat if fiyat is not None else s["fiyat"])
    dun = float(d["Close"].iloc[-2])
    hi = max(float(d["High"].iloc[-1]) if pd.notna(d["High"].iloc[-1]) else f, f)
    out = []
    ch = f / dun - 1
    kt = s.get("kt") or {}
    lo = float(d["Low"].iloc[-1]) if pd.notna(d["Low"].iloc[-1]) else f
    # 🔒 bugün 2. taban ve gün boyu kilitli: fiyat hâlâ günün dibinde (taban fiyatında) olmalı; 'taban' mesajının yerine geçer
    if kt.get("gun") == 0 and kt.get("kilitli_bugun") and ch <= TABAN_GETIRI and f <= lo * (1 + KILIT_ARALIK):
        out.append(("kilitli", 0, ("taban", "sert"), kilit_metni(kt)))
    elif ch <= TABAN_ESIK:
        out.append(("taban", 0, ("sert",), f"🟥 tabanda / tabana yakın: bugün {_yz(ch * 100)}"))
    elif ch >= TAVAN_ESIK:
        out.append(("tavan", 0, (), f"🟩 tavanda / tavana yakın: bugün {_yz(ch * 100)}"))
    elif ch <= SERT_DUSUS:
        out.append(("sert", 0, (), f"📉 sert düşüş: bugün {_yz(ch * 100)}"))
    th = s.get("tahta") or {}
    dun_th = (tahta_riski(d.iloc[:-1]) or {}) if th.get("seviye") else {}
    if th.get("seviye") == dun_th.get("seviye"):   # dün de aynıydı: günlük özette yazıyor, gün içi tekrar etme
        th = {}
    if th.get("seviye") == "sisme":   # tahtacı olay çalışması: 20 günde %25+ çakılma olasılığı normalin 7-8 katı
        out.append(("sisme", 0, (), _sisme_ad(th, "şişme işareti") + ", ".join(th.get("neden") or []) + ". Geçmişte bu durumdakilerin ~%15-19'u 20 günde %25+ çakıldı."))
    elif th.get("seviye") == "dagitim":   # ~4 kat
        out.append(("dagitim", 0, (), "⚠️ dağıtım işareti: " + ((th.get("neden") or [""])[0]) + ". Büyük satıcı çıkıyor olabilir (çakılma olasılığı ~4 kat)."))
    iz = s.get("iz") or {}
    if not pozisyon.get("uzun") and iz.get("stop") and not iz.get("cikti"):
        st = iz["stop"]
        if f < st:
            out.append(("iz_alti", st, ("iz_yakin",), f"⛔ <b>iz stop'un ({st} TL) altında.</b> Kural kapanışa bakar: kapanış da altında "
                                                       f"kalırsa çıkış zamanı (17:30-18:00 arası karar verebilirsin). Geçmişte gün içi iz stop altına inenlerin ~%44'ü "
                                                       f"kapanışta geri aldı; kapanışı beklemek ortalamada gün içinde satmaktan iyiydi."))
        elif f <= st * (1 + IZ_YAKIN):
            out.append(("iz_yakin", st, (), f"⚠️ iz stop'a yakın: {st} TL, {_yz((st / f - 1) * 100)} aşağıda. Kapanış bunun altında olursa çıkış."))
    if sd and sd.get("destek"):
        ds, tol = sd["destek"], sd["tol"] / 100
        S = ds["fiyat"]
        karar = round(S * (1 - tol), 2)
        tanim = f"destek {S} TL ({tarih_tr(ds['tarih'])} dibi" + (f", {ds['test']} kez test edildi)" if ds["test"] >= 2 else ")")
        if f < karar:
            out.append(("d_kirildi", S, ("d_sarkti", "d_yakin"), f"🔻 <b>desteği kırdı</b> (gün içi): {tanim}, karar çizgisi {karar} TL. "
                                                                 f"Kapanış {karar} TL altında kalırsa kırılım teyit olur."))
        elif f < S:
            out.append(("d_sarkti", S, ("d_yakin",), f"↘️ desteğin altına sarktı (gün içi): {tanim}. Karar çizgisi {karar} TL; kapanış belirleyici."))
        elif f <= S * (1 + tol) and dun > S * (1 + tol):
            out.append(("d_yakin", S, (), f"🔹 desteğe geldi: {tanim}, {_yz((S / f - 1) * 100)} aşağıda."))
    if sd and sd.get("direnc"):
        dr, tol = sd["direnc"], sd["tol"] / 100
        R = dr["fiyat"]
        tanim = f"direnç {R} TL ({tarih_tr(dr['tarih'])} tepesi)"
        if f > R * (1 + tol):
            out.append(("r_kirdi", R, ("r_dondu",), f"🔺 <b>direnci aştı</b> (gün içi): {tanim}. Kapanışta da üstünde kalırsa kırılım teyit olur."))
        elif hi >= R and f < R * (1 - tol) and dun < R * (1 - tol):   # gerçekten dirence değdi (bölge kenarı yetmez)
            out.append(("r_dondu", R, (), f"↩️ dirence dayanıp geri döndü: {tanim}, bugünkü tepe {round(hi, 2)} TL."))
    return out


def gunici_mesaj(satirlar, piyasa_satir=None):
    """satirlar: [(kod, fiyat, [metin, ...]), ...]; piyasa_satir: BIST 100 sert hareket günü portföy özeti."""
    govde = "\n\n".join(f"<b>{k}</b> {f} TL\n     " + "\n     ".join(m) for k, f, m in satirlar)
    if piyasa_satir:
        govde = piyasa_satir + ("\n\n" + govde if govde else "")
    return (f"📍 <b>Portföy — gün içi</b> <i>(~15 dk gecikmeli)</i>\n\n{govde}\n\n"
            f"<i>Kapanıştaki sonuç akşamki portföy özetinin başında yazar. {SD_NOT} Yatırım tavsiyesi değildir.</i>\n<a href=\"{PANO_URL}\">Panoyu aç</a>")


def seviye_satiri(kod, s, df, pozisyon):
    """☀️ Sabah mesajı için bir portföy hissesinin izleme seviyeleri (dünkü kapanışa göre)."""
    sd, d = sd_dun(df, bugun_bari=False)
    if d is None:
        return None
    gecmis = d[[x.date() < _bugun_tarih() for x in d.index]]
    if gecmis.empty:
        return None
    c = float(gecmis["Close"].iloc[-1])
    uz = lambda x: _yz((x / c - 1) * 100)
    parca, yakin = [], False
    if sd and sd.get("destek"):
        S = sd["destek"]["fiyat"]
        karar = round(S * (1 - sd["tol"] / 100), 2)
        parca.append(f"destek {S} ({uz(S)}) · karar çizgisi {karar}")
        yakin |= S / c - 1 > -0.02
    else:
        parca.append("altında yakın destek yok")
    if sd and sd.get("direnc"):
        R = sd["direnc"]["fiyat"]
        parca.append(f"direnç {R} ({uz(R)})")
        yakin |= R / c - 1 < 0.02
    iz = s.get("iz") or {}
    if not pozisyon.get("uzun") and iz.get("stop") and not iz.get("cikti"):
        parca.append(f"iz stop {iz['stop']} ({uz(iz['stop'])})")
        yakin |= iz["stop"] / c - 1 > -0.03
    elif not pozisyon.get("uzun") and iz.get("cikti"):
        parca.append(f"iz stop {iz['cikis_tarih']} tarihinde kırıldı")
    return f"{'👉 ' if yakin else ''}<b>{kod}</b> {c:g} TL" + (" · uzun vade" if pozisyon.get("uzun") else "") + "\n     " + " · ".join(parca)


def sabah_mesaji(satirlar):
    return ("☀️ <b>Portföy — günün seviyeleri</b> <i>(dünkü kapanışa göre)</i>\n\n" + "\n\n".join(satirlar) +
            "\n\n<i>👉 = fiyat bir seviyeye %2-3'ten yakın. Gün içinde destek/direnç/iz stop'a gelirse mesaj gelir; "
            "karar kapanışa göre. Yatırım tavsiyesi değildir.</i>")


def kapanis_sd(s, df, pozisyon):
    """Kesin kapanış sonrası: bugün destek/direnç bölgesine değen portföy hissesi için sonuç satırları."""
    sd, d = sd_dun(df)
    if d is None or not sd:
        return []
    c = float(d["Close"].iloc[-1])
    lo = min(float(d["Low"].iloc[-1]) if pd.notna(d["Low"].iloc[-1]) else c, c)
    hi = max(float(d["High"].iloc[-1]) if pd.notna(d["High"].iloc[-1]) else c, c)
    tol, out = sd["tol"] / 100, []
    if sd.get("destek") and lo < sd["destek"]["fiyat"]:
        S = sd["destek"]["fiyat"]
        karar = round(S * (1 - tol), 2)
        if c >= S:
            out.append(f"✅ gün içi desteğin ({S} TL) altına sarktı, <b>kapanışta geri aldı</b> (gün dibi {round(lo, 2)} TL).")
        elif c >= karar:
            out.append(f"↔️ desteğin ({S} TL) hafif altında kapadı ama karar çizgisinin ({karar} TL) üstünde: kırılım sayılmaz, yarın izle.")
        elif not pozisyon.get("uzun"):   # uzun vadede bu durum karar çizgisi mesajıyla ayrıca bildirilir
            out.append(f"🔻 <b>destek ({S} TL) kapanışta kırıldı</b> (karar çizgisi {karar} TL). Sistemin çıkış kuralı iz stop; "
                       f"kırılım tek başına sat sinyali değil ama pozisyonu gözden geçirme noktası.")
    if sd.get("direnc") and hi >= sd["direnc"]["fiyat"]:
        R = sd["direnc"]["fiyat"]
        if c > R * (1 + tol):
            out.append(f"🔺 <b>direnç ({R} TL) kapanışta aşıldı</b>: eski tepe artık destek olabilir.")
        elif c < R * (1 - tol):
            out.append(f"↩️ dirençten ({R} TL) döndü: gün içi {round(hi, 2)} TL'yi gördü, {c:g} TL'den kapadı.")
        else:
            out.append(f"🧱 direnç ({R} TL) bölgesinde kapadı: ne aştı ne döndü.")
    return out


MAX_AL_SATIR = 20  # Telegram mesajı 4096 karakterle sınırlı


def _al_satiri(s, pf):
    isaret = "❗" if s["kod"] in pf else "🟢"
    y = " ★AL+" if s["guclu"] else ""
    if s["kod"] in KUCUK_HISSELER:
        y += " 🔹küçük hisse (tahta sığ, sert oynar — lotu küçük tut)"
    h = f" 📈hacim {s['hacim_kat']}x" if s.get("hacim_teyit") else ""
    if s.get("bayrak"):
        h += f" 🚩bayrak (direk %{s['bayrak']['direk']})"
    if (s.get("uv") or {}).get("durum") == "AL":
        h += " 🌱UV"
    fk = f"F/K {s['fk']}" if s.get("fk") else "F/K —"
    lot = f", öneri {s['lot']} lot" if s.get("lot") else ""
    m = f", 20 günde {_yz(s['mom20'])}" if s.get("mom20") is not None else ""
    iz0 = round(s["fiyat"] * (1 - IZ_STOP_ORAN), 2)
    tk = s.get("tk") or {}
    kir = f"20 günlük zirve {tk['kirilim_seviye']} TL aşıldı, trend şablonunda" if tk.get("kirilim_seviye") else "trend kırılımı"
    t = (f"{isaret} <b>{s['kod']}</b>{y}{h}  {s['fiyat']} TL  ({fk}, RSI {s['rsi']}{m})\n"
         f"     🚀 {kir}. İz stop {iz0} TL (tepe kapanışın %20 altı, fiyat yükseldikçe yukarı taşınır){lot}")
    if tk.get("uzama"):   # bilgi notu, AL engellenmez
        t += "\n     " + uzama_metni(tk["uzama"])
    if s["kod"] in pf:
        t += "\n     " + plan_metni(s, pf[s["kod"]])
    return t


MOMENTUM_PAY = 0.20   # aylık momentum listesi: taranan hisselerin en güçlü %20'si


def momentum_listesi(sonuclar):
    """📈 Ayın güçlüleri: 6 aylık getiri (son ay hariç) sıralamasında ilk %20, sadece fiyatı 200 günlük ortalamanın
    üstündekiler; sadece BIST100 + EK_HISSELER. Gece testi (2022-26): her ay bu listeyi tutmak yüksek faizde çok güçlü, düşük faizde BIST100 gerisinde;
    v3 ile yarı yarıya 4 yılda +%717 / maks düşüş −%21 (v3 tek başına +%562 / −%25). Bilgi, AL sinyali değil."""
    # evren: testteki gibi BIST100 + EK_HISSELER (küçük hisseler ve yeni arzlar hariç: tepede şişirilmiş hisseler çıkıyordu)
    buyuk = set(BIST100) | set(EK_HISSELER)
    tum = [s for s in sonuclar if s.get("mom6") is not None and s["kod"] in buyuk]
    n = max(1, int(len(tum) * MOMENTUM_PAY))
    aday = sorted((s for s in tum if s.get("s200_ust")), key=lambda s: -s["mom6"])
    return [s["kod"] for s in aday[:n]]


def momentum_mesaji(kodlar, by, ay, piyasa=None, onceki=None):
    onceki = set(onceki or [])
    satir = [f"{i}. <b>{k}</b> (6 ayda {_yz(by[k]['mom6'])})" + (" 🆕" if onceki and k not in onceki else "")
             for i, k in enumerate(kodlar[:25], 1) if k in by]
    parca = [f"📈 <b>Ayın güçlüleri — {ay}</b> (son 6 ayın en güçlü %{int(MOMENTUM_PAY * 100)}'si, {len(kodlar)} hisse)",
             "\n".join(satir) + (f"\n…ve {len(kodlar) - 25} hisse daha (panoda 📈)" if len(kodlar) > 25 else "")]
    cikan = sorted(onceki - set(kodlar))
    if cikan:
        parca.append("Listeden çıkanlar: " + ", ".join(cikan[:30]))
    if piyasa and piyasa.get("zayif"):
        parca.append("⚠️ Piyasa zayıf: testte bu durumda liste alınmadı (nakitte beklendi).")
    parca.append("<i>Bilgi amaçlı, AL sinyali değil. Testte ayda bir bu listeyi tutmak yüksek faiz döneminde çok iyi, düşük faiz "
                 "döneminde endeksin gerisindeydi. Yatırım tavsiyesi değildir.</i>")
    return "\n\n".join(parca)


def uv_mesaji(uv_al, uv_sat, pf):
    """🌱 Uzun vade sinyal değişimleri (kapanış sonrası): yeni AL'ler (tümü), SAT'lar (portföydekiler)."""
    parca = [f"🌱 <b>Uzun vade sinyali</b> — {pd.Timestamp.now(tz='Europe/Istanbul').strftime('%d.%m.%Y')}"]
    if uv_al:
        satir = []
        for s in sorted(uv_al, key=lambda x: (x["kod"] not in pf, x["kod"])):
            isaret = "❗" if s["kod"] in pf else "🌱"
            satir.append(f"{isaret} <b>{s['kod']}</b> {s['fiyat']} TL — yükselen trendde 50 günlük ortalamaya ({s['uv']['sma50']}) "
                         f"geri çekilip döndü. Çıkış: 2 gün üst üste 200 günlük ortalamanın ({s['uv']['sma200']}) altında kapanış.")
        parca.append(f"<b>Uzun vade AL ({len(uv_al)})</b>\n" + "\n".join(satir))
    if uv_sat:
        satir = [f"❗ <b>{s['kod']}</b> {s['fiyat']} TL — 2 gündür 200 günlük ortalamanın ({s['uv']['sma200']}) altında: uzun vadeli trend bozuldu."
                 for s in uv_sat]
        parca.append("<b>Portföyünde uzun vade SAT</b>\n" + "\n".join(satir))
    parca.append(f"<a href=\"{PANO_URL}\">Panoyu aç</a>\n<i>Backtest: düşük faiz döneminde işlem başı endekse göre +%10.7, isabet %65 "
                 f"(ortalama 3-4 ay tutuş). Yatırım tavsiyesi değildir.</i>")
    return "\n\n".join(parca)


def telegram_mesaji(yeni_al, yeni_sat, sat_teyit, pf, uyari, piyasa=None, karar_kirilan=None, on_kapanis=False, iptal=None,
                    diger_al=None):
    tarih = pd.Timestamp.now(tz="Europe/Istanbul").strftime("%d.%m.%Y %H:%M")
    parca = [f"📊 <b>BIST Sinyal</b> — {tarih}"]
    if yeni_al:
        # portföydekiler önce; sonra son 20 günde az yükselmiş olan önce (portföy simülasyonunda en iyi öncelik kuralı)
        sirali = sorted(yeni_al, key=lambda x: (x["kod"] not in pf, x["mom20"] if x.get("mom20") is not None else 0))
        gosterilen = [s for s in sirali if s["kod"] in pf] + [s for s in sirali if s["kod"] not in pf][:MAX_AL_SATIR]
        satir = [_al_satiri(s, pf) for s in gosterilen]
        kalan = len(sirali) - len(gosterilen)
        if kalan:
            satir.append(f"…ve {kalan} hisse daha (panoya bak)")
        bas = f"<b>Yeni AL — 🚀 trend kırılımı ({len(yeni_al)})</b>"
        if on_kapanis:
            _s = pd.Timestamp.now(tz="Europe/Istanbul")
            bas += (f"\n⏰ <i>Kapanıştan önce (~{(_s - pd.Timedelta(minutes=gunici.GECIKME)).strftime('%H:%M')} fiyatlarıyla). "
                    f"{gk_metni(gk_oran(_s))} Tutmazsa 18:30'dan sonra iptal mesajı gelir.</i>")
        bas += f"\n💡 <i>{GK_NOT}</i>"
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
            satir.append(f"❗ <b>{s['kod']}</b>  {s['fiyat']} TL  (RSI {s['rsi']})\n     " + plan_metni(s, pf[s["kod"]]))
        parca.append("🔴 <b>Portföyünde SAT'a dönenler</b> <i>(bilgi — çıkış kuralı iz stop)</i>\n" + "\n".join(satir))
    if sat_teyit:   # v2: iz stop kırılanlar (çıkış zamanı)
        satir = [f"📉 <b>{s['kod']}</b>  {s['fiyat']} TL — kapanış iz stop'un altında: <b>kurala göre çıkış zamanı.</b>\n     "
                 + plan_metni(s, pf[s["kod"]]) for s in sat_teyit]
        parca.append("📉 <b>İz stop kırıldı</b>\n" + "\n".join(satir))
    if diger_al:
        parca.append(f"<i>Trend dışı AL ({len(diger_al)}, v2 filtresine takıldı — bilgi):</i> "
                     + ", ".join(f"{s['kod']} {s['fiyat']}" for s in diger_al[:25]) + (" …" if len(diger_al) > 25 else ""))
    if iptal:
        satir = [(f"↩️ <b>{s['kod']}</b>: kapanıştan önce gelen <b>🚀 AL</b> (trend kırılımı) kapanışta tutmadı "
                  f"({s['fiyat']} TL) — geçersiz say.") if eski == "AL" else
                 (f"↩️ <b>{s['kod']}</b>: kapanıştan önce gelen <b>{eski}</b> sinyali kapanışta tutmadı "
                  f"(şimdi {s['sinyal']}, {s['fiyat']} TL) — geçersiz say.") for s, eski in iptal]
        parca.append("↩️ <b>İptal: kapanışta tutmayan sinyaller</b>\n" + "\n".join(satir))
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


BIST100_GECERLI = "2026-12-31"   # BIST100 listesinin geçerli olduğu dönemin sonu (Borsa İstanbul 3 ayda bir değiştirir)
HALKA_ARZ_GUNCEL = "2026-09-26"  # HALKA_ARZ listesinin en son kontrol edildiği gün (ayda bir: halkarz.com)


def bakim_notu(simdi):
    """Haftalık özete: liste bakımının vakti geldiyse kullanıcıya hatırlatma (Claude'a söyleyeceği cümleyle)."""
    bugun = simdi.strftime("%Y-%m-%d")
    notlar = []
    if bugun > BIST100_GECERLI:
        notlar.append("BIST 100 listesinin dönemi bitti (endeks bileşimi değişti)")
    if (pd.Timestamp(bugun) - pd.Timestamp(HALKA_ARZ_GUNCEL)).days > 35:
        notlar.append("halka arz listesi bir aydır kontrol edilmedi")
    if not notlar:
        return None
    return ("🔧 <b>Bakım zamanı:</b> " + "; ".join(notlar) + ". Claude'a \"BIST 100 ve halka arz listelerini güncelle\" "
            "demen yeterli.")


def haftalik_ozet(sonuclar, pf, acik, kapali, simdi):
    """Cuma kapanıştan sonra: haftanın AL'leri, canlı karnenin haftası, portföyün haftalık değişimi."""
    pazartesi = (simdi - pd.Timedelta(days=simdi.weekday())).strftime("%Y-%m-%d")
    parca = [f"🗓 <b>Haftalık özet</b> — {pazartesi} haftası"]
    al = sorted((s for s in sonuclar if (s.get("tk") or {}).get("durum") == "AL" and (s["tk"].get("giris_tarih") or "") >= pazartesi),
                key=lambda s: -(s["tk"].get("degisim") or 0))
    if al:
        parca.append(f"<b>Bu haftanın 🚀 AL'leri ({len(al)})</b>: " + ", ".join(
            f"{s['kod']} ({_yz(s['tk'].get('degisim') or 0)})" for s in al[:10]) + (" …" if len(al) > 10 else ""))
    else:
        parca.append("Bu hafta 🚀 AL gelmedi (piyasa zayıfken kural gereği AL gelmez).")
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
    bn = bakim_notu(simdi)
    if bn:
        parca.append(bn)
    parca.append(f"<a href=\"{PANO_URL}\">Panoyu aç</a> · <a href=\"{PANO_URL}gecmis.html\">Karne</a>\n"
                 f"<i>Yatırım tavsiyesi değildir.</i>")
    return "\n\n".join(parca)


def portfoy_ozeti(sonuclar, pf, piyasa=None, endeks=None, sd_satir=None):
    """Günde bir kez (kapanıştan sonra) portföyün tamamı: sinyal, K/Z, çıkış ve hedefler, dikkat notları.
    sd_satir: bugün destek/direnç seviyesine değen hisselerin kapanış sonucu (kapanis_sd) — özetin başında."""
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
        if (s.get("iz") or {}).get("cikti") and not p.get("uzun"):
            sn += " · 📉 iz stop kırıldı"
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
        if s.get("trend_asagi"):
            notlar.append("📉 trend aşağı (fiyat düşen 200 günlük ortalamanın altında): geçmişte bu durumdakiler sonraki 3 ayda "
                          "çoğunlukla endeksin gerisinde kaldı (özellikle düşük faiz döneminde)")
        if s.get("patlak"):
            notlar.append(f"⚠️ taban serisi ({s['taban15']} kez/15 gün)")
        if s.get("kt"):
            notlar.insert(0, kilit_metni(s["kt"]))
        sc = (s.get("tk") or {}).get("sc") if (s.get("tk") or {}).get("durum") == "AL" else None
        if siki_alt(sc):   # 📏 aşırı uzamış 🚀 pozisyonunda son 5 günde sıkı çizgi (kijun) altında kapanış — bilgi
            notlar.append(f"📏 sıkı çizginin altında kapandı ({', '.join(_gun_ay(x) for x in siki_alt(sc))}; çizgi {_sayi_tr(sc['s'])} TL, kijun) — "
                          "çok yükselmiş hissede geçmişte bazen çöküş habercisi oldu (20 günde ~%5 taban serisi, ~%11 %25+ düşüş), "
                          "ama ~%20'sinde %25+ yükseliş sürdü; kural değil, asıl çıkış iz stop")
        th = s.get("tahta") or {}
        if th.get("seviye") == "sisme":
            notlar.append(_sisme_ad(th, "şişme riski") + ", ".join(th["neden"]) + " — geçmişte bu durumdakilerin ~%15-19'u 20 günde %25+ çakıldı; iz stop'u sıkı takip et")
        elif th.get("seviye") == "dagitim":
            notlar.append("⚠️ dağıtım işareti: " + th["neden"][0] + " — büyük satıcı çıkıyor olabilir")
        b = s.get("bilanco")
        if bilanco_yakin(b, 7):
            ne = "" if b["sonraki"]["kaynak"] == "yahoo" else " en geç"
            notlar.append(f"📅 bilanço{ne} {tarih_tr(b['sonraki']['tarih'])} ({b['kalan_gun']} gün) — o gün fiyat sert oynayabilir")
        if s.get("bolunme") and (pd.Timestamp.now(tz="Europe/Istanbul").tz_localize(None) - pd.Timestamp(s["bolunme"])).days <= 30:
            notlar.append(f"✂️ {tarih_tr(s['bolunme'])} bedelsiz/bölünme görünüyor — maliyetini aracı kurumdaki yeni maliyetle güncelle")
        od = s.get("od")
        if od:
            notlar.append(f"🔻 son {od['u']} günde hisseye özel hacimli düşüş ({_yzd(od['r'])}, BIST 100 {_yzd(od['xu'])}) — geçmişte "
                          "bu durumdakilerin sonraki 20 günde ancak ~%38'i endeksi geçti (normalde ~%46; 2022-23 düşük faizde fark yoktu); kesin değil")
        tm = s.get("temettu")
        if tm and tm.get("ex_kalan") is not None and tm["ex_kalan"] <= 7:
            notlar.append(f"💰 temettü hak kullanım {tarih_tr(tm['ex_tarih'])} ({tm['ex_kalan']} gün) — o sabah fiyat temettü kadar düşük açılır, stop'a dikkat")
        ikon = "🔴" if s["sinyal"] == "SAT" else ("🟢" if s["sinyal"] == "AL" else "🟡")
        parca.append(f"{ikon} <b>{kod}</b> {s['fiyat']} TL — {sn}" + (" · " + " · ".join(notlar) if notlar else "")
                     + "\n     " + plan_metni(s, p)
                     + (f"\n     📊 {bilanco_metni(b)}" if b and bilanco_metni(b) else ""))
    parca.insert(1, f"Toplam K/Z: <b>{_tl(toplam)}</b>")
    # 🛡️ Risk: her pozisyon kendi çıkış seviyesine (iz stop; uzun vadede karar çizgisi) inerse bugünkü değerden kayıp
    deger = risk = 0.0
    kapsam = 0
    for kod, p in pf.items():
        s = by.get(kod)
        if not s:
            continue
        deger += s["fiyat"] * p["adet"]
        pl = pozisyon_plani(s, p)
        cikis = pl.get("karar") if pl["uzun"] else pl.get("stop")
        if cikis and cikis < s["fiyat"]:
            risk += (cikis - s["fiyat"]) * p["adet"]
            kapsam += 1
    if kapsam and deger:
        parca.insert(2, f"🛡️ Her pozisyon çıkış seviyesine (iz stop / karar çizgisi) inerse: <b>{_tl(risk)}</b> "
                        f"(bugünkü portföy değerine göre %{abs(risk) / deger * 100:.1f}" +
                        (f"; {len(pf) - kapsam} hissede seviye yok ya da zaten aşıldı)" if kapsam < len(pf) else ")"))
    kiyas = endeks_kiyas(pf, by, endeks)
    if kiyas:
        kapsam = "" if kiyas["n"] == kiyas["toplam_n"] else f" (alış tarihi girilen {kiyas['n']}/{kiyas['toplam_n']} hisse)"
        yon = "önünde" if kiyas["fark"] >= 0 else "gerisinde"
        parca.insert(2, f"📈 Endeksle kıyas{kapsam}: portföy {_yzd(kiyas['pf_yuzde'])} · aynı parayla aynı günlerde BIST 100 "
                        f"{_yzd(kiyas['xu_yuzde'])} → endeksin <b>{abs(kiyas['fark']):.1f} puan {yon}</b>")
    dag = sektor_dagilimi(pf, by)
    if dag:
        metin = ", ".join(f"{ad} %{pay:.0f}" for ad, pay in dag[:4])
        if len(pf) >= 2 and dag[0][1] > YOGUNLASMA_ESIGI:
            metin = f"⚠️ Portföyünün <b>%{dag[0][1]:.0f}</b>'i tek sektörde ({dag[0][0]}) — o sektördeki bir haber hepsini birlikte etkiler.\n     " + metin
        parca.insert(2, "Dağılım: " + metin)
    hs = [(kod, hareket_satiri(by[kod].get("hr"))) for kod in sorted(pf) if kod in by]
    hs = [f"<b>{k}</b> {m}" for k, m in hs if m]
    if hs:   # sadece eşiği geçenler (1 günde endeksten ≥4 puan ayrışan, sektörüyle açıklanmayan); yoksa satır yok
        parca.insert(1, "🔎 <b>Bugün hisseye özel hareket</b>: " + " · ".join(hs))
    if sd_satir:
        parca.insert(1, "📍 <b>Bugün destek/direnç (kapanış)</b>\n" + "\n".join(sd_satir) + f"\n<i>{SD_NOT}</i>")
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


def gecmis_guncelle(by_kod, bugun, piyasa=None, yeni_kayit=True):
    """Canlı karne, canlıdaki (v3) kuralların aynısını ölçer: 🚀 trend kırılımında gir (şablon + 20g zirve, piyasa
    zayıf değil, aşırı oynak/taban serisi değil); iz stop (kayıttan beri tepe kapanışın %20 altı) kırılınca çık.
    Yeni kayıt sadece kesin kapanışla (yeni_kayit). (Eylül 2026 öncesi kayıtlar eski kurallarla açıldı.)"""
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
        r["tepe"] = max(r.get("tepe") or r["giris_fiyat"], s["fiyat"])
        r["stop"] = round(r["tepe"] * (1 - IZ_STOP_ORAN), 2)
        if s["fiyat"] < r["stop"]:
            _kapa(r, s["fiyat"], "iz stop", bugun)

    acik = {r["kod"] for r in kayitlar if r["durum"] == "açık"}
    kayitli = {(r["kod"], r.get("sinyal_tarih")) for r in kayitlar}
    for kod, s in by_kod.items():
        tk = s.get("tk") or {}
        if (yeni_kayit and tk.get("durum") == "AL" and (tk.get("gun") or 0) <= 1 and not s.get("patlak") and s.get("fiyat")
                and kod not in acik and (kod, tk.get("giris_tarih")) not in kayitli):
            kayitlar.append({"kod": kod, "giris_tarih": bugun, "giris_fiyat": s["fiyat"],
                             "stop": round(s["fiyat"] * (1 - IZ_STOP_ORAN), 2), "tepe": s["fiyat"], "durum": "açık",
                             "guncel": s["fiyat"], "anlik": 0.0,
                             "sinyal_tarih": tk.get("giris_tarih"), "kural": "v3",
                             "piyasa": "zayıf" if (piyasa and piyasa.get("zayif")) else "normal",
                             "hacim": bool(s.get("hacim_teyit"))})

    with open(GECMIS, "w", encoding="utf-8") as f:
        json.dump({"kayitlar": kayitlar}, f, ensure_ascii=False, indent=2)

    acik = [r for r in kayitlar if r["durum"] == "açık"]
    kapali = [r for r in kayitlar if r["durum"] == "kapalı"]
    def _istat(ac, ka):
        x = [r["sonuc"] for r in ka if r.get("sonuc") is not None]
        return {"isabet": round(sum(1 for v in x if v > 0) / len(x) * 100, 1) if x else 0,
                "kapanan": len(ka), "ort": round(sum(x) / len(x), 1) if x else 0, "acik": len(ac)}
    # karne kartları sadece canlı kural (v3) kayıtlarını sayar; eski kurallarla açılmışlar ayrı özet
    v3 = lambda r: r.get("kural") == "v3"
    ozet = _istat([r for r in acik if v3(r)], [r for r in kapali if v3(r)])
    ozet["eski"] = _istat([r for r in acik if not v3(r)], [r for r in kapali if not v3(r)])
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

    _sim = pd.Timestamp.now(tz="Europe/Istanbul")
    # 📊 gün içi görünüm: seans dışında önceki panonun tamamlanmış son seans durumu yeniden kullanılır (indirme kısa kalır)
    gi = gunici.yeniden_kullan(_sim)
    _ara = {}
    data = veri_cek(KODLAR, kesin_kapanis=_sim.hour * 60 + _sim.minute >= KAPANIS_DAKIKA or _sim.weekday() >= 5,
                    gunici_gun=None if gi else gunici.GUN, ara=_ara)
    if gi:
        print(f"Gün içi görünüm: önceki panodan ({gi['t']}).")
    elif "15m" in _ara:
        try:
            _t0 = time.time()
            gi = gunici.hesapla(_ara["15m"], KODLAR, _sim)
            print(f"Gün içi görünüm: {len(gi['v']) if gi else 0} hisse ({time.time() - _t0:.1f} sn).")
        except Exception as e:   # gün içi görünüm taramayı asla bozmasın
            print(f"Gün içi görünüm hesaplanamadı ({type(e).__name__}).")
            gi = None
    _ara.clear()
    piyasa = piyasa_durumu(data)
    endeks = endeks_serisi(data)
    oranlar = oranlari_al(KODLAR)
    bilancolar = bilancolari_al(KODLAR)
    kap_hisse, kap_yeni = kap_guncelle(KODLAR)
    try:   # v3 piyasa filtresi (günlük seri): BIST 100 > 50 günlük ortalama
        _xu = data[ENDEKS + ".IS"]["Close"].dropna()
        xu_ust = _xu > _xu.rolling(50).mean()
    except Exception:
        _xu = xu_ust = None
    # 🔒 kilitli taban: seans içinde Yahoo'nun gün içi Yüksek/Düşük'ü o ana kadarki işlemler → 'şu ana kadar kilitli';
    # kesin kapanıştan sonra (18:30+) ya da son bar bugünün değilse kesin
    _kesin = _sim.hour * 60 + _sim.minute >= KAPANIS_DAKIKA or _sim.weekday() >= 5
    sonuclar, yeni_arzlar = [], []
    for kod in KODLAR:
        try:
            df = data[kod + ".IS"].dropna(subset=["Close"])
            if df.empty:
                continue
            arz = arz_bilgisi(kod, df)
            _bk = bool(_kesin or df.index[-1].date() != _sim.date())   # son günlük mum kesin mi (vadeler: hafta/ay tamam mı)
            a = analiz_et(df, xu_ust, _xu, bar_kesin=_bk, bugun=_sim.date())
            if not a:
                if arz:
                    yeni_arzlar.append(arz)   # sinyal için geçmiş henüz yetersiz
                continue
            a["kod"] = kod
            a["arz"] = arz
            if a.get("kt"):
                a["kt"]["kesin"] = _bk
            if (a.get("tk") or {}).get("sc"):
                a["tk"]["sc"]["kesin"] = _bk   # 📏 bugünkü kijun-altı fiyat kapanışta mı (seans içinde 'şu an altında')
            if (a.get("tk") or {}).get("bugun") and not _bk:
                a["tk"]["gk"] = gk_oran(_sim)   # kesin kapanıştan önce görünen 🚀: o saatte kapanışta tutma oranı
            o = oranlar.get(kod, [None, None, None])
            a["fk"] = o[0] if len(o) > 0 else None
            a["pddd"] = o[1] if len(o) > 1 else None
            a["favok"] = o[2] if len(o) > 2 else None
            a["sektor"] = o[3] if len(o) > 3 else None
            a["endustri"] = o[4] if len(o) > 4 else None
            a["bilanco"] = bilanco_ozet(bilancolar.get(kod))
            a["temettu"] = temettu_ozet(bilancolar.get(kod), a["fiyat"])
            a["kap"] = kap_hisse.get(kod)
            a["lot"] = lot_oner(a["fiyat"], a["fiyat"] * (1 - IZ_STOP_ORAN))   # risk: iz stop başlangıcı
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
    kiyas_gruplari(sonuclar)                       # sektör kıyas grubu (pano da kullanır)
    hr_hepsi = hareket_hepsi(sonuclar, endeks)     # 1/5/20 gün hareket açıklaması (pano JS 'hareket' ile aynı)
    for s in sonuclar:
        s["hr"] = hr_hepsi.get(s["kod"])
        s["od"] = ozel_dusus(s["hr"])

    bugun_al = [s for s in sonuclar if s["sinyal"] == "AL"]
    simdi = pd.Timestamp.now(tz="Europe/Istanbul")
    dakika = simdi.hour * 60 + simdi.minute
    kapanis_zamani = dakika >= KAPANIS_DAKIKA                              # kesin kapanış fiyatı geldi
    kapanis_sonrasi = dakika >= SINYAL_DAKIKA or not SADECE_KAPANIS_MESAJI  # AL/SAT değerlendirme penceresi
    on_kapanis = SADECE_KAPANIS_MESAJI and SINYAL_DAKIKA <= dakika < KAPANIS_DAKIKA
    bugun_iso = simdi.strftime("%Y-%m-%d")
    durum = durum_oku()
    son = dict(durum.get("son", {}))
    by_kod = {s["kod"]: s for s in sonuclar}
    # kapanıştan önce verilen sinyaller: kapanışta tutmayanlar iptal edilir, durum geri alınır
    on_sinyal = {k: v for k, v in durum.get("on_sinyal", {}).items() if v.get("tarih") == bugun_iso}
    iptal = []
    if kapanis_zamani:
        for k, v in on_sinyal.items():
            s = by_kod.get(k)
            if s and s["sinyal"] != v["sinyal"]:
                iptal.append((s, v["sinyal"]))
                if v.get("onceki") is None:
                    son.pop(k, None)
                else:
                    son[k] = v["onceki"]
        on_sinyal = {}
    son_once = dict(son)
    if kapanis_sonrasi:
        yeni, yeni_sat = sinyal_degisimleri(sonuclar, son)
    else:
        yeni, yeni_sat = [], []   # 'son' değişmez: geçişler 17:30'dan sonra değerlendirilir
    if on_kapanis:
        for s in yeni + yeni_sat:
            on_sinyal[s["kod"]] = {"sinyal": s["sinyal"], "onceki": son_once.get(s["kod"]), "tarih": bugun_iso}
    # v3: AL mesajı gösterge oylamasından (SINYAL) değil, 🚀 trend kırılımından. SINYAL'in AL'i/iptali artık mesaj
    # değil; SAT (portföy) bilgi olarak kalır.
    iptal = [(s, eski) for s, eski in iptal if eski == "SAT" and s["kod"] in pf]
    tk_d = durum.get("tk_gonderilen") or {}
    tk_gonderilen = set(tk_d.get("kodlar", [])) if tk_d.get("tarih") == bugun_iso else set()
    tk_aday = [s for s in sonuclar if (s.get("tk") or {}).get("bugun")]
    _riskli = lambda s: s.get("patlak") or s.get("kt") or ((s.get("tahta") or {}).get("seviye") == "sisme")
    patlak_al = [s for s in tk_aday if _riskli(s)]
    tk_aday = [s for s in tk_aday if not _riskli(s)]                      # taban serisi / 🔒 kilitli taban / 🎈 şişme: AL mesajı yok
    if kapanis_zamani:   # kapanıştan önce gönderilip kapanışta tutmayan kırılımlar
        tutan = {s["kod"] for s in tk_aday}
        iptal += [(by_kod[k], "AL") for k in sorted(tk_gonderilen - tutan) if k in by_kod]
        tk_gonderilen &= tutan
    yeni = [s for s in tk_aday if s["kod"] not in tk_gonderilen] if kapanis_sonrasi else []
    tk_gonderilen |= {s["kod"] for s in yeni}
    diger_al = []
    yeni_sat = [s for s in yeni_sat if s["kod"] in pf]   # SAT mesajı sadece portföydekiler için

    # v2: portföyde iz stop kırılımı (uzun vade hariç) — kesin kapanıştan sonra, her AL dalgası için bir kez.
    # durum.json herkese açık: anahtarlar gizli özetle (HMAC); ilk çalışmada sessiz başlangıç kaydı.
    ilk_kez = "iz_kirilim_g" not in durum
    iz_kayit = set(durum.get("iz_kirilim_g", []))
    sat_teyit = []   # mesajda "iz stop kırıldı" bölümü
    for s in (sonuclar if kapanis_zamani else []):
        p = pf.get(s["kod"])
        iz = s.get("iz") or {}
        if not p or p.get("uzun") or not iz.get("cikti"):
            continue
        gk = _gizli(f"iz|{s['kod']}|{s.get('al_tarih')}")
        if gk not in iz_kayit:
            iz_kayit.add(gk)
            if not ilk_kez:
                sat_teyit.append(s)

    # Uzun vade: karar çizgisi (ana destek) KAPANIŞLA kırılınca bir kez uyar. Karar çizgisi hep fiyatın altındaki
    # en yakın destekten hesaplandığı için, DÜNKÜ veriyle hesaplanan çizgiyle kıyaslanır (dosyaya fiyat yazılmaz:
    # fiyat hisseyi ele verir). Uyarılan seviyeler gizli özetle tutulur. Sadece kesin kapanıştan sonra.
    kirilim = set(durum.get("karar_kirilim_g", []))
    karar_kirilan = []
    if kapanis_zamani:
        for s in sonuclar:
            p = pf.get(s["kod"])
            if not (p and p.get("uzun")):
                continue
            try:
                df = data[s["kod"] + ".IS"].dropna(subset=["Close"])
                sd_dun = destek_direnc(bolunme_duzelt(df).iloc[:-1])
            except Exception:
                continue
            if not sd_dun.get("destek"):
                continue
            dun_karar = round(sd_dun["destek"]["fiyat"] * (1 - sd_dun["tol"] / 100), 2)
            gk = _gizli(f"{s['kod']}|{sd_dun['destek']['tarih']}|{sd_dun['destek']['fiyat']}")
            if s["fiyat"] < dun_karar and gk not in kirilim:
                kirilim.add(gk)
                karar_kirilan.append((s, dun_karar))

    uyari = None
    if len(yeni) > ASIRI_ISLEM_ESIGI:
        uyari = (f"Bu taramada {len(yeni)} yeni AL var — çok fazla. Hepsini alma; en yüksek puanlı/AL+ "
                 f"birkaçına odaklan, aşırı işlem komisyonda eritir.")


    # 📈 Ayın güçlüleri: ayın ilk kesin kapanış taramasında yeni liste + Telegram (ilk çalışmada sessiz)
    mom = dict(durum.get("mom_ay") or {})
    ay = simdi.strftime("%Y-%m")
    if kapanis_zamani and simdi.weekday() < 5 and mom.get("ay") != ay:
        yeni_liste = momentum_listesi(sonuclar)
        if mom and tg_gonder(momentum_mesaji(yeni_liste, by_kod, simdi.strftime("%m.%Y"), piyasa, mom.get("kodlar"))):
            print(f"Telegram: ayın güçlüleri ({len(yeni_liste)} hisse).")
        mom = {"ay": ay, "kodlar": yeni_liste}
    for s in sonuclar:
        s["momentum"] = s["kod"] in set(mom.get("kodlar") or [])

    # Sinyal geçmişi (canlı karne): yeni AL'leri kaydet, açıkları stop/SAT ile kapat
    acik, kapali, karne = gecmis_guncelle(by_kod, bugun_iso, piyasa, kapanis_zamani)
    with open("gecmis.html", "w", encoding="utf-8") as f:
        f.write(gecmis_uret(acik, kapali, karne))

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(pano_uret(sonuclar, ornek=False, uyari=uyari, piyasa=piyasa, yeni_arzlar=yeni_arzlar, endeks=endeks,
                          gunici=gi))
    print(f"index.html: {len(sonuclar)} hisse (+{len(yeni_arzlar)} yeni arz), {len(bugun_al)} AL, {len(yeni)} yeni | "
          f"taban serisi: {sum(1 for s in sonuclar if s.get('patlak'))} | "
          f"piyasa: {'zayıf' if piyasa and piyasa['zayif'] else 'normal'} | "
          f"karne: {karne['kapanan']} kapanan, {karne['acik']} açık.")
    if patlak_al:
        print(f"Taban serisi / kilitli taban / şişme {len(patlak_al)} hissenin AL mesajı gönderilmedi.")

    if yeni or yeni_sat or sat_teyit or karar_kirilan or iptal or diger_al:
        print(f"Telegram: {len(yeni)} yeni AL (+{len(diger_al)} trend dışı), {len(yeni_sat)} portföy SAT, {len(sat_teyit)} iz stop kırılımı, "
              f"{len(karar_kirilan)} karar çizgisi kırılımı, {len(iptal)} iptal.")
        tg_gonder(telegram_mesaji(yeni, yeni_sat, sat_teyit, pf, uyari, piyasa, karar_kirilan, on_kapanis, iptal, diger_al))
    else:
        print("Yeni AL / portföyde SAT yok, Telegram sessiz." if kapanis_sonrasi
              else "Gün içi tarama: AL/SAT mesajları kapanış sonrası taramada gönderilir.")

    # 🌱 Uzun vade sinyali: sadece kesin kapanışla (18:30+) değerlendirilir; ilk çalışmada sessiz başlangıç kaydı
    uv_son = dict(durum.get("uv_son", {}))
    if kapanis_zamani:
        uv_ilk = "uv_son" not in durum
        uv_al, uv_sat = [], []
        for s in sonuclar:
            u = (s.get("uv") or {}).get("durum")
            if not u:
                continue
            onceki = uv_son.get(s["kod"])
            uv_son[s["kod"]] = u
            if uv_ilk or onceki is None or onceki == u:
                continue
            if u == "AL" and not s.get("patlak"):
                uv_al.append(s)
            elif u == "SAT" and s["kod"] in pf:
                uv_sat.append(s)
        if uv_al or uv_sat:
            print(f"Telegram: {len(uv_al)} uzun vade AL, {len(uv_sat)} portföy uzun vade SAT.")
            tg_gonder(uv_mesaji(uv_al, uv_sat, pf))

    # Fiyat alarmları: her taramada (gün içi de) kontrol edilir, her alarm bir kez çalar
    tetiklenen = set(durum.get("alarm_tetik", []))
    alarm_yeni = alarm_kontrol(alarmlari_yukle(), by_kod, tetiklenen)
    if alarm_yeni:
        print(f"Telegram: {len(alarm_yeni)} fiyat alarmı.")
        if not tg_gonder(alarm_mesaji(alarm_yeni)):
            for a, _ in alarm_yeni:
                tetiklenen.discard(_alarm_anahtar(a))   # gönderilemediyse sonraki taramada yeniden dene

    # ☀️ Sabah: günün seviyeleri (günün ilk taraması, en geç 12:00; günde bir kez)
    sabah_tarih = durum.get("sabah_tarih")
    if pf and simdi.weekday() < 5 and dakika < 12 * 60 and sabah_tarih != bugun_iso:
        satirlar = []
        for kod in sorted(pf):
            try:
                df = data[kod + ".IS"].dropna(subset=["Close"])
                m = seviye_satiri(kod, by_kod[kod], df, pf[kod]) if kod in by_kod and not df.empty else None
            except Exception:
                m = None
            if m:
                satirlar.append(m)
        if not satirlar or tg_gonder(sabah_mesaji(satirlar)):
            sabah_tarih = bugun_iso
            if satirlar:
                print("Telegram: sabah seviyeleri.")
    # 📍 Portföy gün içi: destek/direnç, iz stop, taban/tavan (hafta içi 10:15-18:10). Her olay günde bir kez; anahtarlar
    # gizli özetle (durum.json herkese açık). Veri koruması: olay Yahoo'nun anlık fiyatıyla da tutmalı (tek kaynaktaki
    # hatalı fiyat yanlış "destek kırıldı" demesin); iki fiyat %1'den fazla farklıysa o hisse bu taramada atlanır.
    gi_d = durum.get("gunici") or {}
    gi_gonderilen = set(gi_d.get("g", [])) if gi_d.get("tarih") == bugun_iso else set()
    if pf and simdi.weekday() < 5 and GUNICI_BAS <= dakika < GUNICI_SON:
        satirlar, yeni_anahtar, supheli = [], set(), 0
        for kod in sorted(pf):
            s = by_kod.get(kod)
            try:
                df = data[kod + ".IS"].dropna(subset=["Close"])
            except Exception:
                continue
            if not s or df.empty:
                continue
            anahtar = lambda o, sv, kod=kod: _gizli(f"gi|{kod}|{o}|{sv}")
            aday = [x for x in gunici_olaylar(s, df, pf[kod]) if x[0] in GUNICI_OLAYLAR and anahtar(x[0], x[1]) not in gi_gonderilen]
            if not aday:
                continue
            anlik = _son_fiyat(kod + ".IS")
            if not anlik or abs(anlik / s["fiyat"] - 1) > GUNICI_VERI_FARK:
                supheli += 1
                continue
            teyit = {(x[0], x[1]) for x in gunici_olaylar(s, df, pf[kod], fiyat=anlik)}
            aday = [x for x in aday if (x[0], x[1]) in teyit]
            metin = []
            for o, sv, bastir, m in aday:
                yeni_anahtar.add(anahtar(o, sv))
                yeni_anahtar |= {anahtar(b, sv) for b in bastir}
                metin.append(m)
            if metin:
                satirlar.append((kod, round(anlik, 2), metin))
        if supheli:
            print(f"Gün içi portföy: {supheli} hissede fiyat kaynakları tutarsız, bu taramada atlandı.")
        # BIST 100 sert hareket: portföyün bugünkü K/Z'si (günde bir kez her yön için)
        piyasa_satir = None
        try:
            xu = data[ENDEKS + ".IS"]["Close"].dropna()
            xu_ch = float(xu.iloc[-1] / xu.iloc[-2] - 1) if xu.index[-1].date() == simdi.date() else 0.0
        except Exception:
            xu_ch = 0.0
        yon = "yukari" if xu_ch >= PIYASA_SERT else ("asagi" if xu_ch <= -PIYASA_SERT else None)
        if yon and _gizli(f"gi|piyasa|{yon}") not in gi_gonderilen:
            gun_kz = onceki = 0.0
            for kod, p in pf.items():
                try:
                    c = data[kod + ".IS"]["Close"].dropna()
                    if c.index[-1].date() == simdi.date():
                        gun_kz += (c.iloc[-1] - c.iloc[-2]) * p["adet"]
                        onceki += c.iloc[-2] * p["adet"]
                except Exception:
                    pass
            if onceki:
                piyasa_satir = (f"{'📈' if yon == 'yukari' else '📉'} <b>BIST 100 bugün {_yz(xu_ch * 100)}</b> · portföyün bugün "
                                f"<b>{_tl(gun_kz)}</b> ({_yz(gun_kz / onceki * 100)})")
                yeni_anahtar.add(_gizli(f"gi|piyasa|{yon}"))
        if satirlar or piyasa_satir:
            print(f"Telegram: portföy gün içi ({len(satirlar)} hisse{', piyasa' if piyasa_satir else ''}).")
            if tg_gonder(gunici_mesaj(satirlar, piyasa_satir)):
                gi_gonderilen |= yeni_anahtar
    # Kesin kapanış: bugün destek/direnç seviyesine değen portföy hisselerinde sonuç → günlük portföy özetinin başında
    sd_kap_satir = []
    if pf and simdi.weekday() < 5 and kapanis_zamani:
        for kod in sorted(pf):
            try:
                df = data[kod + ".IS"].dropna(subset=["Close"])
                m = kapanis_sd(by_kod[kod], df, pf[kod]) if kod in by_kod and not df.empty else []
            except Exception:
                m = []
            if m:
                sd_kap_satir.append(f"<b>{kod}</b>: " + " ".join(m))

    # KAP: portföy hisselerinin yeni bildirimleri (her taramada). kap_son = görülen en büyük bildirim no (genel sayaç,
    # portföy bilgisi içermez); ilk çalışmada sessizce başlangıç kaydı.
    kap_son = durum.get("kap_son") or 0
    en_buyuk = max([b["id"] for L in kap_hisse.values() for b in L] + [kap_son])
    if kap_son and pf:
        m = kap_mesaji(kap_hisse, pf, kap_son)
        if m:
            print("Telegram: portföy KAP bildirimi.")
            if not tg_gonder(m):
                en_buyuk = kap_son   # gönderilemediyse sonraki taramada yeniden dene
    kap_son = en_buyuk

    # Günlük portföy özeti: hafta içi, kapanıştan sonraki ilk taramada bir kez
    ozet_tarih = durum.get("ozet_tarih")
    if pf and simdi.weekday() < 5 and kapanis_zamani and ozet_tarih != bugun_iso:
        if tg_gonder(portfoy_ozeti(sonuclar, pf, piyasa, endeks, sd_kap_satir)):
            ozet_tarih = bugun_iso
            print("Günlük portföy özeti gönderildi.")

    # Haftalık özet: cuma kapanıştan sonraki ilk taramada bir kez
    hafta_tarih = durum.get("hafta_tarih")
    if simdi.weekday() == 4 and kapanis_zamani and hafta_tarih != bugun_iso:
        if tg_gonder(haftalik_ozet(sonuclar, pf, acik, kapali, simdi)):
            hafta_tarih = bugun_iso
            print("Haftalık özet gönderildi.")

    # 🏢 İşlem Odası: sanal robotlar panonun bu taramadaki verisiyle (yeniden veri çekmeden) günde bir kez, kesin kapanıştan
    # sonra karar verir; akşam tek Telegram skor özeti. Hata taramayı ASLA bozmaz.
    if oda:
        try:
            _t0 = time.time()
            _m = oda.canli_calistir(sonuclar, data, simdi, kapanis_zamani, tg_gonder, PANO_URL,
                                    buyuk=set(BIST100) | set(EK_HISSELER))
            print(f"İşlem odası: {_m} ({time.time() - _t0:.1f} sn).")
        except Exception as e:
            print(f"İşlem odası çalışmadı ({type(e).__name__}: {e}); tarama etkilenmedi.")

    with open(DURUM, "w", encoding="utf-8") as f:
        json.dump({"al": sorted(s["kod"] for s in bugun_al), "son": dict(sorted(son.items())),
                   "iz_kirilim_g": sorted(iz_kayit), "ozet_tarih": ozet_tarih, "hafta_tarih": hafta_tarih,
                   "karar_kirilim_g": sorted(kirilim),
                   "alarm_tetik": sorted(tetiklenen), "on_sinyal": dict(sorted(on_sinyal.items())),
                   "uv_son": dict(sorted(uv_son.items())), "kap_son": kap_son,
                   "tk_gonderilen": {"tarih": bugun_iso, "kodlar": sorted(tk_gonderilen)}, "mom_ay": mom,
                   "gunici": {"tarih": bugun_iso, "g": sorted(gi_gonderilen)},
                   "sabah_tarih": sabah_tarih},
                  f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
