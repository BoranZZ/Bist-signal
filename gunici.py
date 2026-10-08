# -*- coding: utf-8 -*-
"""Gün içi görünüm (15 dk / 1 saat / 4 saat) — BİLGİ, AL/SAT sinyali değil.

Her vade için son TAMAMLANMIŞ mumda: trend (EMA20 > EMA50 ve fiyat > EMA50 → yukarı, ikisi de tersi → aşağı, aksi yatay),
RSI(14) ve son 3 mumda önceki 20 mumun en yüksek / en düşük kapanışının aşılması (zirve / dip kırılımı).
Mumlar Yahoo'nun 15 dk verisinden (tarama.veri_cek zaten indiriyor: aynı indirme kapanış düzeltmesine de yarar) türetilir:
1 saat 10:00'dan hizalı (10-11, ..., 17-18), 4 saat 10:00-14:00 / 14:00-18:00 blokları. Yahoo ~15 dk gecikmeli: bitişi
'şimdi − 15 dk'dan sonra olan (yarım) mumlar atılır. Kaydedilmemiş bölünme `sinyal.bolunme_duzelt` ile düzeltilir.

Araştırma (2026-10, scratchpad vade_gunici, 323 hisse, 2023-11 → 2026-10): bu durumlar büyük hisselerde (BIST100+EK)
sonraki 1-5 gün için işlem maliyetini aşan bir ipucu vermedi; RSI < 30 olanlar sonraki 5 günde ortalama hisseden geride
kaldı ('ucuz' demek değil). Bu yüzden sadece hisse penceresinde durum bilgisi olarak gösterilir.
"""
import re, json
import numpy as np
import pandas as pd
from sinyal import ema, rsi, bolunme_duzelt

TZ = "Europe/Istanbul"
GUN = 59            # Yahoo 15 dk verisini en fazla son 60 gün verir; 4 saatlik EMA50 için ~80 mum
GECIKME = 15        # Yahoo BIST verisi ~15 dk gecikmeli: bitişi bundan yeni olan mum henüz yarım
MIN_MUM = 60        # bundan az mum varsa o vade boş (EMA50 oturmaz)
KIRILIM_MUM, KIRILIM_SON = 20, 3
SEANS_BAS, SEANS_SON = 10 * 60, 18 * 60   # sürekli işlem (09:30-09:45 açılış mumları alınmaz)
VADELER = ((15, "15"), (60, "60"), (240, "240"))


def _tek(g, tk):
    try:
        d = g[tk][["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
    except KeyError:
        return None
    if d.empty:
        return None
    d = d.copy()
    d.index = d.index.tz_convert(TZ) if d.index.tz is not None else d.index.tz_localize("UTC").tz_convert(TZ)
    d = d[~d.index.duplicated(keep="last")].sort_index()
    dk = d.index.hour * 60 + d.index.minute
    return d[(dk >= SEANS_BAS) & (dk < SEANS_SON)]


def mumlar(d15, dakika, kesim):
    """15 dk mumlarından 'dakika' (15/60/240) boyunda mum; bitişi kesim'den sonra olan (yarım) mum atılır."""
    dk = d15.index.hour * 60 + d15.index.minute
    gun = d15.index.normalize()
    if dakika == 240:
        bas = np.where(dk < 14 * 60, SEANS_BAS, 14 * 60)
        boy = np.where(dk < 14 * 60, 240, SEANS_SON - 14 * 60)
    else:
        bas = SEANS_BAS + (dk - SEANS_BAS) // dakika * dakika
        boy = np.full(len(dk), dakika)
    anahtar = gun + pd.to_timedelta(bas, unit="m")
    bitis = pd.Series(anahtar + pd.to_timedelta(boy, unit="m"), index=d15.index)
    m = d15.groupby(anahtar).agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
    m["bitis"] = bitis.groupby(anahtar).first().values
    return m[m["bitis"] <= kesim]


def durum(m):
    """[trend (1/0/-1), RSI (tam sayı), kırılım (1 zirve / -1 dip / 0)] ya da None."""
    if m is None or len(m) < MIN_MUM:
        return None
    c = m["Close"]
    e20, e50, r = ema(c, 20), ema(c, 50), rsi(c, 14)
    cs, a, b = float(c.iloc[-1]), float(e20.iloc[-1]), float(e50.iloc[-1])
    tr = 1 if (a > b and cs > b) else (-1 if (a < b and cs < b) else 0)
    onceki = c.shift(1)
    zirve = (c > onceki.rolling(KIRILIM_MUM).max()).iloc[-KIRILIM_SON:].any()
    dip = (c < onceki.rolling(KIRILIM_MUM).min()).iloc[-KIRILIM_SON:].any()
    rv = r.iloc[-1]
    return [tr, None if pd.isna(rv) else int(round(float(rv))), 1 if zirve else (-1 if dip else 0)]


def hesapla(g, kodlar, simdi):
    """g: yf.download(15m) çıktısı. Dönüş: {"g": son mum günü, "t": son tamam mum bitişi 'GG.AA SS:DD', "tam": seans bitti mi,
    "v": {kod: [15dk trend, RSI, kırılım, 1s ..., 4s ...] (eksik vade None)}} ya da None."""
    kesim = simdi.tz_convert(TZ).tz_localize(None) - pd.Timedelta(minutes=GECIKME)
    v, son = {}, None
    for kod in kodlar:
        try:
            d = _tek(g, kod + ".IS")
            if d is None or len(d) < MIN_MUM:
                continue
            d = bolunme_duzelt(d)
            d.index = d.index.tz_localize(None)
            satir = []
            for dakika, _ in VADELER:
                m = mumlar(d, dakika, kesim)
                if dakika == 15 and len(m):
                    son = max(son, m["bitis"].iloc[-1]) if son is not None else m["bitis"].iloc[-1]
                x = durum(m)
                satir += x if x else [None, None, None]
            if any(x is not None for x in satir):
                v[kod] = satir
        except Exception:
            continue
    if not v or son is None:
        return None
    yerel = simdi.tz_convert(TZ)
    tam = bool(yerel.date() > son.date() or yerel.hour * 60 + yerel.minute >= 18 * 60 + 30)
    return {"g": str(son.date()), "t": son.strftime("%d.%m %H:%M"), "tam": tam, "v": v}


def seans_ici(simdi):
    s = simdi.tz_convert(TZ)
    return s.weekday() < 5 and SEANS_BAS <= s.hour * 60 + s.minute < 18 * 60 + 30


def son_islem_gunu(simdi):
    """Seans dışında (akşam / hafta sonu / sabah 10:00 öncesi) en son seansın günü (resmi tatiller bilinmez)."""
    s = simdi.tz_convert(TZ)
    g = s.normalize()
    if s.weekday() >= 5 or s.hour * 60 + s.minute < SEANS_BAS:
        g -= pd.Timedelta(days=1)
        while g.weekday() >= 5:
            g -= pd.Timedelta(days=1)
    return str(g.date())


def onceki(yol="index.html"):
    """Önceki panodaki gün içi verisi (seans dışında aynı hesabı tekrarlamamak için)."""
    try:
        with open(yol, encoding="utf-8") as f:
            m = re.search(r"\nconst GI=(.*?);\n", f.read())
        x = json.loads(m.group(1)) if m else None
        return x if isinstance(x, dict) and x.get("v") else None
    except Exception:
        return None


def yeniden_kullan(simdi, yol="index.html"):
    """Seans dışındaysa ve önceki pano son seansın tamamlanmış gün içi durumunu taşıyorsa onu döndürür."""
    if seans_ici(simdi):
        return None
    x = onceki(yol)
    return x if (x and x.get("tam") and x.get("g") == son_islem_gunu(simdi)) else None
