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
# v2 (gece testleri, 2026-09): çıkış = AL'den sonraki en yüksek kapanışın %20 altı (iz stop). Sınırsız sepet
# simülasyonunda stop+SAT2'ye göre düşük faizde +%9 -> +%67, 2023'te -%6 -> +%45; %18/%22 komşuları tutarlı.
# Giriş filtresi: trend (fiyat>SMA200 ve SMA200 yükseliyor) + aşırı oynak değil (60 günlük günlük oynaklık ≤ %5).
IZ_STOP_ORAN = 0.20
OYNAK_ESIK = 0.05


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


BOLUNME_ALT, BOLUNME_UST = -0.25, 0.35   # BIST günlük sınır ±%10: bundan büyük tek gün hareketi = kaydedilmemiş bölünme


def bolunme_duzelt(df):
    """yfinance BIST bedelsiz/bölünmeleri çoğu zaman kaydetmiyor: o gün fiyat %50-90 "düşmüş" görünür, göstergeler ve
    iz stop bozulur (5 yılda 125 hissede 12 olay: KONTR, FENER, CCOLA, HEKTS, TUKAS...). Tek günlük ≤ −%25 / ≥ +%35
    kapanış değişimi bölünme sayılır; önceki fiyatlar o oranla (hacim tersine) düzeltilir. df.attrs["bolunme"] = tarihler."""
    if df is None or len(df) < 2 or "Close" not in df:
        return df
    c = df["Close"]
    r = c / c.shift(1)
    olay = r[(r - 1 <= BOLUNME_ALT) | (r - 1 >= BOLUNME_UST)].dropna()
    if olay.empty:
        return df
    df = df.copy()
    carpan = pd.Series(1.0, index=df.index)
    for t, oran in olay.items():
        carpan[df.index < t] *= float(oran)
    for k in ("Open", "High", "Low", "Close"):
        if k in df:
            df[k] = df[k] * carpan
    if "Volume" in df:
        df["Volume"] = df["Volume"] / carpan
    df.attrs["bolunme"] = [str(t.date()) for t in olay.index]
    return df


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


def uzun_vade(d):
    """🌱 Uzun vade sinyali (günlük sinyalden bağımsız, yavaş): yükselen trendde (fiyat SMA200 üstü, SMA200 20 günde
    yükselmiş) fiyat SMA50'ye (%2 yakınına) geri çekilip üstünde yükselişle kapanınca AL; 2 gün üst üste SMA200 altı
    kapanışta SAT. Backtest (2021-26, çökenler hariç): düşük faizde işlem başı endekse göre +%10.7, isabet %65;
    yüksek faizde +%3.4 — günlük sinyalden iyi (bkz. CLAUDE.md)."""
    c, s50, s200 = d["Close"], d["SMA50"], d["SMA200"]
    yukselen = (s200 > s200.shift(20)) & (c > s200)
    al_gun = (yukselen & (d["Low"] <= s50 * 1.02) & (c > s50) & (c > c.shift(1))).values
    cik_gun = ((c < s200) & (c.shift(1) < s200.shift(1))).values
    durum, tarih, idx = None, None, d.index
    for i in range(len(d)):
        if durum != "AL" and al_gun[i]:
            durum, tarih = "AL", i
        elif durum == "AL" and cik_gun[i]:
            durum, tarih = "SAT", i
    son_s200 = s200.iloc[-1]
    return {"durum": durum, "tarih": str(idx[tarih].date()) if tarih is not None else None,
            "gun": (len(d) - tarih) if tarih is not None else None,
            "degisim": round((float(c.iloc[-1]) / float(c.iloc[tarih]) - 1) * 100, 1) if tarih is not None else None,
            "sma200": None if pd.isna(son_s200) else round(float(son_s200), 2),
            "sma50": None if pd.isna(s50.iloc[-1]) else round(float(s50.iloc[-1]), 2),
            "trend": bool(yukselen.iloc[-1])}   # şu an yükselen trendde mi (AL yoksa: geri çekilme bekleniyor)


def bayrak_kirilimi(df):
    """🚩 Boğa bayrağı kırılımı son günde mi: direk (≤10 günde ≥%15), bayrak (5-15 gün, geri çekilme ≤ direğin
    yarısı, bayrakta yeni tepe yok, hacim direkten düşük), bugün kapanış bayrak tepesinin üstünde. Backtest: isabeti
    yükseltiyor (%46) ama ayrı sinyal olarak ek getiri yok; kırılımların %70-85'i zaten AL ile aynı gün — bilgi etiketi."""
    if len(df) < 40 or "Volume" not in df:
        return None
    h, l, c, v = df["High"].values, df["Low"].values, df["Close"].values, df["Volume"].values
    i = len(df) - 1
    for L in range(5, 16):
        b0 = i - L
        if b0 < 12:
            break
        dip, tepe = min(c[b0 - 11:b0]), c[b0 - 1]
        if tepe / dip - 1 < 0.15:
            continue
        bh, bl = max(h[b0:i]), min(l[b0:i])
        if (tepe - bl) / (tepe - dip) > 0.5 or bh > tepe * 1.03:
            continue
        if np.mean(v[b0:i]) >= np.mean(v[b0 - 10:b0]):
            continue
        if c[i] > bh:
            return {"direk": round((tepe / dip - 1) * 100), "bayrak_gun": L, "bayrak_dip": round(float(bl), 2)}
    return None


KIRILIM_GUN = 20   # v3: trend şablonundayken önceki 20 günün en yüksek kapanışının üstüne ilk kapanış


def trend_sablonu(d):
    """Minervini trend şablonu (günlük seri): fiyat > SMA50 > SMA150 > SMA200, SMA200 20 günde yükselmiş,
    fiyat 52 hafta zirvesinin en az %75'inde ve 52 hafta dibinin en az %30 üstünde."""
    c = d["Close"]
    s150 = c.rolling(150).mean()
    mx, mn = c.rolling(250).max(), c.rolling(250).min()
    return ((c > s150) & (s150 > d["SMA200"]) & (d["SMA200"] > d["SMA200"].shift(20)) & (d["SMA50"] > s150)
            & (c > d["SMA50"]) & (c >= 0.75 * mx) & (c >= 1.30 * mn))


def trend_kirilimi(d, xu_ust=None, islemler=False):
    """🚀 v3 giriş/çıkış (5 yıllık backtest'te v2'den iyi, bkz. CLAUDE.md): trend şablonundayken 20 günlük zirvenin
    ilk kırılımı (piyasa XU100 > SMA50, 60 gün oynaklık ≤ %5) → AL; ertesi açılıştan girilir, AL'den beri tepe
    kapanışın IZ_STOP_ORAN altına kapanışta çıkılır. Pozisyon açıkken yeni kırılımlar sayılmaz (backtest'le aynı)."""
    c = d["Close"]
    sab = trend_sablonu(d)
    kir = c > c.rolling(KIRILIM_GUN).max().shift(1)
    gir = sab & kir & ~kir.shift(1, fill_value=False)
    gir &= ~(c.pct_change().rolling(60).std() > OYNAK_ESIK)
    if xu_ust is not None:
        gir &= xu_ust.reindex(d.index, method="ffill").fillna(False).astype(bool)
    g, o, cv, idx, n = gir.values, d["Open"].values, c.values, d.index, len(d)
    tum, i, acik = [], 210, None
    while i < n:
        if not g[i]:
            i += 1; continue
        giris = o[i + 1] if i + 1 < n else cv[i]   # bugün sinyal: giriş yarın açılışta (şimdilik kapanış)
        tepe, tepe_i, cik = giris, i, None
        for j in range(i + 1, n):
            if cv[j] > tepe:
                tepe, tepe_i = cv[j], j
            if cv[j] < tepe * (1 - IZ_STOP_ORAN):
                cik = j; break
        tum.append({"i": i, "giris": float(giris), "tepe": float(tepe), "tepe_i": tepe_i, "cik": cik})
        if cik is None:
            acik = tum[-1]; break
        i = cik + 1
    if islemler:
        return [(idx[t["i"] + 1] if t["i"] + 1 < n else idx[t["i"]], idx[t["cik"]] if t["cik"] is not None else None,
                 t["giris"], float(cv[t["cik"]]) if t["cik"] is not None else None) for t in tum]
    fiyat = float(cv[-1])
    sab_son = bool(sab.iloc[-1]) if len(sab) else False
    hh = float(c.iloc[-KIRILIM_GUN - 1:-1].max()) if n > KIRILIM_GUN else None
    son = tum[-1] if tum else None
    # bugün = bugün YENİ pozisyon açıldı (açık pozisyon sürerken gelen yeni zirve kırılımları sayılmaz — backtest'le aynı)
    out = {"sablon": sab_son, "bugun": bool(acik is not None and acik["i"] == n - 1), "durum": None,
           "kirilim_seviye": round(hh, 2) if hh else None,
           "kirilima_uzak": round((hh / fiyat - 1) * 100, 1) if (hh and sab_son and not acik) else None}
    if acik:
        stop = acik["tepe"] * (1 - IZ_STOP_ORAN)
        out.update({"durum": "AL", "giris_tarih": str(idx[acik["i"]].date()), "giris_fiyat": round(acik["giris"], 2),
                    "gun": n - 1 - acik["i"], "degisim": round((fiyat / acik["giris"] - 1) * 100, 1),
                    "tepe": round(acik["tepe"], 2), "tepe_tarih": str(idx[acik["tepe_i"]].date()),
                    "stop": round(stop, 2), "uzaklik": round((stop / fiyat - 1) * 100, 1)})
    elif son and son["cik"] is not None:
        out.update({"durum": "CIKTI", "giris_tarih": str(idx[son["i"]].date()), "cikis_tarih": str(idx[son["cik"]].date()),
                    "tepe": round(son["tepe"], 2), "tepe_tarih": str(idx[son["tepe_i"]].date()),
                    "stop": round(son["tepe"] * (1 - IZ_STOP_ORAN), 2),
                    "sonuc": round((float(cv[son["cik"]]) / son["giris"] - 1) * 100, 1), "cikis_gun": n - 1 - son["cik"]})
    return out


def tahta_riski(d):
    """Tahtacı 'şişir-çak' uyarısı (o güne kadarki veriyle). 5 yıllık olay çalışması (2022-26, tüm hisseler): normalde
    bir hissenin 20 gün içinde ≥%25 çakılma olasılığı %2,3. 🔥 şişme: 10 günde ≥5 tavan (%19, 8 kat), 20 günde ≥%100
    (%15, 7 kat), 50g ortalamanın %70+ üstü ve 20g oynaklık ≥%6 (%16), ≥3 tavan + hacim 5g/60g ≥3x (%19). ⚠️ dağıtım:
    hacim 5g/60g > 2x iken fiyat 10g zirvesinin %8+ altında (%9,5, 4 kat). Kesinlik değil risk: çoğu yine çakılmaz."""
    c, v = d["Close"], d["Volume"].replace(0, float("nan"))
    if len(c) < 61:
        return None
    r = c.pct_change()
    tavan10 = int((r.tail(10) >= 0.095).sum())
    yuk20 = float(c.iloc[-1] / c.iloc[-21] - 1)
    sisme50 = float(c.iloc[-1] / c.tail(50).mean() - 1)
    vol20 = float(r.tail(20).std())
    hk = v.tail(5).mean() / v.tail(60).mean()
    hk = float(hk) if hk == hk else 0.0
    zirve10 = float(c.tail(10).max())
    neden = []
    if tavan10 >= 5:
        neden.append(f"10 günde {tavan10} tavan")
    if yuk20 >= 1.0:
        neden.append(f"20 günde %{yuk20 * 100:.0f} yükseliş")
    if sisme50 >= 0.7 and vol20 >= 0.06:
        neden.append(f"50 günlük ortalamanın %{sisme50 * 100:.0f} üstünde, çok oynak")
    if tavan10 >= 3 and hk >= 3:
        neden.append(f"{tavan10} tavan + hacim {hk:.1f} kat")
    seviye = "sisme" if neden else None
    if not seviye and hk > 2 and c.iloc[-1] < zirve10 * 0.92:
        seviye = "dagitim"
        neden.append(f"hacim {hk:.1f} kat artmışken fiyat 10 günlük zirvenin %{(1 - c.iloc[-1] / zirve10) * 100:.0f} altında")
    return {"seviye": seviye, "neden": neden, "tavan10": tavan10, "yuk20": round(yuk20 * 100, 1),
            "sisme50": round(sisme50 * 100, 1), "hacim_kat": round(hk, 1)}


def analiz_et(df, xu_ust=None):
    df = bolunme_duzelt(df)
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
    # iz stop: son AL dönüşünden beri görülen en yüksek kapanışın IZ_STOP_ORAN altı
    iz = None
    if al_bas is not None:
        # AL'den itibaren gün gün: tepe güncellenir; kapanış tepenin %20 altına ilk indiği gün pozisyon kapanmış sayılır
        kap = d["Close"].iloc[al_bas:]
        tepe, tepe_t, cikis_t = -1.0, None, None
        for t, x in kap.items():
            if x > tepe:
                tepe, tepe_t = float(x), t
            if x < tepe * (1 - IZ_STOP_ORAN):
                cikis_t = t
                break
        iz = {"tepe": round(tepe, 2), "tepe_tarih": str(tepe_t.date()), "stop": round(tepe * (1 - IZ_STOP_ORAN), 2),
              "cikti": cikis_t is not None, "cikis_tarih": str(cikis_t.date()) if cikis_t is not None else None,
              "uzaklik": round((tepe * (1 - IZ_STOP_ORAN) / fiyat - 1) * 100, 1)}
    vol60 = d["Close"].pct_change().tail(60).std()
    oynak = bool(not pd.isna(vol60) and vol60 > OYNAK_ESIK)
    s200 = d["SMA200"]
    trend = bool(len(d) > 220 and not pd.isna(s200.iloc[-1]) and fiyat > s200.iloc[-1] and s200.iloc[-1] > s200.iloc[-21])
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
    # son 20 günde ne kadar yükselmiş (portföy simülasyonu: aynı gün birden çok AL'de az yükselmiş olan daha iyi)
    mom20 = round((fiyat / float(d["Close"].iloc[-21]) - 1) * 100, 1) if len(d) > 21 else None

    # v3: son giriş 🚀 trend kırılımıysa (gösterge AL'inden daha yeni) iz stop o girişten izlenir
    tk = trend_kirilimi(d, xu_ust)
    if tk.get("giris_tarih") and (al_tarih is None or tk["giris_tarih"] >= al_tarih):
        al_tarih = tk["giris_tarih"]
        if tk["durum"] == "AL":
            iz = {"tepe": tk["tepe"], "tepe_tarih": tk["tepe_tarih"], "stop": tk["stop"], "cikti": False,
                  "cikis_tarih": None, "uzaklik": tk["uzaklik"]}
        else:
            iz = {"tepe": tk["tepe"], "tepe_tarih": tk["tepe_tarih"], "stop": tk["stop"], "cikti": True,
                  "cikis_tarih": tk["cikis_tarih"], "uzaklik": round((tk["stop"] / fiyat - 1) * 100, 1)}

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
        "iz": iz,
        "oynak": oynak,
        "vol60": None if pd.isna(vol60) else round(float(vol60) * 100, 1),
        "trend": trend,
        "v2_uygun": bool(trend and not oynak),   # v2 giriş filtresi (piyasa filtresi taramada)
        "al_tarih": al_tarih,
        "hacim_kat": hacim_kat,
        "hacim_teyit": bool(hacim_kat is not None and hacim_kat >= HACIM_ESIK),
        "taban15": taban,
        "mom20": mom20,
        "uv": uzun_vade(d),
        "tk": tk,
        "bolunme": (df.attrs.get("bolunme") or [None])[-1],   # son (kaydedilmemiş) bedelsiz/bölünme tarihi
        "bayrak": bayrak_kirilimi(df),
        "patlak": taban >= PATLAK_TABAN,
        "tahta": tahta_riski(d),
        "sinyal_tarih": sinyal_tarih,
        "sinyal_degisim": sinyal_degisim,
        "yeni": bool(yeni),
        "spark": _spark(d),
    }
