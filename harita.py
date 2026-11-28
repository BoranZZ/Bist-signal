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
SURUM = 5              # 2: 📚 eğitim katmanı (eg); 3: dip arası bölge + ekmek kırıntısı; 4: 🥇 altın/gümüş/döviz bölümü (em); 5: 28.11 rozet denetimi (egr metinleri) → ilk taramada yeniden hesaplanır
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
# Durum kodları: 'y' 🟢 tuttu, 's' 🟡 kısmen, 'r' 🔴 tutmadı, 'o' ⚪ henüz ölçülmedi, 't' 🧪 test sürüyor. Kaynak: 2026-11-19/OZET_19-11.md bölüm 3;
# durak/tepe/kutu/dipara/supurme 28.11 denetimiyle güncellendi (aynı hafta benzer koşu+derinlik kıyası): 2026-11-28/denetim/RAPOR.md.
EGITIM_ROZET = {   # kavram: [durum, BIST'te tek satır, ABD sonucu (None = test sürüyor; gelince [durum, tek satır])]
    "trend": ["r", "3. temasta kırılma yazı-tura (%52); her ek temas kırılmayı ~%7 AZALTIYOR (çok temas = zayıf çizgi değil); kırılım sonrası rastgeleden kötü gitmedi.", ["r", "S&P 500 ve S&P 600'de de 3. temasta kırılma yazı-tura (%50 / %51)."]],
    "yatay": ["r", "3. temasta kırılma %40, 6.+ temasta %33 (çok temas seviyeyi zayıflatmıyor); kırılırsa alttaki seviyeye inme %60, rastgele günde de %61.", None],
    "durak": ["s", "Alt kademe (kelepir bandı) aynı hafta benzer ralli ve düşüş yaşamış başka hisseden iyi değil (12 ayda −4 puan; 25 yıl, 101 olay). 'Arada alma' uyarısı ters değil: benzer düşmüş hisselere göre taban dibinde almak 52 haftada −7, ara kademede +3, kilit üstünde +15 puan; eski 'dipte almak iyi' sonucu kriz zamanlamasıydı.", ["s", "ABD'de de kelepir bandı ve taban dibi benzer hisselerden iyi değil (0 / −5 puan), kutu içinden almak biraz kötü (−4); kilit üstünde almak +5 puan iyi: 'arada alma' uyarısı ABD'de hafifçe haklı."]],
    "tepe": ["s", "Riskte haklı (ana tepe geçilince yeni dip olasılığı %40 → %15); getiride de beklemek kaybettirmedi: benzer düşmüş hisselere göre ana tepe kırılımında almak 52 haftada +11, ilk tepkide +3, dip yakınında −4 puan (eski '−9' kriz zamanlamasıydı; fark 2013 sonrası).", ["y", "ABD'de de riskte haklı (yeni dip büyüklerde %31 → %9, küçüklerde %44 → %19); getiride de: ana tepe kırılımında almak benzer düşmüş hisselerden 52 haftada +7 puan iyi (büyükler +10, küçükler +5), dip yakını −3."]],
    "kutu": ["r", "Kutunun alt üçte birinde almak benzer düşmüş başka hisselerden iyi değil (52 haftada +2, 12 haftada −2 puan); kutu kırılımından da farkı yok (+2): eski '+6 puan' kriz zamanlamasıydı. 'Kutu içinde işlem açma' uyarısı ne doğru ne ters.", ["r", "ABD'de kutu içinden almak benzer hisselerden biraz kötü (52 haftada −4 puan, her dönemde), kırılım farksız: 'kutu içinde işlem açma' uyarısı ABD'de hafifçe haklı."]],
    "kz": ["r", "Oran v3, 🧲 Bant ve 🧲 SMA200 işlemlerinin sonucunu ayırmadı; '%30 kâr kalmıyorsa alma' süzgeci iyi işlemleri de atardı.", ["r", "ABD'de tersine çalışıyor: ana tepeye uzaklık (yüksek oran) büyüdükçe sonuç kötüleşiyor."]],
    "kilit": ["r", "Eğitmenin formülü çözülemedi (kutu üst kenarı kilitlerin ancak 4'te 1 ile yarısını tutturuyor); 'kilit üstünde haftalık kapanışta al' rastgeleden iyi değil.", ["r", "ABD'de de 'kilit üstünde haftalık kapanışta al' rastgeleden iyi değil."]],
    "dipara": ["r", "Bölgeye inince almak, aynı hafta benzer ralli ve düşüş yaşamış başka hisseden iyi değil (52 haftada −11 puan; 25 yılda ve 10 yılda); eski +29 / +22 puan kriz zamanlamasıydı. 'Üstünde tutunursa' teyidini beklemek de iyi değil (−8); kırılım sonrası almak kötü (−37, az olay).", ["r", "ABD'de de bölgede almak benzer hisselerden farksız (+2 puan), teyit beklemek de (+3); kırılım sonrası almak +23 puan iyi: 'kırarsa düşer' ABD'de ters."]],
    "kirinti": ["r", "Yükselişteki ara diplere düşüşte dokununca 26 haftada önce +%15 gelme %61; tepeye aynı uzaklıktaki rastgele seviyede %64: seviyeler özel değil, tutma oranını yalnız tepeden uzaklık belirliyor.", None],
    "taban": ["r", "Bölgeye dönen hisse, aynı hafta benzer düşmüş başka hisselerden belirgin iyi değil (2018 sonrası hafif +, öncesi −); kademeli alım getiriyi artırmadı, bölge altı stop düşürdü (28.11 taban araştırması).", ["r", "S&P 500 + 600'de aynı hafta benzer hisselere göre fark yok (−4 puan)."]],
    "supurme": ["r", "3+ temaslı destek süpürülüp geri alınınca, aynı gün benzer düşmüş başka hisseden iyi değil (60 günde 0, 126 günde −1 puan); eski '+7 puan' kriz zamanlamasıydı. Süpürmesiz tepki de farksız (−2).", ["r", "Wyckoff spring ABD'de benzer ralli ve düşüş yaşamış başka hisseden iyi değil, biraz kötü (52 haftada −4 puan)."]],
}
# 🧱 taban bölgesinin emtia/döviz sonucu (EGITIM_ROZET 3 alanlı kalsın diye ayrı; json 'tbr', yalnız 🥇 kartlarında). Kaynak 2026-11-28/taban/RAPOR.md
TABAN_EMTIA = ["r", "1970'ten beri 21 emtiada ve 46 emtia/endeks/döviz serisinde bölge, aynı derinlikteki rastgele bir seviyeden daha sık kırıldı (52 haftada tutma %58'e karşı %69); bölgeye dönüş benzer düşmüş başka varlıklardan iyi gitmedi. Altında 1970'ten 8 olay: 12 ayda ort. +%11, karışık (1976 ve 2008 iyi, 2013 2-3 yıl düz)."]
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
EG_DA_PENCERE = 156    # dip arası bölge: alt = son 156 haftanın en düşük haftalık dibi (ana dip; videodaki ENTRA kutusunu birebir verir)
EG_DA_FARK = 1.03      # üst = ana dipten sonraki, ana dipten ≥%3 yüksek ilk onaylı %15 zigzag dibi (daha yakın dipler tabanın parçası)
EG_DA_TEYIT = 1.05     # bölgeye inişten sonra yukarıdaki dibin %5 üstünde haftalık kapanış = teyit (2026-11-20/dip-arasi tanımı)
EG_DA_HAFTA = 12       # teyit / kırılım bölgeye inişten sonraki 12 hafta içinde aranır
EG_KR_N = 4            # ekmek kırıntısı: son 3 yılın en büyük tepesine çıkarken bırakılan en çok 4 yükselen dip
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


def zigzag_hl(h, l, Z):
    """Haftalık en yüksek/en düşükle onaylı zigzag (2026-11-20/dip-arasi/dip_arasi.py zz ile aynı).
    Döner [(tür 'H'/'L', pivot haftası, değer, onay haftası)]; pivot ancak fiyat ondan Z kadar dönünce bilinir (bakış-ileri yok)."""
    P = []
    mode, hi, hi_i, lo, lo_i = 0, h[0], 0, l[0], 0
    for i in range(1, len(h)):
        if mode == 0:
            if h[i] > hi:
                hi, hi_i = h[i], i
            if l[i] < lo:
                lo, lo_i = l[i], i
            if l[i] <= hi * (1 - Z) and hi_i < i:
                P.append(("H", hi_i, hi, i)); mode = -1; lo, lo_i = l[i], i
            elif h[i] >= lo * (1 + Z) and lo_i < i:
                P.append(("L", lo_i, lo, i)); mode = 1; hi, hi_i = h[i], i
        elif mode == 1:
            if h[i] > hi:
                hi, hi_i = h[i], i
            elif l[i] <= hi * (1 - Z):
                P.append(("H", hi_i, hi, i)); mode = -1; lo, lo_i = l[i], i
        else:
            if l[i] < lo:
                lo, lo_i = l[i], i
            elif h[i] >= lo * (1 + Z):
                P.append(("L", lo_i, lo, i)); mode = 1; hi, hi_i = h[i], i
    return P


def dip_arasi(h, l, c, wt):
    """9) dip arası takip bölgesi + 10) ekmek kırıntısı (eğitmenin 30.10.2026 kısa videoları). Döner {'da': ..., 'kr': ...} (boş olabilir)."""
    out = {}
    n = len(c)
    P = zigzag_hl(h, l, EG_ZZ)
    Ls = [p for p in P if p[0] == "L"]
    b = max(0, n - EG_DA_PENCERE)
    ia = b + int(np.argmin(l[b:]))
    sira = [s for s, p in enumerate(Ls) if p[1] == ia]
    if n >= 60:
        # ana dip kırılırsa yeni dip ana dip olur (yd = ana dibin yaşı, hafta); ana dipten %3'ten az yüksek dipler tabanın parçası (ikili dip)
        da = {"a": _r(l[ia]), "at": _g(wt[ia]), "y": 0, "yd": int(n - 1 - ia)}
        if sira:
            sonra = [p for p in Ls[sira[0] + 1:] if p[2] >= l[ia] * EG_DA_FARK]
            if sonra:
                _, i2, L2, c2 = sonra[0]
                da.update({"u": _r(L2), "ut": _g(wt[i2]), "y": 1})
                j = next((q for q in range(c2 + 1, n) if l[q] <= L2), None)
                if j is not None:
                    da["gt"] = _g(wt[j])
                    for q in range(j + 1, min(j + 1 + EG_DA_HAFTA, n)):
                        if c[q] >= L2 * EG_DA_TEYIT:
                            da["ty"] = _g(wt[q])
                            break
            elif sira[0] + 1 < len(Ls):
                da["ik"] = True
        out["da"] = da
    Hs = [i for i, p in enumerate(P) if p[0] == "H" and p[1] >= b]   # son 3 yılın en büyük onaylı tepesi (eğitmen: büyük ralli)
    if Hs:
        pi = max(Hs, key=lambda i: P[i][2])
        _, ih, Hp, ch = P[pi]
        zincir = []
        for x in reversed([p for p in P[:pi] if p[0] == "L"]):
            if zincir and x[2] >= zincir[-1][2]:
                break
            zincir.append(x)
            if len(zincir) == EG_KR_N:
                break
        if len(zincir) >= 2:
            out["kr"] = {"t": _r(Hp), "tt": _g(wt[ih]), "g": bool(np.max(h[ch:]) > Hp),
                         "s": [[_r(x[2]), _g(wt[x[1]])] for x in zincir]}
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
    # 9-10) dip arası takip bölgesi + ekmek kırıntısı
    eg.update(dip_arasi(h, l, c, wt))
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
    L = {"kelepir": [], "ucuz": [], "kutu": [], "dusus": [], "tdestek": [], "supurme": [], "dipara": []}
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
            da = eg.get("da")
            if da and da["y"] == 1 and k.get("f") and da["a"] <= k["f"] <= da["u"]:
                L["dipara"].append(kod)
    f = lambda kod: (H[kod].get("f") or 0) / (H[kod]["kel"]["T"] or 1)
    L["kelepir"].sort(key=f)
    L["ucuz"].sort(key=f)
    L["kutu"].sort()
    L["dusus"].sort(key=lambda kod: -H[kod]["yon"]["dusus"])
    L["tdestek"].sort(key=lambda kod: H[kod]["f"] / egitim_destek(H[kod]["eg"])[0])
    L["supurme"].sort(key=lambda kod: (H[kod]["eg"]["sp"]["h"], kod))
    L["dipara"].sort(key=lambda kod: (H[kod]["f"] - H[kod]["eg"]["da"]["a"]) / (H[kod]["eg"]["da"]["u"] - H[kod]["eg"]["da"]["a"]))
    return L


# ============================================================ 🥇 Altın, gümüş ve döviz (SADECE BİLGİ; 2026-11-28, dal `altin-harita`)
# Hisse kartlarının hesapları (kelepir, kutu, yön, seviyeler, 📚 eğitim katmanı) AYNEN; ek olarak 'taban bölgesi'. Veri her tarama içinde
# en çok EM_YENILE_DK dakikada bir ayrı bir yf.download ile iner (daemon iş parçacığı, EM_ZAMAN sn sınırı); hata → eski bölüm (taze False),
# o da yoksa bölüm yazılmaz ve sayfada görünmez. Bölünme düzeltmesi YAPILMAZ (gümüş 30.01.2026 −%31, BTC 12.03.2020 −%37 gerçek hareket).
EMTIA = (  # (kod, sayfadaki ad, Yahoo kodu | None = hesaplanır, birim)
    ("ALTIN", "Ons altın", "GC=F", "$"),
    ("GRAM", "Gram altın", None, "TL"),      # ons (GC=F) × USDTRY=X ÷ 31,1035 (yaklaşık; kuyumcu makası yok)
    ("GUMUS", "Ons gümüş", "SI=F", "$"),
    ("USDTRY", "Dolar/TL", "USDTRY=X", "TL"),
    ("EURTRY", "Euro/TL", "EURTRY=X", "TL"),
    ("BTC", "Bitcoin", "BTC-USD", "$"),
)
ONS_GRAM = 31.1035     # 1 troy ons = 31,1035 gram
EMTIA_ACIK = True
EM_ZAMAN = 20          # sn: indirme bundan uzun sürerse beklenmez (eski bölüm kalır)
EM_YENILE_DK = 30      # dk: bölüm en çok bu sıklıkla yeniden indirilir/hesaplanır (taramalar ~15 dk'da bir)
# 🧱 taban bölgesi: rallinin kalktığı son yatay konsolidasyon (haftalık, tamamlanmış haftalar). Kural metni sayfada (JS tbMetin) da var.
TB_MIN = 8             # en az 8 hafta
TB_GEN = 0.25          # pencerenin en yükseği / en düşüğü − 1 ≤ %25 (fitiller dahil)
TB_SAPMA = 0.08        # her haftalık kapanış pencerenin medyan kapanışının ±%8'i içinde (yatay)
TB_EGIM = 0.06         # kapanışlardan çekilen (log) doğrunun pencere boyunca toplam eğimi ≤ ±%6 (yükselen merdiven taban sayılmaz)
TB_ITKI = 0.40         # kırılımdan sonraki 52 haftada bölgenin üst kenarının ≥ %40 üstü görüldü; o zamana kadar bölge altında kapanış yok
TB_ITKI_HAFTA = 52
TB_ALT_Q, TB_UST_Q = 0.20, 0.80   # bölge = gövde bandının çekirdeği: gövde altlarının %20'lik, gövde üstlerinin %80'lik dilimi


def emtia_hazirla(df):
    """Emtia/döviz/kripto ön işleme: hisse `hazirla`'sının aynısı ama bölünme düzeltmesi YOK. H/L gövdeyi kapsayacak şekilde onarılır."""
    x = df[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"]).copy()
    x = x[x["Close"] > 0]
    if x.index.tz is not None:
        x = x.tz_localize(None)
    for c in ("Open", "High", "Low"):
        x[c] = x[c].where(x[c] > 0, x["Close"])
    x["High"] = x[["High", "Open", "Close"]].max(axis=1)
    x["Low"] = x[["Low", "Open", "Close"]].min(axis=1)
    x["Volume"] = x["Volume"].fillna(0)
    return x


def gram_altin(ons, usd):
    """Gram altın TL = ons $ × dolar/TL ÷ 31,1035 (O/H/L/C ayrı ayrı o günün dolar kapanışıyla; dolar en çok 5 gün ileri taşınır)."""
    if ons is None or usd is None or ons.empty or usd.empty:
        return None
    u = usd["Close"]
    u = u.reindex(ons.index.union(u.index)).ffill(limit=5).reindex(ons.index)
    x = ons.copy()
    for c in ("Open", "High", "Low", "Close"):
        x[c] = ons[c] * u / ONS_GRAM
    return x.dropna(subset=["Close"])


def taban_bolgesi(o, h, l, c, wt):
    """🧱 Son taban bölgesi (rally-base-rally'nin 'base'i). o/h/l/c: TAMAMLANMIŞ haftalık mumlar, wt: hafta tarihleri.
    En yeni haftadan geriye: kırılım haftası b için taban = b'den önce biten, geriye doğru büyütülen en uzun pencere [i, b−1] ki
    (1) en az TB_MIN hafta, (2) en yüksek/en düşük ≤ 1+TB_GEN, (3) her kapanış medyanın ±TB_SAPMA içinde, (4) log kapanış doğrusunun
    toplam eğimi ≤ ±TB_EGIM. Kırılım: b'nin kapanışı penceredeki en yüksek gövdenin üstünde. İtki: b'den sonraki TB_ITKI_HAFTA haftada
    bölge üstü × (1+TB_ITKI) görülmüş ve o haftaya kadar bölge altının altında kapanış yok. İlk (en yeni) uyan döner, yoksa None.
    Bölge = gövde bandının çekirdeği (TB_ALT_Q / TB_UST_Q), 'tüm' = en düşük/en yüksek gövde, tavan = penceredeki en yüksek fitil
    ('kırılan eski tepe'). Bakış-ileri: taban ancak itki görüldükten sonra bilinir (geçmişe dönük bölge, sinyal değil)."""
    n = len(c)
    if n < TB_MIN + 2:
        return None
    o, h, l, c = (np.asarray(v, float) for v in (o, h, l, c))
    bt, bb = np.maximum(o, c), np.minimum(o, c)
    lc = np.log(c)
    for b in range(n - 1, TB_MIN, -1):
        e = b - 1
        bas = None
        hh, ll = h[e], l[e]
        for i in range(e, -1, -1):
            hh, ll = max(hh, h[i]), min(ll, l[i])
            if hh / ll - 1 > TB_GEN:
                break
            cc = c[i:e + 1]
            if np.any(np.abs(cc / np.median(cc) - 1) > TB_SAPMA):
                break
            L = e - i + 1
            if L >= TB_MIN:
                eg = np.polyfit(np.arange(L), lc[i:e + 1], 1)[0] * (L - 1)
                if abs(np.expm1(eg)) <= TB_EGIM:
                    bas = i
        if bas is None or not c[b] > bt[bas:e + 1].max():
            continue
        i = bas
        a, u = float(np.quantile(bb[i:e + 1], TB_ALT_Q)), float(np.quantile(bt[i:e + 1], TB_UST_Q))
        z = min(n, b + TB_ITKI_HAFTA + 1)
        j = next((q for q in range(b, z) if h[q] >= u * (1 + TB_ITKI)), None)
        if j is None or c[b:j + 1].min() < a:
            continue
        sonra = h[b:]
        jt = b + int(np.argmax(sonra))
        geri = next((q for q in range(jt + 1, n) if l[q] <= u), None)
        return {"bt": _g(wt[i]), "bs": _g(wt[e]), "kt": _g(wt[b]), "n": int(e - i + 1), "a": _r(a), "u": _r(u),
                "a0": _r(bb[i:e + 1].min()), "u0": _r(bt[i:e + 1].max()), "tv": _r(h[i:e + 1].max()),
                "tp": _r(h[jt]), "tpt": _g(wt[jt]), "it": round(float(h[jt] / u - 1), 3), "gr": _g(wt[geri]) if geri is not None else None}
    return None


def _em_indir(sure=EM_ZAMAN):
    """Emtia/döviz 10 yıllık günlük veri, tek yf.download; daemon iş parçacığında, `sure` sn'de bitmezse (None, 'zaman aşımı')."""
    sonuc = {}
    kodlar = sorted({y for _, _, y, _ in EMTIA if y} | {"USDTRY=X"})

    def is_():
        try:
            import yfinance as yf
            sonuc["g"] = yf.download(kodlar, period=INDIRME_DONEM, interval="1d", group_by="ticker", auto_adjust=True,
                                     progress=False, threads=True)
        except Exception as e:
            sonuc["hata"] = type(e).__name__

    th = threading.Thread(target=is_, daemon=True)
    th.start()
    th.join(sure)
    if th.is_alive():
        return None, "zaman aşımı"
    g = sonuc.get("g")
    if g is None or getattr(g, "empty", True):
        return None, sonuc.get("hata") or "boş veri"
    return g, None


def _simdi_naif(simdi):
    t = pd.Timestamp(simdi)
    return t.tz_localize(None) if t.tzinfo is not None else t


def emtia_kaydi(d, simdi, ad, yf_kod, birim):
    """Tek varlık: hisse_kaydi (aynı hesaplar) + taban bölgesi + canlı durum. d = emtia_hazirla'dan geçmiş günlük df."""
    hafta_son, tamam = hafta_bilgisi(d.index[-1], simdi, False)
    d = d[d.index <= hafta_son + pd.Timedelta(days=1)]
    k = hisse_kaydi(d, hafta_son, tamam, "em")
    W = haftalik(d)
    t = int(np.asarray(W["hs"] < hafta_son).sum())
    m = t + 1 if tamam and len(W["c"]) > t else t
    try:
        tb = taban_bolgesi(W["o"][:m], W["h"][:m], W["l"][:m], W["c"][:m], list(W["t"][:m]))
        if tb:
            k["tb"] = tb
    except Exception as e:
        print(f"Harita: {ad} taban bölgesi hesaplanamadı ({type(e).__name__}).")
    bu = d[d.index > hafta_son - pd.Timedelta(days=7)]
    canli(k, float(d["Close"].iloc[-1]), float(bu["Low"].min()) if len(bu) else None)
    k.update({"ad": ad, "br": birim, "yf": yf_kod, "son": _g(d.index[-1]), "hafta": _g(hafta_son), "tamam": tamam,
              "g0": _g(pd.date_range(end=hafta_son, periods=GRAFIK_HAFTA + 1, freq="W-FRI")[0])})
    k.pop("g", None)
    return k


def emtia_hesapla(g, simdi):
    """g: _em_indir çıktısı (çoklu sütun). Döner {kod: kayıt} (hesaplanamayan varlık atlanır)."""
    def al(y):
        try:
            x = g[y]
        except (KeyError, TypeError):
            return None
        x = x.dropna(subset=["Close"]) if "Close" in x else None
        return emtia_hazirla(x) if x is not None and len(x) >= 300 else None
    ham = {y: al(y) for y in {yk for _, _, yk, _ in EMTIA if yk} | {"USDTRY=X"}}
    H = {}
    for kod, ad, yk, br in EMTIA:
        try:
            d = gram_altin(ham.get("GC=F"), ham.get("USDTRY=X")) if kod == "GRAM" else ham.get(yk)
            if d is None or len(d) < 300:
                continue
            H[kod] = emtia_kaydi(d, simdi, ad, yk or "GC=F × USDTRY=X ÷ 31,1035", br)
        except Exception as e:
            print(f"Harita: {kod} hesaplanamadı ({type(e).__name__}).")
    return H


def emtia_guncelle(eski, simdi, g=None):
    """harita.json 'em' bölümü. eski: önceki bölüm (yoksa None). EM_YENILE_DK dolmadıysa ve sürüm aynıysa eskisi aynen döner.
    g: önceden indirilmiş veri (test). İndirme/hesap başarısızsa eski bölüm taze=False ile, o da yoksa None (bölüm gizlenir)."""
    sn = _simdi_naif(simdi)
    son = max([v for v in ((eski or {}).get("t"), (eski or {}).get("d")) if v] or [None], key=lambda v: v or "")
    if eski and eski.get("v") == SURUM and son and g is None:
        try:   # son başarılı yenileme (t) ya da son başarısız deneme (d) EM_YENILE_DK'dan yeniyse tekrar indirme
            if pd.Timedelta(0) <= sn - pd.Timestamp(son) < pd.Timedelta(minutes=EM_YENILE_DK):
                return eski, "🥇 önceki veri"
        except Exception:
            pass
    neden = None
    if g is None:
        g, neden = _em_indir()
    H = emtia_hesapla(g, simdi) if g is not None else {}
    if H:
        return {"v": SURUM, "t": sn.strftime("%Y-%m-%d %H:%M"), "taze": True, "sira": [k for k, *_ in EMTIA if k in H], "h": H}, \
            f"🥇 {len(H)} varlık yenilendi"
    zaman = sn.strftime("%Y-%m-%d %H:%M")
    if eski and eski.get("h") and eski.get("v") == SURUM:
        e = dict(eski)
        e.update({"taze": False, "d": zaman})
        return e, f"🥇 alınamadı ({neden or 'veri yok'}), eski veri"
    return {"v": SURUM, "d": zaman, "taze": False, "h": {}}, f"🥇 alınamadı ({neden or 'veri yok'}), bölüm gizli"


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


def calistir(data, simdi, kapanis_zamani, ana, kucuk, manip=(), dikkat=(), yol=HARITA_JSON, html_yol=HARITA_HTML, uzun=None, em_veri=None):
    """tarama.py'den: data = taramanın günlük verisi (yf.download çoklu sütun, KOD.IS), ana/kucuk = kod kümeleri.
    dikkat = ⚠️/🎈 işaretli kodlar (kartta 'dikkat' notu). em_veri: önceden indirilmiş emtia verisi (test; yoksa gerekirse indirilir).
    Döner kısa log metni. İstisna fırlatabilir (tarama try/except'li)."""
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
    em_not = ""
    em = None
    if EMTIA_ACIK:   # 🥇 altın/gümüş/döviz: kendi hatası haritayı ve taramayı bozmaz
        try:
            em, em_not = emtia_guncelle((eski or {}).get("em"), simdi, g=em_veri)
        except Exception as e:
            em, em_not = None, f"🥇 hesaplanamadı ({type(e).__name__})"
    veri = {"v": SURUM, "anahtar": anahtar_yaz, "uretim": uretim, "guncel": simdi.strftime("%Y-%m-%d %H:%M"),
            "taze": taze or bool(eski and eski.get("anahtar") == anahtar),
            "hafta": hs_str, "tamam": tamam, "bayrak": {"yabanci": YABANCI_ACIK}, "egr": EGITIM_ROZET, "tbr": TABAN_EMTIA,
            "g0": _g(pd.date_range(end=hafta_son, periods=GRAFIK_HAFTA + 1, freq="W-FRI")[0]),
            "liste": listeler(H), "h": H}
    if em:
        veri["em"] = em
    yaz(veri, yol)
    html_yaz(html_yol)
    return f"Harita: {notu} ({len(H)} hisse)" + (f"; {em_not}" if em_not else "")


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
