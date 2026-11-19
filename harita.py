# -*- coding: utf-8 -*-
"""🎯 Tahtacı Haritası — SADECE BİLGİ sayfası (harita.html + harita.json). AL/SAT, Telegram, backtest, İşlem Odası DEĞİŞMEZ.

Her hisse için HAFTALIK grafikte seviyeler ve durum bilgisi. Araştırma: Documents/Bist-arastirma/2026-11-19/test1/RAPOR.md (E kelepir,
C yön durumu) ve .../test2/RAPOR.md (seviyeler, 📦 kutu alt bölgesi). Mantık oradaki betiklerle BİREBİR (testE.olaylar,
testC.bolumler, olaylar.k4_olaylar, harita.tahtaci_haritasi); değiştirirsen araştırmanın sayıları geçersiz olur.

Akış (tarama.py her taramada `calistir` çağırır; hata taramayı bozmaz):
  * Günde bir kez (+ yeni hafta başlayınca + cuma kesin kapanıştan sonra) `yenile`: 10 yıllık GÜNLÜK veri ayrı indirilir (kelepir
    5+3 yıl geriye bakar; canlı tarama 4 yıl indiriyor). Son 4 yıl taramanın düzeltilmiş verisinden, öncesi bu indirmeden; sonra
    bölünme düzeltmesi + W-FRI haftalık mum (araştırmayla aynı). İndirme ~10 sn, daemon iş parçacığında ZAMAN_ASIMI sn sınırı.
    Seviyeler/parametreler harita.json'a yazılır (ham veri saklanmaz: dosya küçük kalır).
  * Her taramada `canli`: sadece anlık fiyat (ve bu haftanın en düşüğü) saklanan seviyelerle kıyaslanır (~0,1 sn).
Haftalık kurallar (kelepir, kutu) 'bu hafta' = taramanın son işlem gününün haftası; o haftanın parametreleri yalnız ÖNCEKİ
tamamlanmış haftalardan hesaplanır, bu haftanın kapanışı yerine anlık fiyat kullanılır (hafta kapanışında kesinleşir). Yön durumu
yalnız tamamlanmış haftalarla.
"""
import json
import os
import threading
import time

import numpy as np
import pandas as pd

HARITA_JSON = "harita.json"
HARITA_HTML = "harita.html"
SURUM = 2              # 2: 📚 eğitim katmanı (eg) eklendi → ilk taramada yeniden hesaplanır
YABANCI_ACIK = False   # yabancı payı satırı: test OLUMSUZ (2026-11-19/yabanci/RAPOR.md); kullanıcı karar verene kadar kapalı, sayfada görünmez
INDIRME_DONEM = "10y"
ZAMAN_ASIMI = 45       # sn: uzun geçmiş indirmesi bundan uzun sürerse eski harita kalır, tarama devam eder
GRAFIK_HAFTA = 156     # sayfadaki küçük grafik: son 3 yıl haftalık kapanış

# 🟢 kelepir / ucuz (test1 E, ana ayar 4 kat / +%30)
KEL_PEN, KEL_TAB, KEL_KAT, KEL_BANT, KEL_ALT, UCUZ_GERI = 260, 156, 4.0, 0.30, 0.70, 0.214
# 📊 yön durumu (test1 C, ana ayar %40 / %15 / %20 / %8)
YON_X, YON_Z, YON_R, YON_TZ, YON_PEN, YON_MAKS = 0.40, 0.15, 0.20, 0.08, 104, 156
YON_ASILDI_GOSTER = 26  # ana tepe aşıldıysa kaç hafta daha 'aşıldı' diye gösterilir
# 📦 kutu alt bölgesi (test2 K4: 8 hafta, ≤%30, tepeden ≥%20)
KUTU_N, KUTU_GEN, KUTU_CEK = 8, 0.30, 0.20
TABAN_MIN_HAFTA = 12    # dip bundan yeniyse 'taban oluşmadı': kutu üst kenarı ve maliyet vekili gösterilmez


# ============================================================ veri
def hazirla(df):
    """Araştırmanın (test1 ortak.yukle) ön işlemesi: boş/0 kapanış at, bölünme düzelt, 0 olan O/H/L'yi kapanışla doldur."""
    from sinyal import bolunme_duzelt
    x = df[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
    x = x[x["Close"] > 0]
    if x.index.tz is not None:
        x = x.tz_localize(None)
    x = bolunme_duzelt(x)
    x["Open"] = x["Open"].where(x["Open"] > 0, x["Close"])
    x["High"] = x["High"].where(x["High"] > 0, x["Close"])
    x["Low"] = x["Low"].where(x["Low"] > 0, x["Close"])
    x["Volume"] = x["Volume"].fillna(0)
    return x


def haftalik(df):
    """W-FRI haftalık mum (test1 ortak.haftalik ile aynı) + hacim; 'hs' = haftanın cuma tarihi (dönem sonu)."""
    wk = df.index.to_period("W-FRI")
    pos = np.arange(len(df))
    s = pd.Series(pos).groupby(np.asarray(wk.astype(str))).agg(["min", "max"]).sort_values("min")
    ilk, son = s["min"].values, s["max"].values
    H, L, C, O, V = (df[c].values.astype(float) for c in ("High", "Low", "Close", "Open", "Volume"))
    return {"o": O[ilk], "h": np.maximum.reduceat(H, ilk), "l": np.minimum.reduceat(L, ilk), "c": C[son],
            "v": np.add.reduceat(np.nan_to_num(V), ilk), "t": df.index[son], "hs": wk[son].end_time.normalize(),
            "ilk": ilk, "son": son}


# ============================================================ hesaplar (araştırmayla birebir)
def kelepir_param(h, l, wt, t):
    """test1 testE.olaylar'ın t haftası: tepe P = son 260 haftanın (son 4 hafta hariç) en yüksek fiyatı, taban T = P'den önceki 156
    haftanın en düşüğü. Sadece t'den önceki haftaları kullanır."""
    if t < 60:
        return None
    a = max(0, t - KEL_PEN)
    z = t - 4
    if z <= a:
        return None
    pP = a + int(np.argmax(h[a:z]))
    P = float(h[pP])
    a2 = max(0, pP - KEL_TAB)
    if pP - a2 < 8:
        return None
    pT = a2 + int(np.argmin(l[a2:pP]))
    T = float(l[pT])
    if not T > 0:
        return None
    return {"P": P, "P_t": wt[pP], "T": T, "T_t": wt[pT], "kat": P / T, "kel_alt": KEL_ALT * T, "kel_ust": T * (1 + KEL_BANT),
            "ucuz_ust": T + UCUZ_GERI * (P - T), "ralli_hafta": int(pP - pT)}


def kelepir_durum(k, x):
    """'kelepir' | 'ucuz' | 'altinda' (bandın da altında) | None."""
    if not k or k["kat"] < KEL_KAT or not x:
        return None
    if k["kel_alt"] <= x <= k["kel_ust"]:
        return "kelepir"
    if k["kel_ust"] < x <= k["ucuz_ust"]:
        return "ucuz"
    if x < k["kel_alt"]:
        return "altinda"
    return None


def zigzag_tepeler(c, Z):
    """test1 testC.zigzag_tepeler: kapanış zigzag (tepe indeksi, değer, onay haftası)."""
    out = []
    yon = 0
    ci, cv = 0, c[0]
    li, lv = 0, c[0]
    for t in range(1, len(c)):
        x = c[t]
        if yon >= 0:
            if x > cv:
                ci, cv = t, x
            if x <= cv * (1 - Z):
                out.append((ci, cv, t))
                yon = -1
                li, lv = t, x
        if yon < 0:
            if x < lv:
                li, lv = t, x
            if x >= lv * (1 + Z):
                yon = 1
                ci, cv = t, x
    return out


def yon_durumu(c):
    """test1 testC.bolumler (ana ayar) + son bölümün DURUMU. c = tamamlanmış haftalık kapanışlar.
    Döner None (büyük düşüş bölümü yok) ya da {i_zirve, zirve, i_dip, dip, ana_tepe, tepecik, ilk_tepki, tepecik_gecildi,
    dip_yakini, asildi (hafta indeksi|None), i_ilk/i_tepecik/i_yakin/i_asildi}."""
    X, Z, r, z = YON_X, YON_Z, YON_R, YON_TZ
    n = len(c)
    if n < 31:
        return None
    tep = zigzag_tepeler(c, Z)
    t, son_bitis = 30, -1
    son = None
    while t < n:
        a = max(0, t - YON_PEN)
        pH = a + int(np.argmax(c[a:t + 1]))
        H0 = c[pH]
        if pH <= son_bitis or c[t] > H0 * (1 - X):
            t += 1
            continue
        bas = t
        D = c[pH:t + 1].min()
        pD = pH + int(np.argmin(c[pH:t + 1]))
        R, pR, tepecik = c[pD], pD, None
        done = {"i": None, "iii": None, "iv": None}
        bitis, asildi, LH = None, None, H0
        while t < n:
            x = c[t]
            if x < D:
                D, pD = x, t
                R, pR, tepecik = x, t, None
            else:
                if x > R:
                    R, pR = x, t
                if tepecik is None and pR > pD and x <= R * (1 - z):
                    tepecik = R
            LHs = [v for (p, v, o) in tep if pH < p < pD and o <= t]
            LH = LHs[-1] if LHs else H0
            if done["i"] is None and x >= D * (1 + r):
                done["i"] = t
            if tepecik is not None and tepecik < LH and done["iii"] is None and x > tepecik:
                done["iii"] = t
            if done["iv"] is None and t - pD >= 4 and x <= D * 1.10:
                done["iv"] = t
            if t > pD and x > LH:
                bitis = asildi = t
                break
            if x > H0 or t - bas > YON_MAKS:
                bitis = t
                break
            t += 1
        son = {"i_zirve": int(pH), "zirve": float(H0), "i_dip": int(pD), "dip": float(D), "ana_tepe": float(LH),
               "tepecik": None if tepecik is None else float(tepecik), "i_ilk": done["i"], "i_tepecik": done["iii"],
               "i_yakin": done["iv"], "i_asildi": asildi, "acik": bitis is None, "bitis": bitis}
        if bitis is None:
            bitis = n - 1
        son_bitis = bitis
        t = bitis + 1
    if son is None:
        return None
    if son["acik"] or (son["i_asildi"] is not None and n - 1 - son["i_asildi"] < YON_ASILDI_GOSTER):
        return son
    return None


def kutu_param(H, L, w):
    """test2 olaylar.k4_olaylar(yer='ici') — w haftası için kutu: önceki N haftanın en yüksek/en düşüğü (w hariç)."""
    N = KUTU_N
    if w < N + 53:
        return None
    top = float(H[w - N:w].max())
    bot = float(L[w - N:w].min())
    a = w - N - 52
    pk_i = a + int(np.argmax(H[a:w - N]))
    pk = float(H[pk_i])
    gecerli = (top / bot - 1 <= KUTU_GEN) and not (pk < top * (1 + KUTU_CEK) or H[pk_i:w - N].max() > pk)
    return {"alt": bot, "ust": top, "ucte": bot + (top - bot) / 3, "tepe": pk, "gecerli": bool(gecerli)}


def kutu_durum(k, x, wl):
    """Kapanış (anlık fiyat) kutunun alt üçte birinde ve haftanın en düşüğü kutu dibinin %3'ten fazla altına inmemiş."""
    return bool(k and k.get("gecerli", True) and x and k["alt"] <= x <= k["ucte"] and (wl is None or wl >= k["alt"] * 0.97))


def yabanci_payi(kod):
    """Yer tutucu: yabancı payı satırı (test olumsuz, kapalı). Açılırsa {'oran': %, 'degisim_4h': puan} döndürecek."""
    return None


def _profil(d, n=60):
    """test2 harita._profil: 52 haftalık (260 gün) hacim profili → (POC, VAH, VAL)."""
    lo, hi = d.Low.min(), d.High.max()
    if not (hi > lo > 0) or d.Volume.sum() <= 0:
        return np.nan, np.nan, np.nan
    b = np.exp(np.linspace(np.log(lo), np.log(hi), n + 1))
    m = np.sqrt(b[1:] * b[:-1])
    tp = ((d.High + d.Low + d.Close) / 3).values
    v = np.zeros(n)
    np.add.at(v, np.clip(np.searchsorted(b, tp) - 1, 0, n - 1), d.Volume.values)
    poc = int(v.argmax())
    a = z = poc
    s, tot = v[poc], v.sum()
    while s < 0.7 * tot:
        lft = v[a - 1] if a > 0 else -1
        rgt = v[z + 1] if z < n - 1 else -1
        if rgt >= lft:
            z += 1
            s += rgt
        else:
            a -= 1
            s += lft
    return m[poc], b[z + 1], b[a]


def seviyeler(d, kilit_hafta=26, tepe_hafta=156, kutu_oran=1.5):
    """test2 harita.tahtaci_haritasi (birebir): günlük df'nin son satırına kadarki veriyle. Son haftalık satır = bu hafta."""
    W = d.resample("W-FRI").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}).dropna(subset=["Close"])
    if len(W) < 60:
        return None
    H, L, C = W.High.values, W.Low.values, W.Close.values
    n = len(C)
    M = min(tepe_hafta, n)
    i_hi = n - M + int(np.argmax(H[-M:]))
    i_lo = i_hi + int(np.argmin(L[i_hi:]))
    tepe, dip = float(H[i_hi]), float(L[i_lo])
    kilit = float(np.max(C[-kilit_hafta - 1:-1]))
    x = d[d.index > W.index[i_lo] - pd.Timedelta(days=7)]
    maliyet = float((x.Volume * (x.High + x.Low + x.Close) / 3).sum() / x.Volume.sum()) if x.Volume.sum() > 0 else np.nan
    poc, vah, val = _profil(d.iloc[-260:])
    hi_ = lo_ = C[-2]
    sure = 0
    for q in range(n - 2, max(-1, n - 262), -1):
        hi_, lo_ = max(hi_, C[q]), min(lo_, C[q])
        if hi_ / lo_ > kutu_oran:
            break
        sure += 1
    return {"tepe": tepe, "tepe_t": W.index[i_hi], "dip": dip, "dip_t": W.index[i_lo], "dip_yas": int(n - 1 - i_lo),
            "orta": dip + (tepe - dip) / 2, "kilit": kilit, "maliyet": maliyet, "poc": float(poc), "vah": float(vah), "val": float(val),
            "taban_sure": int(sure)}


# ============================================================ 📚 eğitim katmanı (SADECE GÖSTERİM; kavramların çoğu BIST'te TUTMADI)
# Eğitmenin (DC Akademi, Smart Money/ICT) dünyada çok kullanılan kavramlarının ŞEFFAF, ölçülebilir yaklaşık tanımları. Eğitmenin kendi
# hesabı bilinmiyor. Her kavramın BIST ölçüm sonucu EGITIM_ROZET'te (tek yer: yeni test sonucu gelince sadece burayı güncelle).
# Durum kodları: 'y' 🟢 tuttu, 's' 🟡 kısmen, 'r' 🔴 tutmadı, 'o' ⚪ henüz ölçülmedi. Kaynak: 2026-11-19/OZET_19-11.md bölüm 3.
EGITIM_ROZET = {   # kavram: [durum, BIST'te tek satır, ABD sonucu (None = test sürüyor; gelince [durum, tek satır])]
    "trend": ["r", "3. temasta kırılma yazı-tura (%52); her ek temas kırılmayı ~%7 AZALTIYOR (çok temas = zayıf çizgi değil); kırılım sonrası rastgeleden kötü gitmedi.", ["r", "S&P 500 ve S&P 600'de de 3. temasta kırılma yazı-tura (%50 / %51)."]],
    "yatay": ["r", "3. temasta kırılma %40, 6.+ temasta %33 (çok temas seviyeyi zayıflatmıyor); kırılırsa alttaki seviyeye inme %60, rastgele günde de %61.", None],
    "durak": ["s", "Alt kademe (kelepir bandı) 25 yılda tuttu; ama 'arada alma' uyarısı ters çıktı: ara kademede ve taban dibinde almak kilit üstünde almaktan iyiydi.", ["s", "'Arada alma' uyarısı ABD'de de ters: kutu içinden almak 17 yılın 17'sinde rastgeleden iyi; kelepir ABD'de de tuttu."]],
    "tepe": ["s", "Riskte haklı (ana tepe geçilince yeni dip olasılığı %40 → %15), getiride haksız (beklemek 52 haftada −9 puan).", ["s", "ABD'de de aynı: yeni dip olasılığı büyüklerde %31 → %9, küçüklerde %44 → %19; ama beklemek 52 haftada −7 / −15 puan."]],
    "kutu": ["y", "Kutunun alt üçte birinde almak kutu kırılımını beklemekten iyiydi (~+6 puan, iki dönemde de); 'kutu içinde işlem açma' uyarısı ters çıktı.", ["y", "ABD'de de kutu içinden almak beklemekten iyi (17 yılın 17'si); 'kutu içinde işlem açma' uyarısı ters."]],
    "kz": ["r", "Oran v3, 🧲 Bant ve 🧲 SMA200 işlemlerinin sonucunu ayırmadı; '%30 kâr kalmıyorsa alma' süzgeci iyi işlemleri de atardı.", ["r", "ABD'de tersine çalışıyor: ana tepeye uzaklık (yüksek oran) büyüdükçe sonuç kötüleşiyor."]],
    "kilit": ["r", "Eğitmenin formülü çözülemedi (kutu üst kenarı kilitlerin ancak 4'te 1 ile yarısını tutturuyor); 'kilit üstünde haftalık kapanışta al' rastgeleden iyi değil.", ["r", "ABD'de de 'kilit üstünde haftalık kapanışta al' rastgeleden iyi değil."]],
    "supurme": ["s", "3+ temaslı destek süpürülüp geri alınınca 120 günde rastgeleden +7 puan; ama süpürmesiz tepki de +5, kırılıp geri alınmayan +12: süpürmeye özgü değil, genel 'düşüş sonrası alım' etkisi.", ["s", "Wyckoff spring ABD'de de aynı hissenin sıradan haftasından +8-10 puan iyi, ama aynı hafta başka hisse almaktan iyi değil."]],
}
EG_PIVOT = 2           # haftalık dönüş noktası: iki yanındaki 2 haftanın en düşüğü/en yükseği (test1 B ana tanımı)
EG_TOL = 0.5           # temas toleransı = 0,5 haftalık ATR (test1 B ana tanımı)
EG_PENCERE = 104       # trend çizgisi ve yatay seviyeler: son 2 yıl
# bariz destek/direnç + süpürme: 2026-11-20/temas araştırmasının ana tanımı (seviye.seviyeler, PG): günlük pivot 5, tolerans 0,5 ATR(14),
# seviye ömrü son temastan 250 gün, test 20 günde sonuçlanmazsa düşer, kapanışla sarkma ≤5 günde geri alınırsa süpürme
SV_K, SV_TOL, SV_EXP, SV_TO, SV_SW = 5, 0.5, 250, 20, 5
SV_UZAK = 0.15         # kapanışın en çok %15 uzağındaki seviyeler gösterilir
SV_BAR = 750           # hesap son ~3 yılın günlük verisiyle (t7: 256 hissede tam 10 yılla 0 fark; 500 günde 7 hissede fark)
EG_SUP_GUN = 40        # son dip süpürmesi: son 40 işlem günü (~8 hafta)
EG_SUP_TEMAS = 3       # süpürülen destek bariz olmalı: en az 3 temas (araştırmanın süpürme testi)
EG_ZZ = 0.15           # iki durak / ana tepe: haftalık kapanışta %15'lik dönüş (zigzag)
EG_DERIN = 0.95        # alt durak: üst duraktan en az %5 derin önceki dip
EG_KILIT = 26          # yaklaşık kilit: son 26 haftanın en yüksek haftalık kapanışı
EG_YAKIN = 0.03        # üst liste 'çok temaslı desteğe yakın': fiyat en yakın 3+ temaslı desteğin en çok %3 üstünde
EG_SUP_LISTE = 20      # üst liste 'son dip süpürmesi': geri alma son 20 işlem gününde (~4 hafta)


def _pivot(x, k, dip):
    """Haftalık dönüş noktaları: x[i] iki yanındaki k haftanın en düşüğü (dip) / en yükseği (tepe). Son k hafta onaysız."""
    n = len(x)
    p = np.zeros(n, bool)
    if n < 2 * k + 1:
        return p
    from numpy.lib.stride_tricks import sliding_window_view
    w = sliding_window_view(x, 2 * k + 1)
    ref = w.min(axis=1) if dip else w.max(axis=1)
    p[k:n - k] = x[k:n - k] == ref
    return p


def _atr_hafta(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).rolling(n, min_periods=5).mean().values


def _cizgi(x, xc, tol, P, n):
    """test1 testB çizgi kuralının 'bugün' hâli (ayna uzayında yükselen çizgi): x = log dip (düşen çizgide −log tepe), xc = log kapanış.
    İki dönüş noktası q<p, x[q]<x[p]; q..p arası x çizgi−tol altına inmez, p sonrası kapanış çizgi−tol altına inmez (kırılmamış).
    Temas = x çizgiye tol kadar yaklaşan hafta (ardışık haftalar tek temas). En çok temaslı, eşitse son teması yeni olan."""
    best = None
    for i, q in enumerate(P):
        for p in P[i + 1:]:
            if p - q < 4 or not x[p] > x[q]:
                continue
            s = (x[p] - x[q]) / (p - q)
            ss = np.arange(q, n)
            line = x[q] + s * (ss - q)
            tt = tol[ss]
            ara = ss <= p
            if np.any(x[ss[ara]] < line[ara] - tt[ara]) or np.any(xc[ss[~ara]] < line[~ara] - tt[~ara]):
                continue
            tm = x[ss] <= line + tt
            bas = tm & ~np.r_[False, tm[:-1]]
            temas = int(bas.sum())
            son = int(ss[np.flatnonzero(tm)[-1]])
            anah = (temas, son, -q)
            if best is None or anah > best[0]:
                best = (anah, q, s, temas, son)
    return best


def gunluk_seviyeler(lo, hi, cl, tol, k=SV_K, EXP=SV_EXP, TO=SV_TO, SW=SV_SW, basla=None):
    """2026-11-20/temas seviye.seviyeler'in (yatay destek) birebir kopyası; sadece canlıda gereken 'sup' olayları kaydedilir.
    lo/hi/cl: log fiyat (direnç için −log High / −log Low / −log Close), tol: her bar için log tolerans. Döner (sup olayları, aktif seviyeler).
    Temas n: seviyeyi kuran pivot dip = 1; her zıplama (kapanış ≥ L + 2·tol) +1. Süpürme: kapanışla L − tol altına sarktıktan 1..SW bar
    sonra kapanış L üstü."""
    n = len(cl); aktif = []; ev = []
    basla = n if basla is None else basla
    for t in range(n):
        tt = tol[t]
        if not tt == tt:
            continue
        kayit = t >= basla
        for S in list(aktif):
            L = S["L"]
            d = S["dur"]
            if d == "kurulum":
                if cl[t] < L - tt:
                    aktif.remove(S); continue
                if cl[t] >= L + 2 * tt:
                    S["dur"] = "serbest"
                continue
            if d == "serbest":
                if lo[t] <= L + tt:
                    S.update(dur="test", ep=t, minl=lo[t], b=None, g=None)
                elif t - S["son"] > EXP:
                    aktif.remove(S); continue
                else:
                    continue
            S["minl"] = min(S["minl"], lo[t])
            if S["b"] is None and cl[t] < L - tt:
                S["b"] = t; S["g"] = None
            if S["b"] is not None and S["g"] is None and t > S["b"]:
                if cl[t] > L:
                    S["g"] = t
                    if kayit:
                        ev.append({"t": t, "n": S["n"], "L": L, "gun": t - S["b"], "derin": S["minl"] - L, "b": S["b"]})
                elif t - S["b"] >= SW:
                    aktif.remove(S); continue
            if S["g"] is not None and t > S["g"] and cl[t] < L - tt:
                S["b"] = t; S["g"] = None
            if cl[t] >= L + 2 * tt:
                S["n"] += 1; S["dur"] = "serbest"; S["son"] = t
                continue
            if (S["b"] is None or S["g"] is not None) and t - S["ep"] > TO:
                aktif.remove(S); continue
        p = t - k
        if p >= k and lo[p] == lo[p - k:t + 1].min():
            if not any(abs(Q["L"] - lo[p]) <= tt for Q in aktif):
                aktif.append({"L": lo[p], "n": 1, "dur": "kurulum", "son": t, "p": p})
    return ev, aktif


def _atr_wilder(H, L, C, a=14):
    pc = np.r_[np.nan, C[:-1]]
    tr = np.nanmax(np.vstack([H - L, np.abs(H - pc), np.abs(L - pc)]), axis=0)
    return pd.Series(tr).ewm(alpha=1 / a, adjust=False, min_periods=a).mean().values


def bariz_seviyeler(d, bar=SV_BAR):
    """Günlük df → {'sd': destekler, 'sr': dirençler, 'sp': son süpürme}. sd/sr = [[en yakın, temas], ([en yakın 3+ temaslı, temas])],
    yalnız kapanışın %15 içindekiler (araştırmanın bugun.py'si). sp: son EG_SUP_GUN günde 3+ temaslı desteğin süpürülüp geri alınması."""
    x = d.iloc[-bar:] if bar else d
    H, L, C = (x[c].values.astype(float) for c in ("High", "Low", "Close"))
    if len(C) < 60:
        return {}
    a = _atr_wilder(H, L, C) / C
    tol = SV_TOL * a
    lh, ll, lc = np.log(H), np.log(L), np.log(C)
    out = {}
    tt = tol[-1]
    for ad, (lo, hi, cc), sgn in (("sd", (ll, lh, lc), 1), ("sr", (-lh, -ll, -lc), -1)):
        ev, ak = gunluk_seviyeler(lo, hi, cc, tol, basla=len(C) - EG_SUP_GUN if ad == "sd" else None)
        ak = [S for S in ak if S["dur"] != "kurulum" and S["L"] < cc[-1] + tt and abs(np.exp(sgn * S["L"]) / C[-1] - 1) <= SV_UZAK]
        if ak:
            en = max(ak, key=lambda S: S["L"])
            liste = [[_r(np.exp(sgn * en["L"])), int(en["n"])]]
            cok = [S for S in ak if S["n"] >= 3]
            if cok:
                ec = max(cok, key=lambda S: S["L"])
                if ec is not en:
                    liste.append([_r(np.exp(sgn * ec["L"])), int(ec["n"])])
            out[ad] = liste
        if ad == "sd":
            sup = [e for e in ev if e["n"] >= EG_SUP_TEMAS]
            if sup:
                e = sup[-1]
                out["sp"] = {"t": _g(x.index[e["t"]]), "bt": _g(x.index[e["b"]]), "s": _r(np.exp(e["L"])), "d": _r(np.exp(e["L"] + e["derin"])),
                             "n": int(e["n"]), "h": int(len(C) - 1 - e["t"]), "gun": int(e["gun"])}
    return out


def zigzag_dipler(c, Z):
    """Kapanış zigzag dipleri (dip indeksi, değer, onay haftası); zigzag_tepeler'in aynası."""
    out = []
    yon = 0
    li, lv = 0, c[0]
    ci, cv = 0, c[0]
    for t in range(1, len(c)):
        x = c[t]
        if yon <= 0:
            if x < lv:
                li, lv = t, x
            if x >= lv * (1 + Z):
                out.append((li, lv, t))
                yon = 1
                ci, cv = t, x
        if yon > 0:
            if x > cv:
                ci, cv = t, x
            if x <= cv * (1 - Z):
                yon = -1
                li, lv = t, x
    return out


def egitim_katmani(h, l, c, wt, yd=None, tepe3=None):
    """📚 Eğitim katmanı: TAMAMLANMIŞ haftalık h/l/c (wt = hafta tarihleri) ile 8 kavramın yaklaşık hâli. yd = yon_durumu sonucu (varsa
    ana tepe/tepecik oradan, araştırmanın tanımı), tepe3 = son 3 yılın en yükseği (hedef yedeği). Döner sözlük (harita.json 'eg')."""
    n = len(c)
    if n < 60:
        return None
    a = _atr_hafta(h, l, c) / c                       # haftalık ATR, fiyata oranla (log birimi yaklaşığı)
    a = pd.Series(a).ffill().bfill().values
    tol = EG_TOL * a
    k = EG_PIVOT
    pd_, pt_ = _pivot(l, k, True), _pivot(h, k, False)
    bas = n - EG_PENCERE
    eg = {}
    # 1) trend çizgisi (yükselen: dipler; düşen: tepeler, ayna uzayında)
    lw, hw, cw = np.log(l), np.log(h), np.log(c)
    Pd = [p for p in np.flatnonzero(pd_) if p >= bas]
    Pt = [p for p in np.flatnonzero(pt_) if p >= bas]
    by = _cizgi(lw, cw, tol, Pd, n)
    bd = _cizgi(-hw, -cw, tol, Pt, n)
    sec = None
    if by and (not bd or by[0] >= bd[0]):
        sec = (1, by)
    elif bd:
        sec = (-1, bd)
    if sec:
        yon, (_, q, s, temas, son) = sec
        x0 = lw[q] if yon == 1 else hw[q]
        eg["tc"] = {"y": yon, "n": temas, "q": int(q), "x0": float(x0), "s": float(s * yon), "st": int(n - 1 - son),
                    "qt": _g(wt[q]), "e": round(float(np.expm1(s * yon)), 4)}
    # 2) bariz destek/direnç ve 8) son dip süpürmesi günlük veriyle: hisse_kaydi (bariz_seviyeler)
    # 3) iki durak: son onaylı %15 zigzag dibi (üst) + ondan %5+ derin önceki dip (alt)
    zd = [z for z in zigzag_dipler(c, EG_ZZ) if z[0] > 0]   # serinin ilk haftası "dip" sayılmaz
    i_ust = None
    if zd:
        i_ust = zd[-1][0]
        ust = float(l[i_ust])
        dr = {"u": _r(ust), "ut": _g(wt[i_ust])}
        for i_, v_, _ in reversed(zd[:-1]):
            if l[i_] < ust * EG_DERIN:
                dr.update({"a": _r(l[i_]), "at": _g(wt[i_])})
                break
        eg["dr"] = dr
    # 4) ana tepe / tepecik: büyük düşüş bölümü varsa araştırmanın tanımı (yon_durumu), yoksa son zigzag dibine ait tepe
    if yd:
        eg["tp"] = {"k": "yon", "at": _r(yd["ana_tepe"]), "dp": _r(yd["dip"]), "dt": _g(wt[yd["i_dip"]]) if yd["i_dip"] < n else None,
                    "g": yd["i_asildi"] is not None, "tc": _r(yd["tepecik"]) if yd["tepecik"] else None, "tg": yd["i_tepecik"] is not None}
    elif i_ust is not None:
        tep = [z for z in zigzag_tepeler(c, EG_ZZ) if z[0] < i_ust]
        if tep:
            at = float(tep[-1][1])
            sonra = c[i_ust + 1:]
            gi = np.flatnonzero(sonra > at)
            tc, tg = None, False
            R, pR = c[i_ust], i_ust
            for t_ in range(i_ust + 1, n):
                if c[t_] > R:
                    R, pR = c[t_], t_
                if pR > i_ust and c[t_] <= R * (1 - YON_TZ):
                    tc = float(R)
                    tg = bool(np.any(c[t_ + 1:] > tc))
                    break
            eg["tp"] = {"k": "zz", "at": _r(at), "att": _g(wt[tep[-1][0]]), "dp": _r(c[i_ust]), "dt": _g(wt[i_ust]),
                        "g": bool(len(gi)), "gt": _g(wt[i_ust + 1 + int(gi[0])]) if len(gi) else None,
                        "tc": _r(tc) if tc else None, "tg": tg}
    # 5) kutu: son 8 tamamlanmış hafta
    ka, ku = float(l[n - KUTU_N:].min()), float(h[n - KUTU_N:].max())
    eg["kt"] = {"a": _r(ka), "u": _r(ku)}
    # 6) kâr/zarar: alt duraktan (yoksa üst) ana tepeye kâr, stop = durağın 1 haftalık ATR altı
    dr = eg.get("dr")
    tp = eg.get("tp")
    if dr:
        giris = dr.get("a") or dr["u"]
        hk = "t" if tp and tp.get("at") and tp["at"] > giris else "3y"
        hedef = tp["at"] if hk == "t" else (tepe3 if tepe3 and tepe3 > giris else None)
        stop = giris * (1 - a[n - 1])
        if hedef and giris > stop > 0:
            eg["kz"] = {"g": _r(giris), "s": _r(stop), "h": _r(hedef), "o": round((hedef - giris) / (giris - stop), 1),
                        "ad": "a" if dr.get("a") else "u", "hk": hk}
    # 7) yaklaşık kilit: son tamamlanan hafta hariç son 26 haftanın en yüksek kapanışı; son haftalık kapanış üstünde mi
    kl = float(c[n - 1 - EG_KILIT:n - 1].max())
    eg["kl"] = {"v": _r(kl), "u": bool(c[n - 1] > kl), "c": _r(c[n - 1])}
    return eg


def egitim_destek(eg, en_az=3):
    """En yakın bariz destek (en az `en_az` temas, kapanışın %15 içinde) → (seviye, temas) | None. JS `egYakin` ile aynı seçim."""
    if not eg:
        return None
    alt = [z for z in eg.get("sd", []) if z[0] and z[1] >= en_az]
    return tuple(max(alt, key=lambda z: z[0])) if alt else None


# ============================================================ tek hisse kaydı
def _r(v, sig=5):
    if v is None or not np.isfinite(v):
        return None
    return float(f"{float(v):.{sig}g}")


def _g(ts):
    return None if ts is None else str(pd.Timestamp(ts).date())


def hisse_kaydi(d, hafta_son, tamam, grup):
    """d: hazırlanmış günlük df (son satır = taramanın son işlem günü). hafta_son: 'bu hafta'nın cuma tarihi; tamam: bu hafta kapandı mı.
    Döner harita.json'daki hisse kaydı (canlı alanlar `canli` ile doldurulur)."""
    W = haftalik(d)
    hs = W["hs"]
    once = np.asarray(hs < hafta_son)              # bu haftadan önceki (tamamlanmış) haftalar
    t = int(once.sum())                            # bu haftanın indeksi
    h, l, c = W["h"][:t], W["l"][:t], W["c"][:t]
    wt = list(W["t"][:t])
    kayit = {"g": grup}
    kel = kelepir_param(h, l, wt, t)
    if kel:
        kayit["kel"] = {"P": _r(kel["P"]), "P_t": _g(kel["P_t"]), "T": _r(kel["T"]), "T_t": _g(kel["T_t"]), "kat": round(kel["kat"], 2),
                        "kel_alt": _r(kel["kel_alt"]), "kel_ust": _r(kel["kel_ust"]), "ucuz_ust": _r(kel["ucuz_ust"]),
                        "hizli": kel["ralli_hafta"] < 52, "rh": kel["ralli_hafta"]}
    kt = kutu_param(h, l, t)
    if kt and kt["gecerli"]:
        kayit["kutu"] = {k: _r(v) for k, v in kt.items() if k != "gecerli"}
    # yön durumu: yalnız tamamlanmış haftalar (bu hafta kapandıysa o da)
    ct = W["c"][:t + 1] if tamam and len(W["c"]) > t else c
    wtt = list(W["t"][:len(ct)])
    yd = yon_durumu(ct)
    if yd:
        son_i = len(ct) - 1
        kayit["yon"] = {"zirve": _r(yd["zirve"]), "zirve_t": _g(wtt[yd["i_zirve"]]), "dip": _r(yd["dip"]), "dip_t": _g(wtt[yd["i_dip"]]),
                        "dip_yas": son_i - yd["i_dip"], "dusus": round(1 - yd["dip"] / yd["zirve"], 3), "ana_tepe": _r(yd["ana_tepe"]),
                        "tepecik": _r(yd["tepecik"]) if yd["tepecik"] else None,
                        "ilk": yd["i_ilk"] is not None, "tgec": yd["i_tepecik"] is not None, "yakin": yd["i_yakin"] is not None,
                        "asildi": None if yd["i_asildi"] is None else son_i - yd["i_asildi"],
                        "son_hafta": _g(wtt[son_i])}
    sv = seviyeler(d)
    if sv:
        kayit["sv"] = {"tepe": _r(sv["tepe"]), "tepe_t": _g(sv["tepe_t"]), "dip": _r(sv["dip"]), "dip_t": _g(sv["dip_t"]),
                       "dip_yas": sv["dip_yas"], "orta": _r(sv["orta"]), "poc": _r(sv["poc"]), "vah": _r(sv["vah"]), "val": _r(sv["val"]),
                       "sure": sv["taban_sure"]}
        if sv["dip_yas"] >= TABAN_MIN_HAFTA:
            kayit["sv"]["kilit"] = _r(sv["kilit"])
            kayit["sv"]["mal"] = _r(sv["maliyet"])
    # grafik: son GRAFIK_HAFTA haftanın kapanışı + bu hafta (canlıda güncellenir), ortak cuma ızgarasında
    izgara = pd.date_range(end=hafta_son, periods=GRAFIK_HAFTA + 1, freq="W-FRI")
    seri = pd.Series(W["c"], index=hs).groupby(level=0).last()
    s = seri.reindex(izgara.union(seri.index)).ffill().reindex(izgara)
    kayit["s"] = [None if not np.isfinite(v) else _r(v, 4) for v in s.values]
    kayit["_wl"] = _g(hafta_son)
    # 📚 eğitim katmanı (hata olursa yalnız bu bölüm düşer; harita ve tarama etkilenmez)
    try:
        m = len(ct)
        eg = egitim_katmani(W["h"][:m], W["l"][:m], ct, wtt, yd, sv["tepe"] if sv else None)
        if eg:
            tc = eg.get("tc")
            if tc:
                q, x0, sl = tc.pop("q"), tc.pop("x0"), tc.pop("s")
                deger = lambda j: float(np.exp(x0 + sl * (j - q)))
                j0 = max(q, int(hs.searchsorted(izgara[0])))
                g0 = int(izgara.get_indexer([hs[j0]])[0]) if j0 < len(hs) else -1
                tc["v"] = _r(deger(t))
                if g0 >= 0:
                    tc["a"] = [g0, _r(deger(j0)), GRAFIK_HAFTA, tc["v"]]
            eg.update(bariz_seviyeler(d))
            kayit["eg"] = eg
    except Exception as e:
        print(f"Harita: eğitim katmanı hesaplanamadı ({type(e).__name__}).")
    return kayit


# ============================================================ canlı (her tarama)
def canli(kayit, x, wl):
    """Anlık fiyat x ve bu haftanın en düşüğü wl ile durumlar. Sadece kıyaslama; yeni veri çekmez."""
    d = {}
    if x:
        kd = kelepir_durum(kayit.get("kel"), x)
        if kd:
            d["kel"] = kd
        if kutu_durum(kayit.get("kutu"), x, wl):
            d["kutu"] = True
        sv = kayit.get("sv")
        if sv and sv.get("tepe") and sv.get("dip") and sv["tepe"] > sv["dip"]:
            d["konum"] = round((x - sv["dip"]) / (sv["tepe"] - sv["dip"]), 3)
        if kayit.get("s"):
            kayit["s"][-1] = _r(x, 4)
    kayit["f"] = _r(x)
    kayit["d"] = d
    return kayit


def listeler(H):
    L = {"kelepir": [], "ucuz": [], "kutu": [], "dusus": [], "tdestek": [], "supurme": []}
    for kod, k in H.items():
        d = k.get("d") or {}
        if d.get("kel") == "kelepir":
            L["kelepir"].append(kod)
        elif d.get("kel") == "ucuz":
            L["ucuz"].append(kod)
        if d.get("kutu"):
            L["kutu"].append(kod)
        y = k.get("yon")
        if y and y.get("asildi") is None:
            L["dusus"].append(kod)
        eg = k.get("eg")
        if eg:
            ds = egitim_destek(eg)
            if ds and k.get("f") and ds[0] <= k["f"] <= ds[0] * (1 + EG_YAKIN):
                L["tdestek"].append(kod)
            if eg.get("sp") and eg["sp"]["h"] < EG_SUP_LISTE:
                L["supurme"].append(kod)
    f = lambda kod: (H[kod].get("f") or 0) / (H[kod]["kel"]["T"] or 1)
    L["kelepir"].sort(key=f)
    L["ucuz"].sort(key=f)
    L["kutu"].sort()
    L["dusus"].sort(key=lambda kod: -H[kod]["yon"]["dusus"])
    L["tdestek"].sort(key=lambda kod: H[kod]["f"] / egitim_destek(H[kod]["eg"])[0])
    L["supurme"].sort(key=lambda kod: (H[kod]["eg"]["sp"]["h"], kod))
    return L


# ============================================================ indirme + yenileme
def _uzun_indir(kodlar, sure=ZAMAN_ASIMI):
    """10 yıllık günlük veri tek toplu indirme; daemon iş parçacığında, `sure` sn'de bitmezse None (tarama beklemez)."""
    sonuc = {}

    def is_():
        try:
            import yfinance as yf
            sonuc["g"] = yf.download([k + ".IS" for k in kodlar], period=INDIRME_DONEM, interval="1d", group_by="ticker",
                                     auto_adjust=True, progress=False, threads=True)
        except Exception as e:
            sonuc["hata"] = type(e).__name__

    th = threading.Thread(target=is_, daemon=True)
    th.start()
    th.join(sure)
    if th.is_alive():
        return None, "zaman aşımı"
    return sonuc.get("g"), sonuc.get("hata")


def _birlestir(uzun, kisa):
    """Son 4 yıl taramanın (kapanışı düzeltilmiş) verisinden, öncesi uzun indirmeden."""
    if kisa is None or kisa.empty:
        return uzun
    if uzun is None or uzun.empty:
        return kisa
    k = kisa.copy()
    u = uzun.copy()
    if k.index.tz is not None:
        k = k.tz_localize(None)
    if u.index.tz is not None:
        u = u.tz_localize(None)
    return pd.concat([u[u.index < k.index[0]], k])


def hafta_bilgisi(son_gun, simdi, kapanis_zamani):
    """'Bu hafta'nın cuma tarihi ve kapanıp kapanmadığı. son_gun: taramanın son işlem günü (Timestamp)."""
    hs = pd.Timestamp(son_gun).to_period("W-FRI").end_time.normalize()
    bugun = pd.Timestamp(simdi.date()) if hasattr(simdi, "date") else pd.Timestamp(simdi)
    tamam = bugun > hs or (bugun == hs and bool(kapanis_zamani))
    return hs, bool(tamam)


def yenile(kodlar, gruplar, kisa_veri, hafta_son, tamam, uzun=None):
    """Tüm hisseler için kayıtları yeniden hesaplar. uzun: önceden indirilmiş 10y veri (test için); yoksa indirir.
    Döner (H, not) — indirme başarısızsa (None, neden)."""
    t0 = time.time()
    if uzun is None:
        uzun, hata = _uzun_indir(kodlar)
        if uzun is None:
            return None, f"uzun geçmiş alınamadı ({hata})"
    t1 = time.time()
    H = {}
    for kod in kodlar:
        try:
            try:
                u = uzun[kod + ".IS"][["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
            except KeyError:
                u = None
            k = kisa_veri.get(kod)
            d = _birlestir(u, k)
            if d is None or len(d) < 300:
                continue
            d = hazirla(d)
            if len(d) < 300:
                continue
            d = d[d.index <= hafta_son + pd.Timedelta(days=1)]
            H[kod] = hisse_kaydi(d, hafta_son, tamam, gruplar.get(kod, "ana"))
        except Exception as e:
            print(f"Harita: {kod} hesaplanamadı ({type(e).__name__}).")
    return H, f"yenilendi: {len(H)} hisse, indirme {t1 - t0:.1f} sn, hesap {time.time() - t1:.1f} sn"


def oku(yol=HARITA_JSON):
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def yaz(veri, yol=HARITA_JSON):
    with open(yol, "w", encoding="utf-8", newline="\n") as f:
        json.dump(veri, f, ensure_ascii=False, separators=(",", ":"))


def calistir(data, simdi, kapanis_zamani, ana, kucuk, manip=(), dikkat=(), yol=HARITA_JSON, html_yol=HARITA_HTML, uzun=None):
    """tarama.py'den: data = taramanın günlük verisi (yf.download çoklu sütun, KOD.IS), ana/kucuk = kod kümeleri.
    dikkat = ⚠️/🎈 işaretli kodlar (kartta 'dikkat' notu). Döner kısa log metni. İstisna fırlatabilir (tarama try/except'li)."""
    kodlar = sorted((set(ana) | set(kucuk)) - set(manip))
    gruplar = {k: ("ana" if k in ana else "kucuk") for k in kodlar}
    kisa, son_gun = {}, None
    for kod in kodlar:
        try:
            x = data[kod + ".IS"].dropna(subset=["Close"])
        except KeyError:
            continue
        if len(x):
            if x.index.tz is not None:
                x = x.tz_localize(None)
            kisa[kod] = x[["Open", "High", "Low", "Close", "Volume"]]
            son_gun = x.index[-1] if son_gun is None or x.index[-1] > son_gun else son_gun
    if son_gun is None:
        return "Harita: tarama verisi yok, atlandı"
    hafta_son, tamam = hafta_bilgisi(son_gun, simdi, kapanis_zamani)
    eski = oku(yol)
    anahtar = {"v": SURUM, "gun": str(simdi.date()), "hafta": _g(hafta_son), "tamam": tamam}
    notu = "canlı fiyat güncellendi"
    H = None
    if not eski or eski.get("anahtar") != anahtar:
        H, notu = yenile(kodlar, gruplar, kisa, hafta_son, tamam, uzun=uzun)
        if H is None and eski:
            notu += "; eski harita kullanılıyor"
    taze = H is not None
    if H is None:
        if not eski:
            return f"Harita: {notu}; dosya yok, atlandı"
        H = eski.get("h", {})
        anahtar_yaz = eski.get("anahtar")
        uretim = eski.get("uretim")
    else:
        anahtar_yaz = anahtar
        uretim = simdi.strftime("%Y-%m-%d %H:%M")
    hs_str = _g(hafta_son)
    for kod, k in H.items():
        x = kisa.get(kod)
        fiyat, wl = None, None
        if x is not None and len(x):
            fiyat = float(x["Close"].iloc[-1])
            bu = x[x.index > hafta_son - pd.Timedelta(days=7)]
            if len(bu) and k.get("_wl") == hs_str:
                wl = float(bu["Low"].min())
        if fiyat is None:
            fiyat = k.get("f")
        canli(k, fiyat, wl)
        k["dk"] = kod in set(dikkat)
    veri = {"v": SURUM, "anahtar": anahtar_yaz, "uretim": uretim, "guncel": simdi.strftime("%Y-%m-%d %H:%M"),
            "taze": taze or bool(eski and eski.get("anahtar") == anahtar),
            "hafta": hs_str, "tamam": tamam, "bayrak": {"yabanci": YABANCI_ACIK}, "egr": EGITIM_ROZET,
            "g0": _g(pd.date_range(end=hafta_son, periods=GRAFIK_HAFTA + 1, freq="W-FRI")[0]),
            "liste": listeler(H), "h": H}
    yaz(veri, yol)
    html_yaz(html_yol)
    return f"Harita: {notu} ({len(H)} hisse)"


def html_yaz(yol=HARITA_HTML):
    """harita.html'i şablondan yaz (sadece değiştiyse). Fork'larda da *.py ile gelir."""
    try:
        with open(yol, encoding="utf-8") as f:
            if f.read() == SAYFA:
                return False
    except OSError:
        pass
    with open(yol, "w", encoding="utf-8", newline="\n") as f:
        f.write(SAYFA)
    return True


from harita_sayfa import SAYFA  # noqa: E402  (şablon ayrı dosyada: düzenlemesi kolay)
