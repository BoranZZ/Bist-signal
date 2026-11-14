# -*- coding: utf-8 -*-
"""📅 Ekonomik takvim — SADECE BİLGİ (AL/SAT, iz stop, piyasa filtresi, İşlem Odası DEĞİŞMEZ). Ağ KULLANMAZ: yalnız takvim.json.

Araştırma: Documents/Bist-arastirma/2026-11-14/takvim/RAPOR.md (2016-26, 689 olay).
- BIST 100'ü ölçülebilir oynatan tek düzenli olay Fed kararı (ertesi gün olağanın ~1,31 katı). Seçim 1,54× (az olay), TÜİK ~1,35× (2022 sonrası).
- TCMB, ABD verileri, ECB ortalamada olağan günden ayırt edilemiyor; hiçbir olay yönü rastgeleden sık çevirmiyor → metinler YÖN SÖYLEMEZ.
- 'Olay öncesi AL'i atla/bekle' filtresi v3'ü GEÇMEDİ.
Bakım: takvim.json Claude tarafından yenilenir (takvim_kontrol.py ile resmî sayfalarla karşılaştırılır); `yenile_hatirlat`
tarihi geldiğinde ya da son kesin tarihe 45 gün kalınca haftalık özette hatırlatma çıkar.
"""
import json
from datetime import date, timedelta

DOSYA = "takvim.json"
BAYRAK = {"TR": "🇹🇷", "ABD": "🇺🇸", "AB": "🇪🇺"}
GUN = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
AY = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
YENILE_GUN = 45
TCMB_NOT = "ortalamada olağan gün gibi; sürpriz kararlarda tek gün ±%3-5 görüldü (22.06.2023 +%4,7 · 22.10.2026 −%3,1)"


def yukle(yol=DOSYA):
    """takvim.json → dict; yoksa/bozuksa boş takvim (pano ve Telegram sessizce gizler)."""
    try:
        with open(yol, encoding="utf-8") as f:
            J = json.load(f)
        J["olaylar"] = sorted((o for o in J.get("olaylar", []) if o.get("t")), key=lambda o: (o["t"], o.get("saat", "")))
        return J
    except Exception:
        return {"olaylar": []}


def _d(s):
    return date.fromisoformat(s)


def sonraki_is_gunu(g):
    g = g + timedelta(days=1)
    while g.weekday() >= 5:
        g += timedelta(days=1)
    return g


def etki_gunu(o):
    """Olayın BIST'e yansıdığı gün: seans içindeyse o gün (hafta sonuysa sonraki iş günü), seans sonrasıysa sonraki iş günü.
    (Resmî tatiller bilinmiyor — bilinen sınır.)"""
    g = _d(o["t"])
    return sonraki_is_gunu(g) if (o.get("seans") == "sonra" or g.weekday() >= 5) else g


def tarih_tr(g):
    return f"{GUN[g.weekday()]} {g.day:02d} {AY[g.month - 1]}"


def tipik_metin(J, tur, olagan):
    """'Tipik hareket' (dürüst sürüm): son 60 günün ortalama mutlak günlük hareketi × olay türünün katı; kat sadece Fed/seçim/TÜİK."""
    kat = (J.get("tipik_goster") or {}).get(tur)
    if kat:
        k = f"{kat:.2f}".replace(".", ",")
        if olagan:
            return (f"geçmişte o gün olağanın ~{k} katı oynak (tipik ±%{olagan * kat:.1f}; olağan ±%{olagan:.1f})").replace(".", ",")
        return f"geçmişte o gün olağanın ~{k} katı oynak"
    if tur == "TCMB":
        return TCMB_NOT
    return "geçmişte BIST'i belirgin oynatmadı"


def _bas(m):
    return m[:1].upper() + m[1:]


def _ad(o):
    return f"{BAYRAK.get(o.get('ulke'), '')} {o['ad']}".strip() + ("" if o.get("dogrulandi", True) else " (tarih kesinleşmedi)")


# ----------------------------- Telegram -----------------------------
def sabah_satirlari(J, bugun, olagan=None, min_onem=2):
    """Günün ilk taraması: bugün olan (★★+) ve dün akşam (seans sonrası) olup etkisi bugün olan olaylar."""
    out = []
    for o in J.get("olaylar", []):
        if o.get("onem", 1) < min_onem:
            continue
        t, e = _d(o["t"]), etki_gunu(o)
        if t == bugun:
            if o.get("seans") == "sonra":
                out.append(f"📅 Bu akşam {o.get('saat', '')} {_ad(o)} — BIST kapandıktan sonra; etkisi yarın görülür. "
                           f"{_bas(tipik_metin(J, o['tur'], olagan))}.")
            else:
                out.append(f"📅 Bugün {o.get('saat', '')} {_ad(o)} — {tipik_metin(J, o['tur'], olagan)}. O gün fiyat sert oynayabilir; yön söylemez.")
        elif t < bugun and e == bugun:
            out.append(f"📅 {'Dün akşam' if (bugun - t).days == 1 else tarih_tr(t) + ' akşamı'} {o.get('saat', '')} {_ad(o)} açıklandı — "
                       f"bugün BIST oynak olabilir: {tipik_metin(J, o['tur'], olagan)}. Yön söylemez.")
    return out


def al_notu(J, bugun, min_onem=3):
    """🚀 AL satırı/başlığı notu: önemli olay bugün akşam (seans sonrası) ya da sonraki iş günü varsa (0-1 gün kala)."""
    yarin = sonraki_is_gunu(bugun)
    out = []
    for o in J.get("olaylar", []):
        if o.get("onem", 1) < min_onem:
            continue
        t = _d(o["t"])
        if t == bugun and o.get("seans") == "sonra":
            out.append(f"bu akşam {o.get('saat', '')} {_ad(o)} var (etkisi yarın)")
        elif t == yarin:
            out.append(f"{'yarın' if (yarin - bugun).days == 1 else tarih_tr(yarin)} {o.get('saat', '')} {_ad(o)} var")
    if not out:
        return None
    return ("📅 " + _bas("; ".join(out)) + ": o gün fiyat sert oynayabilir. Geçmişte olay öncesi gelen 🚀 AL'ler daha kötü "
            "sonuç vermedi; bilgi notudur.")


def olay_sonrasi(J, bugun, xu_gun, olagan=None, min_onem=2):
    """Akşam: etkisi bugün olan olay(lar) için BIST 100'ün tepkisi. xu_gun = BIST 100 bugünkü değişim (%)."""
    if xu_gun is None:
        return []
    out = []
    for o in J.get("olaylar", []):
        if o.get("onem", 1) < min_onem or etki_gunu(o) != bugun:
            continue
        ne = "dün akşamki " if _d(o["t"]) < bugun else ""
        kat = f" (olağan bir günün ~{abs(xu_gun) / olagan:.1f} katı)".replace(".", ",") if olagan else ""
        out.append(f"📊 Olay sonrası: {ne}{_ad(o)} — BIST 100 {'🟢▲' if xu_gun >= 0 else '🔴▼'} "
                   f"%{abs(xu_gun):.1f}".replace(".", ",") + kat)
    return out


def son_kesin(J):
    k = [o["t"] for o in J.get("olaylar", []) if o.get("dogrulandi", True)]
    return max(k) if k else None


def bakim_notu(J, bugun):
    """Haftalık özet: takvim yenileme zamanı geldiyse (yenile_hatirlat ya da son kesin tarihe ≤45 gün)."""
    if not J.get("olaylar"):
        return None
    sk = son_kesin(J)
    hat = J.get("yenile_hatirlat")
    neden = None
    if sk and (_d(sk) - bugun).days <= YENILE_GUN:
        neden = f"ekonomik takvimin kesin tarihleri {tarih_tr(_d(sk))} {_d(sk).year}'de bitiyor"
    elif hat and bugun >= _d(hat):
        neden = "yeni resmî takvimler (TÜİK / TCMB / Fed) yayımlanmış olabilir"
    if not neden:
        return None
    return f"📅 <b>Takvimi yenile:</b> {neden}. Claude'a \"takvimi yenile\" de."


# ----------------------------- pano -----------------------------
def pano_veri(J, bugun, olagan=None, gun=16):
    """index.html için: dünden itibaren ~16 gün (istemci kendi tarihine göre 7 günü süzer) + sıradaki ilk olay."""
    if not J.get("olaylar"):
        return None
    bas, son = bugun - timedelta(days=1), bugun + timedelta(days=gun)
    sec = [o for o in J["olaylar"] if bas <= _d(o["t"]) <= son]
    sonra = [o for o in J["olaylar"] if _d(o["t"]) > son][:1]
    o2 = []
    for o in sec + sonra:
        e = etki_gunu(o)
        o2.append({"t": o["t"], "s": o.get("saat", ""), "u": BAYRAK.get(o.get("ulke"), ""), "a": o["ad"], "o": o.get("onem", 1),
                   "sn": o.get("seans") == "sonra", "e": e.isoformat(), "d": bool(o.get("dogrulandi", True)),
                   "n": tipik_metin(J, o["tur"], olagan)})
    return {"o": o2, "ol": round(olagan, 2) if olagan else None, "son": J.get("gecerli_son"), "sk": son_kesin(J)}
