"""KAP bildirimleri (bilgi amaçlı): kap.org.tr'nin kendi sitesinin kullandığı bildirim sorgusu (tek POST ile tüm
şirketler). Özel durum açıklamaları (ODA) ve finansal raporlar (FR); tekrar eden/teknik konular ayıklanır.
Haberin çoğu fiyata hızla yansır — sinyal değil, bağlam.
Ayrıca 📊 bilanço tepkisi ve 'zarardaki şirket' notu için her şirketin dönem başına İLK 'Finansal Rapor' yayın zamanı (`fr`)
kap.json'da ~400 gün saklanır (aynı FR sorgusundan; ilk kurulumda geçmiş, taramaya birkaç küçük sorgu eklenerek parça parça dolar)."""
import json
import time
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
# 📊 Finansal rapor yayınları (strateji2 tanımı: konu tam 'Finansal Rapor', anahtar (kod, yıl, dönem), en erken yayın)
FR_KONU = "Finansal Rapor"
FR_SAKLA_GUN = 400      # 'ilk yayın' ayrımı için (düzeltilen rapor yeniden yayınlanınca ilk sayılmasın) ~13 ay geçmiş
FR_PENCERE = 15         # geçmiş doldurma: sorgu başına gün (yoğun dönemde 15 günde ~1.400 FR; 2000 sınırına gelirse ikiye bölünür)
FR_ADIM = 4             # her taramada en çok bu kadar geçmiş sorgusu (~1-2 sn/sorgu); 400 gün ~7 taramada dolar
FR_BEKLE = 1.0          # geçmiş sorguları arasında bekleme (sn) — KAP'a nazik


def _sorgu(sinif, bas, son):
    govde = {"fromDate": bas, "toDate": son, "memberType": "IGS", "mkkMemberOidList": [], "disclosureClass": sinif,
             "subjectList": [], "isLate": "", "mainSector": "", "sector": "", "subSector": "", "marketOidList": [],
             "index": "", "bdkReview": "", "bdkMemberOidList": [], "year": "", "term": "", "ruleType": "", "period": "",
             "fromSrc": False, "srcCategory": "", "discIndex": []}
    r = requests.post(KAP_URL, json=govde, timeout=30,
                      headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    r.raise_for_status()
    return r.json()


def _fr_ayikla(x, fr):
    """Ham KAP kaydı 'Finansal Rapor' ise fr listesine (kod, yıl, dönem 1-4, 'YYYY-MM-DD HH:MM') ekler."""
    if (x.get("subject") or "") != FR_KONU or not x.get("stockCodes") or x.get("year") is None or x.get("period") is None:
        return
    try:
        t = pd.to_datetime(x["publishDate"], format="%d.%m.%Y %H:%M:%S").strftime("%Y-%m-%d %H:%M")
        y, q = int(x["year"]), int(x["period"])
    except Exception:
        return
    for k in str(x["stockCodes"]).split(","):
        if k.strip():
            fr.append((k.strip(), y, q, t))


def fr_cek(bas, son):
    """[bas, son] aralığındaki 'Finansal Rapor' yayınları (2000 kayıt sınırına yaklaşırsa aralık ikiye bölünür)."""
    d = _sorgu("FR", bas, son)
    if len(d) >= 1990 and bas != son:
        a, b = pd.Timestamp(bas), pd.Timestamp(son)
        m = (a + (b - a) / 2).normalize()
        return fr_cek(bas, str(m.date())) + fr_cek(str((m + pd.Timedelta(days=1)).date()), son)
    fr = []
    for x in d:
        _fr_ayikla(x, fr)
    return fr


def fr_birlestir(eski, yeni, kodset=None, sinir=None):
    """{kod: [[yıl, dönem, t], ...]} + [(kod, yıl, dönem, t)] → her (kod, yıl, dönem) için EN ERKEN yayın; sinir'den
    ('YYYY-MM-DD') eski kayıtlar atılır. kodset verilirse sadece o hisseler."""
    en = {}
    for k, L in (eski or {}).items():
        for y, q, t in L:
            en[(k, y, q)] = min(t, en.get((k, y, q), t))
    for k, y, q, t in yeni:
        if kodset is None or k in kodset:
            en[(k, y, q)] = min(t, en.get((k, y, q), t))
    out = {}
    for (k, y, q), t in en.items():
        if (sinir is None or t >= sinir) and (kodset is None or k in kodset):
            out.setdefault(k, []).append([y, q, t])
    return {k: sorted(L, key=lambda x: x[2]) for k, L in sorted(out.items())}


def kap_cek(bugun=None, fr=None):
    """Son SORGU_GUN günün ODA + FR bildirimleri: [{"id", "t" (YYYY-MM-DD HH:MM), "kodlar", "konu", "ozet"}].
    fr (liste) verilirse 'Finansal Rapor' yayınları (kod, yıl, dönem, t) ona eklenir."""
    bugun = pd.Timestamp(bugun or pd.Timestamp.now(tz="Europe/Istanbul").strftime("%Y-%m-%d"))
    bas, son = str((bugun - pd.Timedelta(days=SORGU_GUN)).date()), str(bugun.date())
    out = []
    for sinif in ("ODA", "FR"):
        for x in _sorgu(sinif, bas, son):
            if sinif == "FR" and fr is not None:
                _fr_ayikla(x, fr)
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


def kap_guncelle(kodlar, bugun=None, fr_doldur=True):
    """Önbelleği (kap.json) yeni bildirimlerle birleştirir. Döner: ({kod: [bildirim, ...] yeniden eskiye, en çok
    HISSE_BASI}, yeni_bildirimler_listesi, fr). KAP'a ulaşılamazsa önbellekle devam eder (yeni = []).
    fr = {"kod": {kod: [[yıl, dönem, ilk yayın], ...]}, "tam": son FR_SAKLA_GUN gün dolduruldu mu}. Kapsam kap.json'da
    `fr_bas` (doldurulan en eski gün) / `fr_son` (son başarılı sorgu günü); taramalar SORGU_GUN'den uzun kesilirse geçmiş
    baştan doldurulur (en erken yayın korunur)."""
    bugun = bugun or pd.Timestamp.now(tz="Europe/Istanbul").strftime("%Y-%m-%d")
    try:
        with open(KAP_CACHE, encoding="utf-8") as f:
            onb = json.load(f)
    except Exception:
        onb = {}
    tum = {b["id"]: b for b in onb.get("bildirim", [])}
    yeni = []
    fr_yeni = []
    bas = str((pd.Timestamp(bugun) - pd.Timedelta(days=SORGU_GUN)).date())
    fr_bas, fr_son = onb.get("fr_bas"), onb.get("fr_son")
    try:
        for b in kap_cek(bugun, fr=fr_yeni):
            if b["id"] not in tum:
                yeni.append(b)
            tum[b["id"]] = b
        if not fr_bas or not fr_son or fr_son < bas:   # ilk kurulum ya da kesinti: kapsam bugünkü sorgudan başlar
            fr_bas = bas
        fr_son = bugun
    except Exception as e:
        print(f"KAP'a ulaşılamadı ({type(e).__name__}); önbellekle devam.")
    hedef = str((pd.Timestamp(bugun) - pd.Timedelta(days=FR_SAKLA_GUN)).date())
    if fr_doldur and fr_bas and fr_son == bugun and fr_bas > hedef:   # geçmişi parça parça doldur (yeniden eskiye)
        try:
            for _ in range(FR_ADIM):
                if fr_bas <= hedef:
                    break
                son_ = str((pd.Timestamp(fr_bas) - pd.Timedelta(days=1)).date())
                bas_ = str(max(pd.Timestamp(fr_bas) - pd.Timedelta(days=FR_PENCERE), pd.Timestamp(hedef)).date())
                time.sleep(FR_BEKLE)
                fr_yeni += fr_cek(bas_, son_)
                fr_bas = bas_
        except Exception as e:
            print(f"KAP finansal rapor geçmişi bu taramada doldurulamadı ({type(e).__name__}).")
    fr = fr_birlestir(onb.get("fr"), fr_yeni, set(kodlar), sinir=hedef)
    yeni = [b for b in yeni if set(kodlar).intersection(b["kodlar"])]
    print(f"KAP: takip edilen hisselerde {len(yeni)} yeni bildirim.")
    sinir = str((pd.Timestamp(bugun) - pd.Timedelta(days=SAKLA_GUN)).date())
    kodset = set(kodlar)
    sakla = sorted((b for b in tum.values() if b["t"] >= sinir and kodset.intersection(b["kodlar"])),
                   key=lambda b: b["id"], reverse=True)
    with open(KAP_CACHE, "w", encoding="utf-8") as f:
        json.dump({"tarih": bugun, "bildirim": sakla, "fr_bas": fr_bas, "fr_son": fr_son, "fr": fr}, f, ensure_ascii=False)
    hisse = {}
    for b in sakla:
        for k in b["kodlar"]:
            if k in kodset and len(hisse.setdefault(k, [])) < HISSE_BASI:
                hisse[k].append({"id": b["id"], "t": b["t"], "konu": b["konu"], "ozet": b["ozet"][:220]})
    return hisse, yeni, {"kod": fr, "tam": bool(fr_bas and fr_bas <= hedef)}


def donem_adi(y, q):
    """(2026, 2) → '2Ç26'."""
    return f"{q}Ç{y % 100:02d}"


def fr_yayinlar(fr_kod, kod):
    """Bir hissenin [(ilk yayın, dönem adı), ...] listesi (eskiden yeniye)."""
    return [(t, donem_adi(y, q)) for y, q, t in (fr_kod or {}).get(kod, [])]


def fr_son_donem(fr_kod, kod):
    """KAP'ta yayınlanmış en son finansal rapor dönemi (yıl, dönem) ya da None."""
    return max(((y, q) for y, q, _ in (fr_kod or {}).get(kod) or []), default=None)


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
