# -*- coding: utf-8 -*-
"""🏢 İşlem Odası — TEKRAR OYNATMA dosyası üreticisi → oda_replay.json (oda.html '⟲ Tekrar oynat' bunu okur).

Elle çalıştırılır (ayda bir yeterli; Actions'ta her taramada ÇALIŞMAZ, ~5-10 dk sürer):  python oda_replay.py
Paralel araştırmanın (scratchpad oda_arastirma: hazirla.py + sim.py + replay.py) projeye taşınmış hali; robot motoru
oda.py'de (robot_karar / emir_uygula / gun_isle — canlıyla aynı kod yolu).
  1) Veri: tarama.KODLAR + BIST 100, Yahoo 5 yıl günlük (canlı taramayla aynı kaynak), bolunme_duzelt.
  2) Her hisse-gün için robotların gördüğü alanlar, canlı fonksiyonların gün gün karşılığı (araştırmada dogrula_canli.py ile
     analiz_et → ozet_hazirla yolu ile karşılaştırıldı): v3 kırılımı, trend şablonu/20g zirveye uzaklık, destekten tepki,
     🌱 uzun vade, RSI, momentum, taban serisi/🔒/🎈, kilitli taban/tavan, sıkı çizgi (kijun, aşırı uzama).
  3) Son ~1 yıl (250 işlem günü) gün gün: oda.gun_isle (dünkü emirler bugünün açılışıyla, bugünün kapanışıyla karar).
  4) Dürüstlük ölçüleri: 🎲 şans bandı (Rastgele robot SANS_N farklı zarla, %5/%50/%95), her robot için 'ikiz' testi
     (her alımı aynı gün rastgele hisseyle değiştir, SANS_N deneme → şans yüzdeliği), aynı kural 4 yılda (2022-10 →).
Bilinen sınırlar: evren bugünkü liste (hayatta kalan yanlılığı); fiyatlar bölünme/temettü düzeltmeli; 5 yıllık veriyle
v3'ün 'pozisyon açık mı' durumu canlı taramanın 2 yıllık verisinden eski işlemlerde birkaç hissede farklı olabilir."""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import yfinance as yf

import oda
import sinyal as S
import tarama

CIKTI = "oda_replay.json"
PENCERE = 250                 # tekrar oynatılan işlem günü (~1 yıl)
UZUN_BAS = "2022-10-10"       # 'aynı kural 4 yılda' başlangıcı (araştırmayla aynı)
NEDEN = {"iz": "iz stop (tepeden %20 düşüş)", "sk": "sıkı çizgi altında kapanış", "dk": "destek kırıldı",
         "dr": "dirence ulaştı", "sr": "süre doldu", "uv": "🌱 SAT: 2 gün 200 günlük ortalama altı",
         "ls": "ayın güçlüleri listesinden düştü", "pz": "piyasa zayıf: nakite geçti", "sb": "trend şablonu bozuldu",
         "bk": "🛡️ Bekçi: toplam düşüş limiti", "kr": "🛡️ Bekçi: tek hisse sınırı aşıldı (fazlası satıldı)"}


def neden_kod(t):
    t = t or ""
    for a, k in (("iz stop", "iz"), ("sıkı", "sk"), ("destek", "dk"), ("dirence", "dr"), ("gün doldu", "sr"), ("🌱", "uv"),
                 ("listeden", "ls"), ("piyasa", "pz"), ("şablon", "sb"), ("düşüş limiti", "bk"), ("aştı", "kr")):
        if a in t:
            return k
    return "?"


# ================== 1-2) veri ve gün gün özellikler (araştırma hazirla.py) ==================
def indir(kodlar):
    tickers = [k + ".IS" for k in kodlar] + [tarama.ENDEKS + ".IS"]
    print(f"{len(tickers)} sembol indiriliyor (5 yıl günlük)...", flush=True)
    return yf.download(tickers, period="5y", interval="1d", group_by="ticker", auto_adjust=True, progress=False, threads=True)


def sd_seri(d):
    """sinyal.destek_direnc'in her gün için karşılığı: tepki, destek fiyatı, tol, direnç fiyatı (yoksa nan)."""
    n = len(d)
    hl = S._hl_var(d)
    c = d["Close"].values.astype(float)
    lo = d["Low"].values.astype(float) if hl else c
    hi = d["High"].values.astype(float) if hl else c
    atr = (S._atr(d, 14) if hl else d["Close"].diff().abs().rolling(14).mean()).values
    K = S.PIVOT_K
    dip_p, tep_p = [], []
    for p in range(K, n - K):
        w = lo[p - K:p + K + 1]
        if not np.isnan(w).any() and lo[p] == w.min():
            dip_p.append(p)
        w = hi[p - K:p + K + 1]
        if not np.isnan(w).any() and hi[p] == w.max():
            tep_p.append(p)
    dip_p, tep_p = np.array(dip_p, int), np.array(tep_p, int)
    tepki = np.zeros(n, bool); dS = np.full(n, np.nan); tolA = np.full(n, np.nan); dR = np.full(n, np.nan)
    for t in range(S.SD_GUN, n):
        f = c[t]
        if not f == f:
            continue
        a = atr[t]
        atr_pct = a / f if a == a else 0.0
        tol = min(max(0.5 * atr_pct, S.SD_TOL_MIN), S.SD_TOL_MAX)
        tolA[t] = tol
        bas = t - S.SD_GUN + 1
        lo_b, hi_b = bas + K, t - S.SD_YENI
        dm = dip_p[(dip_p >= lo_b) & (dip_p <= hi_b)]
        tm = tep_p[(tep_p >= lo_b) & (tep_p <= hi_b)]
        dun = c[t - 1]
        dfy = lo[dm]; tfy = hi[tm]
        ok = (dfy <= f) | ((dfy * (1 - tol) <= f) & (dun >= dfy))
        destek = None
        if ok.any():
            cand = np.flatnonzero(ok)
            best = max(cand, key=lambda q: (dfy[q], dm[q]))
            destek = (dm[best], dfy[best])
        ust = tfy > f
        direnc = None
        if ust.any():
            cand = np.flatnonzero(ust)
            best = min(cand, key=lambda q: (tfy[q], -tm[q]))
            direnc = (tm[best], tfy[best])
        tp = yk = False
        if destek is not None:
            Sx = destek[1]
            dS[t] = Sx
            test = int((np.abs(dfy - Sx) <= Sx * tol).sum())
            if test >= S.SD_MIN_TEST:
                dok = np.nanmin(lo[t - 4:t + 1]) <= Sx * (1 + tol)
                tp = bool(dok and f > dun and f <= Sx * (1 + tol))
        if direnc is not None:
            R = direnc[1]
            dR[t] = R
            test = int((np.abs(tfy - R) <= R * tol).sum())
            if test >= S.SD_MIN_TEST:
                yk = (R - f) / f <= tol
        if tp and yk:
            if direnc[1] - f < f - destek[1]:
                tp = False
        tepki[t] = tp
    return tepki, dS, tolA, dR


def uv_seri(d):
    c, s50, s200 = d["Close"], d["SMA50"], d["SMA200"]
    yukselen = (s200 > s200.shift(20)) & (c > s200)
    al_gun = (yukselen & (d["Low"] <= s50 * 1.02) & (c > s50) & (c > c.shift(1))).values
    cik_gun = ((c < s200) & (c.shift(1) < s200.shift(1))).values
    n = len(d)
    durum = np.zeros(n, np.int8)
    yeni = np.zeros(n, bool)
    dr = None
    for i in range(n):
        if dr != "AL" and al_gun[i]:
            dr = "AL"; yeni[i] = True
        elif dr == "AL" and cik_gun[i]:
            dr = "SAT"
        durum[i] = 1 if dr == "AL" else (-1 if dr == "SAT" else 0)
    return durum, yeni


def ozellik(d, xu_ust, xu):
    n = len(d)
    c = d["Close"]; cv = c.values.astype(float)
    hh = d["High"]; ll = d["Low"]; v = d["Volume"].replace(0, np.nan)
    r = c.pct_change()
    F = {}
    tum = S.trend_kirilimi(d, xu_ust, ham=True)
    bugun = np.zeros(n, bool); acik = np.zeros(n, bool)
    for x in tum:
        bugun[x["i"]] = True
        acik[x["i"]:(x["cik"] if x["cik"] is not None else n)] = True
    sab = S.trend_sablonu(d).fillna(False).values.astype(bool)
    hh20 = c.rolling(S.KIRILIM_GUN).max().shift(1).values
    uzak = np.round((hh20 / cv - 1) * 100, 1)
    uzak[~sab | acik] = np.nan
    F["tk_bugun"], F["tk_acik"], F["sablon"], F["kir_uzak"] = bugun, acik, sab, uzak
    F["oynak"] = (r.rolling(60).std() > S.OYNAK_ESIK).values
    F["mom20"] = (c / c.shift(20) - 1).values
    F["mom6"] = (c.shift(21) / c.shift(126) - 1).values
    F["s200_ust"] = ((c > d["SMA200"]) & (np.arange(n) > 200)).values
    F["uv_durum"], F["uv_yeni"] = uv_seri(d)
    F["sd_tepki"], F["sd_destek"], F["sd_tol"], F["sd_direnc"] = sd_seri(d)
    R = S.rsi(c)
    F["rsi"] = R.values; F["drsi"] = R.diff().values
    tav10 = (r >= 0.095).rolling(10).sum()
    yuk20 = c / c.shift(20) - 1
    sis50 = c / c.rolling(50).mean() - 1
    vol20 = r.rolling(20).std()
    hk = (v.rolling(5).mean() / v.rolling(60).mean()).fillna(0)
    sisme = (tav10 >= 5) | (yuk20 >= 1.0) | ((sis50 >= 0.7) & (vol20 >= 0.06)) | ((tav10 >= 3) & (hk >= 3))
    sisme &= pd.Series(np.arange(n) >= 60, index=d.index)
    F["sisme"] = sisme.values
    tab = (r <= S.TABAN_GETIRI)
    F["patlak"] = (tab.astype(int).rolling(S.TABAN_GUN, min_periods=1).sum() >= S.PATLAK_TABAN).values
    ev = S.kilitli_taban_seri(d, xu).values
    tb = tab.values
    kt = np.zeros(n, bool)
    for t in range(1, n):
        if (ev[t] and tb[t]) or (ev[t - 1] and tb[t - 1] and tb[t]):
            kt[t] = True
    kt &= ~F["patlak"]
    F["kt"] = kt
    rng = (hh - ll) <= S.KILIT_ARALIK * c
    F["kil_taban"] = (tab & rng).values
    F["kil_tavan"] = ((r >= 0.09) & rng).values
    mn250 = c.rolling(250).min()
    F["uzama"] = (((c / mn250) >= S.UZAMA_DIPKAT) | ((c / c.shift(126) - 1) >= S.UZAMA_R6)).values & (np.arange(n) >= 249)
    F["kijun"] = S.kijun(d).values
    F["gecmis"] = np.arange(1, n + 1)
    return F


def hazirla(g):
    """İndirilen veriden K×T özellik dizileri (araştırmanın hazir.pkl yapısı)."""
    xd = g[tarama.ENDEKS + ".IS"].dropna(subset=["Close"])
    xu = xd["Close"].astype(float); xu.index = pd.DatetimeIndex(xu.index)
    xu_ust = S.sma(xu, 50).lt(xu)
    gun = xu.index
    kodlar = sorted({t[:-3] for t in g.columns.get_level_values(0) if t != tarama.ENDEKS + ".IS"})
    A = {}
    tamam = []
    for kn, kod in enumerate(kodlar):
        try:
            d = g[kod + ".IS"][["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
        except KeyError:
            continue
        d = d[d.index.isin(gun)]
        if len(d) < 60:
            continue
        d = S.bolunme_duzelt(d)
        d = d.copy(); d["SMA50"] = S.sma(d["Close"], 50); d["SMA200"] = S.sma(d["Close"], 200)
        F = ozellik(d, xu_ust, xu)
        F["O"], F["H"], F["L"], F["C"] = (d[k].values.astype(float) for k in ("Open", "High", "Low", "Close"))
        pos = gun.get_indexer(d.index)
        for k, arr in F.items():
            A.setdefault(k, {"dt": arr.dtype, "rows": {}})["rows"][kod] = (pos, arr)
        tamam.append(kod)
        if kn % 50 == 0:
            print(f"  özellikler {kn}/{len(kodlar)}", flush=True)
    K, T = len(tamam), len(gun)
    M = {}
    for k, v in A.items():
        dt = v["dt"]
        X = (np.full((K, T), np.nan) if np.issubdtype(dt, np.floating) else np.zeros((K, T), bool if dt == np.bool_ else dt))
        for ki, kod in enumerate(tamam):
            pos, arr = v["rows"][kod]
            X[ki, pos] = arr
        M[k] = X
    M["riskli"] = M["patlak"] | M["kt"] | M["sisme"]
    u = M["kir_uzak"]
    with np.errstate(invalid="ignore"):
        erken = (u > 0) & (u <= 3.0)
        M["rsi_al"] = (M["rsi"] >= 25) & (M["rsi"] <= 33) & (M["drsi"] >= 2.4)
    M["aday"] = M["tk_bugun"] | erken | M["sd_tepki"] | M["uv_yeni"] | M["rsi_al"]
    M["Cf"] = pd.DataFrame(M["C"].T).ffill().values.T
    buyuk = set(tarama.BIST100) | set(tarama.EK_HISSELER)
    return {"kod": tamam, "gun": gun, "A": M, "xu": xu, "xu_open": xd["Open"].astype(float).reindex(gun), "xu_ust": xu_ust,
            "buyuk": buyuk, "buyuk_m": np.array([k in buyuk for k in tamam]), "ki": {k: i for i, k in enumerate(tamam)},
            "ay": np.array([t.month for t in gun]), "tarih": [str(t.date()) for t in gun]}


# ================== 3) simülasyon (araştırma sim.py; motor oda.py) ==================
def ozet(D, k, t):
    A = D["A"]
    f = A["C"][k, t]
    uz = A["kir_uzak"][k, t]
    sdd, sdr = A["sd_destek"][k, t], A["sd_direnc"][k, t]
    uvd = A["uv_durum"][k, t]
    m6 = A["mom6"][k, t]
    r, dr = A["rsi"][k, t], A["drsi"][k, t]
    kj = A["kijun"][k, t]
    return {"fiyat": float(f),
            "tk": {"bugun": bool(A["tk_bugun"][k, t]), "sablon": bool(A["sablon"][k, t]),
                   "kirilima_uzak": None if uz != uz else float(uz), "durum": "AL" if A["tk_acik"][k, t] else None},
            "oynak": bool(A["oynak"][k, t]),
            "sd": {"tepki": bool(A["sd_tepki"][k, t]), "destek": None if sdd != sdd else float(sdd),
                   "direnc": None if sdr != sdr else float(sdr),
                   "tol": float(A["sd_tol"][k, t]) if A["sd_tol"][k, t] == A["sd_tol"][k, t] else 0.0},
            "uv": {"durum": "AL" if uvd == 1 else ("SAT" if uvd == -1 else None), "yeni": bool(A["uv_yeni"][k, t])},
            "rsi": None if r != r else float(r), "rsi_degisim": None if dr != dr else float(dr),
            "mom20": float(A["mom20"][k, t]) if A["mom20"][k, t] == A["mom20"][k, t] else 0.0,
            "mom6": None if m6 != m6 else float(m6), "s200_ust": bool(A["s200_ust"][k, t]),
            "buyuk": bool(D["buyuk_m"][k]), "riskli": bool(A["riskli"][k, t]),
            "uzama": bool(A["uzama"][k, t]), "kijun": None if kj != kj else float(kj)}


def gun_verisi(D, t, tut, ay_ilk, momentum=True, rastgele=True, filtre=True):
    """Robotların gördüğü gün verisi: o gün aday olanlar + elde tutulanlar (+ ay başında büyük liste, + 🎲 evreni)."""
    A = D["A"]
    var = ~np.isnan(A["C"][:, t])
    m = A["aday"][:, t] & var
    if momentum and ay_ilk:
        m |= D["buyuk_m"] & ~np.isnan(A["mom6"][:, t]) & var
    idx = set(np.flatnonzero(m).tolist()) | {D["ki"][k] for k in tut if k in D["ki"] and var[D["ki"][k]]}
    kod = D["kod"]
    gv = {"tarih": D["tarih"][t], "ay_ilk": ay_ilk, "xu": {"fiyat": float(D["xu"].iloc[t]), "ust": bool(D["xu_ust"].iloc[t])},
          "hisseler": {kod[k]: ozet(D, k, t) for k in idx}, "evren": []}
    if rastgele:
        e = var & (A["gecmis"][:, t] >= 250)
        if filtre:
            e &= ~A["riskli"][:, t]
        gv["evren"] = [kod[k] for k in np.flatnonzero(e)]
    return gv


def acilis(D, t, kodlar):
    A = D["A"]
    out = {}
    for kod in kodlar:
        if kod == oda.XU:
            o = D["xu_open"].iloc[t]
            out[kod] = {"fiyat": float(o) if o == o and o > 0 else float(D["xu"].iloc[t])}
            continue
        k = D["ki"].get(kod)
        if k is None:
            continue
        o = A["O"][k, t]
        if not (o == o and o > 0):
            continue
        out[kod] = {"fiyat": float(o), "kilit_taban": bool(A["kil_taban"][k, t]), "kilit_tavan": bool(A["kil_tavan"][k, t])}
    return out


def oda_oynat(D, i0, i1):
    """Bütün robotlar birlikte, canlıyla aynı yol (oda.gun_isle). Döner: durum, olaylar [[gün sırası, kim, metin]], dur."""
    dz = oda.yeni_durum(D["tarih"][i0])
    olay, dur = [], {rid: [] for rid in oda.ROBOTLAR}
    for t in range(i0, i1):
        tut = {k for kasa in dz["robot"].values() for k in kasa["poz"]}
        bek = {e["kod"] for kasa in dz["robot"].values() for e in kasa["bekleyen"]}
        gv = gun_verisi(D, t, tut | bek, (t == i0) or D["ay"][t] != D["ay"][t - 1])   # bugün alınacaklar da (kapanışla değerlenir)
        for o in oda.gun_isle(dz, D["tarih"][t], gv, acilis(D, t, bek)):
            if o[1] == "bekci" or "lamadı" in o[2]:   # alım-satım olayları sayfada işlem listesinden üretilir
                olay.append([t - i0, o[1], o[2]])
        dz["xu"].append([D["tarih"][t], round(float(D["xu"].iloc[t]), 2)])
        for rid, kasa in dz["robot"].items():
            dur[rid].append({"durdu": "d", "mola": "m"}.get(oda.bekci_hal(kasa), "a"))
    for kasa in dz["robot"].values():
        kasa["_i0"], kasa["_i1"] = i0, i1
    return dz, olay, {r: "".join(v) for r, v in dur.items()}


def calistir(D, rid, i0, i1, robot=None):
    """Tek robot (araştırma sim.calistir) — 🎲 şans bandı için (tohum değişir) ve oda_oynat ile eşitlik kontrolü."""
    robot = robot or oda.ROBOTLAR[rid]
    kasa = oda.yeni_kasa(rid, D["tarih"][i0])
    mom, rnd = robot["tur"] == "momentum", robot["tur"] == "rastgele"
    for t in range(i0, i1):
        if kasa["bekleyen"]:
            oda.emir_uygula(kasa, acilis(D, t, {e["kod"] for e in kasa["bekleyen"]}), D["tarih"][t])
        ay_ilk = (t == i0) or D["ay"][t] != D["ay"][t - 1]
        gv = gun_verisi(D, t, kasa["poz"].keys(), ay_ilk, momentum=mom, rastgele=rnd, filtre=robot.get("filtre", True))
        oda.robot_karar(rid, gv, kasa, robot=robot)
    kasa["_i0"], kasa["_i1"] = i0, i1
    return kasa


def islemler(kasa):
    acik, out = {}, []
    for e in kasa["defter"]:
        if e["yon"] == "AL":
            acik[e["kod"]] = {"t": e["t"], "baz": e["adet"] * e["fiyat"] * (1 + oda.KOMISYON), "kz": 0.0}
        else:
            a = acik.get(e["kod"])
            if a is None:
                continue
            a["kz"] += e["kz"]
            if e.get("kismi"):
                continue
            acik.pop(e["kod"])
            out.append({"kod": e["kod"], "getiri": round(a["kz"] / a["baz"] * 100, 2), "kz": round(a["kz"], 2)})
    for kod, a in acik.items():
        p = kasa["poz"].get(kod)
        if p:
            kz = a["kz"] + p["adet"] * (p["fiyat"] * (1 - oda.KOMISYON) - p["maliyet"])
            out.append({"kod": kod, "getiri": round(kz / a["baz"] * 100, 2), "kz": round(kz, 2)})
    return out


def olc(D, kasa):
    sr = pd.Series([v for _, v in kasa["seri"]], index=pd.DatetimeIndex([t for t, _ in kasa["seri"]]))
    T = islemler(kasa)
    g = np.array([x["getiri"] for x in T]) if T else np.array([0.0])
    ay = sr.resample("ME").last()
    ay_r = ay.pct_change(); ay_r.iloc[0] = ay.iloc[0] / oda.BASLANGIC - 1
    iyi = max(T, key=lambda x: x["getiri"]) if T else None
    kotu = min(T, key=lambda x: x["getiri"]) if T else None
    return {"getiri": (sr.iloc[-1] / oda.BASLANGIC - 1) * 100, "dd": (sr / sr.cummax() - 1).min() * 100,
            "islem": sum(1 for e in kasa["defter"] if e["yon"] == "AL"), "isabet": float((g > 0).mean() * 100) if T else 0.0,
            "en_iyi": (iyi["kod"], iyi["getiri"]) if iyi else None, "en_kotu": (kotu["kod"], kotu["getiri"]) if kotu else None,
            "ay": ay_r}


def ikiz(D, kasa, robot, n=200, tohum=0):
    """Robotun HER alımını aynı gün, aynı kasa payıyla RASTGELE bir hisseyle değiştirir ve robotun çıkış gününde satar
    (aynı zamanlama, aynı tutuş süresi). Döner: n tohumun toplam getirileri (%)."""
    A = D["A"]
    tix = {t: i for i, t in enumerate(D["tarih"])}
    i0, i1 = kasa["_i0"], kasa["_i1"]
    acik, trades = {}, []
    for e in kasa["defter"]:
        if e["yon"] == "AL":
            acik[e["kod"]] = len(trades); trades.append([tix[e["t"]], None])
        elif not e.get("kismi"):
            j = acik.pop(e["kod"], None)
            if j is not None:
                trades[j][1] = tix[e["t"]]
    pay = min(1.0 / robot.get("yuva", 10), oda.BEKCI["tek_hisse"]) if robot["tur"] != "endeks" else 1.0
    rng = np.random.default_rng(tohum)
    O, Cf = A["O"], A["Cf"]
    mom = robot["tur"] == "momentum"
    by_a = {}
    for j, (a, b) in enumerate(trades):
        by_a.setdefault(a, []).append(j)
    secim = {}
    for a, js in by_a.items():
        ok = (O[:, a] > 0) & ~np.isnan(A["C"][:, a]) & (A["gecmis"][:, a] >= 250) & ~A["riskli"][:, a - 1] & ~A["kil_tavan"][:, a]
        if mom:
            ok &= D["buyuk_m"] & ~np.isnan(A["mom6"][:, a - 1])
        havuz = np.flatnonzero(ok)
        secim[a] = np.array([rng.choice(havuz, size=len(js), replace=False) for _ in range(n)])
    nakit = np.full(n, oda.BASLANGIC)
    adet, cik_gun = {}, {}
    deger = np.full(n, oda.BASLANGIC)
    for j, (a, b) in enumerate(trades):
        if b is not None:
            cik_gun.setdefault(b, []).append(j)
    son = None
    for t in range(i0, i1):
        for j in cik_gun.get(t, []):
            if j in adet:
                k, u = adet.pop(j)
                px = np.where(O[k, t] > 0, O[k, t], Cf[k, t - 1])
                nakit += u * px * (1 - oda.KOMISYON) * 0.999
        if t in by_a:
            for c, j in enumerate(by_a[t]):
                k = secim[t][:, c]
                px = O[k, t] * 1.001
                hedef = np.minimum(pay * deger, nakit)
                u = np.floor(hedef / (px * (1 + oda.KOMISYON)))
                nakit -= u * px * (1 + oda.KOMISYON)
                adet[j] = (k, u)
        deger = nakit + sum(u * Cf[k, t] for k, u in adet.values())
        son = deger.copy()
    return (son / oda.BASLANGIC - 1) * 100


def robot_cikti(D, rid, kasa, ix, n_sans, uzun_kasa=None):
    rb = oda.ROBOTLAR[rid]
    m = olc(D, kasa)
    il = []
    for e in kasa["defter"]:
        g = ix.get(e["t"])
        if g is None:
            continue
        a = round(e["adet"], 4) if e["kod"] == oda.XU else int(e["adet"])
        if e["yon"] == "AL":
            il.append([g, "A", e["kod"], a, round(e["fiyat"], 2)])
        else:
            il.append([g, "S", e["kod"], a, round(e["fiyat"], 2), round(e["kz_yuzde"], 1), neden_kod(e.get("neden"))])
    r = {"id": rid, "ad": rb["ad"], "aciklama": rb["aciklama"], "d": [int(round(v)) for _, v in kasa["seri"]], "i": il,
         "oz": {"get": round(m["getiri"], 1), "dd": round(m["dd"], 1), "n": m["islem"], "isabet": round(m["isabet"]),
                "iyi": [m["en_iyi"][0], round(m["en_iyi"][1], 1)] if m["en_iyi"] else None,
                "kotu": [m["en_kotu"][0], round(m["en_kotu"][1], 1)] if m["en_kotu"] else None,
                "ay": [round(x * 100, 1) for x in m["ay"].values], "ay_t": [str(t.date())[:7] for t in m["ay"].index]}}
    if rid == "rsi":
        r["tahmini"] = True
    if rb["tur"] not in ("endeks", "rastgele") and n_sans:
        g_ = ikiz(D, kasa, rb, n=n_sans, tohum=1)
        r["sans"] = {"p5": round(float(np.percentile(g_, 5)), 1), "med": round(float(np.median(g_)), 1),
                     "p95": round(float(np.percentile(g_, 95)), 1), "yuzde": int(round((g_ < m["getiri"]).mean() * 100))}
    if uzun_kasa is not None:
        m4 = olc(D, uzun_kasa)
        u = {"get": round(m4["getiri"]), "dd": round(m4["dd"], 1), "bas": uzun_kasa["seri"][0][0]}
        if rb["tur"] not in ("endeks", "rastgele") and n_sans:
            g4 = ikiz(D, uzun_kasa, rb, n=n_sans, tohum=1)
            u["yuzde"] = int(round((g4 < m4["getiri"]).mean() * 100))
        r["uzun"] = u
    return r


def uret(D, i0, i1, cikti=CIKTI, n_sans=oda.SANS_N, uzun=True):
    t0 = time.time()
    dz, olay, dur = oda_oynat(D, i0, i1)
    tarih = D["tarih"][i0:i1]
    ix = {t: i for i, t in enumerate(tarih)}
    print(f"Ana oynatma ({tarih[0]} → {tarih[-1]}, {len(tarih)} gün): {time.time() - t0:.0f} sn", flush=True)
    u0 = int(D["gun"].searchsorted(pd.Timestamp(UZUN_BAS)))
    dz4 = oda_oynat(D, u0, i1)[0] if uzun and u0 < i0 else None
    if dz4:
        print(f"4 yıl oynatma ({D['tarih'][u0]} →): {time.time() - t0:.0f} sn", flush=True)
    robots = []
    for rid in oda.ROBOTLAR:
        robots.append(dict(robot_cikti(D, rid, dz["robot"][rid], ix, n_sans, dz4["robot"][rid] if dz4 else None), dur=dur[rid]))
        print(f"  {rid:<11} {robots[-1]['oz']['get']:+7.1f}%  alım {robots[-1]['oz']['n']:>4}  "
              f"şans yüzdeliği {robots[-1].get('sans', {}).get('yuzde', '—')}  4y {robots[-1].get('uzun', {}).get('get', '—')}", flush=True)
    bant = []
    for s in range(n_sans):
        rb = dict(oda.ROBOTLAR["rastgele"]); rb["tohum"] = s
        bant.append([v for _, v in calistir(D, "rastgele", i0, i1, robot=rb)["seri"]])
    B = np.array(bant)
    out = {"v": 1, "uretim": str(pd.Timestamp.now(tz="Europe/Istanbul").strftime("%Y-%m-%d %H:%M")), "bas_tl": int(oda.BASLANGIC),
           "not": "Sanal para ile kural robotları; geçmiş veriyle tekrar oynatma. Alım ertesi gün açılış fiyatından, "
                  "%0,2 komisyon + 1 fiyat adımı kayma. Yatırım tavsiyesi değildir.",
           "gun": tarih, "xu": [round(float(D["xu"].iloc[t]), 1) for t in range(i0, i1)], "neden": NEDEN, "robot": robots,
           "bant": {"p5": [int(x) for x in np.percentile(B, 5, axis=0)], "p50": [int(x) for x in np.percentile(B, 50, axis=0)],
                    "p95": [int(x) for x in np.percentile(B, 95, axis=0)]},
           "olay": olay}
    s = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    with open(cikti, "w", encoding="utf-8") as f:
        f.write(s)
    print(f"{cikti}: {len(s.encode('utf-8')) / 1024:.0f} KB, {len(tarih)} gün, {time.time() - t0:.0f} sn", flush=True)
    return out


def main():
    t0 = time.time()
    D = hazirla(indir(tarama.KODLAR))
    print(f"Özellikler hazır: {len(D['kod'])} hisse ({time.time() - t0:.0f} sn)", flush=True)
    simdi = pd.Timestamp.now(tz="Europe/Istanbul")
    i1 = len(D["gun"])
    if D["tarih"][-1] == simdi.strftime("%Y-%m-%d") and simdi.hour * 60 + simdi.minute < tarama.KAPANIS_DAKIKA:
        i1 -= 1   # bugünün mumu henüz kesin değil
    uret(D, max(0, i1 - PENCERE), i1)


if __name__ == "__main__":
    sys.exit(0 if main() is None else 1)
