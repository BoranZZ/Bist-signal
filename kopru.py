"""Kumbara köprüsü: portföyü ve güncel fiyatları kullanıcının özel Drive dosyasına yazan Apps Script adresine gönderir.
Kumbara (claude.ai artifact) internetten veri çekemez, Drive bağlayıcısıyla bu dosyayı okur.

Adres KUMBARA_KOPRU_URL secret'ından gelir; yoksa (arkadaş kopyaları dahil) hiçbir şey yapılmaz.
DİKKAT: Actions logları ve durum.json herkese açık. Buradan log'a yalnız sabit durum metni döner:
hisse kodu, adet, fiyat, adres ya da hata gövdesi ASLA yazılmaz. Tarama bu modül yüzünden bozulmamalı (çağıran try/except'li).
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

TUR = "kumbara-portfoy-v1"
ONS_GRAM = 31.1035
GITHUB_API = "https://api.github.com"
SATIS_SINIR = 300   # Apps Script 50.000 karakterden uzununu reddeder


def _sayi(x, basamak=4):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return round(x, basamak) if x > 0 and x == x and x != float("inf") else None


def kur_al(zaman):
    """Dolar, euro, gram altın (ons × dolar ÷ 31,1035; serbest piyasadan biraz farklı olabilir). Hata: None, kur eski kalır."""
    try:
        import yfinance as yf
        d = yf.download(["USDTRY=X", "EURTRY=X", "GC=F"], period="5d", interval="1d", group_by="ticker",
                        auto_adjust=True, progress=False, threads=False)
        son = lambda k: float(d[k]["Close"].dropna().iloc[-1])
        usd, eur = son("USDTRY=X"), son("EURTRY=X")
        kur = {"USD": _sayi(usd), "EUR": _sayi(eur), "GRAM": _sayi(son("GC=F") * usd / ONS_GRAM, 2), "zaman": zaman}
        return kur if kur["USD"] and kur["EUR"] and kur["GRAM"] else None
    except Exception:
        return None


def satis_temizle(kayitlar):
    """Defterden yalnız para hesabı için gerekenler; not, plan ve duygu gibi kişisel alanlar Drive'a bile gitmez."""
    tarih = lambda x: x if isinstance(x, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", x) else ""
    cikti = []
    for r in kayitlar if isinstance(kayitlar, list) else []:
        if not isinstance(r, dict):
            continue
        i, h = r.get("i"), r.get("h")
        n, m, f = _sayi(r.get("n")), _sayi(r.get("m")), _sayi(r.get("f"))
        if not (isinstance(i, str) and re.fullmatch(r"[\w-]{1,40}", i) and isinstance(h, str)
                and re.fullmatch(r"[A-Z0-9]{1,10}", h) and n and m and f):
            continue
        cikti.append({"i": i, "h": h, "a": tarih(r.get("a")), "s": tarih(r.get("s")), "n": n, "m": m, "f": f,
                      "k": _sayi(r.get("k"), 2) or 0})
    cikti.sort(key=lambda x: x["s"])
    return cikti[-SATIS_SINIR:]


def _degisken_oku(ad):
    """Actions variable'ını API ile okur; workflow env'ine KONMAZ, çünkü env değerleri herkese açık loga düşer.
    Metni döner; variable hiç yoksa "" (404); anahtar yoksa ya da okunamazsa None. Hata metni bilerek yazılmaz."""
    anahtar = os.environ.get("KUMBARA_DEFTER_ANAHTAR", "").strip()
    depo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not anahtar or not depo:
        return None
    ist = urllib.request.Request(f"{GITHUB_API}/repos/{depo}/actions/variables/{ad}", headers={
        "Authorization": f"Bearer {anahtar}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.urlopen(ist, timeout=20) as r:
            return json.loads(r.read().decode("utf-8", "replace"))["value"]
    except urllib.error.HTTPError as e:
        return "" if e.code == 404 else None
    except Exception:
        return None


def degiskenleri_yukle():
    """Portföy ve alarmları loga düşmeden okuyup yalnız bu işlemin ortamına koyar.
    Env zaten doluysa (anahtarsız kopyalar) dokunmaz. Dönüş: True tamam, None anahtar yok, False okunamadı."""
    if not os.environ.get("KUMBARA_DEFTER_ANAHTAR", "").strip() or not os.environ.get("GITHUB_REPOSITORY", "").strip():
        return None
    tamam = True
    for ad in ("PORTFOY", "ALARMLAR"):
        if os.environ.get(ad, "").strip():
            continue
        deger = _degisken_oku(ad)
        if deger is None:
            tamam = False
        else:
            os.environ[ad] = deger
    return tamam


def satislar_al():
    """Anahtar yoksa ya da okunamazsa None: Kumbara son bildiği satışları korur."""
    ham = _degisken_oku("DEFTER")
    if ham is None:
        return None
    if not ham:
        return []   # defter henüz hiç kaydedilmemiş
    try:
        return satis_temizle(json.loads(ham).get("k"))
    except Exception:
        return None


def paket(pf, fiyatlar, kur, zaman, satislar=None):
    hisseler = [{"kod": k, "adet": _sayi(p["adet"]), "maliyet": _sayi(p["maliyet"]), "fiyat": _sayi(fiyatlar.get(k))}
                for k, p in sorted(pf.items())]
    o = {"tur": TUR, "zaman": zaman, "hisseler": hisseler, "kur": kur}
    if satislar is not None:
        o["satislar"] = satislar
    return o


def gonder(pf, fiyatlar):
    """Log'a yazılabilir tek satırlık durum döner; adres yoksa None."""
    url = os.environ.get("KUMBARA_KOPRU_URL", "").strip()
    if not url:
        return None
    # Boş portföy yalnız panoda gerçekten boşaltılmışsa gider; okunamayan variable Kumbara'daki son listeyi silmesin
    if not pf and os.environ.get("PORTFOY", "").strip() != "[]":
        return "Kumbara köprüsü: portföy okunamadı, son kayıt korundu."
    zaman = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    satislar = satislar_al()
    ek = " Satış defteri okunamadı." if satislar is None and os.environ.get("KUMBARA_DEFTER_ANAHTAR", "").strip() else ""
    govde = json.dumps(paket(pf, fiyatlar, kur_al(zaman), zaman, satislar), ensure_ascii=False).encode("utf-8")
    try:
        # Apps Script POST'u işler, sonra sonucu 302 ile başka adresten verir (urllib GET olarak izler)
        ist = urllib.request.Request(url, data=govde, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(ist, timeout=30) as r:
            ok = json.loads(r.read().decode("utf-8", "replace")).get("ok") is True
        return ("Kumbara köprüsü: yazıldı." if ok else "Kumbara köprüsü: Drive yazımı reddedildi.") + ek
    except Exception as e:   # metni yazma: adres içerebilir
        return f"Kumbara köprüsü: gönderilemedi ({type(e).__name__})."
