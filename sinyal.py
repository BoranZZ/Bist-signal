"""
Gösterge ve sinyal çekirdeği.
Tek kural seti; hem canlı tarama hem backtest aynı fonksiyonları kullanır
(kurallar iki yerde farklı olmasın diye).
"""
import numpy as np
import pandas as pd


def sma(series, period):
    return series.rolling(period).mean()


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line


def gostergeler(df):
    """df ('Close' şart) -> göstergeler + her gün için puan ve sinyal sütunları."""
    d = df.copy()
    c = d["Close"]
    d["SMA20"] = sma(c, 20)
    d["SMA50"] = sma(c, 50)
    d["SMA200"] = sma(c, 200)
    d["RSI"] = rsi(c, 14)
    m, s, h = macd(c)
    d["MACD"], d["MACD_SIGNAL"], d["MACD_HIST"] = m, s, h

    # --- Puanlama (her satır için, vektörel) ---
    puan = pd.Series(0.0, index=d.index)
    puan += (c > d["SMA50"]).astype(float)                       # trend
    puan += (d["SMA20"] > d["SMA50"]).astype(float)              # dizilim
    kesisim = (m.shift(1) <= s.shift(1)) & (m > s)               # taze MACD kesişimi
    puan += kesisim.astype(float) * 2
    puan += ((~kesisim) & (m > s)).astype(float)                # pozitif momentum
    puan += ((d["RSI"] >= 45) & (d["RSI"] <= 68)).astype(float)  # sağlıklı RSI
    puan -= (d["RSI"] > 75).astype(float)                        # aşırı alım cezası
    d["PUAN"] = puan
    d["MACD_KESISIM"] = kesisim

    d["SINYAL"] = np.where(puan >= 4, "AL", np.where(puan >= 2, "NÖTR", "SAT"))

    # Stop: son 20 günün dibi ya da %8 altı (hangisi yüksekse = daha yakın koruma)
    d["STOP"] = np.maximum(c.rolling(20).min(), c * 0.92)
    return d


def analiz_et(df):
    """Son gün için özet sözlük (canlı tarama için)."""
    c = df["Close"].dropna()
    if len(c) < 60:
        return None
    d = gostergeler(df)
    son, onceki = d.iloc[-1], d.iloc[-2]

    fiyat = float(son["Close"])
    rsi_val = None if pd.isna(son["RSI"]) else float(son["RSI"])
    gerekce = []
    if not pd.isna(son["SMA50"]):
        gerekce.append("Fiyat 50 günlük ortalama üstünde (yükseliş trendi)"
                       if fiyat > son["SMA50"] else "Fiyat 50 günlük ortalama altında (zayıf trend)")
    if not pd.isna(son["SMA20"]) and not pd.isna(son["SMA50"]) and son["SMA20"] > son["SMA50"]:
        gerekce.append("20 günlük ortalama 50'nin üstünde")
    if bool(son["MACD_KESISIM"]):
        gerekce.append("MACD yeni AL kesişimi verdi")
    elif son["MACD"] > son["MACD_SIGNAL"]:
        gerekce.append("MACD sinyal çizgisi üstünde (pozitif momentum)")
    if rsi_val is not None:
        if 45 <= rsi_val <= 68:
            gerekce.append(f"RSI {rsi_val:.0f} (sağlıklı momentum bölgesi)")
        elif rsi_val > 75:
            gerekce.append(f"RSI {rsi_val:.0f} (aşırı alım — dikkat)")
        elif rsi_val < 30:
            gerekce.append(f"RSI {rsi_val:.0f} (aşırı satım)")

    degisim = (fiyat / float(onceki["Close"]) - 1) * 100 if onceki["Close"] else None
    return {
        "fiyat": round(fiyat, 2),
        "degisim": round(degisim, 2) if degisim is not None else None,
        "rsi": round(rsi_val, 1) if rsi_val is not None else None,
        "sma50": None if pd.isna(son["SMA50"]) else round(float(son["SMA50"]), 2),
        "macd_kesisim": bool(son["MACD_KESISIM"]),
        "puan": float(son["PUAN"]),
        "sinyal": str(son["SINYAL"]),
        "gerekce": gerekce,
        "stop": round(float(son["STOP"]), 2),
    }
