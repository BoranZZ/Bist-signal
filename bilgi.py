"""🎁 🪤 🎢 💎 Bilgi paketi (2026-11-17, dal `bilgi-paketi`). HEPSİ SADECE BİLGİ: v3 AL/SAT, iz stop, 🔐 kâr kilidi, piyasa filtresi,
backtest ve İşlem Odası DEĞİŞMEZ. Araştırmalar (tekrar araştırma yapma): Documents/Bist-arastirma/2026-11-14/
  tuzak/haber/RAPOR.md  → 🎁 bedelsiz sonrası (SPK onayından sonraki 20 işlem günü), dipte zayıf bilanço → 'panikle satma' notu
  tuzak/fiyat/RAPOR.md  → 🎢 aşırı koşmuş + oynak, 🪤 trend tuzağı metni, 🎈/⚠️ risk notu, 'çöküşlerin çoğu piyasa geneli' notu
  tuzak/kirmizi/RAPOR.md → 🪤 tavanlı kırılım (v3 AL'inden önceki 20 günde ≥2 tavan)
  ucuz/RAPOR.md         → 💎 kalitesine göre ucuz, 🪤 ucuz ama dikkat, 🪤 son 12 ayda bedelli/tahsisli artırım, F/K · PD/DD İş Yatırım'dan
Metinler tek yerde (NOT / BASLIK); pano.py bunları JS'e BP_NOT olarak gömer. Hata hiçbir zaman taramayı düşürmez (tarama try/except)."""
import re

import numpy as np
import pandas as pd

# --- Metinler (sayılar araştırma raporlarından; kural değişirse yeniden ölç) ----------------------------------------------------
OKK, OKY = "<span class=okk>▼</span>", "<span class=oky>▲</span>"
RISK_NOTU = ("Bu bir risk notu: çakılma (20 günde %25+ düşüş) riski normalin 3-11 katı ve tipik hisse endeksin gerisinde kaldı, "
             "ama ortalama getiri endeksle benzer — azı çok yükseldi. 'Düşecek' demek değil.")
NOT = {
    "bz": ("Bedelsiz hisseye para getirmez (pay sayısı artar, fiyat aynı oranda bölünür) ama 'bedava hisse' heyecanı yaratır. Geçmişte "
           f"(2018-26, 357 onay) hisse onaydan sonraki 20 işlem gününde <b>%63 oranında BIST 100'ün gerisinde kaldı</b> (aynı hisselerin "
           f"diğer günlerinde %54); ortalama {OKK} −3,7 puan, 20 gün içinde %10+ düşüş görme %45 (diğer günlerde %31). 9 yılın 9'unda aynı "
           "yön. Hacimle 'mal boşaltma' izi yok: heves fiyatlanıp sönüyor. SAT sinyali değil; yeni alım düşünüyorsan acele etme."),
    "bd": (f"Geçmişte (2017-25) son 12 ayda bedelli/tahsisli artırım yapan hisseler sonraki 12 ayda sektörlerinin ortalama hissesini {OKK} "
           "<b>%42 oranında geçti</b> (diğerlerinde %51); 9 yılın 9'unda daha düşük. Yeni pay satışı mevcut ortakların payını sulandırır. "
           "Bilgi; SAT sinyali değil."),
    "ko": (f"{OKK} 2017-26'da bu durumdaki hisselerin ~%11'i (ana liste) / %15'i (küçükler) sonraki 20 günde %25+ çakıldı (normalde %2 / "
           "%4; benzer ama daha az koşmuş hisselerde %5); yarıdan fazlası 60 günde endeksin gerisinde kaldı. Ama ~%13'ü %50+ daha yükseldi "
           "— 'düşecek' demek değil, kayıp riski büyük. Stopunu bil. AL'i susturmaz (filtre olarak testte kârı düşürdü)."),
    "tv": (f"Geçmişte böyle 🚀 AL'lerin {OKK} <b>%45'i zararla kapandı</b> (diğer AL'lerde %29), %34'ü %10'dan fazla kaybettirdi "
           "(diğerlerinde %23). Ortalama yine artı (+%8, diğerleri +%21), yani AL iptal değil; tavanlı hisse çok sallanır, iz stop'a erken "
           "takılabilir. Daha küçük pozisyon düşün. Filtre değil: bu AL'leri atlamak testte toplam kârı düşürdü."),
    "uc_e": (f"Geçmişte (2017-25) böyle ucuz hisselerin 12 ayda {OKY} <b>%60'ı sektörünün ortalama hissesini geçti</b> (rastgele %50), "
             "%55'i BIST 100'ü geçti (aynı sektörden rastgele hissede %49). 2022-26'da daha zayıf (%57; endeksi geçen %46). 3 ayda fark "
             "küçük, son 1 yılda kısa vadede fark yoktu. Ucuz olmak 'yükselir' demek değil: ~10'da 4'ü yine sektörünün gerisinde kaldı. "
             "🚀 AL'lerde ucuz/pahalı ayrımı sonucu değiştirmedi."),
    "uc_t": (f"Geçmişte böyle 'ucuz ama işaretli' hisselerin 12 ayda {OKK} yalnız %47'si endeksi geçti (aynı sektörden rastgele hissede "
             "%53); 2022-26'da %33."),
    "uc_p": f"Geçmişte en pahalı %20'lik dilimdeki hisselerin 12 ayda {OKK} %44'ü sektörünü geçti (rastgele %50). Bilgi, SAT sinyali değil.",
    "uc_b": "Bankalarda ve sigorta/aracı kurumlarda bu ucuzluk ölçüsü geçmişte işe yaramadı; rozet verilmez.",
    "uc_dip": ("Kaynak: İş Yatırım mali tabloları (son 4 çeyrek ana ortaklık net kârı; ana ortaklık özkaynağı); piyasa değeri = son fiyat × "
               "ödenmiş sermaye (bilanço sonrası bedelsiz/bölünme hesaba katılır). Enflasyon muhasebesi (2023 sonrası) yüzünden eski "
               "yıllarla kıyaslanmaz; bankalar enflasyon muhasebesi uygulamaz."),
    "dz": (f"Geçmişte bu durumda (ana liste, dipteki hissede zayıf bilanço tepkisi) hisse sonraki 20 günde {OKY} <b>%70 oranında endeksi "
           "geçti</b> (aynı 2 günlük düşüşü haber olmadan yapanlarda %38). Panikle satmak çoğu zaman hataydı; 60 günde fark kayboluyor. "
           "Az örnek (ana listede 63), kesin değil; iz stop kuralı aynen geçerli."),
    "tz": (f"{OKK} Geçmişte bu tip sıçramaların ~%54'ü 15 gün içinde %5+ geri verdi — trend çizgisi kırılmayan benzer sıçramalarda da oran "
           "aynı (tipik bir günde %46). Yani tuzak olan şey düşüşteki hissede tek günlük sert sıçramanın kendisi; çizgi kırılımı tek başına "
           "AL sebebi değil."),
    "risk": RISK_NOTU,
    "sk": ("200 günlük ortalamanın altında, son 2 haftadır oynaklığı çok daralmış hisse dar bandını yukarı kırdı — v3 kırılımından önceki "
           f"aşama olabilir. Geçmişte (sinyal2/erken, ana liste 2017-26, ~990 işlem; ertesi açılışta alıp %15 iz stop) aynı hissenin "
           "sıradan gününe göre iyi görünüyordu (+12 / +7,5 puan), ama bu kıyas sonucu şişiriyordu: aynı gün benzer durumdaki hisselerle "
           "kıyaslayınca fark yok (−1 puan). İsabet %42-49 — çok sayıda küçük zarar, az sayıda büyük kazanç. "
           f"{OKK} Aynı gün sıradan bir hisseden 3-6 ayda biraz kötü (−4 / −5 puan; 28.11); 2022-26'da BIST 100'ü geçmedi; AL sinyali olarak elendi, sadece bilgi (Telegram'a gelmez)."),
    "cokus": ("Büyük çöküşlerin çoğu (2017-26'da %61-77'si) hiçbir rozet yanmadan gelir; bunların çoğu piyasa genelindeki düşüşlerdir "
              "(Covid 2020, seçim öncesi 2023, Mart 2025, Eylül 2026). Tek hisseye bakan rozetler bunu önceden göremez. 🚀 pozisyonlarda "
              "koruma %20 iz stop + 🔐 kâr kilidi + piyasa filtresidir."),
}
# Tablo rozetlerinin title'ı (düz metin)
BASLIK = {
    "bz": "Geçmişte SPK bedelsiz onayından sonraki 20 işlem gününde hisselerin %63'ü endeksin gerisinde kaldı (diğer günlerde %54); ort. −3,7 puan. Uyarı, SAT sinyali değil",
    "bd": "Son 12 ayda bedelli/tahsisli sermaye artırımı: geçmişte bu hisseler 12 ayda sektörünü %42 oranında geçti (diğerleri %51; 9 yılın 9'unda daha düşük). Bilgi",
    "ko": "120 günde 2 katın üstü + 60 günlük oynaklık %4+: geçmişte 20 günde %25+ çakılma ~%14 (benzer günlerde %5); ama ~%13'ü %50+ daha yükseldi. Risk notu, SAT değil",
    "tv": "🚀 AL'den önceki 20 günde 2+ tavan: geçmişte bu AL'lerin %45'i zararla kapandı (diğerleri %29); ortalama yine artı. Not, filtre değil",
    "uc_e": "Sektörüne ve kârlılığına göre ucuz: geçmişte 12 ayda %60'ı sektörünü geçti (rastgele %50). Bilgi, AL sinyali değil",
    "sk": "SMA200 altında, oynaklığı daralmış hisse dar bandını yukarı kırdı (v3'ten önceki aşama olabilir). Aynı gün benzer durumdaki hisselerden farkı yok (eski '+12 puan' şişirici kıyastı), isabet %42-49; 2022-26'da BIST 100'ü geçmedi. Bilgi, AL değil",
    "uc_t": "Ucuz görünüyor ama tuzak işareti var (manipülasyon / şişme / bedelli artırım): geçmişte yalnız %47'si endeksi geçti. Bilgi",
}
TV_TG = "🪤 🔴▼ Son 20 günde {n} tavan: bu tür AL'lerin %45'i zararla bitti (normal %29). AL iptal değil; küçük pozisyon."

# --- KAP sınıflaması (tuzak/haber/siniflandir.py'nin sermaye artırımı kısmı; elle kontrolde bu türlerde yön hatası ~0) -------------
_TR = str.maketrans({"İ": "i", "I": "i", "ı": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u", "ö": "o",
                     "Ö": "o", "ç": "c", "Ç": "c", "â": "a", "î": "i", "û": "u", "̇": ""})
_SPOR = {"BJKAS", "FENER", "GSRAY", "TSPOR"}


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").translate(_TR).lower()).strip()


def _has(s, *kel):
    return any(k in s for k in kel)


def sermaye_tur(konu, ozet, kod=None):
    """KAP bildirimi → 'o' bedelsiz SPK onayı, 'd' bedelsiz dağıtım/tescil, 'k' bedelsiz karar/başvuru, 'x' bedelsiz iptal,
    'b' bedelli/tahsisli, None (diğer). siniflandir.sinifla ile aynı sıra: spor sözleşmesi, 'olumsuzun sonu', birleşme önce elenir."""
    k, o = _norm(konu), _norm(ozet)
    if kod in _SPOR and _has(o, "fesh", "fesih", "transfer", "sozlesme"):
        return None
    if (_has(o, "kaldirilmasi", "kaldirildi", "davanin reddi", "lehine", "yasaginin iptali", "feragat", "teyit", "cezasinin iptal",
             "islemin iptal", "tastik", "tasdik") and not _has(k, "kar payi", "sermaye artirimi")):
        return None
    if _has(k, "devrolma", "birlesme"):
        return None
    if not (_has(k, "sermaye artirimi", "sermaye artirim", "kayitli sermaye tavani") or _has(o, "bedelsiz", "bedelli", "ruchan", "yeni pay alma")):
        return None
    if _has(k, "kayitli sermaye tavani") and not _has(o, "bedelsiz", "bedelli"):
        return None
    if _has(o, "bedelsiz", "ic kaynak", "kar payindan pay", "temettu payi olarak", "kar payi olarak pay"):
        if _has(o, "iptal", "vazgec", "geri cek"):
            return "x"
        if _has(o, "onay", "onaylan", "uygun goru", "izahname", "ihrac belgesi"):
            return "o"
        if _has(o, "dagitim", "hak kullanim", "tescil", "tamamlan", "kayden"):
            return "d"
        return "k"
    if _has(o, "birincil piyasa"):
        return None
    if _has(o, "bedelli", "ruchan", "yeni pay alma", "tahsis"):
        return None if _has(o, "iptal", "vazgec") else "b"
    return None


BZ_GUN = 20   # rozet onayın tepki gününden (gün 0) itibaren 20 işlem günü görünür (araştırma: 10 gün daha keskin, 40 günde söner)


def tepki_gunu(yayin, takvim):
    """KAP yayını ('YYYY-MM-DD HH:MM') → takvimdeki ilk tepki günü sırası (18:00 ve sonrası ertesi gün; hafta sonu/tatil → sonraki
    işlem günü). len(takvim) dönebilir: tepki günü henüz gelmedi (bu akşam/hafta sonu yayın)."""
    t = pd.Timestamp(yayin)
    d = t.normalize() + pd.Timedelta(days=1 if t.hour >= 18 else 0)
    return int(pd.DatetimeIndex(takvim).normalize().searchsorted(d))


def bedelsiz_olaylar(bildirimler):
    """kap.json 'bildirim' listesinden SPK bedelsiz onayları: {kod: [(yayın, id, özet), ...]} (eskiden yeniye)."""
    out = {}
    for b in bildirimler or []:
        for k in b.get("kodlar") or []:
            if sermaye_tur(b.get("konu"), b.get("ozet"), k) == "o":
                out.setdefault(k, []).append((b["t"], b["id"], (b.get("ozet") or "")[:160]))
    return {k: sorted(v) for k, v in out.items()}


def bedelsiz_rozet(olaylar, takvim):
    """Bir hissenin onayları + işlem takvimi → en son onay tepki gününden beri < BZ_GUN işlem günü geçtiyse
    {"t": yayın, "id": KAP id, "g": geçen işlem günü (0 = tepki günü / henüz gelmedi), "o": özet} ya da None."""
    if not olaylar or takvim is None or not len(takvim):
        return None
    t, i, oz = olaylar[-1]
    j = tepki_gunu(t, takvim)
    g = max(0, (len(takvim) - 1) - j)
    if g >= BZ_GUN:
        return None
    return {"t": t, "id": i, "g": int(g), "o": oz}


# --- 💎 Kalitesine göre ucuz (ucuz/RAPOR.md tanım c ≥ 0,8) + F/K · PD/DD (İş Yatırım) + 🪤 bedelli/tahsisli ----------------------
# Değerleme grubu = Yahoo endüstrisi → tarama.KIYAS_GRUP → BIRLESTIR (araştırmanın ortak.py'si, küçük gruplar birleştirildi) → ELLE
BIRLESTIR = {
    "Perakende": "Perakende", "Dayanıklı tüketim": "Elektronik/dayanıklı", "Communication Equipment": "Elektronik/dayanıklı",
    "Elektronik dağıtım": "Elektronik/dayanıklı", "Gübre/tarım girdisi": "Kimya/gübre", "Kimya": "Kimya/gübre", "Ambalaj": "Kimya/gübre",
    "Turizm/yeme-içme": "Turizm/spor", "Spor/eğlence": "Turizm/spor", "Güneş enerjisi": "Elektrik ekipmanı",
    "Yapı ürünleri": "Çimento/yapı", "Çimento/yapı malz.": "Çimento/yapı", "Household & Personal Products": "Gıda/içecek",
    "Rafineri": "Enerji", "Elektrik/doğalgaz": "Enerji", "GYO": "Gayrimenkul", "Gayrimenkul geliştirme/hizmet": "Gayrimenkul",
    "Banka": "Banka", "Sigorta/finansman": "Finans", "Aracı kurum": "Finans", "Asset Management": "Holding",
}
ELLE = {"SAHOL": "Holding", "GMTAS": "Perakende", "ISGSY": "Holding", "SMRVA": "Finans", "HDFGS": "Finans", "ICUGS": "Finans"}
TIP = {"Banka": "b", "Finans": "f", "Holding": "h", "Gayrimenkul": "g"}   # diğerleri 'n' (sanayi/hizmet)
UC_ESIK = 0.8          # c (kaliteye göre ucuzluk sırası) ≥ 0,8 → 💎 ; ≤ 0,2 → pahalı (bilgi satırı)
UC_MIN_HISSE = 40      # regresyona giren hisse bundan azsa (İş Yatırım verisi dolmadı/çöktü) 💎 hiç gösterilmez
UC_YAS_GUN = 200       # bilinen bilanço bundan eskiyse o hisse değerlenmez
SPK_BILINME = {1: 50, 2: 70, 3: 50, 4: 80}   # KAP yayın kaydı yoksa: dönem sonu + bu kadar gün (araştırmadaki gibi)
BEDELLI_ORAN = 1.10    # ödenmiş sermaye geçen yılın aynı dönemine göre ≥ %10 arttı ...
BEDELLI_NAKIT = 0.08   # ... ve sermaye artırımından nakit girişi (son 4 çeyrek ya da geçen yıl) ≥ eski sermayenin %8'i (bedelsizde nakit yok)


def deger_grubu(kod, endustri, kiyas_grup):
    g = (kiyas_grup or {}).get(endustri, endustri) if endustri else None
    g = BIRLESTIR.get(g, g)
    return ELLE.get(kod, g)


def _donem_sonu(y, q):
    return pd.Timestamp(int(y), 3 * int(q), 1) + pd.offsets.MonthEnd(0)


def _bilinme(kod, y, q, fr_kod):
    """Dönemin bilindiği gün: KAP'taki ilk 'Finansal Rapor' yayını (18:00 sonrası ertesi gün), yoksa dönem sonu + SPK_BILINME."""
    for yy, qq, t in (fr_kod or {}).get(kod) or []:
        if int(yy) == int(y) and int(qq) == int(q):
            tt = pd.Timestamp(t)
            return tt.normalize() + pd.Timedelta(days=1 if tt.hour >= 18 else 0)
    return _donem_sonu(y, q) + pd.Timedelta(days=SPK_BILINME[int(q)])


def bedelli_mi(e):
    """İş Yatırım kaydı (s: ödenmiş sermaye, s1: geçen yıl aynı dönem, k / k2: sermaye artırımı nakit girişi son 4 çeyrek / geçen yıl)
    → (bool, artış oranı|None). Bedelsiz pay sayısını artırır ama nakit getirmez; bedelli/tahsisli nakit getirir."""
    s, s1 = e.get("s"), e.get("s1")
    if not s or not s1 or s1 <= 0:
        return False, None
    r = s / s1
    nakit = max(x for x in (e.get("k"), e.get("k2"), 0.0) if x is not None)
    return bool(r >= BEDELLI_ORAN and nakit >= BEDELLI_NAKIT * s1), round(r, 3)


def pay_carpani(pe, bolunmeler):
    """Bilanço döneminden (pe) SONRAKİ bölünme/bedelsizlerin pay çarpanı (bilançodaki ödenmiş sermaye eski pay biriminde)."""
    m = 1.0
    for t, x in bolunmeler or []:
        if str(t)[:10] > str(pe.date()) and x and x > 0:
            m *= float(x)
    return m


def deger_hesapla(sonuclar, isy, fr_kod=None, yahoo_bol=None, kiyas_grup=None, bugun=None):
    """sonuclar'a yazar: s['fk'], s['pddd'] (İş Yatırım + son fiyat; yoksa None — Yahoo'nun yanlış oranı yedek olarak KULLANILMAZ) ve
    s['bp']['uc'] (💎 / 🪤 ucuz ama dikkat / pahalı / banka), s['bp']['bd'] (🪤 son 12 ayda bedelli/tahsisli). isy: bilanco.zarar_guncelle
    dönüşü {kod: {d, n, p, e, e1, s, s1, k, k2, t}}. Döner: kaç hisse değerlendi (regresyondaki hisse sayısı)."""
    bugun = pd.Timestamp(bugun or pd.Timestamp.now(tz="Europe/Istanbul").strftime("%Y-%m-%d"))
    sat = []
    for s in sonuclar:
        s["fk"] = s["pddd"] = None
        e = (isy or {}).get(s["kod"]) or {}
        bp = s.get("bp") or {}
        bl = bp.pop("bl", None)            # fiyattan bulunan (Yahoo'nun kaydetmediği) bölünmeler: [[gün, pay çarpanı]]
        if not bp:
            s.pop("bp", None)
        if not e.get("p") or e.get("e") is None or e.get("s") is None or not s.get("fiyat"):
            continue
        y, q = e["p"]
        pe = _donem_sonu(y, q)
        if (bugun - _bilinme(s["kod"], y, q, fr_kod)).days > UC_YAS_GUN:
            continue
        b, oran = bedelli_mi(e)
        if b:
            s.setdefault("bp", {})["bd"] = {"d": e.get("d"), "r": round((oran - 1) * 100), "s": e["s"], "s1": e["s1"],
                                            "k": max(x for x in (e.get("k"), e.get("k2"), 0.0) if x is not None)}
        carp = pay_carpani(pe, list((yahoo_bol or {}).get(s["kod"]) or []) + list(bl or []))
        mc = float(s["fiyat"]) * float(e["s"]) * carp
        ozk, ozk1, ni = e.get("e"), e.get("e1"), e.get("n")
        ort = (ozk + ozk1) / 2 if (ozk1 is not None and ozk1 > 0) else ozk
        g = deger_grubu(s["kod"], s.get("endustri"), kiyas_grup)
        sat.append({"kod": s["kod"], "grup": g, "tip": TIP.get(g, "n") if g else None, "mc": mc, "ozk": ozk, "ni": ni,
                    "roe": (ni / ort) if (ni is not None and ort and ort > 0) else np.nan,
                    "pddd": mc / ozk if ozk and ozk > 0 else np.nan, "fk": mc / ni if ni and ni > 0 else np.nan,
                    "bp": ozk / mc if (ozk is not None and mc > 0) else np.nan, "bd": b, "d": e.get("d")})
        s["pddd"] = round(mc / ozk, 2) if ozk and ozk > 0 else None
        s["fk"] = round(mc / ni, 1) if ni and ni > 0 else None
    P = pd.DataFrame(sat)
    if P.empty:
        return 0
    P = P[P.grup.notna()].copy()
    by = {s["kod"]: s for s in sonuclar}
    # (c) log(PD/DD) = grup sabiti + b·ROE (finans ayrı eğim; ROE −0,5…1,0 kırpılı) — kalıntı düşükse 'hak ettiğinden ucuz'
    R = P[(P.tip != "g") & (P.pddd > 0) & P.roe.notna()]
    if len(R) < UC_MIN_HISSE:
        return len(R)
    roe = R.roe.clip(-0.5, 1.0).values
    fin = R.tip.isin(["b", "f"]).values.astype(float)
    X = pd.get_dummies(R.grup).astype(float)
    X["roe"] = roe * (1 - fin)
    X["roe_f"] = roe * fin
    yv = np.log(R.pddd.values)
    beta, *_ = np.linalg.lstsq(X.values, yv, rcond=None)
    fit = X.values @ beta
    P.loc[R.index, "resid"] = yv - fit
    P.loc[R.index, "bek"] = np.exp(fit)
    P["c"] = P.resid.rank(pct=True, ascending=False)
    # GYO/gayrimenkul: grup içi B/P (defter/piyasa) yüzdeliği; grupta < 5 hisse varsa tüm havuzda
    say = P.groupby("grup").bp.transform("count")
    P["pbp"] = np.where(say >= 5, P.groupby("grup").bp.rank(pct=True), P.bp.rank(pct=True))
    P.loc[P.bp.isna(), "pbp"] = np.nan
    P["gm"] = P.groupby("grup").pddd.transform("median")
    P["gs"] = P.groupby("grup").pddd.transform("count")
    for r in P.itertuples():
        s = by[r.kod]
        ucuz = bool((r.tip in ("n", "h") and r.c >= UC_ESIK and r.ni is not None and r.ni > 0)
                    or (r.tip == "g" and r.pbp >= UC_ESIK))
        if r.tip in ("b", "f"):
            tur = "b"
        elif ucuz:
            ned = []
            if s.get("mn"):
                ned.append("mn")
            if (s.get("tahta") or {}).get("seviye") == "sisme":
                ned.append("sisme")
            if r.bd:
                ned.append("bd")
            tur = "t" if ned else "e"
        elif r.tip in ("n", "h") and r.c <= 1 - UC_ESIK:
            tur = "p"
        else:
            continue
        u = {"r": tur, "gn": r.grup, "d": r.d}
        if tur != "b":
            u.update({"pd": _y(r.pddd, 2), "fk": _y(r.fk, 1), "roe": _y(r.roe * 100, 0) if r.roe == r.roe else None,
                      "gm": _y(r.gm, 2), "gs": int(r.gs) if r.gs == r.gs else None})
            if r.tip == "g":
                u["gy"] = _y((1 - r.pbp) * 100, 0)        # grupta en ucuz %x
            else:
                u.update({"bek": _y(r.bek, 2), "isk": _y((np.exp(r.resid) - 1) * 100, 0), "sira": _y((1 - r.c) * 100, 0)})
            if tur == "t":
                u["ned"] = ned
        s.setdefault("bp", {})["uc"] = u
    return len(R)


def _y(x, n):
    try:
        return None if x is None or x != x else (round(float(x), n) if n else int(round(float(x))))
    except Exception:
        return None


# --- 📊 zayıf bilanço tepkisi + dipte (SMA200'ün %20+ altı) → 'panikle satma' notu (ana liste; tuzak/haber K1) --------------------
DZ_ESIK = -0.20
DZ_GUN = 20          # not, tepki ölçüm gününden (j+1) sonra 20 işlem günü (araştırmanın ufku; 60 günde fark kayboluyor)


def dipte_zayif(c, bt):
    """c: bölünme düzeltilmiş kapanış, bt: sinyal.bilanco_tepkisi çıktısı. Zayıf tepki + haberden önceki gün (j−1) kapanış SMA200'ün
    %20+ altındaysa {"u": uzaklık %} ya da None."""
    if not bt or bt.get("s") != "z" or bt.get("g") is None or bt["g"] > DZ_GUN or c is None:
        return None
    c = c.dropna()
    c = c[~c.index.duplicated(keep="last")]
    gun = pd.DatetimeIndex(c.index).normalize()
    j = int(gun.searchsorted(pd.Timestamp(bt["j"])))
    if j < 1 or j >= len(c) or gun[j] != pd.Timestamp(bt["j"]):
        return None
    sma = c.rolling(200, min_periods=180).mean()
    if sma.iloc[j - 1] != sma.iloc[j - 1]:
        return None
    u = float(c.iloc[j - 1] / sma.iloc[j - 1] - 1)
    return {"u": round(u * 100)} if u <= DZ_ESIK else None


# --- Telegram /hisse kısa satırları (AL mesajına sadece 🪤 tavanlı kırılım girer: tarama._al_satiri) -----------------------------
def tg_satirlari(s):
    bp = s.get("bp") or {}
    u = []
    if bp.get("bz"):
        u.append(f"🎁 bedelsiz SPK onayı ({bp['bz']['t'][8:10]}.{bp['bz']['t'][5:7]}) — geçmişte onaydan sonraki 20 günde %63'ü endeksin gerisinde kaldı")
    if bp.get("ko"):
        u.append(f"🎢 aşırı koşmuş + oynak (120 günde +%{bp['ko']['r']}, oynaklık %{bp['ko']['v']}) — çakılma riski ~3 kat; stopunu bil")
    if bp.get("tv"):
        u.append(f"🪤 tavanlı kırılım: 🚀 AL'den önceki 20 günde {bp['tv']['n']} tavan (bu AL'lerin %45'i zararla kapandı, normal %29)")
    if bp.get("sk"):
        u.append(f"🗜️ sıkışma kırılımı ({bp['sk']['t'][8:10]}.{bp['sk']['t'][5:7]}) — bilgi, AL değil")
    if bp.get("bd"):
        u.append(f"🪤 son 12 ayda bedelli/tahsisli artırım (sermaye +%{bp['bd']['r']}, {bp['bd']['d']})")
    uc = bp.get("uc") or {}
    if uc.get("r") == "e":
        u.append(f"💎 sektörüne ve kârlılığına göre ucuz (PD/DD {uc.get('pd')}, sektör medyanı {uc.get('gm')}) — bilgi, AL değil")
    elif uc.get("r") == "t":
        u.append("🪤 ucuz görünüyor ama dikkat (tuzak işareti var)")
    if bp.get("dz"):
        u.append(f"📊 dipte zayıf bilanço (SMA200'ün %{abs(bp['dz']['u'])} altı) — geçmişte panikle satmak çoğu zaman hataydı")
    return u


# --- Taramanın tek giriş noktası (tarama.main, try/except içinde) ----------------------------------------------------------------
def kap_bildirimleri(dosya="kap.json"):
    """kap.json'daki 45 günlük ODA+FR bildirim önbelleği (kap.kap_guncelle yazar). Yoksa []."""
    import json
    try:
        with open(dosya, encoding="utf-8") as f:
            return json.load(f).get("bildirim") or []
    except Exception:
        return []


def paket_uygula(sonuclar, isy, fr_kod=None, kapanislar=None, bildirimler=None, yahoo_bol=None, kiyas_grup=None, ana=None,
                 bugun=None):
    """sonuclar'a s['bp'] (yalnız dolu alanlar) + s['fk'] / s['pddd'] (İş Yatırım) yazar. Döner sayım sözlüğü (log için)."""
    kapanislar = kapanislar or {}
    n_reg = deger_hesapla(sonuclar, isy, fr_kod, yahoo_bol, kiyas_grup, bugun)
    olay = bedelsiz_olaylar(bildirimler)
    for s in sonuclar:
        bp = s.get("bp") or {}
        if (s.get("tahta") or {}).get("seviye") == "sisme":
            bp.pop("ko", None)                     # 🎈 öncelikli (aynı riskin daha sert hâli)
        c = kapanislar.get(s["kod"])
        try:
            bz = bedelsiz_rozet(olay.get(s["kod"]), c.index if c is not None else None)
            if bz:
                bp["bz"] = bz
        except Exception:
            pass
        if s.get("bt") and (ana is None or s["kod"] in ana):
            try:
                dz = dipte_zayif(c, s["bt"])
                if dz:
                    bp["dz"] = dz
            except Exception:
                pass
        if bp:
            s["bp"] = bp
        else:
            s.pop("bp", None)
    say = {k: sum(1 for s in sonuclar if (s.get("bp") or {}).get(k)) for k in ("bz", "bd", "ko", "tv", "dz", "sk")}
    say["uc_e"] = sum(1 for s in sonuclar if ((s.get("bp") or {}).get("uc") or {}).get("r") == "e")
    say["uc_t"] = sum(1 for s in sonuclar if ((s.get("bp") or {}).get("uc") or {}).get("r") == "t")
    say["fk"] = sum(1 for s in sonuclar if s.get("pddd") is not None)
    say["reg"] = n_reg
    return say
