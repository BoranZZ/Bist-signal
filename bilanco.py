"""Bilanço takibi (bilgi amaçlı): çeyreklik net kâr / satış, geçen yılın aynı çeyreğine göre değişim, sonraki
bilançonun tahmini tarihi. Kaynak yfinance (son ~6 çeyrek). Geçmişi kısa olduğu için backtest'le sinyale
katkısı ölçülemiyor — sinyal kurallarına girmez, sadece panoda/portföy özetinde bilgi.
'Zarardaki şirket' notu (son 4 çeyrek net kâr toplamı ≤ 0) için kaynak İş Yatırım mali tabloları (Yahoo'nun çeyrekleri eksik:
ana listede 123 hissenin 36'sında son 4 çeyrek ardışık değil, PGSUS gibi işareti ters çıkanlar var). Bkz. `zarar_guncelle`."""
import json
import time

import pandas as pd
import requests
import yfinance as yf

BILANCO_CACHE = "bilanco.json"
YENILEME_GUN = 3   # bilanço verisi yavaş değişir; ama açıklama döneminde gecikmesin diye 3 günde bir

# SPK II-14.1 konsolide son teslim süreleri (çeyrek sonundan itibaren gün): 3 ve 9 ay 40, 6 ay 60, yıllık 70.
# Çoğu şirket daha erken açıklar; tarih "en geç" tahminidir.
SPK_SURE = {3: 40, 6: 60, 9: 40, 12: 70}


def _satir(q, adlar):
    for a in adlar:
        if a in q.index:
            return q.loc[a]
    return None


def bilanco_cek_tek(kod):
    """Ham çeyreklik veri: {"para", "ceyrek": [[tarih, net, satis], ...] eskiden yeniye, "takvim": tarih|None}."""
    try:
        t = yf.Ticker(kod + ".IS")
        q = t.quarterly_income_stmt
        if q is None or q.empty:
            return None
        net = _satir(q, ["Net Income", "Net Income Common Stockholders"])
        satis = _satir(q, ["Total Revenue", "Operating Revenue"])
        if net is None:
            return None
        ceyrek = []
        for c in sorted(q.columns):
            n = net.get(c)
            s = satis.get(c) if satis is not None else None
            if pd.isna(n):
                continue
            ceyrek.append([str(pd.Timestamp(c).date()), float(n), None if s is None or pd.isna(s) else float(s)])
        para = None
        try:
            para = t.info.get("financialCurrency")
        except Exception:
            pass
        takvim = ex_tarih = None
        try:
            cal = t.calendar or {}
            ed = cal.get("Earnings Date")
            if ed:
                takvim = str(pd.Timestamp(ed[0]).date())
            if cal.get("Ex-Dividend Date"):
                ex_tarih = str(pd.Timestamp(cal["Ex-Dividend Date"]).date())
        except Exception:
            pass
        temettu = []
        try:
            dv = t.dividends
            dv = dv[dv.index >= dv.index.max() - pd.DateOffset(years=2)] if len(dv) else dv
            temettu = [[str(i.date()), round(float(v), 4)] for i, v in dv.items()]
        except Exception:
            pass
        return {"para": para or "TRY", "ceyrek": ceyrek, "takvim": takvim, "ex_tarih": ex_tarih, "temettu": temettu}
    except Exception:
        return None


def bilancolari_al(kodlar, bugun=None):
    """Önbellek (bilanco.json) YENILEME_GUN günden eskiyse ya da hisse yoksa yeniden çeker."""
    bugun = bugun or pd.Timestamp.now(tz="Europe/Istanbul").strftime("%Y-%m-%d")
    veri, tarih, c = {}, None, {}
    try:
        with open(BILANCO_CACHE, encoding="utf-8") as f:
            c = json.load(f)
        veri, tarih = c.get("veri", {}), c.get("tarih")
    except Exception:
        pass
    eski = tarih is None or (pd.Timestamp(bugun) - pd.Timestamp(tarih)).days >= YENILEME_GUN
    simdi = pd.Timestamp.now(tz="Europe/Istanbul")
    if eski and veri and 9 * 60 + 30 <= simdi.hour * 60 + simdi.minute < 18 * 60 + 30:
        eski = False   # tam yenileme birkaç dakika sürer: seans içi taramaları yavaşlatmasın, kapanış sonrasına kalsın
    eksik = list(kodlar) if eski else [k for k in kodlar if k not in veri or (veri[k] and "temettu" not in veri[k])]
    if not eksik:
        print("Bilanço verisi önbellekten.")
        return veri
    print(f"Bilanço verisi güncelleniyor ({len(eksik)} hisse)...")
    for k in eksik:
        h = bilanco_cek_tek(k)
        if h is not None or k not in veri:
            veri[k] = h
        time.sleep(0.2)
    with open(BILANCO_CACHE, "w", encoding="utf-8") as f:
        json.dump(dict(c, tarih=bugun if eski else tarih, veri=veri), f, ensure_ascii=False)   # 'isy' vb. diğer anahtarlar korunur
    return veri


def _degisim(simdi, once):
    """Geçen yılın aynı çeyreğine göre: (etiket, yüzde|None)."""
    if simdi is None or once is None:
        return None, None
    if once > 0 and simdi > 0:
        return "büyüme" if simdi >= once else "düşüş", round((simdi / once - 1) * 100)
    if once <= 0 < simdi:
        return "zarardan kâra", None
    if once > 0 >= simdi:
        return "kârdan zarara", None
    return ("zarar azaldı" if simdi > once else "zarar büyüdü"), None


def _ceyrek_adi(tarih):
    t = pd.Timestamp(tarih)
    return f"{t.month // 3}Ç{t.year % 100:02d}"


def sonraki_bilanco(son_donem, takvim, bugun):
    """Sonraki bilanço için tarih: Yahoo takvimi (ileri tarihliyse) yoksa SPK son teslim tahmini."""
    bugun = pd.Timestamp(bugun)
    if takvim and pd.Timestamp(takvim) >= bugun:
        return {"tarih": takvim, "kaynak": "yahoo"}
    if not son_donem:
        return None
    d = pd.Timestamp(son_donem)
    # açıklanmamış ilk çeyrek: son dönem + 3 ay (ay sonu); son teslimi geçtiyse bir sonraki
    for _ in range(4):
        d = (d + pd.offsets.MonthEnd(3))
        son_gun = d + pd.Timedelta(days=SPK_SURE.get(d.month, 60))
        if son_gun >= bugun:
            return {"tarih": str(son_gun.date()), "kaynak": "spk", "donem": _ceyrek_adi(d)}
    return None


def bilanco_ozet(ham, bugun=None):
    """Panoya/mesaja gidecek özet. ham yoksa None."""
    if not ham or not ham.get("ceyrek"):
        return None
    bugun = bugun or pd.Timestamp.now(tz="Europe/Istanbul").strftime("%Y-%m-%d")
    cq = ham["ceyrek"]
    by = {c[0]: c for c in cq}
    son = cq[-1]
    gecen = by.get(str((pd.Timestamp(son[0]) - pd.DateOffset(years=1) + pd.offsets.MonthEnd(0)).date()))
    net_et, net_yuz = _degisim(son[1], gecen[1] if gecen else None)
    sat_et, sat_yuz = _degisim(son[2], gecen[2] if gecen else None)
    sonraki = sonraki_bilanco(son[0], ham.get("takvim"), bugun)
    kalan = (pd.Timestamp(sonraki["tarih"]) - pd.Timestamp(bugun)).days if sonraki else None
    return {"para": ham.get("para") or "TRY", "donem": _ceyrek_adi(son[0]), "donem_tarih": son[0],
            "net": son[1], "net_degisim": net_et, "net_yuz": net_yuz, "satis_degisim": sat_et, "satis_yuz": sat_yuz,
            "seri": [[_ceyrek_adi(c[0]), c[1]] for c in cq[-6:]],
            "sonraki": sonraki, "kalan_gun": kalan,
            # eski dönem: son teslim süresini aşan açıklanmamış bilanço (ya da veri kaynağı gecikmesi)
            "gecikmis": bool(sonraki and sonraki.get("kaynak") == "spk"
                             and (pd.Timestamp(bugun) - pd.Timestamp(son[0])).days > 3 * 31 + SPK_SURE.get(12, 70))}


def _yuzde(x):
    return f"+%{x}" if x >= 0 else f"−%{-x}"


def temettu_ozet(ham, fiyat, bugun=None):
    """Son 12 ay nakit temettü (hisse başı, TL) ve fiyata göre verim; ileri tarihli hak kullanım günü (biliniyorsa).
    yfinance BIST bedelsiz/bölünme kaydı tutmadığından bedelsiz sonrası verim şişebilir → %25 üstü 'şüpheli'."""
    if not ham:
        return None
    bugun = pd.Timestamp(bugun or pd.Timestamp.now(tz="Europe/Istanbul").strftime("%Y-%m-%d"))
    son12 = [x for x in (ham.get("temettu") or []) if pd.Timestamp(x[0]) >= bugun - pd.DateOffset(years=1)]
    toplam = round(sum(x[1] for x in son12), 2)
    ex = ham.get("ex_tarih")
    ex = ex if ex and pd.Timestamp(ex) >= bugun else None
    if not son12 and not ex:
        return None
    verim = round(toplam / fiyat * 100, 1) if (fiyat and fiyat == fiyat and toplam) else None
    return {"son12": toplam, "adet": len(son12), "son_tarih": son12[-1][0] if son12 else None, "verim": verim,
            "supheli": bool(verim and verim > 25), "ex_tarih": ex,
            "ex_kalan": (pd.Timestamp(ex) - bugun).days if ex else None}


def bilanco_metni(b):
    """Tek satır: '2Ç26 net kâr: geçen yıla göre +%35 · satış +%20 · sonraki bilanço ~09.11 (en geç)'."""
    if not b:
        return ""
    p = []
    if b["net_yuz"] is not None:
        p.append(f"{b['donem']} net kâr geçen yıla göre {_yuzde(b['net_yuz'])}")
    elif b["net_degisim"]:
        p.append(f"{b['donem']} net kâr: {b['net_degisim']}")
    if b["satis_yuz"] is not None:
        p.append(f"satış {_yuzde(b['satis_yuz'])}")
    if b.get("para") and b["para"] != "TRY":
        p.append(f"rakamlar {b['para']}")
    return " · ".join(p)


def bilanco_yakin(b, gun=14):
    """Sonraki bilanço 0..gun gün içinde mi (portföy uyarısı için)."""
    return bool(b and b.get("kalan_gun") is not None and 0 <= b["kalan_gun"] <= gun)


def tarih_tr(iso):
    return pd.Timestamp(iso).strftime("%d.%m")


# --- 'Zarardaki şirket' notu (2026-10-20, scratchpad strateji2/: BİLGİ, filtre değil) ------------------------------------------
# Son 4 çeyrek ana ortaklık net kârı toplamı ≤ 0. Geçmişte (2017-26, 286 hisse) bu şirketlerdeki 🚀 alımları ort. +%17, kârlılarda
# +%23 getirdi; atmak portföyü iyileştirmedi. Kaynak İş Yatırım MaliTablo (strateji2 ile aynı kalem: '3Z' = ana ortaklık payları;
# bankalarda UFRS 'net dönem kârı'). Dönem KAP'tan bilinir (kap.fr_son_donem: yayınlanan en son finansal rapor); hisse başına TEK
# istek (yıl/dönem 4 hücre: bu dönem kümülatif, geçen yıl yıllık, geçen yıl aynı dönem). Sadece YENİ dönem yayınlanınca (ya da
# ZARAR_YENILE_GUN'de bir) yeniden çekilir; her taramada en çok ZARAR_BUTCE hisse / ZARAR_SURE sn → tarama belirgin uzamaz.
ISY_URL = "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo"
ISY_KALEM = "3Z"
ZARAR_BUTCE = 40          # her taramada en çok bu kadar hisse; asıl sınır süre (İş Yatırım ~0,1-8 sn/istek, ort. ~1,7)
ZARAR_SURE = 8.0          # seans içi (09:30-18:30, hafta içi) toplam süre sınırı (sn)
ZARAR_SURE_DIS = 30.0     # seans dışı (kesin kapanış sonrası / hafta sonu): ilk kurulum birkaç akşamda tamamlanır
ISY_ZAMAN_ASIMI = (4, 10)
ZARAR_YENILE_GUN = 45


def _isy_sayi(x):
    try:
        return None if x in (None, "") else float(x)
    except Exception:
        return None


def isy_ttm(degerler, q):
    """[bu dönem kümülatif, geçen yıl 12 ay, geçen yıl aynı dönem] → son 4 çeyrek toplamı (yıllıkta dönemin kendisi).
    strateji2'deki çeyreklik farkların 4'lü toplamıyla cebirsel olarak aynı."""
    v1, v2, v3 = (list(degerler) + [None, None, None])[:3]
    if q == 4:
        return v1
    if v1 is None or v2 is None or v3 is None:
        return None
    return v1 + v2 - v3


def isy_ttm_cek(kod, y, q, grp=None, oturum=None):
    """İş Yatırım'dan (y, q) için son 4 çeyrek net kâr. Döner (ttm|None, finansal grup|None). Ağ hatası dışarı fırlar."""
    yil_ay = [(y, 3 * q), (y - 1, 12), (y - 1, 3 * q), (y - 1, 3 * q)]
    sorgu = "&".join(f"year{i + 1}={a}&period{i + 1}={b}" for i, (a, b) in enumerate(yil_ay))
    get = (oturum or requests).get
    for g in ([grp] if grp else ["XI_29", "UFRS"]):     # sanayi/hizmet XI_29, banka/finans UFRS
        r = get(f"{ISY_URL}?companyCode={kod}&exchange=TRY&financialGroup={g}&{sorgu}", timeout=ISY_ZAMAN_ASIMI,
                headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        v = r.json().get("value") or []
        if not v:
            continue
        sat = next((x for x in v if x.get("itemCode") == ISY_KALEM), None)
        if sat is None:
            return None, g
        return isy_ttm([_isy_sayi(sat.get(f"value{i}")) for i in (1, 2, 3)], q), g
    return None, grp


def zarar_guncelle(kodlar, son_donem, bugun=None, butce=ZARAR_BUTCE, sure=None):
    """son_donem: {kod: (yıl, dönem 1-4)} KAP'ta yayınlanmış son finansal rapor. bilanco.json 'isy' önbelleğini (hisse:
    {"g": grup, "p": [yıl, dönem], "n": son 4 çeyrek net kâr, "t": çekildiği gün, "a": son deneme günü}) gerekirse günceller.
    Döner {kod: {"d": '2Ç26', "n": toplam}} (sadece verisi olanlar). Kaynağa ulaşılamazsa önbellekle devam."""
    simdi = pd.Timestamp.now(tz="Europe/Istanbul")
    bugun = bugun or simdi.strftime("%Y-%m-%d")
    if sure is None:
        seans = simdi.weekday() < 5 and 9 * 60 + 30 <= simdi.hour * 60 + simdi.minute < 18 * 60 + 30
        sure = ZARAR_SURE if seans else ZARAR_SURE_DIS
    try:
        with open(BILANCO_CACHE, encoding="utf-8") as f:
            c = json.load(f)
    except Exception:
        c = {}
    isy = dict(c.get("isy") or {})
    yeni_donem, yenile = [], []
    for k in kodlar:
        hedef = son_donem.get(k)
        if not hedef:
            continue
        e = isy.get(k) or {}
        if e.get("a") == bugun:
            continue                                       # bugün denendi (İş Yatırım KAP'tan geç güncelleyebilir: yarın yine)
        if e.get("p") != list(hedef):
            yeni_donem.append(k)
        elif not e.get("t") or (pd.Timestamp(bugun) - pd.Timestamp(e["t"])).days >= ZARAR_YENILE_GUN:
            yenile.append(k)
    sira = (yeni_donem + yenile)[:butce]
    if sira:
        t0, n_ok, n_den = time.time(), 0, 0
        oturum = requests.Session()
        for k in sira:
            if time.time() - t0 > sure:
                break
            y, q = son_donem[k]
            e = dict(isy.get(k) or {})
            e["a"] = bugun          # hata olsa da bugün bir daha denenmez (takılan tek hisse sırayı kilitlemesin)
            isy[k] = e
            n_den += 1
            try:
                ttm, g = isy_ttm_cek(k, int(y), int(q), e.get("g"), oturum)
            except Exception as ex:   # yavaş/ulaşılamıyor: bu taramada bırak, kalanlar sonraki taramalarda
                print(f"İş Yatırım mali tablo alınamadı ({type(ex).__name__}); önbellekle devam.")
                break
            if g:
                e["g"] = g
            if ttm is not None:
                e.update(p=[int(y), int(q)], n=ttm, t=bugun)
                n_ok += 1
            time.sleep(0.3)
        print(f"Zarar notu: İş Yatırım'dan {n_den} hisse istendi, {n_ok} güncellendi (bekleyen: {len(yeni_donem)} yeni dönem, "
              f"{len(yenile)} yenileme; {time.time() - t0:.1f} sn).")
        try:
            with open(BILANCO_CACHE, encoding="utf-8") as f:
                c = json.load(f)
        except Exception:
            pass
        c["isy"] = dict(sorted(isy.items()))
        with open(BILANCO_CACHE, "w", encoding="utf-8") as f:
            json.dump(c, f, ensure_ascii=False)
    return {k: {"d": f"{e['p'][1]}Ç{e['p'][0] % 100:02d}", "n": e["n"]}
            for k, e in isy.items() if e.get("p") and e.get("n") is not None}
