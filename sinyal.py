# -*- coding: utf-8 -*-
"""
Çoklu gösterge motoru. Her gösterge KENDİ sinyalini üretir (AL/SAT/NÖTR);
genel sinyal bunların uyumundan (kaç gösterge AL diyor) çıkar. Şeffaf.
Canlı tarama + backtest aynı fonksiyonları kullanır.
"""
import numpy as np
import pandas as pd

# oy veren yönlü göstergeler ve eşikler
AL_ESIK = 4   # 5 göstergeden >=4 AL -> genel AL
SAT_ESIK = 1  # <=1 AL -> genel SAT

# destek/direnç: son SD_GUN günün lokal dip/tepeleri
SD_GUN = 120   # kaç günlük geçmişe bakılır
PIVOT_K = 5    # dip/tepe, iki yanındaki 5 günün en düşüğü/en yükseği olmalı
SD_YENI = 10   # son 10 günde oluşan dip/tepeler seviye sayılmaz (henüz test edilmedi)
SD_MIN_TEST = 2                        # etiket için seviye en az 2 kez test edilmiş olmalı
SD_TOL_MIN, SD_TOL_MAX = 0.01, 0.025   # "yakın" eşiğinin alt/üst sınırı

# hacim teyidi (5 yıllık backtest: AL günü hacmi yüksekse sinyal daha güçlü, özellikle düşük faizde)
HACIM_ESIK = 1.5       # AL'e dönüş günü hacmi / önceki 20 günün ortalaması
# taban serisi (fon krizinde çöken şişirilmiş hisseler): son 15 günde en az 4 kez ~%10 düşüş
TABAN_GETIRI, TABAN_GUN, PATLAK_TABAN = -0.09, 15, 4


def sma(s, n): return s.rolling(n).mean()
def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def rsi(s, n=14):
    d = s.diff()
    ag = d.clip(lower=0).ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    al = (-d.clip(upper=0)).ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    rs = ag / al.replace(0, np.nan)
    return 100 - 100/(1+rs)


def macd(s, f=12, sl=26, sg=9):
    m = ema(s, f) - ema(s, sl)
    sig = ema(m, sg)
    return m, sig


def _atr(df, n=10):
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, min_periods=n, adjust=False).mean()


def supertrend(df, n=10, mult=3.0):
    """Döndürür: yön Serisi (1=AL/yeşil, -1=SAT/kırmızı) ve çizgi."""
    c = df["Close"].to_numpy(dtype=float)
    atr = _atr(df, n).to_numpy(dtype=float)
    hl2 = ((df["High"] + df["Low"]) / 2).to_numpy(dtype=float)
    ub = hl2 + mult * atr
    lb = hl2 - mult * atr
    N = len(c)
    ubf = np.full(N, np.nan); lbf = np.full(N, np.nan)
    dirn = np.ones(N, dtype=int); line = np.full(N, np.nan)
    for i in range(N):
        if np.isnan(ub[i]):                      # ATR henüz oluşmadı
            continue
        if i == 0 or np.isnan(ubf[i-1]):         # ilk geçerli bar: tohumla
            ubf[i], lbf[i], dirn[i] = ub[i], lb[i], 1
            line[i] = lbf[i]
            continue
        ubf[i] = ub[i] if (ub[i] < ubf[i-1] or c[i-1] > ubf[i-1]) else ubf[i-1]
        lbf[i] = lb[i] if (lb[i] > lbf[i-1] or c[i-1] < lbf[i-1]) else lbf[i-1]
        if c[i] > ubf[i-1]:
            dirn[i] = 1
        elif c[i] < lbf[i-1]:
            dirn[i] = -1
        else:
            dirn[i] = dirn[i-1]
        line[i] = lbf[i] if dirn[i] == 1 else ubf[i]
    idx = df.index
    return pd.Series(dirn, index=idx), pd.Series(line, index=idx)


def stochastic(df, k=14, d=3):
    ll = df["Low"].rolling(k).min()
    hh = df["High"].rolling(k).max()
    pk = 100*(df["Close"] - ll)/(hh - ll).replace(0, np.nan)
    return pk, pk.rolling(d).mean()


def adx(df, n=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    up = h.diff(); dn = -l.diff()
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = c.shift(1)
    tr = pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    pdi = 100*pd.Series(plus, index=c.index).ewm(alpha=1/n, min_periods=n, adjust=False).mean()/atr
    mdi = 100*pd.Series(minus, index=c.index).ewm(alpha=1/n, min_periods=n, adjust=False).mean()/atr
    dx = 100*(pdi-mdi).abs()/(pdi+mdi).replace(0, np.nan)
    return dx.ewm(alpha=1/n, min_periods=n, adjust=False).mean()


def bollinger(s, n=20, mult=2):
    mid = s.rolling(n).mean()
    sd = s.rolling(n).std()
    up = mid + mult*sd; lo = mid - mult*sd
    pctb = (s - lo)/(up - lo).replace(0, np.nan)
    return up, mid, lo, pctb


def _hl_var(df):
    return "High" in df.columns and "Low" in df.columns


def gostergeler(df):
    d = df.copy()
    c = d["Close"]
    d["SMA20"], d["SMA50"], d["SMA200"] = sma(c, 20), sma(c, 50), sma(c, 200)
    d["EMA20"], d["EMA50"] = ema(c, 20), ema(c, 50)
    d["RSI"] = rsi(c, 14)
    m, sig = macd(c)
    d["MACD"], d["MACD_SIGNAL"] = m, sig
    d["STOP"] = np.maximum(c.rolling(20).min(), c*0.92)

    hl = _hl_var(df)
    if hl:
        st_dir, st_line = supertrend(df)
        d["ST_DIR"], d["ST_LINE"] = st_dir, st_line
        pk, pd_ = stochastic(df)
        d["STOCH_K"], d["STOCH_D"] = pk, pd_
        d["ADX"] = adx(df)
    else:
        d["ST_DIR"] = np.where(c > d["EMA20"], 1, -1)  # HL yoksa yaklaşık
        d["ST_LINE"] = np.nan
        d["STOCH_K"] = d["STOCH_D"] = np.nan
        d["ADX"] = np.nan
    _, _, _, pctb = bollinger(c)
    d["BOLL_B"] = pctb

    # --- yönlü oylar (Series) ---
    v_st = (d["ST_DIR"] == 1)
    v_macd = (d["MACD"] > d["MACD_SIGNAL"])
    v_ema = (d["EMA20"] > d["EMA50"])
    v_rsi = (d["RSI"] > 52)
    v_stoch = (d["STOCH_K"] > d["STOCH_D"]) & (d["STOCH_K"] < 80)
    if not hl:
        v_stoch = pd.Series(False, index=c.index)
    oy = v_st.astype(int) + v_macd.astype(int) + v_ema.astype(int) + v_rsi.astype(int) + v_stoch.astype(int)
    d["OY"] = oy
    d["SINYAL"] = np.where(oy >= AL_ESIK, "AL", np.where(oy <= SAT_ESIK, "SAT", "NÖTR"))
    return d


def _sig(b):
    return "AL" if b else "SAT"


def _detay(son, hl):
    L = []
    L.append({"ad": "SuperTrend", "sinyal": "AL" if son["ST_DIR"] == 1 else "SAT",
              "aciklama": "Fiyat SuperTrend çizgisinin üstünde (yeşil)" if son["ST_DIR"] == 1
              else "Fiyat SuperTrend çizgisinin altında (kırmızı)"})
    L.append({"ad": "MACD", "sinyal": _sig(son["MACD"] > son["MACD_SIGNAL"]),
              "aciklama": "MACD sinyal çizgisinin üstünde" if son["MACD"] > son["MACD_SIGNAL"]
              else "MACD sinyal çizgisinin altında"})
    L.append({"ad": "EMA 20/50", "sinyal": _sig(son["EMA20"] > son["EMA50"]),
              "aciklama": "Kısa ortalama uzunun üstünde (yükseliş dizilimi)" if son["EMA20"] > son["EMA50"]
              else "Kısa ortalama uzunun altında"})
    r = son["RSI"]
    L.append({"ad": "RSI", "sinyal": "AL" if (not pd.isna(r) and r > 52) else "SAT",
              "aciklama": f"RSI {r:.0f}" + (" (aşırı alım)" if (not pd.isna(r) and r > 70) else
                          " (aşırı satım)" if (not pd.isna(r) and r < 30) else "")})
    if hl and not pd.isna(son["STOCH_K"]):
        sb = son["STOCH_K"] > son["STOCH_D"] and son["STOCH_K"] < 80
        L.append({"ad": "Stochastic", "sinyal": _sig(sb),
                  "aciklama": f"%K {son['STOCH_K']:.0f}, %D {son['STOCH_D']:.0f}"})
    # bağlam (oy vermez)
    ek = []
    if hl and not pd.isna(son["ADX"]):
        a = son["ADX"]
        ek.append(("ADX", f"{a:.0f} — " + ("güçlü trend" if a > 25 else "zayıf/yatay trend")))
    if not pd.isna(son["BOLL_B"]):
        b = son["BOLL_B"]
        yer = "üst banda yakın (güçlü/aşırı)" if b > 0.9 else ("alt banda yakın (zayıf/tepki)" if b < 0.1 else "orta bantta")
        ek.append(("Bollinger", yer))
    return L, ek


def _pivotlar(seri, k, tepe):
    """Lokal tepe (tepe=True) ya da dip noktaları: [(konum, fiyat), ...]."""
    v = seri.to_numpy(dtype=float)
    out = []
    for i in range(k, len(v) - k):
        pencere = v[i-k:i+k+1]
        if np.isnan(pencere).any():
            continue
        if v[i] == (pencere.max() if tepe else pencere.min()):
            out.append((i, float(v[i])))
    return out


def destek_direnc(df):
    """Fiyatın altındaki en yakın geçmiş dip (destek) ve üstündeki en yakın geçmiş tepe (direnç).
    Etiketler: 'tepki' = desteğe indi ve yukarı dönüyor; 'yaklas' = dirence yakın."""
    t = df.tail(SD_GUN)
    hl = _hl_var(df)
    close = t["Close"]
    low = t["Low"] if hl else close
    high = t["High"] if hl else close
    fiyat = float(close.iloc[-1])

    # yakınlık eşiği hissenin oynaklığına göre: 0.5×ATR, en az %1, en fazla %2.5
    # (BIST'te günlük ATR medyanı ~%4; daha geniş eşik hisselerin yarısını etiketliyordu)
    atr = _atr(df, 14).iloc[-1] if hl else df["Close"].diff().abs().rolling(14).mean().iloc[-1]
    atr_pct = float(atr) / fiyat if not pd.isna(atr) else 0.0
    tol = min(max(0.5 * atr_pct, SD_TOL_MIN), SD_TOL_MAX)

    sinir = len(t) - 1 - SD_YENI
    dipler = [p for p in _pivotlar(low, PIVOT_K, False) if p[0] <= sinir]
    tepeler = [p for p in _pivotlar(high, PIVOT_K, True) if p[0] <= sinir]

    alt = [p for p in dipler if p[1] <= fiyat]
    ust = [p for p in tepeler if p[1] > fiyat]
    destek = max(alt, key=lambda p: (p[1], p[0])) if alt else None    # en yakın, eşitse en yeni
    direnc = min(ust, key=lambda p: (p[1], -p[0])) if ust else None

    def seviye(p, liste):
        f = p[1]
        benzer = sorted(q[0] for q in liste if abs(q[1] - f) <= f * tol)  # aynı bölgeyi test edenler
        return {"fiyat": round(f, 2), "tarih": str(t.index[p[0]].date()), "test": len(benzer),
                "tarihler": [str(t.index[i].date()) for i in benzer],
                "uzaklik": round((f / fiyat - 1) * 100, 1)}

    ds = seviye(destek, dipler) if destek else None
    dr = seviye(direnc, tepeler) if direnc else None

    tepki = yaklas = False
    if ds and ds["test"] >= SD_MIN_TEST:
        S = destek[1]
        dokundu = float(low.tail(5).min()) <= S * (1 + tol)          # son 5 günde desteğe indi
        donus = fiyat > float(close.iloc[-2])                         # yukarı dönüyor
        yakin = fiyat <= S * (1 + tol)                                # henüz uzaklaşmadı
        tepki = dokundu and donus and yakin
    if dr and dr["test"] >= SD_MIN_TEST:
        yaklas = (direnc[1] - fiyat) / fiyat <= tol
    if tepki and yaklas:   # dar bantta ikisi birden çıkmasın: fiyat hangisine yakınsa o
        if direnc[1] - fiyat < fiyat - destek[1]:
            tepki = False
        else:
            yaklas = False

    return {"destek": ds, "direnc": dr, "tol": round(tol * 100, 1), "gun": SD_GUN,
            "min_test": SD_MIN_TEST, "tepki": bool(tepki), "yaklas": bool(yaklas)}


def _spark(d, n=130):
    """Grafik verisi: son n gün (~6 ay) kapanış, ortalamalar, SuperTrend ve sinyal (A/S/N, AL/SAT dönüş işaretleri için)."""
    t = d.tail(n)
    def arr(col):
        return [None if (col not in t or pd.isna(x)) else round(float(x), 2) for x in (t[col] if col in t else [np.nan]*len(t))]
    out = {"c": arr("Close"), "s20": arr("SMA20"), "s50": arr("SMA50"),
           "t": [str(x.date()) for x in t.index],
           "sg": "".join({"AL": "A", "SAT": "S"}.get(x, "N") for x in t["SINYAL"])}
    if "ST_LINE" in t:
        out["st"] = arr("ST_LINE")
    return out


def analiz_et(df):
    c = df["Close"].dropna()
    if len(c) < 60:
        return None
    d = gostergeler(df)
    son, onceki = d.iloc[-1], d.iloc[-2]
    hl = _hl_var(df)
    detay, ek = _detay(son, hl)
    sd = destek_direnc(df)
    al_oy = sum(1 for x in detay if x["sinyal"] == "AL")
    fiyat = float(son["Close"])
    rsi_val = None if pd.isna(son["RSI"]) else float(son["RSI"])
    gerekce = [x["ad"] for x in detay if x["sinyal"] == "AL"]
    degisim = (fiyat/float(onceki["Close"]) - 1)*100 if onceki["Close"] else None

    # --- sinyal ne zamandır sürüyor? ---
    sig = list(d["SINYAL"].values)
    cur = sig[-1]
    run = 1
    for i in range(len(sig)-2, -1, -1):
        if sig[i] == cur:
            run += 1
        else:
            break
    start_idx = len(sig) - run
    # NÖTR'e nereden gelindi? (sarı: AL'den, turuncu: SAT'tan)
    notr_kaynak = sig[start_idx - 1] if (cur == "NÖTR" and start_idx > 0) else None
    sinyal_tarih = str(d.index[start_idx].date())
    bas_fiyat = float(d["Close"].iloc[start_idx])
    sinyal_degisim = round((fiyat/bas_fiyat - 1)*100, 1) if bas_fiyat else None
    yeni = run <= 1  # son barda döndü = bugün taze
    stop = round(float(son["STOP"]), 2)
    giris_stop = round(float(d["STOP"].iloc[start_idx]), 2)  # AL başladığındaki sabit stop
    hedef = round(fiyat + 2*(fiyat - giris_stop), 2) if (cur == "AL" and fiyat > giris_stop) else None

    # son AL'in başladığı gün ve o günkü stop (portföydeki pozisyonun çıkış seviyesi)
    al_bas = next((i for i in range(len(sig) - 1, -1, -1) if sig[i] == "AL" and (i == 0 or sig[i-1] != "AL")), None)
    al_stop = round(float(d["STOP"].iloc[al_bas]), 2) if al_bas is not None else None
    al_tarih = str(d.index[al_bas].date()) if al_bas is not None else None

    # hacim teyidi: AL'e dönüş günü hacmi önceki 20 günün ortalamasının HACIM_ESIK katından fazla mı
    hacim_kat = None
    if cur == "AL" and "Volume" in d:
        v = d["Volume"].astype(float)
        ort = v.iloc[max(0, start_idx - 20):start_idx].mean()
        if ort and not pd.isna(ort):
            hacim_kat = round(float(v.iloc[start_idx]) / float(ort), 1)

    # taban serisi: son TABAN_GUN günde kaç kez ~%10 düştü
    taban = int((d["Close"].pct_change().tail(TABAN_GUN) <= TABAN_GETIRI).sum())

    return {
        "fiyat": round(fiyat, 2),
        "degisim": round(degisim, 2) if degisim is not None else None,
        "rsi": round(rsi_val, 1) if rsi_val is not None else None,
        "puan": float(son["OY"]),
        "uyum": f"{al_oy}/{len(detay)}",
        "sinyal": str(son["SINYAL"]),
        "detay": detay,
        "ek": [{"ad": a, "aciklama": b} for a, b in ek],
        "sd": sd,
        "destek_tepki": sd["tepki"],
        "direnc_yakin": sd["yaklas"],
        "gerekce": gerekce,
        "stop": stop,
        "giris_stop": giris_stop,
        "hedef": hedef,
        "sinyal_gun": run,
        "notr_kaynak": notr_kaynak,
        "al_stop": al_stop,
        "al_tarih": al_tarih,
        "hacim_kat": hacim_kat,
        "hacim_teyit": bool(hacim_kat is not None and hacim_kat >= HACIM_ESIK),
        "taban15": taban,
        "patlak": taban >= PATLAK_TABAN,
        "sinyal_tarih": sinyal_tarih,
        "sinyal_degisim": sinyal_degisim,
        "yeni": bool(yeni),
        "spark": _spark(d),
    }
