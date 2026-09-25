"""Bilanço takibi (bilgi amaçlı): çeyreklik net kâr / satış, geçen yılın aynı çeyreğine göre değişim, sonraki
bilançonun tahmini tarihi. Kaynak yfinance (son ~6 çeyrek). Geçmişi kısa olduğu için backtest'le sinyale
katkısı ölçülemiyor — sinyal kurallarına girmez, sadece panoda/portföy özetinde bilgi."""
import json
import time

import pandas as pd
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
        takvim = None
        try:
            ed = (t.calendar or {}).get("Earnings Date")
            if ed:
                takvim = str(pd.Timestamp(ed[0]).date())
        except Exception:
            pass
        return {"para": para or "TRY", "ceyrek": ceyrek, "takvim": takvim}
    except Exception:
        return None


def bilancolari_al(kodlar, bugun=None):
    """Önbellek (bilanco.json) YENILEME_GUN günden eskiyse ya da hisse yoksa yeniden çeker."""
    bugun = bugun or pd.Timestamp.now(tz="Europe/Istanbul").strftime("%Y-%m-%d")
    veri, tarih = {}, None
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
    eksik = list(kodlar) if eski else [k for k in kodlar if k not in veri]
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
        json.dump({"tarih": bugun if eski else tarih, "veri": veri}, f, ensure_ascii=False)
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
