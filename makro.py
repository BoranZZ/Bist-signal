# -*- coding: utf-8 -*-
"""🌍 Dünya ve makro katmanı — SADECE BİLGİ (AL/SAT, iz stop, kâr kilidi, piyasa filtresi, İşlem Odası DEĞİŞMEZ).

Araştırma: Documents/Bist-arastirma/2026-11-14/makro/RAPOR.md (10 yıl, 257 hisse, 21 makro seri).
- Az sayıda sağlam hisse↔makro ilişkisi var (altın madencileri↔altın, TUPRS/AYGAZ↔petrol, EREGL/KRDMD↔çelik);
  THYAO/PGSUS/TAVHL↔petrol 'son yıllarda' (2022 sonrası) var, 2017-21'de yoktu.
- Etki aynı gün / ertesi sabah açılışta fiyatlanıyor; sonrasında sürüklenme YOK → al-sat sinyali değil.
- Makro rejim filtresi v3'ü GEÇMEDİ → filtre olarak kullanılmaz.

Veri: tek yf.download (günlük), önbellek makro.json (30 dk). Sabah 'gece' hesabı için günde bir kez küçük bir
saatlik indirme (vadeli kontratlar). Her şey try/except + zaman aşımı: hata olursa son veri kullanılır, tarama düşmez.
"""
import json, os, threading, time
from datetime import datetime, timedelta, timezone

DOSYA = "makro.json"
ONBELLEK_DK = 30
ZAMAN_ASIMI = 40          # sn: indirme bundan uzun sürerse beklenmez (son veri kullanılır)
TR = timezone(timedelta(hours=3))

# (anahtar, yfinance kodu, ad, birim ('%' ya da 'bp'), 'büyük hareket' eşiği (2017-21 günlerinin en büyük %10'u; None = yok),
#  fiyat birimi, panoda göster)
SERILER = [
    ("BRENT", "BZ=F", "Brent petrol", "%", 3.4, " $", True),
    ("WTI", "CL=F", "WTI petrol", "%", 3.4, " $", False),          # sadece Brent'in çapraz kontrolü
    ("ALTIN", "GC=F", "Altın (ons)", "%", 1.4, " $", True),
    ("CELIK", "SLX", "Çelik (SLX)", "%", 3.2, " $", True),
    ("BAKIR", "HG=F", "Bakır", "%", None, " $", True),
    ("DOGALGAZ", "NG=F", "Doğalgaz (ABD)", "%", None, " $", True),
    ("USDTRY", "TRY=X", "Dolar/TL", "%", 1.7, "", True),
    ("EURTRY", "EURTRY=X", "Euro/TL", "%", None, "", False),       # sadece dolar/TL'nin çapraz kontrolü
    ("DXY", "DX-Y.NYB", "Dolar endeksi", "%", 0.6, "", True),
    ("US10Y", "^TNX", "ABD 10 yıllık faiz", "bp", 6, "", True),
    ("VIX", "^VIX", "VIX (korku endeksi)", "%", 12.5, "", True),
    ("SP500", "^GSPC", "S&P 500", "%", 1.6, "", True),
    ("ES", "ES=F", "S&P vadelisi", "%", 1.0, "", False),          # sadece sabah 'gece' hesabı
    ("DAX", "^GDAXI", "DAX (Almanya)", "%", None, "", True),
    ("EEM", "EEM", "Gelişen ülke ETF", "%", None, " $", True),
    ("TUR", "TUR", "Türkiye ETF (TUR)", "%", 3.3, " $", True),
]
SERI = {s[0]: s for s in SERILER}
GECE_VADELI = ["BZ=F", "CL=F", "GC=F", "ES=F", "HG=F"]   # gece işlem gören vadeliler (saatlik)

# Beyaz liste (araştırmadan, 'son 2 yıl' etkisi): makro 'birim' kadar hareket edince hissenin ENDEKSTEN farkı (puan).
# katman 1 = 10 yılın iki yarısında da aynı yönde + haftalıkta da var; 2 = 'son yıllarda' (2017-21'de yoktu, ortama bağlı).
# Dolar/TL çiftleri bilerek yok (yönetilen kur → ölçüm oynak). Yılda bir yenilenir (CLAUDE.md, Periyodik bakım).
DUYARLI = {
    "TRALT": ("ALTIN", 10, 7.8, 1),
    "TRMET": ("ALTIN", 10, 7.7, 1),
    "TRENJ": ("ALTIN", 10, 7.2, 1),
    "TUPRS": ("BRENT", 10, 3.6, 1),
    "AYGAZ": ("BRENT", 10, 2.4, 1),
    "EREGL": ("CELIK", 10, 2.3, 1),
    "KRDMD": ("CELIK", 10, 3.2, 1),
    "KRDMA": ("CELIK", 10, 3.4, 1),
    "ENKAI": ("TUR", 5, -1.7, 1),      # son 2 yılda zayıfladı (t −1,2)
    "THYAO": ("BRENT", 10, -2.0, 2),
    "PGSUS": ("BRENT", 10, -2.5, 2),
    "TAVHL": ("BRENT", 10, -2.4, 2),
    "ISDMR": ("CELIK", 10, 1.8, 2),
}
KISA = {"BRENT": "petrol", "ALTIN": "altın", "CELIK": "çelik", "TUR": "Türkiye ETF'i"}
ETKI_MIN = 0.3   # puan: bundan küçük beklenen etki yazılmaz
NOT_KISA = "Etki genelde aynı gün ya da ertesi sabah açılışta fiyatlanır; sonrasında sürmesi beklenmez. Al-sat sinyali değildir."


# ----------------------------- yardımcılar -----------------------------
def _yz(x, nd=1):
    """+%1,2 / −%0,4 biçimi (işaretli)."""
    if x is None:
        return "—"
    return ("+" if x >= 0 else "−") + "%" + f"{abs(x):.{nd}f}".replace(".", ",")


def _sayi(x):
    if x is None:
        return "—"
    nd = 0 if abs(x) >= 1000 else (1 if abs(x) >= 100 else 2)
    s = f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def _deg(anahtar, x):
    """Değişimi birimine göre yaz: '%1,2' ya da '+5 bp' (işaretsiz yüzde, yön ok ile)."""
    if x is None:
        return "—"
    if SERI[anahtar][3] == "bp":
        return f"{'+' if x >= 0 else '−'}{abs(x):.0f} bp"
    return "%" + f"{abs(x):.1f}".replace(".", ",")


def _ok(x):
    return "▲" if (x or 0) >= 0 else "▼"


def _simdi():
    return datetime.now(TR)


def _zamanli(f, sure):
    """f()'i ayrı (daemon) iş parçacığında çalıştırır; 'sure' sn'de bitmezse None döner (tarama beklemez)."""
    sonuc = {}

    def calis():
        try:
            sonuc["v"] = f()
        except Exception as e:   # noqa: BLE001
            sonuc["e"] = e
    th = threading.Thread(target=calis, daemon=True)
    th.start()
    th.join(sure)
    if th.is_alive():
        raise TimeoutError("makro indirme zaman aşımı")
    if "e" in sonuc:
        raise sonuc["e"]
    return sonuc.get("v")


def oku(yol=DOSYA):
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _yaz(veri, yol=DOSYA):
    try:
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


# ----------------------------- indirme -----------------------------
def _gunluk_indir():
    import yfinance as yf
    kodlar = [s[1] for s in SERILER]
    d = yf.download(kodlar, period="1mo", interval="1d", progress=False, group_by="ticker", auto_adjust=False,
                    threads=True, timeout=15)
    out = {}
    for a, kod, *_ in SERILER:
        try:
            c = d[kod]["Close"].dropna()
        except Exception:
            continue
        if len(c) < 2:
            continue
        son, onc = float(c.iloc[-1]), float(c.iloc[-2])
        bes = float(c.iloc[-6]) if len(c) >= 6 else None
        if SERI[a][3] == "bp":   # ^TNX yüzde cinsinden (4,15 = %4,15) → değişim baz puan
            g, g5 = (son - onc) * 100, ((son - bes) * 100 if bes is not None else None)
        else:
            g, g5 = (son / onc - 1) * 100, ((son / bes - 1) * 100 if bes else None)
        out[a] = {"son": round(son, 4), "g": round(g, 2), "g5": round(g5, 2) if g5 is not None else None,
                  "tarih": str(c.index[-1].date())}
    return out


def _supheli_isaretle(s):
    """Vadeli kontrat değişimi / donuk kur: çapraz kontrol tutmazsa hareket 'şüpheli' (yorum yapılmaz)."""
    b, w = s.get("BRENT"), s.get("WTI")
    if b and w and b.get("g") is not None and w.get("g") is not None and abs(b["g"]) >= 3 and abs(w["g"]) < 1:
        b["supheli"] = "kontrat değişimi olabilir (WTI aynı yönde oynamadı)"
    u, e = s.get("USDTRY"), s.get("EURTRY")
    if u and u.get("g") is not None and abs(u["g"]) > 5:
        if not (e and e.get("g") is not None and e["g"] * u["g"] > 0 and abs(e["g"]) > 2):
            u["supheli"] = "veri hatası olabilir (Euro/TL aynı yönde oynamadı)"
    return s


def indir(zorla=False, yol=DOSYA, simdi=None):
    """Günlük makro verisi (önbellek 30 dk). Hata/zaman aşımında son veri 'taze': False ile döner; ASLA istisna fırlatmaz."""
    simdi = simdi or _simdi()
    eski = oku(yol)
    try:
        t = datetime.fromisoformat(eski["t"]) if eski.get("t") else None
    except Exception:
        t = None
    if not zorla and t and eski.get("s") and (simdi - t).total_seconds() < ONBELLEK_DK * 60:
        eski["taze"] = True
        return eski
    try:
        _t0 = time.time()
        s = _zamanli(_gunluk_indir, ZAMAN_ASIMI)
        if not s or len(s) < 5:
            raise ValueError("eksik veri")
        yeni = dict(eski)
        yeni.update({"t": simdi.isoformat(timespec="seconds"), "s": _supheli_isaretle(s), "hata": None,
                     "sure": round(time.time() - _t0, 1)})
        _yaz({k: v for k, v in yeni.items() if k != "taze"}, yol)
        yeni["taze"] = True
        return yeni
    except Exception as e:
        eski = dict(eski)
        eski["taze"] = False
        eski["hata_simdi"] = type(e).__name__
        return eski


def _gece_indir(ref_utc):
    import yfinance as yf
    d = yf.download(GECE_VADELI, period="5d", interval="60m", progress=False, group_by="ticker", auto_adjust=False,
                    threads=True, timeout=15)
    out = {}
    for kod in GECE_VADELI:
        try:
            c = d[kod]["Close"].dropna()
            c.index = c.index.tz_convert("UTC") if c.index.tz is not None else c.index.tz_localize("UTC")
            onc = c[c.index <= ref_utc]
            if not len(onc) or (ref_utc - onc.index[-1]).total_seconds() > 6 * 3600:
                continue
            out[kod] = round((float(c.iloc[-1]) / float(onc.iloc[-1]) - 1) * 100, 2)
        except Exception:
            continue
    return out


def _onceki_is_gunu(g):
    g = g - timedelta(days=1)
    while g.weekday() >= 5:
        g -= timedelta(days=1)
    return g


def gece(veri, simdi=None):
    """Dünkü BIST kapanışından (18:00) şimdiye kadar dünyada olanlar: {anahtar: değişim}. Vadeliler saatlik veriden,
    gece işlem görmeyenler (VIX, ABD faizi, SLX, TUR, dolar endeksi) dünkü (BIST kapanışından sonra biten) seanstan.
    Veri taze değilse None (eski veriyle sabah mesajı yanlış yönlendirir → hiç gönderilmez)."""
    simdi = simdi or _simdi()
    if not veri or not veri.get("taze") or not veri.get("s"):
        return None
    ref = datetime.combine(_onceki_is_gunu(simdi.date()), datetime.min.time()).replace(hour=18, tzinfo=TR)
    try:
        vad = _zamanli(lambda: _gece_indir(ref.astimezone(timezone.utc)), ZAMAN_ASIMI) or {}
    except Exception:
        vad = {}
    kod2a = {s[1]: s[0] for s in SERILER}
    out = {kod2a[k]: v for k, v in vad.items()}
    s = veri["s"]
    for a in ("VIX", "US10Y", "CELIK", "TUR", "DXY", "SP500", "USDTRY"):
        x = s.get(a)
        if x and x.get("g") is not None and a not in out:
            out[a] = x["g"]
    for a in ("BRENT", "ALTIN", "ES"):   # saatlik alınamadıysa günlük (bugünkü) değişim
        if a not in out and s.get(a) and s[a].get("g") is not None:
            out[a] = s[a]["g"]
    sup = {}
    if "BRENT" in out and "WTI" in out and abs(out["BRENT"]) >= 3 and abs(out["WTI"]) < 1:
        sup["BRENT"] = True
    if (s.get("USDTRY") or {}).get("supheli"):
        sup["USDTRY"] = True
    return {"d": out, "sup": sup, "t": simdi.isoformat(timespec="minutes")}


# ----------------------------- duyarlılık -----------------------------
def buyuk(anahtar, x):
    esik = SERI[anahtar][4] if anahtar in SERI else None
    return esik is not None and x is not None and abs(x) >= esik


def etkilenenler(hareket, sadece_buyuk=True, supheli=None, kodlar=None):
    """hareket: {makro: değişim %}. Beyaz listedeki hisselerin geçmiş ortalamaya göre beklenen endeksten farkı.
    Döner: [{kod, m, puan, katman, x}] (|puan| büyükten küçüğe)."""
    supheli = supheli or {}
    out = []
    for kod, (m, birim, etki, katman) in DUYARLI.items():
        if kodlar is not None and kod not in kodlar:
            continue
        x = hareket.get(m)
        if x is None or supheli.get(m) or (sadece_buyuk and not buyuk(m, x)):
            continue
        p = etki * x / birim
        if abs(p) >= ETKI_MIN:
            out.append({"kod": kod, "m": m, "puan": round(p, 1), "katman": katman, "x": x})
    return sorted(out, key=lambda e: -abs(e["puan"]))


def _puan(p):
    return ("+" if p >= 0 else "−") + f"{abs(p):.1f}".replace(".", ",")


def _aralik(L):
    a, b = sorted((e["puan"] for e in L), key=abs)[0], sorted((e["puan"] for e in L), key=abs)[-1]
    return f"≈ {_puan(a)} puan" if abs(a - b) < 0.05 else f"≈ {_puan(a)}…{_puan(b)} puan"


def gruplar(et):
    """Etkilenenleri (makro, yön) grubuna toplar: [(m, lehine?, [kayıt...])]."""
    g = {}
    for e in et:
        g.setdefault((e["m"], e["puan"] >= 0), []).append(e)
    return sorted(g.items(), key=lambda kv: -max(abs(e["puan"]) for e in kv[1]))


def _hareket_sozu(m, x):
    return f"{KISA.get(m, SERI[m][2])} {_deg(m, x)} {'yükseldi' if x >= 0 else 'düştü'}"


def etki_satirlari(et, html=True):
    """Telegram satırları: '🟢▲ THYAO, PGSUS — petrol %5,3 düştü (≈ +1,1…+1,3 puan, son yıllarda)'."""
    out = []
    for (m, leh), L in gruplar(et):
        son = ", son yıllarda" if all(e["katman"] == 2 for e in L) else ""
        kod = ", ".join((f"<b>{e['kod']}</b>" if html else e["kod"]) for e in L)
        out.append(f"{'🟢▲' if leh else '🔴▼'} {kod} — {_hareket_sozu(m, L[0]['x'])} ({_aralik(L)}{son})")
    return out


# ----------------------------- Telegram -----------------------------
def sabah_mesaji(gc, takvim_satirlari=None, tarih=None):
    """☀️ Gece dünyada: en az bir 'büyük' gece hareketi ya da S&P vadelisi ≥ ±%1 varsa (ya da takvimde bugün önemli olay varsa).
    Veri yoksa / bayatsa makro kısmı hiç yazılmaz. Döner: metin ya da None (sus)."""
    takvim_satirlari = takvim_satirlari or []
    parca = []
    if gc and gc.get("d"):
        d, sup = gc["d"], gc.get("sup") or {}
        b = [a for a in ("BRENT", "ALTIN", "CELIK", "USDTRY", "DXY", "US10Y", "VIX", "SP500", "TUR")
             if a in d and buyuk(a, d[a]) and not sup.get(a)]
        es = d.get("ES")
        if b or (es is not None and abs(es) >= 1):
            sat = [f"{SERI[a][2]} {_ok(d[a])} {_deg(a, d[a])} {'yükseldi' if d[a] >= 0 else 'düştü'}" for a in b]
            ek = [f"{ad} {_ok(d[a])} {_deg(a, d[a])}" for a, ad in (("ES", "ABD vadelisi"), ("TUR", "TUR ETF"))
                  if a in d and a not in b]
            if ek:
                sat.append(" · ".join(ek))
            et = etkilenenler(d, supheli=sup)
            if et:
                sat.append("Etkilenebilecekler (geçmiş ortalama, endeksten fark):")
                sat += etki_satirlari(et)
            parca.append("\n".join(sat))
    if not parca and not takvim_satirlari:
        return None
    tarih = tarih or _simdi().strftime("%d.%m")
    bas = (f"📊 ☀️ <b>Gece dünyada</b> ({tarih}, dünkü BIST kapanışından beri)" if parca
           else f"📅 <b>Bugün takvimde</b> ({tarih})")
    son = []
    if parca:
        son.append(f"<i>ℹ️ Yön okları fiyatın yönüdür (iyi/kötü değil). {NOT_KISA}</i>")
    if takvim_satirlari:
        son.append("<i>📅 Takvim bilgidir, yön söylemez; 🚀 AL/SAT kurallarını değiştirmez.</i>")
    return "\n\n".join([bas] + parca + ["\n".join(takvim_satirlari)] * bool(takvim_satirlari) + son)


def aksam_satiri(veri, pf_kodlar, by_kod=None, xu_gun=None):
    """Akşam portföy özeti: portföyde beyaz liste hissesi varsa ve onun makrosu bugün büyük oynadıysa tek satır."""
    if not veri or not veri.get("taze") or not veri.get("s"):
        return None
    h = {a: x.get("g") for a, x in veri["s"].items() if x.get("g") is not None}
    sup = {a: True for a, x in veri["s"].items() if x.get("supheli")}
    et = etkilenenler(h, supheli=sup, kodlar=set(pf_kodlar))
    if not et:
        return None
    by_kod = by_kod or {}
    mak = {}
    for (m, leh), L in gruplar(et):   # aynı makro tek kez yazılır, altında hisseler
        kods = []
        for e in L:
            g = (by_kod.get(e["kod"]) or {}).get("degisim")
            kods.append(f"<b>{e['kod']}</b>" + (f" {_yz(g)}" if g is not None else ""))
        mak.setdefault(m, []).append(f"{', '.join(kods)} {'🟢▲ lehine' if leh else '🔴▼ aleyhine'} ({_aralik(L)})")
    parca = [f"{SERI[m][2]} {_ok(veri['s'][m]['g'])} {_deg(m, veri['s'][m]['g'])} → " + ", ".join(v) for m, v in mak.items()]
    xu = f" · BIST 100 {_yz(xu_gun)}" if xu_gun is not None else ""
    return ("🌍 <b>Bugün dünya</b>" + xu + ": " + "; ".join(parca) +
            ".\n     <i>Geçmiş ortalama, endeksten fark; tek günde asıl hareketi çoğu zaman başka haber belirler. "
            "Al-sat sinyali değildir.</i>")


# ----------------------------- pano -----------------------------
def pano_veri(veri, simdi=None):
    """index.html için küçük JSON: seriler, bugünkü büyük hareketten etkilenebilecekler, beyaz liste."""
    duy = {k: [m, b, e, kat, SERI[m][2]] for k, (m, b, e, kat) in DUYARLI.items()}
    if not veri or not veri.get("s"):
        return {"yok": True, "duy": duy, "kisa": KISA}
    s = veri["s"]
    sat = []
    for a, kod, ad, bir, esik, fb, goster in SERILER:
        x = s.get(a)
        if not goster or not x:
            continue
        sat.append({"a": a, "ad": ad, "son": x.get("son"), "g": x.get("g"), "g5": x.get("g5"), "bp": bir == "bp",
                    "fb": fb.strip(), "b": bool(buyuk(a, x.get("g")) and not x.get("supheli")), "sup": x.get("supheli"),
                    "tr": x.get("tarih")})
    h = {a: x.get("g") for a, x in s.items() if x.get("g") is not None}
    sup = {a: True for a, x in s.items() if x.get("supheli")}
    et = etkilenenler(h, supheli=sup)
    return {"t": veri.get("t"), "taze": bool(veri.get("taze")), "s": sat,
            "et": [{"kod": e["kod"], "m": e["m"], "p": e["puan"], "k": e["katman"], "x": e["x"]} for e in et],
            "duy": duy, "kisa": KISA}


if __name__ == "__main__":   # elle deneme: python makro.py
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    v = indir(zorla=True)
    print(f"indirme {time.time() - t0:.1f} sn, taze={v.get('taze')}, {len(v.get('s') or {})} seri")
    for a, x in (v.get("s") or {}).items():
        print(f"  {a:9s} {x}")
