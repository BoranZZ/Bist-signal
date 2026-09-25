"""KAP bildirimleri (bilgi amaçlı): kap.org.tr'nin kendi sitesinin kullandığı bildirim sorgusu (tek POST ile tüm
şirketler). Özel durum açıklamaları (ODA) ve finansal raporlar (FR); tekrar eden/teknik konular ayıklanır.
Haberin çoğu fiyata hızla yansır — sinyal değil, bağlam."""
import json
from html import escape

import pandas as pd
import requests

KAP_CACHE = "kap.json"
KAP_URL = "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria"
KAP_LINK = "https://www.kap.org.tr/tr/Bildirim/"
SORGU_GUN = 7        # her taramada son 7 gün (sorgu en çok 2000 kayıt döndürür; ODA+FR 7 günde ~500)
SAKLA_GUN = 45       # önbellekte hisse başı bildirimler bu kadar gün tutulur
HISSE_BASI = 5
# Panoda gösterilmeyen teknik/tekrarlı konular
GURULTU = ("Pay Dışında Sermaye Piyasası Aracı", "Şirket Genel Bilgi Formu", "Kurumsal Yönetim", "Sürdürülebilirlik",
           "Yatırım Kuruluşu Varant", "Piyasa Yapıcılığı", "Temerrüt İşlemi", "Pay Bazında Devre Kesici")
# Telegram'da da atlanan (panoda görünür): her gün tekrar eden geri alım bildirimleri
TG_ATLA = ("Payların Geri Alınmasına İlişkin Bildirim",)


def _sorgu(sinif, bas, son):
    govde = {"fromDate": bas, "toDate": son, "memberType": "IGS", "mkkMemberOidList": [], "disclosureClass": sinif,
             "subjectList": [], "isLate": "", "mainSector": "", "sector": "", "subSector": "", "marketOidList": [],
             "index": "", "bdkReview": "", "bdkMemberOidList": [], "year": "", "term": "", "ruleType": "", "period": "",
             "fromSrc": False, "srcCategory": "", "discIndex": []}
    r = requests.post(KAP_URL, json=govde, timeout=30,
                      headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    r.raise_for_status()
    return r.json()


def kap_cek(bugun=None):
    """Son SORGU_GUN günün ODA + FR bildirimleri: [{"id", "t" (YYYY-MM-DD HH:MM), "kodlar", "konu", "ozet"}]."""
    bugun = pd.Timestamp(bugun or pd.Timestamp.now(tz="Europe/Istanbul").strftime("%Y-%m-%d"))
    bas, son = str((bugun - pd.Timedelta(days=SORGU_GUN)).date()), str(bugun.date())
    out = []
    for sinif in ("ODA", "FR"):
        for x in _sorgu(sinif, bas, son):
            konu = x.get("subject") or ""
            if not x.get("stockCodes") or any(g in konu for g in GURULTU):
                continue
            try:
                t = pd.to_datetime(x["publishDate"], format="%d.%m.%Y %H:%M:%S").strftime("%Y-%m-%d %H:%M")
            except Exception:
                continue
            out.append({"id": int(x["disclosureIndex"]), "t": t, "konu": konu, "ozet": (x.get("summary") or "").strip(),
                        "kodlar": [k.strip() for k in x["stockCodes"].split(",") if k.strip()]})
    return out


def kap_guncelle(kodlar, bugun=None):
    """Önbelleği (kap.json) yeni bildirimlerle birleştirir. Döner: ({kod: [bildirim, ...] yeniden eskiye, en çok
    HISSE_BASI}, yeni_bildirimler_listesi). KAP'a ulaşılamazsa önbellekle devam eder (yeni = [])."""
    bugun = bugun or pd.Timestamp.now(tz="Europe/Istanbul").strftime("%Y-%m-%d")
    try:
        with open(KAP_CACHE, encoding="utf-8") as f:
            onb = json.load(f)
    except Exception:
        onb = {}
    tum = {b["id"]: b for b in onb.get("bildirim", [])}
    yeni = []
    try:
        for b in kap_cek(bugun):
            if b["id"] not in tum:
                yeni.append(b)
            tum[b["id"]] = b
    except Exception as e:
        print(f"KAP'a ulaşılamadı ({type(e).__name__}); önbellekle devam.")
    yeni = [b for b in yeni if set(kodlar).intersection(b["kodlar"])]
    print(f"KAP: takip edilen hisselerde {len(yeni)} yeni bildirim.")
    sinir = str((pd.Timestamp(bugun) - pd.Timedelta(days=SAKLA_GUN)).date())
    kodset = set(kodlar)
    sakla = sorted((b for b in tum.values() if b["t"] >= sinir and kodset.intersection(b["kodlar"])),
                   key=lambda b: b["id"], reverse=True)
    with open(KAP_CACHE, "w", encoding="utf-8") as f:
        json.dump({"tarih": bugun, "bildirim": sakla}, f, ensure_ascii=False)
    hisse = {}
    for b in sakla:
        for k in b["kodlar"]:
            if k in kodset and len(hisse.setdefault(k, [])) < HISSE_BASI:
                hisse[k].append({"id": b["id"], "t": b["t"], "konu": b["konu"], "ozet": b["ozet"][:220]})
    return hisse, yeni


def kap_mesaji(hisse, pf, son_id):
    """Portföy hisselerinin son_id'den yeni bildirimleri (geri alım hariç) → Telegram metni ya da None.
    hisse: kap_guncelle'nin döndürdüğü {kod: [bildirim, ...]}; aynı bildirim birden çok kodda olabilir."""
    bid = {}
    for k in pf:
        for b in hisse.get(k) or []:
            if b["id"] > son_id and not any(b["konu"].startswith(a) for a in TG_ATLA):
                bid.setdefault(b["id"], (b, []))[1].append(k)
    satir = []
    for _, (b, kod) in sorted(bid.items()):
        ozet = b["ozet"] if b["ozet"] and b["ozet"] != b["konu"] else ""
        satir.append(f"❗ <b>{', '.join(kod)}</b> — {escape(b['konu'])}{': ' + escape(ozet[:200]) if ozet else ''} "
                     f"<a href=\"{KAP_LINK}{b['id']}\">KAP</a> <i>({b['t'][8:10]}.{b['t'][5:7]} {b['t'][11:]})</i>")
    if not satir:
        return None
    return ("📰 <b>Portföyünde KAP bildirimi</b>\n\n" + "\n".join(satir) +
            "\n\n<i>Haberler çoğu zaman fiyata hızla yansır; aceleyle işlem yapma. Yatırım tavsiyesi değildir.</i>")
