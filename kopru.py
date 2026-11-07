"""Kumbara köprüsü: portföyü ve güncel fiyatları kullanıcının özel Drive dosyasına yazan Apps Script adresine gönderir.
Kumbara (claude.ai artifact) internetten veri çekemez, Drive bağlayıcısıyla bu dosyayı okur.

Adres KUMBARA_KOPRU_URL secret'ından gelir; yoksa (arkadaş kopyaları dahil) hiçbir şey yapılmaz.
DİKKAT: Actions logları ve durum.json herkese açık. Buradan log'a yalnız sabit durum metni döner:
hisse kodu, adet, fiyat, adres ya da hata gövdesi ASLA yazılmaz. Tarama bu modül yüzünden bozulmamalı (çağıran try/except'li).
"""
import json
import os
import time
import urllib.request

TUR = "kumbara-portfoy-v1"
ONS_GRAM = 31.1035


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


def paket(pf, fiyatlar, kur, zaman):
    hisseler = [{"kod": k, "adet": _sayi(p["adet"]), "maliyet": _sayi(p["maliyet"]), "fiyat": _sayi(fiyatlar.get(k))}
                for k, p in sorted(pf.items())]
    return {"tur": TUR, "zaman": zaman, "hisseler": hisseler, "kur": kur}


def gonder(pf, fiyatlar):
    """Log'a yazılabilir tek satırlık durum döner; adres yoksa None."""
    url = os.environ.get("KUMBARA_KOPRU_URL", "").strip()
    if not url:
        return None
    # Boş portföy yalnız panoda gerçekten boşaltılmışsa gider; okunamayan variable Kumbara'daki son listeyi silmesin
    if not pf and os.environ.get("PORTFOY", "").strip() != "[]":
        return "Kumbara köprüsü: portföy okunamadı, son kayıt korundu."
    zaman = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    govde = json.dumps(paket(pf, fiyatlar, kur_al(zaman), zaman), ensure_ascii=False).encode("utf-8")
    try:
        # Apps Script POST'u işler, sonra sonucu 302 ile başka adresten verir (urllib GET olarak izler)
        ist = urllib.request.Request(url, data=govde, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(ist, timeout=30) as r:
            ok = json.loads(r.read().decode("utf-8", "replace")).get("ok") is True
        return "Kumbara köprüsü: yazıldı." if ok else "Kumbara köprüsü: Drive yazımı reddedildi."
    except Exception as e:   # metni yazma: adres içerebilir
        return f"Kumbara köprüsü: gönderilemedi ({type(e).__name__})."
