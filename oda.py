# -*- coding: utf-8 -*-
"""🏢 İşlem Odası — SANAL parayla kural robotları (yapay zekâ yok; yatırım tavsiyesi değil; kullanıcı portföyüyle ilgisi yok).

Her robot 100.000 sanal TL ile başlar ve panonun zaten hesapladığı verilerle (tarama.py'nin `sonuclar`'ı — yeniden veri
çekme yok) kendi kuralını uygular. Robot kuralları, 🛡️ Risk Bekçisi eşikleri ve motor (robot_karar / emir_uygula) paralel
araştırmanın referans uygulamasından alındı (scratchpad oda_arastirma/robotlar.py; 2022-10 → 2026-10, iki faiz
dönemi, 200 rastgele 'ikiz' ve 🎲 şans bandıyla; ayrıntı CLAUDE.md 'İşlem Odası'). Değiştirmek için: ROBOTLAR / BEKCI.
2026-10-10 motor düzeltmeleri: Bekçi'nin kırpması (kısmi satış) ve kilitli tabanda bekleyen satış yuva açmaz, yuvalar
doluyken alım yazılmaz (10 yuvalı robot asla 11 pozisyon taşımaz); nakit yuva payının yarısından azsa alım yok; canlıda
hak kullanım günü net temettü (%85) kasaya girer. 💰 Birikim kıyasları (Faizci, Altıncı, Dolarcı, Dengeci) ve TÜFE'ye
göre reel getiri eklendi.

ZAMANLAMA (canlı = tekrar oynatma, aynı `gun_isle`):
  Kesin kapanıştan sonraki (18:30+) taramada, günde bir kez: (1) dünkü kararların emirleri BUGÜNÜN AÇILIŞ fiyatıyla yazılır
  (emir_uygula; bütün günün mumu belli olduğu için 'kilitli taban/tavan' kesin bilinir), (2) bugünün kapanışıyla robot
  kararları (robot_karar) → bir sonraki işlem gününün açılışında yazılacak emirler. Gün içi taramalar sadece anlık kasa
  değerini günceller. Alış açılış + 1 fiyat adımı, satış − 1 adım (kayma), her yönde %0,2 komisyon; lot tam sayı; kilitli
  tabanda satılamaz (emir ertesi güne kalır), kilitli tavanda alınamaz (emir iptal).

Dosyalar: oda.json (canlı durum, HERKESE AÇIK — sadece sanal robot kasaları), oda.html (bu dosyadaki şablondan yazılır,
veriyi fetch ile okur), oda_replay.json (~5 yıllık tek uzun tekrar oynatma + hazır dönemlerin şans istatistikleri; sayfada dönem seçici;
oda_replay_sans.json: özel dönem şans bandı için, sayfa tembel yükler; `python oda_replay.py`).
"""
import datetime as _dt
import hashlib
import json
import math
import random
import re

from sinyal import KILIT_ARALIK, TABAN_GETIRI

# ================== ROBOT MOTORU (araştırmanın referans uygulaması; robotlar.py'den) ==================
KOMISYON = 0.002          # her yönde (backtest.KOMISYON ile aynı)
BASLANGIC = 100_000.0
KUCUK_ALIM = 0.5          # nakit, yuva payının (pay × kasa) bu oranından azsa alım yapılmaz (küçük kırıntı alımlar yok)
YUVA_DUZELTME = True      # kırpma / kilitli tabanda bekleyen satış yuva açmaz + yuvalar doluyken alım yok (False: 2026-10-10
                          # öncesi davranış — sadece önce/sonra karşılaştırması için; KUCUK_ALIM = 0 ile birlikte eski motor)

# ------------------------------------------------------------------ robot tanımları (araştırma sonucu varsayılanlar)
ROBOTLAR = {
    "kirilimci": {"ad": "🚀 Kırılımcı", "tur": "kirilim", "yuva": 10, "iz": 0.20, "filtre": True,
                  "aciklama": "🚀 trend kırılımı (v3) gelen hisseyi ertesi açılışta alır; tepe kapanışın %20 altına inince satar."},
    "kirilimci20": {"ad": "🚀 Kırılımcı · 20 yuva", "tur": "kirilim", "yuva": 20, "iz": 0.20, "filtre": True,
                    "aciklama": "Kırılımcı ile aynı kural (🚀 v3 kırılımı, %20 iz stop), ama kasa 20 yuvaya bölünür: her hisseye "
                                "kasanın %5'i. Kıyas: 'yuvalar dolu diye kaçan roketler' ne kadar önemli?"},
    "siki": {"ad": "📏 Kırılımcı + sıkı çizgi", "tur": "kirilim", "yuva": 10, "iz": 0.20, "siki": True, "filtre": True,
             "aciklama": "Kırılımcı ile aynı; ayrıca hisse aşırı uzadıysa kijun (sıkı çizgi) altında kapanışta satar."},
    "erkenci": {"ad": "👀 Erkenci", "tur": "erken", "yuva": 10, "iz": 0.20, "uzak": 3.0, "filtre": True,
                "aciklama": "Trend şablonunda, 20 günlük zirveye ≤%3 kalan hisseyi kırılımı beklemeden alır; %20 iz stop."},
    "momentumcu": {"ad": "📈 Momentumcu", "tur": "momentum", "yuva": 10, "piyasa": True,
                   "aciklama": "Her ayın ilk kapanışında 'ayın güçlüleri' listesinin en güçlü 10'unu alır, listeden düşeni satar; "
                               "BIST 100 50 günlük ortalamasının altındaysa nakitte bekler."},
    "dipavcisi": {"ad": "🧲 Dip avcısı", "tur": "dip", "yuva": 10, "sure": 20, "trend": True, "filtre": True,
                  "aciklama": "'Destekten tepki' veren hisseyi alır; destek çizgisinin altında kapanışta (sıkı stop), dirence "
                              "varınca ya da 20 işlem gününde satar."},
    "uzunvadeci": {"ad": "🌱 Uzun vadeci", "tur": "uzun", "yuva": 10, "filtre": True,
                   "aciklama": "🌱 uzun vade AL'i (yükselen trendde 50 günlüğe geri çekilip dönüş) gelince alır; 2 gün 200 "
                               "günlük ortalama altında kapanışta satar."},
    "rsi": {"ad": "↩️ RSI dönüşçü (tahmini)", "tur": "rsi", "yuva": 10, "iz": 0.20, "filtre": True,
            "aciklama": "RSI 25-33 arasında ve bir günde ≥2,4 puan yükselince alır (arkadaşın AL kuralı); çıkış kuralı "
                        "bilinmediği için %20 iz stop varsayıldı — TAHMİNİ."},
    "rastgele": {"ad": "🎲 Rastgele", "tur": "rastgele", "yuva": 10, "iz": 0.20, "filtre": True,
                 "aciklama": "Şans kıyası: 🚀 kırılım gelen gün, o gün kaç kırılım varsa o kadar RASTGELE hisse alır; "
                             "Kırılımcı ile aynı %20 iz stop. Kırılımcı bunu yenemiyorsa seçim becerisi yok demektir."},
    "endeksci": {"ad": "🧭 Endeksçi", "tur": "endeks",
                 "aciklama": "İlk gün tüm parayla BIST 100'ü alır ve tutar (endeks fonu gibi; kıyas çizgisi)."},
    # 💰 Birikim köşesi: hisse seçmeyen kıyas robotları (yarışmacı değil; Bekçi yok; Telegram sıralamasına girmez)
    "faizci": {"ad": "🏦 Faizci", "tur": "faiz",
               "aciklama": "Tüm parayı 32 günlük TL vadeli mevduata koyar, vade sonunda faiziyle yeniler. Faiz: TCMB politika "
                           "faizi (gerçek mevduat faizi bankaya göre farklı; 2023-24'te çoğu zaman politika faizinin üstündeydi). "
                           "Brüt faiz × 32/365; stopaj vadenin açıldığı/yenilendiği günün oranıyla kesilir (%5 → %7,5 → %10 → "
                           "%15 → %17,5)."},
    "altinci": {"ad": "🥇 Altıncı", "tur": "altin",
                "aciklama": "İlk gün tüm parayla gram altın alır ve tutar (ons altın × dolar/TL ÷ 31,1035). Banka makası toplam "
                            "%2 (alışta %1, satışta %1; kasa değeri satış fiyatından), alışta %0,2 BSMV; kesirli gram."},
    "dolarci": {"ad": "💵 Dolarcı", "tur": "dolar",
                "aciklama": "İlk gün tüm parayla dolar alır ve tutar (USD/TL). Makas toplam ~%1 (yarısı alışta, yarısı satışta; "
                            "kasa değeri satış fiyatından), alışta %0,2 BSMV; faizsiz (döviz hesabı faizi yok sayıldı)."},
    "dengeci": {"ad": "⚖️ Dengeci", "tur": "denge",
                "aciklama": "1/3 TL mevduat (Faizci gibi), 1/3 gram altın (Altıncı gibi), 1/3 BIST 100 (Endeksçi gibi). Üç ayda "
                            "bir (ilk vade sonu ≥90 gün) yeniden 1/3'e dengeler; payı %2'den az sapan kalem için işlem yapmaz."},
}
KIYAS_TUR = {"endeks", "faiz", "altin", "dolar", "denge"}     # Bekçi yok, yuva yok
BIRIKIM_TUR = {"faiz", "altin", "dolar", "denge"}             # 💰 Birikim köşesi (sıralamaya girmez)

# 🛡️ Risk Bekçisi varsayılanları (araştırma: bekci_test.txt)
BEKCI = {"tek_hisse": 0.10,      # alışta bir hisseye en fazla kasanın %10'u (= 10 yuva)
         "kirp": 0.25,           # bir hisse sonradan kasanın %25'ini aşarsa fazlası satılır (yoğunlaşma freni)
         "gunluk_zarar": 0.05,   # kasa bir günde ≥%5 düşerse ertesi gün yeni alım yok
         "gunluk_bekle": 1,
         "dusus": 0.25,          # kasa zirvesinden ≥%25 düşerse: tüm pozisyonlar satılır, 20 işlem günü alım yok
         "dusus_bekle": 20}
# Not (bekci_test.txt / bekci_oneri.txt): bu kurallar 4 yılda robot başına 0-2 kez tetiklendi; getiri ve en büyük düşüşe
# etkileri karışık (dönemden döneme işaret değiştiriyor) → kâr aracı değil, emniyet kemeri. En tutarlı risk azaltıcı
# daha çok yuva (tek hisse %5 / 20 yuva) çıktı.

# ------------------------------------------------------------------ kesirli varlıklar, mevduat, vergiler
XU = "XU100"
ALTIN, USD, MEVDUAT = "ALTIN", "USD", "MEVDUAT"
KESIRLI = (XU, ALTIN, USD)                 # kesirli adet; fiyat adımı/kayma yok
MAKAS = {ALTIN: 0.01, USD: 0.005}          # her yönde (altın toplam %2, dolar toplam ~%1); kasa değeri satış (makas düşülmüş) fiyattan
BSMV = 0.002                               # döviz/altın alışında kambiyo BSMV'si
ONS_GRAM = 31.1035
VADE_GUN = 32
DENGE_GUN = 90                             # Dengeci: son dengelemeden en az bu kadar takvim günü sonra, ilk vade sonunda dengeler
DENGE_ESIK = 0.02                          # payı hedeften kasanın %2'sinden az sapan kalem için dengeleme işlemi yok
# TL mevduat faiz stopajı (vadenin açıldığı/yenilendiği güne göre; 6 aya kadar vadeli TL mevduat; 31.12.2026'ya kadar uzatıldı)
STOPAJ = [("2020-09-30", 0.05), ("2024-05-01", 0.075), ("2024-11-01", 0.10), ("2025-02-01", 0.15), ("2025-07-09", 0.175)]
TEMETTU_STOPAJ = 0.15                      # nakit temettüde gerçek kişi stopajı (kasaya %85 girer)


def stopaj_orani(tarih):
    r = 0.15                               # 30.09.2020 öncesi (oynatma bu tarihten sonra başlıyor; kullanılmaz)
    for t, v in STOPAJ:
        if tarih >= t:
            r = v
    return r


def _gun(t):
    return _dt.date.fromisoformat(t[:10])


def gun_farki(a, b):
    return (_gun(b) - _gun(a)).days


def mevduat_degeri(m, tarih):
    """Gösterim: anapara + vadenin bugüne kadar işlemiş NET faizi (vade bozulsa bu faiz alınmazdı)."""
    g = max(0, gun_farki(m["t"], tarih))
    return m["ana"] + m["ana"] * m["oran"] * g / 365 * (1 - m["st"])


# ------------------------------------------------------------------ BIST fiyat adımı (pay piyasası)
def fiyat_adimi(p):
    if p < 20: return 0.01
    if p < 50: return 0.02
    if p < 100: return 0.05
    if p < 250: return 0.10
    if p < 500: return 0.25
    if p < 1000: return 0.50
    if p < 2500: return 1.00
    return 2.50


def yeni_kasa(rid, tarih=None):
    return {"robot": rid, "nakit": BASLANGIC, "poz": {}, "deger": BASLANGIC, "dun_deger": BASLANGIC, "tepe_deger": BASLANGIC,
            "durdu": 0, "durdu_neden": None, "bekleyen": [], "defter": [], "seri": [], "baslangic": tarih}


# ------------------------------------------------------------------ canlı tarama sonucundan robot özeti
def ozet_hazirla(s, d=None, buyuk=False):
    """tarama.py'deki analiz_et sonucu `s` (+ isteğe bağlı günlük df `d`: gostergeler() çıktısı) → robotun gördüğü alanlar.
    `d` verilirse rsi_degisim / kijun / uzama da doldurulur (analiz_et bunları döndürmüyor)."""
    tk, sd, uv, th = s.get("tk") or {}, s.get("sd") or {}, s.get("uv") or {}, s.get("tahta") or {}
    o = {"fiyat": s.get("fiyat"),
         "tk": {"bugun": bool(tk.get("bugun")), "sablon": bool(tk.get("sablon")), "kirilima_uzak": tk.get("kirilima_uzak"),
                "durum": tk.get("durum"), "seviye": tk.get("kirilim_seviye")},
         "oynak": bool(s.get("oynak")),
         "sd": {"tepki": bool(sd.get("tepki")), "destek": (sd.get("destek") or {}).get("fiyat"),
                "direnc": (sd.get("direnc") or {}).get("fiyat"), "tol": (sd.get("tol") or 0) / 100.0},
         "uv": {"durum": uv.get("durum"), "yeni": uv.get("durum") == "AL" and uv.get("gun") == 1},
         "rsi": s.get("rsi"), "rsi_degisim": None, "mom20": (s.get("mom20") or 0) / 100.0,
         "mom6": None if s.get("mom6") is None else s["mom6"] / 100.0, "s200_ust": bool(s.get("s200_ust")),
         "buyuk": bool(buyuk),
         # tarama._riskli ile aynı: taban serisi / 🔒 kilitli taban / 🎈 şişme
         "riskli": bool(s.get("patlak") or s.get("kt") or th.get("seviye") == "sisme"),
         "uzama": False, "kijun": None}
    if d is not None and len(d) > 2:
        import sinyal as S
        r = d["RSI"] if "RSI" in d else S.rsi(d["Close"])
        o["rsi_degisim"] = float(r.iloc[-1] - r.iloc[-2]) if r.iloc[-2] == r.iloc[-2] else None
        if r.iloc[-1] == r.iloc[-1]:
            o["rsi"] = float(r.iloc[-1])      # yuvarlanmamış (25-33 sınırında analiz_et'in 1 hanesi karar değiştirebilir)
        kj = S.kijun(d).iloc[-1]
        o["kijun"] = float(kj) if kj == kj else None
        o["uzama"] = bool(S.asiri_uzama(d["Close"], len(d) - 1))
    return o


# ------------------------------------------------------------------ yardımcılar
def _fiyat(kod, gv):
    if kod == XU:
        return gv["xu"]["fiyat"]
    if kod in MAKAS:
        return (gv.get("piyasa") or {}).get(kod)
    return (gv["hisseler"].get(kod) or {}).get("fiyat")


def net_fiyat(kod, f):
    """Kasa değeri için: altın/dolar bankanın ALIŞ fiyatından (satarken eline geçen; makas düşülmüş)."""
    return f * (1 - MAKAS[kod]) if kod in MAKAS else f


def _deger(kasa, gv):
    top = kasa["nakit"]
    for kod, p in kasa["poz"].items():
        f = _fiyat(kod, gv) or p.get("fiyat")
        if f:
            p["fiyat"] = f
        top += p["adet"] * net_fiyat(kod, p["fiyat"])
    if kasa.get("mevduat"):
        top += mevduat_degeri(kasa["mevduat"], gv["tarih"])
    return top


def kasa_anlik(kasa, F, tarih):
    """Gün içi anlık kasa değeri (F: {kod: fiyat}; olmayan için son bilinen)."""
    top = kasa["nakit"] + sum(p["adet"] * net_fiyat(kod, F.get(kod) or p["fiyat"]) for kod, p in kasa["poz"].items())
    if kasa.get("mevduat"):
        top += mevduat_degeri(kasa["mevduat"], tarih)
    return top


def _rng(tarih, rid):
    return random.Random(int(hashlib.sha1(f"{rid}|{tarih}".encode()).hexdigest()[:12], 16))


def _al_adaylari(robot, gv, kasa):
    """Bugünkü giriş adayları (öncelik sırasıyla)."""
    hs, tur = gv["hisseler"], robot["tur"]
    tut = set(kasa["poz"])
    aday = []
    for kod, h in hs.items():
        if kod in tut or not h.get("fiyat"):
            continue
        if robot.get("filtre") and h.get("riskli"):
            continue
        if tur == "kirilim" and h["tk"]["bugun"]:
            aday.append((h["mom20"], kod))                       # az yükselmiş olan önce (proje 'AL önceliği')
        elif tur == "erken":
            u = h["tk"]["kirilima_uzak"]
            if (h["tk"]["sablon"] and u is not None and 0 < u <= robot.get("uzak", 3.0)          # = panodaki 👀 rozeti
                    and not (robot.get("oynak_sart") and h.get("oynak"))
                    and (gv["xu"]["ust"] or not robot.get("piyasa_sart"))):
                aday.append((u, kod))                            # zirveye en yakın önce
        elif tur == "dip" and h["sd"]["tepki"] and h["sd"]["destek"]:
            if robot.get("trend") and not h["s200_ust"]:
                continue
            aday.append((h["mom20"], kod))
        elif tur == "uzun" and h["uv"]["yeni"]:
            aday.append((h["mom20"], kod))
        elif tur == "rsi":
            r, dr = h.get("rsi"), h.get("rsi_degisim")
            if r is not None and dr is not None and 25 <= r <= 33 and dr >= 2.4:
                aday.append((h["mom20"], kod))
    aday.sort()
    return [k for _, k in aday]


def _momentum_listesi(gv, pay=0.20):
    """tarama.momentum_listesi ile aynı: BIST100+EK, mom6 olanların %20'si kadar; SMA200 üstündekilerden en yüksek mom6."""
    tum = [(k, h) for k, h in gv["hisseler"].items() if h.get("buyuk") and h.get("mom6") is not None and h.get("fiyat")]
    n = max(1, int(len(tum) * pay))
    aday = sorted((x for x in tum if x[1]["s200_ust"]), key=lambda x: -x[1]["mom6"])
    return [k for k, _ in aday[:n]]


def _r(x, n=4):
    return None if x is None else round(float(x), n)


def _al_notu(tur, h, n, bos, sira):
    """Alımın 'neden'i: [ölçü, o günkü aday sayısı, boş yuva, sıra]. Ölçü: 🚀 kırılan seviye (önceki 20 günün en yüksek
    kapanışı) / 👀 zirveye uzaklık % / 🧲 destek / ↩️ RSI / 📈 6 ay getirisi %; 🌱 ve 🎲 için yok."""
    o = None
    if tur == "kirilim":
        o = _r(h["tk"].get("seviye"))
    elif tur == "erken":
        o = _r(h["tk"].get("kirilima_uzak"), 1)
    elif tur == "dip":
        o = _r(h["sd"].get("destek"))
    elif tur == "rsi":
        o = _r(h.get("rsi"), 1)
    elif tur == "momentum" and h.get("mom6") is not None:
        o = _r(h["mom6"] * 100, 1)
    return [o, n, bos, sira]


# ------------------------------------------------------------------ mevduat (Faizci / Dengeci)
def mevduat_ac(kasa, tarih, faiz):
    x = kasa["nakit"]
    kasa["mevduat"] = {"ana": x, "t": tarih, "oran": faiz / 100.0, "st": stopaj_orani(tarih)}
    kasa["nakit"] = 0.0
    kasa.setdefault("denge_t", tarih)
    kasa["defter"].append({"t": tarih, "kod": MEVDUAT, "yon": "MEV", "adet": round(x, 2), "oran": round(faiz, 2),
                           "st": kasa["mevduat"]["st"]})


def mevduat_isle(kasa, gv, tur):
    """Vadesi dolan mevduat: brüt faiz (oran × 32/365) − stopaj anaparaya eklenir, aynı gün o günkü politika faiziyle yenilenir.
    Dengeci'de son dengelemeden ≥ DENGE_GUN geçtiyse yenilenmez: para nakde döner, dengeleme emirleri yazılır."""
    m = kasa["mevduat"]
    faiz = (gv.get("piyasa") or {}).get("faiz")
    while gun_farki(m["t"], gv["tarih"]) >= VADE_GUN:
        brut = m["ana"] * m["oran"] * VADE_GUN / 365
        st = brut * m["st"]
        m["ana"] += brut - st
        yeni = str(_gun(m["t"]) + _dt.timedelta(days=VADE_GUN))
        kasa["defter"].append({"t": gv["tarih"], "kod": MEVDUAT, "yon": "FAIZ", "brut": round(brut, 2), "stopaj": round(st, 2),
                               "oran": round(m["oran"] * 100, 2), "st": m["st"], "vade": yeni})
        if tur == "denge" and gun_farki(kasa.get("denge_t") or m["t"], yeni) >= DENGE_GUN:
            kasa["nakit"] += m["ana"]
            kasa["mevduat"] = None
            kasa["denge_bekle"] = True
            return
        m["t"] = yeni
        if faiz is not None:
            m["oran"] = faiz / 100.0
        m["st"] = stopaj_orani(yeni)


def _kiyas_karar(robot, gv, kasa, deger):
    tur, emir, poz = robot["tur"], [], kasa["poz"]
    ilk = not any(e["yon"] in ("AL", "MEV") for e in kasa["defter"])
    if tur == "endeks":
        if not poz and not kasa["defter"]:
            emir.append({"kod": XU, "yon": "AL", "pay": 1.0})
    elif tur in ("altin", "dolar"):
        if not poz and ilk:
            emir.append({"kod": ALTIN if tur == "altin" else USD, "yon": "AL", "pay": 1.0})
    elif tur == "faiz":
        if not kasa.get("mevduat") and kasa["nakit"] > 1:
            emir.append({"kod": MEVDUAT, "yon": "AL"})
    elif tur == "denge":
        if ilk:
            emir += [{"kod": ALTIN, "yon": "AL", "pay": 1 / 3}, {"kod": XU, "yon": "AL", "pay": 1 / 3}, {"kod": MEVDUAT, "yon": "AL"}]
        elif kasa.get("denge_bekle"):
            hedef = deger / 3
            for kod in (ALTIN, XU):
                p = poz.get(kod)
                nf = net_fiyat(kod, p["fiyat"]) if p else None
                fark = hedef - (p["adet"] * nf if p else 0.0)
                if abs(fark) < DENGE_ESIK * deger:
                    continue
                if fark < 0:
                    emir.append({"kod": kod, "yon": "SAT", "adet": min(p["adet"], -fark / nf), "neden": "dengeleme (1/3'e)"})
                else:
                    emir.append({"kod": kod, "yon": "AL", "tutar": fark})
            emir.append({"kod": MEVDUAT, "yon": "AL"})
            kasa["denge_bekle"] = False
            kasa["denge_t"] = gv["tarih"]
        elif not kasa.get("mevduat") and kasa["nakit"] > 1:
            emir.append({"kod": MEVDUAT, "yon": "AL"})       # faiz bilinmediği için açılamadıysa yeniden dene
    return emir


# ------------------------------------------------------------------ ANA FONKSİYON
def robot_karar(rid, gun_verisi, kasa, robot=None, bekci=None):
    """Kesin kapanış taramasında çağrılır. Pozisyon izleyicilerini (tepe, gün, uzama) ve risk durumunu günceller,
    ertesi açılışta uygulanacak emirleri kasa['bekleyen']'e yazar ve döndürür. Emir: {kod, yon: AL|SAT, pay|neden}."""
    robot = robot or ROBOTLAR[rid]
    B = dict(BEKCI, **(bekci or {}))
    gv, hs, tur = gun_verisi, gun_verisi["hisseler"], robot["tur"]
    kiyas = tur in KIYAS_TUR
    if kasa.get("mevduat"):
        mevduat_isle(kasa, gv, tur)
    # 1) izleyiciler
    for kod, p in kasa["poz"].items():
        h = hs.get(kod)
        f = _fiyat(kod, gv)
        if not f:
            continue
        p["fiyat"] = f
        p["tepe"] = max(p.get("tepe", f), f)
        p["gun"] = p.get("gun", 0) + 1
        if h and h.get("uzama"):
            p["uzadi"] = True
    deger = _deger(kasa, gv)
    kasa["dun_deger"], kasa["deger"] = kasa["deger"], deger
    kasa["tepe_deger"] = max(kasa["tepe_deger"], deger)
    kasa["seri"].append([gv["tarih"], round(deger, 2), len(kasa["poz"])])
    # 2) 🛡️ Risk Bekçisi (kıyas robotlarında yok)
    if not kiyas:
        if kasa["durdu"] > 0:
            kasa["durdu"] -= 1
            if kasa["durdu"] == 0:
                kasa["tepe_deger"] = deger          # bekleme bitti: düşüş ölçümü yeniden başlar
                kasa["durdu_neden"] = None
        if B["gunluk_zarar"] and deger <= kasa["dun_deger"] * (1 - B["gunluk_zarar"]):
            kasa["durdu"] = max(kasa["durdu"], B["gunluk_bekle"]); kasa["durdu_neden"] = "gunluk"
        if B["dusus"] and kasa["durdu_neden"] != "dusus_aktif" and deger <= kasa["tepe_deger"] * (1 - B["dusus"]):
            kasa["durdu"] = max(kasa["durdu"], B["dusus_bekle"]); kasa["durdu_neden"] = "dusus_aktif"
            kasa.setdefault("bekci_olay", []).append(gv["tarih"])
            for kod, p in kasa["poz"].items():
                p["sat"] = "bekçi: düşüş limiti"
                p["sat_not"] = {"k": _r(p.get("fiyat"))}
    # 3) kıyas robotları (Endeksçi + 💰 birikim): kendi basit kuralları
    if kiyas:
        emir = _kiyas_karar(robot, gv, kasa, deger)
        kasa["bekleyen"] = emir
        return emir
    emir = []
    ay_listesi = None
    if tur == "momentum" and gv.get("ay_ilk"):
        ay_listesi = _momentum_listesi(gv) if (gv["xu"]["ust"] or not robot.get("piyasa")) else []
    for kod, p in kasa["poz"].items():
        if p.get("sat"):
            emir.append({"kod": kod, "yon": "SAT", "neden": p["sat"]}); continue
        h = hs.get(kod) or {}
        f = p.get("fiyat")
        neden = None
        if robot.get("iz") and f < p["tepe"] * (1 - robot["iz"]):
            neden = f"iz stop (tepe {p['tepe']:.2f})"
        elif robot.get("siki") and p.get("uzadi") and h.get("kijun") and f < h["kijun"]:
            neden = "sıkı çizgi altında kapanış"
        elif tur == "dip":
            if f < p["stop"]:
                neden = "destek kırıldı"
            elif p.get("hedef") and f >= p["hedef"] and robot.get("hedef", True):
                neden = "dirence ulaştı"
        elif tur == "uzun" and h.get("uv", {}).get("durum") == "SAT":
            neden = "🌱 SAT (200 günlük altı)"
        elif tur == "momentum" and ay_listesi is not None:
            ust = ay_listesi[:robot["yuva"]] if robot.get("kati") else ay_listesi
            if kod not in ust:
                neden = "listeden düştü" if ay_listesi or not robot.get("piyasa") else "piyasa zayıf: nakite geç"
        elif tur == "erken" and robot.get("sablon_cik") and not h.get("tk", {}).get("sablon") and h.get("tk", {}).get("durum") != "AL":
            neden = "şablon bozuldu"
        if not neden and robot.get("sure") and p["gun"] >= robot["sure"]:
            neden = f"{robot['sure']} işlem günü doldu"
        if neden:
            p["sat"] = neden
            # satışın 'neden'i: tepe kapanış, iz seviyesi, karar günü kapanışı (+ kilitli tabanda bekleme emir_uygula'da)
            p["sat_not"] = {"tp": _r(p["tepe"]), "k": _r(f), **({"iz": _r(p["tepe"] * (1 - robot["iz"]))} if robot.get("iz") else {})}
            emir.append({"kod": kod, "yon": "SAT", "neden": neden})
    # 3b) 🛡️ kırpma: bir hisse kasanın B['kirp'] oranını aştıysa fazlası satılır (pozisyon kapanmaz → yuva AÇMAZ)
    if B.get("kirp"):
        satilacak = {e["kod"] for e in emir if e["yon"] == "SAT"}
        for kod, p in kasa["poz"].items():
            if kod in satilacak or kod in KESIRLI or not p.get("fiyat"):
                continue
            fazla = p["adet"] * p["fiyat"] - B["kirp"] * deger
            n = math.floor(fazla / p["fiyat"]) if fazla > 0 else 0
            if n > 0 and n < p["adet"]:
                emir.append({"kod": kod, "yon": "SAT", "adet": n, "neden": "bekçi: kasanın %%%d'ini aştı, fazlası satıldı" % round(B["kirp"] * 100)})
    # 4) girişler. Boş yuva = yuva − (pozisyon − yarın TAMAMEN satılacaklar). Kırpma (kısmi satış) ve kilitli tabanda bekleyen
    #    satış (dün de satılamadı) yuva açmaz. Nakit yuva payının yarısından azsa alım yok (satışların tahmini geliri dahil).
    if kasa["durdu"] == 0:
        tam = [e["kod"] for e in emir if e["yon"] == "SAT" and (not YUVA_DUZELTME or (not e.get("adet")
                                                                                   and not kasa["poz"][e["kod"]].get("kilit")))]
        bos = robot["yuva"] - (len(kasa["poz"]) - len(tam))
        pay = min(1.0 / robot["yuva"], B["tek_hisse"])
        hedef = pay * deger
        if tur == "momentum":
            aday = [k for k in (ay_listesi or []) if k not in kasa["poz"]]
        elif tur == "rastgele":
            k_say = sum(1 for k, h in hs.items() if h["tk"]["bugun"] and not (robot.get("filtre") and h.get("riskli")))
            if k_say and bos > 0:
                havuz = sorted(k for k in gv["evren"] if k not in kasa["poz"]
                               and not (robot.get("filtre") and (hs.get(k) or {}).get("riskli")))
                aday = _rng(gv["tarih"], rid + str(robot.get("tohum", ""))).sample(havuz, min(k_say, len(havuz)))
            else:
                aday = []
        else:
            aday = _al_adaylari(robot, gv, kasa)
        nakit = kasa["nakit"] + sum(kasa["poz"][k]["adet"] * kasa["poz"][k]["fiyat"] * (1 - KOMISYON) for k in tam)
        alinan, atla = 0, []
        for sira, kod in enumerate(aday, 1):
            if alinan >= bos:
                atla.append((kod, "yuva")); continue
            if KUCUK_ALIM and nakit < KUCUK_ALIM * hedef:
                atla.append((kod, "nakit")); continue
            h = hs.get(kod) or {}
            e = {"kod": kod, "yon": "AL", "pay": pay, "not": _al_notu(tur, h, len(aday), max(bos, 0), sira)}
            if tur == "dip":
                e["stop"] = h["sd"]["destek"] * (1 - h["sd"]["tol"])
                e["hedef"] = h["sd"]["direnc"]
            emir.append(e)
            nakit -= min(hedef, nakit)
            alinan += 1
        if atla:
            if tur == "kirilim":     # 🚀 kaçan roketler (sonuçları canlıda tk'den, tekrar oynatmada v3 işleminden)
                kasa.setdefault("atla", []).extend([gv["tarih"], k, n] for k, n in atla)
            else:
                kasa.setdefault("atla_n", []).append([gv["tarih"], sum(1 for _, n in atla if n == "yuva"),
                                                      sum(1 for _, n in atla if n == "nakit")])
    kasa["bekleyen"] = emir
    return emir


def emir_uygula(kasa, acilis, tarih, kayma_adim=1):
    """Ertesi gün ilk taramada: kasa['bekleyen'] emirlerini o günün açılışıyla uygular.
    acilis = {kod: {"fiyat": açılış, "kilit_taban": bool, "kilit_tavan": bool}} (XU100 / ALTIN / USD için de;
    MEVDUAT için {"faiz": politika faizi %}). Önce satışlar. Yuvalar doluyken (satış gerçekleşmediyse) ve nakit yuva
    payının yarısından azsa alım yazılmaz; kasa['_red'] = [(kod, neden)] (olay akışı için)."""
    kalan, red = [], []
    emirler = kasa.get("bekleyen", [])
    poz = kasa["poz"]
    yuva = (ROBOTLAR.get(kasa.get("robot")) or {}).get("yuva")
    for e in [e for e in emirler if e["yon"] == "SAT"]:
        kod = e["kod"]
        p = poz.get(kod); a = acilis.get(kod)
        if p is None:
            continue
        if not a or not a.get("fiyat") or a.get("kilit_taban"):
            if not e.get("adet"):
                p["kilit"] = p.get("kilit", 0) + 1           # tam satış bekliyor: bu pozisyon yarın da yuva açmış sayılmaz
            kalan.append(e); continue                         # kilitli taban / veri yok: ertesi gün yeniden denenir
        mk = MAKAS.get(kod, 0.0)
        if kod in KESIRLI:
            f, kom_oran = a["fiyat"] * (1 - mk), (KOMISYON if kod == XU else 0.0)
        else:
            f, kom_oran = max(a["fiyat"] - kayma_adim * fiyat_adimi(a["fiyat"]), 0.01), KOMISYON
        adet = min(e.get("adet") or p["adet"], p["adet"])
        tutar = adet * f
        kom = tutar * kom_oran
        kasa["nakit"] += tutar - kom
        net = (tutar - kom) - adet * p["maliyet"]
        kayit = {"t": tarih, "kod": kod, "yon": "SAT", "adet": adet, "fiyat": round(f, 4),
                 "kz": round(net, 2), "kz_yuzde": round((tutar - kom) / (adet * p["maliyet"]) * 100 - 100, 2),
                 "giris": p["tarih"], "neden": e.get("neden"), **({"kismi": 1} if adet < p["adet"] else {})}
        if mk:
            kayit["makas"] = round(adet * a["fiyat"] * mk, 2)
        if adet >= p["adet"] and (p.get("sat_not") or p.get("kilit")):
            kayit["not"] = dict(p.get("sat_not") or {}, **({"kb": p["kilit"]} if p.get("kilit") else {}))
        kasa["defter"].append(kayit)
        if adet < p["adet"]:
            p["adet"] -= adet
        else:
            del poz[kod]
    deger = kasa["deger"]
    for e in [e for e in emirler if e["yon"] == "AL"]:
        kod = e["kod"]
        a = acilis.get(kod)
        if kod == MEVDUAT:
            if a and a.get("faiz") is not None and kasa["nakit"] > 1 and not kasa.get("mevduat"):
                mevduat_ac(kasa, tarih, a["faiz"])
            continue
        ekle = kod in poz and e.get("tutar") is not None      # Dengeci: var olan kesirli kaleme ekleme
        if (kod in poz and not ekle) or not a or not a.get("fiyat") or a.get("kilit_tavan"):
            continue                                          # kilitli tavan: alınamadı (emir iptal)
        if YUVA_DUZELTME and yuva and not ekle and len(poz) >= yuva:
            red.append((kod, "yuva")); continue               # satış gerçekleşmedi (kilitli taban): 11. pozisyon açılmaz
        hedef = e["tutar"] if e.get("tutar") is not None else e["pay"] * deger
        if kod not in KESIRLI and KUCUK_ALIM and kasa["nakit"] < KUCUK_ALIM * hedef:
            red.append((kod, "nakit")); continue              # küçük kırıntı alım yok
        mk = MAKAS.get(kod, 0.0)
        if kod in KESIRLI:
            f, ek = a["fiyat"] * (1 + mk), (BSMV if mk else KOMISYON)
        else:
            f, ek = a["fiyat"] + kayma_adim * fiyat_adimi(a["fiyat"]), KOMISYON
        hedef = min(hedef, kasa["nakit"])
        birim = f * (1 + ek)
        adet = hedef / birim if kod in KESIRLI else math.floor(hedef / birim)
        if adet <= 0:
            continue
        tutar = adet * f
        kom = tutar * ek
        kasa["nakit"] -= tutar + kom
        kayit = {"t": tarih, "kod": kod, "yon": "AL", "adet": adet, "fiyat": round(f, 4)}
        if mk:
            kayit["makas"], kayit["bsmv"] = round(adet * a["fiyat"] * mk, 2), round(kom, 2)
        if e.get("not"):
            kayit["not"] = e["not"]
        if ekle:
            p = poz[kod]
            p["maliyet"] = (p["adet"] * p["maliyet"] + tutar + kom) / (p["adet"] + adet)
            p["adet"] += adet
        else:
            poz[kod] = {"adet": adet, "maliyet": (tutar + kom) / adet, "tarih": tarih, "fiyat": a["fiyat"] if kod in KESIRLI else f,
                        "tepe": a["fiyat"] if kod in KESIRLI else f,
                        "gun": 0, **({"stop": e["stop"], "hedef": e.get("hedef")} if "stop" in e else {})}
        kasa["defter"].append(kayit)
    kasa["bekleyen"] = kalan
    kasa["_red"] = red
    return kasa


def seri_degerler(kasa):
    return [x[1] for x in kasa["seri"]]


def skor_satiri(kasa, xu_bas, xu_son, bant_yuzde=None):
    """Skor tablosu için robot başına gösterilecek istatistikler (yanılgıya karşı: getiri TEK BAŞINA gösterilmez).
    xu_bas: robotun başladığı günkü BIST 100 (sonradan katılan robotlar için kendi başlangıcı)."""
    sat = [e for e in kasa["defter"] if e["yon"] == "SAT" and not e.get("kismi")]
    seri = seri_degerler(kasa) or [BASLANGIC]
    tepe, dd = seri[0], 0.0
    for v in seri:
        tepe = max(tepe, v); dd = min(dd, v / tepe - 1)
    return {"getiri": round((kasa["deger"] / BASLANGIC - 1) * 100, 1),
            "xu_fark": round(((kasa["deger"] / BASLANGIC) / (xu_son / xu_bas) - 1) * 100, 1),
            "en_buyuk_dusus": round(dd * 100, 1),
            "islem": sum(1 for e in kasa["defter"] if e["yon"] == "AL"),
            "isabet": round(100 * sum(1 for e in sat if e["kz"] > 0) / len(sat)) if sat else None,
            "acik": len(kasa["poz"]), "gun": len(seri),
            "sans_yuzde": bant_yuzde,          # 🎲 şans bandındaki yeri (replay/200 zar)
            "durdu": kasa["durdu"]}


# ================== ODA: canlı + tekrar oynatma ortak katman ==================
ODA = "oda.json"
ODA_HTML = "oda.html"
SURUM = 2
OLAY_N = 300              # oda.json'daki olay akışı (son N)
SANS_N = 200              # tekrar oynatmada 🎲 şans bandı ve ikiz deneme sayısı (oda_replay.py)
# sayfa / kart için ek bilgiler (kurallar yukarıda, ROBOTLAR'da)
ROBOT_EK = {
    "kirilimci": {"renk": "#FF6FB5"},
    "kirilimci20": {"renk": "#FF9ED2", "kisa": "Kırılımcı·20",
                    "not": "Kıyas amaçlı: aynı kural, yarı büyüklükte 20 pozisyon. Gece araştırmasında (2022-26, 1 yıllık kayan "
                           "pencereler) 20 yuva 10 yuvadan biraz daha iyi ve daha az düşüşlü çıktı; 2022-23 düşük faiz döneminde "
                           "başlayan pencerelerde ise geride kaldı."},
    "siki": {"renk": "#E879F9", "kisa": "Sıkı çizgi"},
    "erkenci": {"renk": "#5BD6FF"},
    "momentumcu": {"renk": "#FFC94D"},
    "dipavcisi": {"renk": "#7CF29A",
                  "not": "Ders robotu: çok sık işlem yapıyor; komisyon + kayma kazancı eritiyor (araştırmada 4 yılda ~1.300 "
                         "işlem, −%40). 'Çok işlem = komisyon erir' örneği olarak odada."},
    "uzunvadeci": {"renk": "#34D399"},
    "rsi": {"renk": "#F97316", "kisa": "RSI dönüşçü", "not": "TAHMİNİ: arkadaşın AL kuralından; çıkış kuralı bilinmediği için %20 iz stop varsayıldı."},
    "rastgele": {"renk": "#FF9A62", "not": "Kıyas: aynı gün aynı sayıda rastgele hisse. Bir robot bunu geçemiyorsa seçimi "
                                           "şanstan ayrılmıyor demektir. Bu hisse evreninde (2022-26) rastgele bile "
                                           "çoğu zaman BIST 100'ü yendi — 'endeksi yendi' tek başına başarı değil."},
    "endeksci": {"renk": "#B9A6FF", "not": "Kıyas çizgisi: BIST 100 al-tut (fiyat endeksi; temettü yok)."},
    "faizci": {"renk": "#60A5FA", "not": "Birikim kıyası (yarışmacı değil). Politika faizi gerçek mevduat faizinden farklı olabilir; "
                                         "kasa değeri vadenin bugüne kadar işlemiş net faizini de içerir (vade bozulursa alınmaz)."},
    "altinci": {"renk": "#FACC15", "not": "Birikim kıyası (yarışmacı değil). Fiyat: ons altın (GC=F vadeli) × USD/TL ÷ 31,1035 — "
                                          "Kapalıçarşı/banka fiyatından birkaç puan farklı olabilir."},
    "dolarci": {"renk": "#4ADE80", "not": "Birikim kıyası (yarışmacı değil). Döviz hesabının faizi yok sayıldı."},
    "dengeci": {"renk": "#C4B5FD", "not": "Birikim kıyası (yarışmacı değil): mevduat + altın + BIST 100 üçte bir."},
}
PENCERE_NOT = ("İlk aylarda sıralama büyük ölçüde şans: araştırmada 1 aylık pencerelerde birinci robotun ertesi ay da birinci "
               "kalma oranı %13'tü (şansla aynı, ~%14).")


def em_ad(rid):
    """'🚀 Kırılımcı' → ('🚀', 'Kırılımcı')"""
    a = ROBOTLAR[rid]["ad"]
    e, _, ad = a.partition(" ")
    return e, ad


def grup(rid):
    t = ROBOTLAR[rid]["tur"]
    return "birikim" if t in BIRIKIM_TUR else ("kiyas" if t in ("endeks", "rastgele") else "yaris")


def robot_meta():
    """Sayfa için robot listesi (kurallar ROBOTLAR'dan; tek kaynak)."""
    out = []
    for rid, rb in ROBOTLAR.items():
        em, ad = em_ad(rid)
        ek = ROBOT_EK.get(rid, {})
        out.append({"id": rid, "em": em, "ad": ad, "kisa": ek.get("kisa", ad), "renk": ek.get("renk", "#B596FF"), "kural": rb["aciklama"],
                    "not": ek.get("not"), "tahmini": rid == "rsi", "bekci": rb["tur"] not in KIYAS_TUR, "grup": grup(rid),
                    "tur": rb["tur"], "yuva": rb.get("yuva")})
    return out


def bekci_hal(kasa):
    if kasa.get("durdu", 0) > 0:
        return "durdu" if kasa.get("durdu_neden") == "dusus_aktif" else "mola"
    return "aktif"


def _tl(x):
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _yz(x):
    return ("+" if x >= 0 else "−") + "%" + f"{abs(x):.1f}".replace(".", ",")


def yeni_durum(tarih):
    """Canlı oda başlangıcı: her robot 100.000 sanal TL nakit, hiç işlem yok."""
    return {"v": SURUM, "bas": tarih, "son_tarih": None, "tg_tarih": None, "guncel": None, "bekci": BEKCI,
            "xu": [], "robot": {rid: yeni_kasa(rid, tarih) for rid in ROBOTLAR}, "olay": [], "anlik": None, "makro": {}}


def _adet_tr(kod, adet):
    if kod == ALTIN:
        return _tl(adet) + " gr"
    return _tl(adet) if kod in KESIRLI else str(adet)


def defter_olay(rid, e):
    """Defter kaydı → olay akışı metni."""
    y = e["yon"]
    if y == "AL":
        return f"{e['kod']} aldı: {_adet_tr(e['kod'], e['adet'])} × {_tl(e['fiyat'])} TL"
    if y == "SAT":
        return f"{e['kod']} {'kısmen ' if e.get('kismi') else ''}sattı ({e.get('neden') or ''}) {_yz(e['kz_yuzde'])}"
    if y == "MEV":
        return f"32 günlük mevduat açtı: {_tl(e['adet'])} TL, yıllık %{_tl(e['oran'])} (stopaj %{_tl(e['st'] * 100)})"
    if y == "FAIZ":
        return (f"mevduat vadesi doldu: brüt faiz {_tl(e['brut'])} TL, stopaj {_tl(e['stopaj'])} TL; faiziyle yenilendi")
    if y == "TEM":
        return (f"{e['kod']} temettüsü kasaya girdi: net {_tl(e['net'])} TL ({e['adet']} lot × {_tl(e['hisse_basi'])} TL, "
                f"%{TEMETTU_STOPAJ * 100:.0f} stopaj {_tl(e['stopaj'])} TL; hak kullanım {e['ex'][8:10]}.{e['ex'][5:7]})")
    return ""


def gun_isle(dz, tarih, gv, acilis, robotlar=None, bekci=None):
    """Bir işlem günü (canlı ve tekrar oynatma aynı yol): her robot için (1) bekleyen emirleri BUGÜNÜN açılışıyla yaz
    (emir_uygula), (2) bugünün kapanışıyla karar ver (robot_karar). acilis: {kod: {fiyat, kilit_taban, kilit_tavan}}.
    Döner: olay listesi [[tarih, robot|'bekci', metin], ...] (alım-satım, kilit, kaçan roket, 🛡️ Bekçi)."""
    B = dict(BEKCI, **(bekci or {}))
    olay = []
    for rid in (robotlar or ROBOTLAR):
        kasa = dz["robot"][rid]
        em, ad = em_ad(rid)
        tur = ROBOTLAR[rid]["tur"]
        n_def = len(kasa["defter"])
        if kasa["bekleyen"]:
            once = list(kasa["bekleyen"])
            emir_uygula(kasa, acilis, tarih)
            for e in once:
                a = acilis.get(e["kod"]) or {}
                if e["yon"] == "SAT" and e["kod"] in kasa["poz"] and a.get("kilit_taban"):
                    olay.append([tarih, rid, f"{e['kod']} satılamadı: kilitli tabanda alıcı yok, emir ertesi güne kaldı"])
                elif e["yon"] == "AL" and e["kod"] not in kasa["poz"] and a.get("kilit_tavan"):
                    olay.append([tarih, rid, f"{e['kod']} alınamadı: kilitli tavanda satıcı yok (emir iptal)"])
            for kod, n in kasa.pop("_red", []):
                olay.append([tarih, rid, f"{kod} alınamadı: " + ("yuvalar dolu (satış gerçekleşmedi)" if n == "yuva" else
                                                                  "nakit yuva payının yarısından az")])
        n0 = kasa["durdu_neden"]
        emirler = robot_karar(rid, gv, kasa, bekci=bekci)
        for e in kasa["defter"][n_def:]:
            m = defter_olay(rid, e)
            if m:
                olay.append([tarih, rid, m])
        if tur in KIYAS_TUR:
            continue
        for neden, metin in (("yuva", "yuvalar dolu"), ("nakit", "nakit kalmadı, para hisselerde")):
            kac = [k for t, k, n, *_ in kasa.get("atla", ()) if t == tarih and n == neden]
            if kac:
                olay.append([tarih, rid, f"⛔ {', '.join(kac[:6])}{' +' + str(len(kac) - 6) if len(kac) > 6 else ''} "
                                         f"{'roketi' if len(kac) == 1 else 'roketleri'} kaçtı: {metin}"])
        if kasa["durdu_neden"] == "dusus_aktif" and n0 != "dusus_aktif":
            olay.append([tarih, "bekci", f"{em} {ad} DURDURULDU: kasa zirvesinden {_yz((kasa['deger'] / kasa['tepe_deger'] - 1) * 100)} "
                                         f"(sınır −%{B['dusus'] * 100:.0f}); pozisyonlar ertesi açılışta satılacak, "
                                         f"{B['dusus_bekle']} işlem günü yeni alım yok"])
        elif B["gunluk_zarar"] and kasa["deger"] <= kasa["dun_deger"] * (1 - B["gunluk_zarar"]):
            olay.append([tarih, "bekci", f"{em} {ad} bugün {_yz((kasa['deger'] / kasa['dun_deger'] - 1) * 100)}: günlük zarar "
                                         f"sınırı (−%{B['gunluk_zarar'] * 100:.0f}) aşıldı, yarın yeni alım yok"])
        if n0 == "dusus_aktif" and kasa["durdu"] == 0:
            olay.append([tarih, "bekci", f"{em} {ad} yeniden başladı (bekleme bitti)"])
        for e in emirler:
            if e.get("adet") and "kasanın" in (e.get("neden") or ""):
                olay.append([tarih, "bekci", f"{em} {ad}: {e['kod']} kasanın %{B['kirp'] * 100:.0f}'ini aştı; {e['adet']} lot "
                                             f"satılacak (fazlası)"])
    return olay


# ---------------- makro veri: TCMB politika faizi, TÜFE (anahtarsız sayfalar), Yahoo altın/dolar ----------------
TCMB_FAIZ_URL = ("https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Temel+Faaliyetler/Para+Politikasi/"
                 "Merkez+Bankasi+Faiz+Oranlari/1+Hafta+Repo")
TCMB_TUFE_URL = ("https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Istatistikler/Enflasyon+Verileri/"
                 "Tuketici+Fiyatlari")


def _tcmb_metin(url, timeout=20):
    import requests
    h = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout).text
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))


def politika_faizi_tablo():
    """TCMB 1 hafta repo (politika faizi) tablosu → [(yürürlük 'YYYY-MM-DD', yıllık %)] eskiden yeniye."""
    m = re.findall(r"(\d{2})\.(\d{2})\.(\d{4}) - (\d+[\.,]\d+)", _tcmb_metin(TCMB_FAIZ_URL))
    s = sorted({f"{y}-{a}-{g}": float(v.replace(",", ".")) for g, a, y, v in m}.items())
    if not s:
        raise ValueError("politika faizi tablosu boş")
    return s


def tufe_tablo():
    """TCMB TÜFE tablosu → {'YYYY-MM': aylık değişim %}."""
    m = re.findall(r"(\d{2})-(\d{4}) (-?\d+[\.,]\d+) (-?\d+[\.,]\d+)", _tcmb_metin(TCMB_TUFE_URL))
    out = {}
    for a, y, _yil, ay in m:
        out.setdefault(f"{y}-{a}", float(ay.replace(",", ".")))
    if not out:
        raise ValueError("TÜFE tablosu boş")
    return dict(sorted(out.items()))


def tufe_kum(tufe, bas, son):
    """bas tarihinin ayından son tarihin ayına kadar (SON AÇIKLANAN aya kadar) bileşik TÜFE. Döner: (oran, ilk ay, son ay)
    ya da ay yoksa None. Başlangıç ayı tam sayılır."""
    if not tufe:
        return None
    a, b = bas[:7], son[:7]
    aylar = [k for k in sorted(tufe) if a <= k <= b]
    if not aylar:
        return None
    c = 1.0
    for k in aylar:
        c *= 1 + tufe[k] / 100
    return c - 1, aylar[0], aylar[-1]


def _replay_makro(yol="oda_replay.json"):
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f).get("makro") or {}
    except Exception:
        return {}


def makro_guncelle(dz, tarih, yahoo=True):
    """Kesin kapanış işleminde: Yahoo'dan GC=F + USDTRY=X son günler, TCMB'den politika faizi + TÜFE (günde bir kez).
    Her biri ayrı try/except: hata olursa son bilinen değer kalır (ilk kez de olmazsa oda_replay.json'daki son değer);
    tarama ASLA bozulmaz. Döner: makro sözlüğü ve 'notlar' (log için)."""
    M = dz.setdefault("makro", {})
    notlar = []
    if yahoo:
        try:
            import pandas as pd
            import yfinance as yf
            g = yf.download(["GC=F", "USDTRY=X"], period="10d", interval="1d", group_by="ticker", auto_adjust=True,
                            progress=False, threads=False)
            gc = g["GC=F"]["Close"].dropna()
            us = g["USDTRY=X"]["Close"].dropna()
            gc, us = gc[gc.index <= pd.Timestamp(tarih)], us[us.index <= pd.Timestamp(tarih)]
            if len(gc) and len(us) and float(gc.iloc[-1]) > 0 and float(us.iloc[-1]) > 0:
                M["usd"] = round(float(us.iloc[-1]), 4)
                M["gram"] = round(float(gc.iloc[-1]) * M["usd"] / ONS_GRAM, 2)
                M["yahoo_t"] = tarih
            else:
                notlar.append("Yahoo altın/dolar boş")
        except Exception as e:
            notlar.append(f"Yahoo altın/dolar alınamadı ({type(e).__name__})")
    if M.get("tcmb_t") != tarih:
        try:
            pf = [x for x in politika_faizi_tablo() if x[0] <= tarih]
            M["faiz"], M["faiz_t"] = pf[-1][1], pf[-1][0]
        except Exception as e:
            notlar.append(f"politika faizi alınamadı ({type(e).__name__})")
        try:
            M["tufe"] = {k: v for k, v in tufe_tablo().items() if k >= "2021-01"}
        except Exception as e:
            notlar.append(f"TÜFE alınamadı ({type(e).__name__})")
        M["tcmb_t"] = tarih
    if M.get("faiz") is None or not M.get("tufe"):
        r = _replay_makro()
        if M.get("faiz") is None and r.get("faiz"):
            M["faiz_t"], M["faiz"] = r["faiz"]
            notlar.append("politika faizi oda_replay.json'dan")
        if not M.get("tufe") and r.get("tufe"):
            M["tufe"] = dict(r["tufe"])
    return M, notlar


# ---------------- canlı (tarama.py her çalıştığında) ----------------
def _f(x):
    try:
        x = float(x)
        return x if x == x and x > 0 else None
    except (TypeError, ValueError):
        return None


def kilit(c, pc, h, l, yon):
    """Gün boyu kilitli taban (yon −1) / tavan (+1): kapanış ±%9 ve Yüksek−Düşük ≤ %0,15 × kapanış (sinyal.kilitli_gun)."""
    if not (c and pc and h and l):
        return False
    r = c / pc - 1
    return bool((r <= TABAN_GETIRI if yon < 0 else r >= -TABAN_GETIRI) and (h - l) <= KILIT_ARALIK * c)


def gozlem_canli(sonuclar, data, bugun, gerekli=(), buyuk=()):
    """tarama.py'nin bugünkü analiz sonuçlarından robotların gördüğü gün verisi (yeniden veri çekme yok).
    Sadece BUGÜN işlem görmüş hisseler (simülasyonla aynı). rsi_degisim / kijun / uzama sadece gereken hisselerde
    hesaplanır (RSI 24-34 arası: ↩️ adayı olabilir; 📏 robotun elindekiler). Döner: (hisseler, evren, acilis, bolunme)."""
    from sinyal import bolunme_duzelt
    hs, evren, acilis, bol = {}, [], {}, {}
    gerekli, buyuk = set(gerekli), set(buyuk)
    tarih = str(bugun)
    for s in sonuclar:
        kod = s["kod"]
        try:
            df = data[kod + ".IS"].dropna(subset=["Close"])
            if len(df) < 2 or df.index[-1].date() != bugun:
                continue
            o, h, l = _f(df["Open"].iloc[-1]), _f(df["High"].iloc[-1]), _f(df["Low"].iloc[-1])
            c, pc = _f(df["Close"].iloc[-1]), _f(df["Close"].iloc[-2])
        except Exception:
            continue
        if not s.get("fiyat"):
            continue
        b = c / pc if (c and pc and s.get("bolunme") == tarih) else None
        if b:
            bol[kod] = b
        rsi = s.get("rsi")
        d = None
        if kod in gerekli or (rsi is not None and 24 <= rsi <= 34):
            try:
                d = bolunme_duzelt(df[["Open", "High", "Low", "Close", "Volume"]])
            except Exception:
                d = None
        hs[kod] = ozet_hazirla(s, d, buyuk=kod in buyuk)
        if not (s.get("tk") or {}).get("kisa") and not hs[kod]["riskli"]:
            evren.append(kod)
        if o:
            acilis[kod] = {"fiyat": o, "kilit_taban": False if b else kilit(c, pc, h, l, -1),
                           "kilit_tavan": False if b else kilit(c, pc, h, l, 1)}
    return hs, evren, acilis, bol


def bolunme_uygula(dz, bol):
    """Bedelsiz/bölünme günü: elde tutulan adet ve fiyatlar düzeltilir (kasa değişmez; yoksa yanlış 'iz stop' olurdu).
    Tekrar oynatmada gerekmez (fiyatlar zaten düzeltilmiş)."""
    for kasa in dz["robot"].values():
        for kod, b in bol.items():
            p = kasa["poz"].get(kod)
            if not p:
                continue
            p["adet"] = max(1, round(p["adet"] / b))
            for k in ("maliyet", "fiyat", "tepe", "stop", "hedef"):
                if p.get(k):
                    p[k] *= b



def oku(yol=ODA):
    """oda.json'u oku. Eski dosyada olmayan robotlar / alanlar sorun değil (canli_calistir yeni robotları o gün 100.000 TL ile
    ekler; eksik alanlar .get / setdefault ile okunur)."""
    try:
        with open(yol, encoding="utf-8") as f:
            dz = json.load(f)
        if dz.get("v") == SURUM and isinstance(dz.get("robot"), dict):
            dz.setdefault("makro", {})
            dz.setdefault("olay", [])
            return dz
    except Exception:
        pass
    return None


def yaz(dz, yol=ODA):
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(dz, f, ensure_ascii=False, separators=(",", ":"))


def _bilanco_dosya(yol="bilanco.json"):
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f).get("veri") or {}
    except Exception:
        return {}


def temettu_isle(dz, tarih, bil=None, pencere=30):
    """Canlı: hak kullanım (ex) günü elde tutulan hisse için kasaya NET temettü (brüt × %85) girer. Kaynak bilanco.json'daki
    Yahoo temettü listesi ([ex tarihi, hisse başı TL]; 3 günde bir yenilenir → kayıt birkaç gün geç gelebilir, son `pencere`
    gün taranır). Hak kazanmak için alış ex gününden ÖNCE olmalı (ex günü açılışta alan almaz). Her (hisse, ex) bir kez.
    Tekrar oynatmada GEREKMEZ: oradaki Yahoo fiyatları temettü düzeltmeli (temettü brüt olarak fiyata yeniden yatırılmış)."""
    bil = bil if bil is not None else _bilanco_dosya()
    if not bil:
        return []
    olay = []
    alt = str(_gun(tarih) - _dt.timedelta(days=pencere))
    for rid, kasa in dz["robot"].items():
        if ROBOTLAR.get(rid, {}).get("tur") in KIYAS_TUR:
            continue
        bas = max(dz.get("bas") or "", kasa.get("baslangic") or "")
        kodlar = set(kasa["poz"]) | {e["kod"] for e in kasa["defter"] if e["yon"] == "SAT" and e["t"] >= alt}
        alindi = kasa.setdefault("tem", [])
        for kod in sorted(kodlar):
            for ex, tut in ((bil.get(kod) or {}).get("temettu") or []):
                if not (ex > bas and alt <= ex <= tarih) or f"{kod}|{ex}" in alindi or not tut or tut <= 0:
                    continue
                adet = 0
                for e in kasa["defter"]:
                    if e["kod"] != kod or e["t"] >= ex:
                        continue
                    if e["yon"] == "AL":
                        adet += e["adet"]
                    elif e["yon"] == "SAT":
                        adet -= e["adet"]
                p = kasa["poz"].get(kod)
                if p and p["tarih"] < ex and not any(e["kod"] == kod and e["yon"] == "SAT" and e["t"] >= ex for e in kasa["defter"]):
                    adet = p["adet"]                       # bölünme düzeltmesi sonrası güncel adet
                alindi.append(f"{kod}|{ex}")
                if adet <= 0:
                    continue
                brut = adet * tut
                st = brut * TEMETTU_STOPAJ
                kasa["nakit"] += brut - st
                e = {"t": tarih, "kod": kod, "yon": "TEM", "adet": adet, "hisse_basi": tut, "brut": round(brut, 2),
                     "stopaj": round(st, 2), "net": round(brut - st, 2), "ex": ex}
                kasa["defter"].append(e)
                olay.append([tarih, rid, defter_olay(rid, e)])
    return olay


def atla_guncelle(dz, sonuclar):
    """Canlı: kaçan 🚀 roketlerin sonucu (v3'ün kendi işlemi: sinyal günü = giris_tarih; açıksa bugünkü değişim, kapandıysa
    sonuç). Kayıt: [tarih, kod, neden, sonuç %, kapandı 0/1]."""
    tk = {s["kod"]: (s.get("tk") or {}) for s in sonuclar}
    for kasa in dz["robot"].values():
        for a in kasa.get("atla", ()):
            if len(a) >= 5 and a[4] == 1:
                continue
            t = tk.get(a[1])
            if not t or t.get("giris_tarih") != a[0]:
                continue
            r, k = (t.get("degisim"), 0) if t.get("durum") == "AL" else ((t.get("sonuc"), 1) if t.get("durum") == "CIKTI" else (None, 0))
            if r is not None:
                del a[3:]
                a += [r, k]


def ozet_mesaji(dz, url=None):
    """Akşam Telegram'ına TEK mesaj (sade): ilk 3 + son 3 robot (getiri tek başına değil: BIST 100 farkı, en büyük düşüş),
    bugün kim ne aldı/sattı, kasa dolu diye alınamayan roketler, 💰 kıyas satırı (sıralamaya girmez), Bekçi olayları;
    'sıralama şans' notu sadece cuma (ilk 6 ay)."""
    t = dz["son_tarih"]
    xu = dz["xu"]
    xs = [x[1] for x in xu]
    xi = {x[0]: x[1] for x in xu}
    xg = (xs[-1] / xs[0] - 1) * 100 if len(xs) > 1 else 0.0
    yar = [rid for rid in ROBOTLAR if rid in dz["robot"] and grup(rid) != "birikim"]

    def xbas(k):
        s = k.get("seri") or []
        return xi.get(s[0][0], xs[0]) if s else xs[-1]

    sk = sorted(((skor_satiri(dz["robot"][rid], xbas(dz["robot"][rid]), xs[-1]), rid) for rid in yar), key=lambda x: -x[0]["getiri"])

    def satir(i, s, rid):
        em, ad = em_ad(rid)
        dur = {"durdu": " ⛔ Bekçi durdurdu", "mola": " ⏸️ mola"}.get(bekci_hal(dz["robot"][rid]), "")
        return (f"{i}) {em} {ad} {_yz(s['getiri'])} · BIST 100'e göre {_puan(s['xu_fark'])} · en büyük düşüş "
                f"{_yz(s['en_buyuk_dusus'])}{dur}")
    bugun = [(rid, e) for rid in yar for e in dz["robot"][rid]["defter"] if e["t"] == t and e["yon"] in ("AL", "SAT")]
    m = [f"🏢 <b>İşlem odası</b> — {t[8:10]}.{t[5:7]}.{t[:4]} (sanal para, {len(xs)}. gün, bugün {len(bugun)} işlem)"]
    if len(sk) <= 6:
        m += [satir(i, s, rid) for i, (s, rid) in enumerate(sk, 1)]
    else:
        m.append("<b>İlk 3</b>")
        m += [satir(i, s, rid) for i, (s, rid) in enumerate(sk[:3], 1)]
        m.append("<b>Son 3</b>")
        m += [satir(i, s, rid) for i, (s, rid) in list(enumerate(sk, 1))[-3:]]
    if bugun:
        par = []
        for rid in yar:
            al = [e["kod"] for r, e in bugun if r == rid and e["yon"] == "AL"]
            sa = [f"{e['kod']} {_yz(e['kz_yuzde'])}" for r, e in bugun if r == rid and e["yon"] == "SAT" and not e.get("kismi")]
            if not (al or sa):
                continue
            em = em_ad(rid)[0]
            k = []
            if al:
                k.append("AL " + ", ".join(al[:4]) + (f" +{len(al) - 4}" if len(al) > 4 else ""))
            if sa:
                k.append("SAT " + ", ".join(sa[:3]) + (f" +{len(sa) - 3}" if len(sa) > 3 else ""))
            par.append(f"{em} " + " · ".join(k))
        m.append("Bugün: " + " | ".join(par))
    else:
        m.append("Bugün alım-satım yok.")
    kac = {}
    for rid in yar:
        if ROBOTLAR[rid]["tur"] != "kirilim":
            continue
        n = sum(1 for a in dz["robot"][rid].get("atla", ()) if a[0] == t)    # yuva dolu ya da nakit kalmadı
        if n:
            kac[rid] = n
    if kac:
        enc = max(kac.values())
        m.append(f"🚫 Kasa dolu, bugün {enc} roket alınamadı (" + ", ".join(f"{em_ad(r)[0]} {n}" for r, n in kac.items()) + ")")
    m.append(f"BIST 100 aynı dönemde {_yz(xg)}")
    ky = kiyas_satiri(dz)
    if ky:
        m.append(ky)
    bek = [o[2] for o in dz["olay"] if o[0] == t and o[1] == "bekci"]
    if bek:
        m.append("🛡️ " + " · ".join(bek[:3]))
    if len(xs) < 126 and _gun(t).weekday() == 4:
        m.append(f"<i>{PENCERE_NOT} 🎲 Rastgele'yi geçemeyen robotun seçim becerisi yok sayılır.</i>")
    if url:
        m.append(f"<a href=\"{url}oda.html\">Odayı aç</a>")
    m.append("<i>Sanal para; yatırım tavsiyesi değil.</i>")
    return chr(10).join(m)


def kiyas_satiri(dz):
    """'Kıyas: Faiz +x% · Altın +y% · Dolar +z% · TÜFE +t%' (her biri kendi başlangıcından; TÜFE son açıklanan aya kadar)."""
    p = []
    bas = None
    for rid, ad in (("faizci", "Faiz"), ("altinci", "Altın"), ("dolarci", "Dolar")):
        k = dz["robot"].get(rid)
        if not k or not k.get("seri"):
            continue
        bas = bas or k["seri"][0][0]
        p.append(f"{ad} {_yz((k['deger'] / BASLANGIC - 1) * 100)}")
    if not p:
        return ""
    tf = tufe_kum((dz.get("makro") or {}).get("tufe"), bas, dz["son_tarih"])
    p.append(f"TÜFE {_yz(tf[0] * 100)} ({tf[2][5:7]}.{tf[2][:4]}'e kadar)" if tf else "TÜFE henüz açıklanmadı")
    return "💰 Kıyas: " + " · ".join(p)


def _puan(x):
    return ("+" if x >= 0 else "−") + f"{abs(x):.1f}".replace(".", ",") + " puan"


def canli_calistir(sonuclar, data, simdi, kesin, tg_gonder=None, url=None, buyuk=(), yol=ODA, html_yol=ODA_HTML, temettu=None,
                   makro=True):
    """tarama.py her çalıştığında çağrılır (çağıran try/except'li: oda hatası taramayı bozmaz). Kesin kapanıştan sonra
    günde bir kez gün işlenir + akşam tek Telegram özeti; gün içinde sadece anlık kasa değeri güncellenir.
    temettu: tarama'nın bilanço verisi ({kod: {temettu: [[ex, TL]...]}}); yoksa bilanco.json okunur."""
    bugun = simdi.date()
    tarih = str(bugun)
    dz = oku(yol) or yeni_durum(tarih)
    try:
        xdf = data[XU + ".IS"].dropna(subset=["Close"])
        xu_bugun = xdf.index[-1].date() == bugun
        xc = xdf["Close"]
        xu = {"fiyat": float(xc.iloc[-1]), "ust": bool(xc.iloc[-1] > xc.rolling(50).mean().iloc[-1])}
        xo = _f(xdf["Open"].iloc[-1]) or xu["fiyat"]
    except Exception:
        xu_bugun, xu, xo = False, None, None
    sonuc = "değişiklik yok"
    if kesin and simdi.weekday() < 5 and xu_bugun and (dz["son_tarih"] or "") < tarih:
        ilk = dz["son_tarih"] is None
        yeni = [rid for rid in ROBOTLAR if rid not in dz["robot"]]
        for rid in yeni:                         # sonradan eklenen robotlar canlıya BUGÜNDEN 100.000 TL ile katılır
            dz["robot"][rid] = yeni_kasa(rid, tarih)
        M, mn = makro_guncelle(dz, tarih, yahoo=makro)
        hs, evren, acilis, bol = gozlem_canli(sonuclar, data, bugun, gerekli=dz["robot"]["siki"]["poz"] if "siki" in dz["robot"] else (),
                                              buyuk=buyuk)
        acilis[XU] = {"fiyat": xo}
        if M.get("gram"):
            acilis[ALTIN] = {"fiyat": M["gram"]}
        if M.get("usd"):
            acilis[USD] = {"fiyat": M["usd"]}
        acilis[MEVDUAT] = {"fiyat": 1.0, "faiz": M.get("faiz")}
        bolunme_uygula(dz, bol)
        try:
            olay0 = temettu_isle(dz, tarih, temettu)
        except Exception as e:
            olay0 = []
            mn.append(f"temettü işlenemedi ({type(e).__name__})")
        gv = {"tarih": tarih, "ay_ilk": ilk or dz["son_tarih"][:7] != tarih[:7], "xu": xu, "hisseler": hs, "evren": evren,
              "piyasa": {ALTIN: M.get("gram"), USD: M.get("usd"), "faiz": M.get("faiz")}}
        olay = olay0 + gun_isle(dz, tarih, gv, acilis)
        try:
            atla_guncelle(dz, sonuclar)
        except Exception:
            pass
        dz["xu"].append([tarih, round(xu["fiyat"], 2)])
        dz["olay"] = (dz["olay"] + olay)[-OLAY_N:]
        dz["son_tarih"], dz["anlik"], dz["guncel"] = tarih, None, simdi.strftime("%Y-%m-%dT%H:%M")
        if ilk:
            dz["tg_tarih"] = tarih   # ilk gün henüz sonuç yok: mesaj yok (fork'ta durum kaydedilmiyorsa da her akşam mesaj gitmez)
        emir = sum(len(k["bekleyen"]) for k in dz["robot"].values())
        sonuc = (f"{tarih} işlendi ({len(hs)} hisse, {len(olay)} olay, sonraki açılış için {emir} emir"
                 + (f"; yeni robot: {', '.join(yeni)}" if yeni else "") + (f"; {'; '.join(mn)}" if mn else "") + ")")
    elif dz["son_tarih"] and not kesin and simdi.weekday() < 5:
        F = {s["kod"]: _f(s.get("fiyat")) for s in sonuclar}
        if xu:
            F[XU] = xu["fiyat"]
        k = {rid: round(kasa_anlik(kasa, F, tarih)) for rid, kasa in dz["robot"].items()}
        dz["anlik"] = {"t": simdi.strftime("%Y-%m-%d %H:%M"), "k": k, "xu": round(xu["fiyat"], 2) if xu else None}
        sonuc = "gün içi kasa değeri güncellendi"
    if dz["son_tarih"] == tarih and dz.get("tg_tarih") != tarih and tg_gonder:
        if tg_gonder(ozet_mesaji(dz, url)):
            dz["tg_tarih"] = tarih
            sonuc += "; Telegram özeti gönderildi"
    yaz(dz, yol)
    html_yaz(html_yol)
    return sonuc


def html_yaz(yol=ODA_HTML):
    """oda.html'i şablondan yaz (sadece değiştiyse). Fork'larda da *.py ile gelir; sayfa kendiliğinden oluşur."""
    try:
        with open(yol, encoding="utf-8") as f:
            if f.read() == ODA_SAYFA:
                return False
    except OSError:
        pass
    with open(yol, "w", encoding="utf-8", newline="\n") as f:
        f.write(ODA_SAYFA)
    return True


# ===== ŞABLON (oda.html) — düzenlerken: tek tırnaklı JS dizelerinde kesme işaretinden önce ters bölü; sonra node --check =====
_SABLON = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>İşlem Odası</title>
<style>
:root{--bg:#F4F1FB;--panel:#FFFFFF;--ink:#1D1530;--muted:#6E6488;--line:#E3DCF2;--accent:#6D3FD8;--pos:#1B8A52;--neg:#C2412F;
--chip:#EFE9FB;--salon1:#1A1033;--salon2:#251549}
@media (prefers-color-scheme:dark){:root{--bg:#0F0A1E;--panel:#19122E;--ink:#ECE7FA;--muted:#A79BC8;--line:#2E2450;--accent:#B596FF;
--pos:#5BD69A;--neg:#FF7A6B;--chip:#241A40}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
font-feature-settings:"tnum" 1;-webkit-font-smoothing:antialiased}
a{color:var(--accent)}
.ust{display:flex;flex-wrap:wrap;align-items:center;gap:10px 16px;padding:14px 18px;border-bottom:1px solid var(--line);background:var(--panel)}
.ust h1{font-size:18px;margin:0;font-weight:700}.ust .alt{color:var(--muted);font-size:12.5px}
.ust .sag{margin-left:auto;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.seg button{border:0;background:transparent;color:var(--ink);padding:7px 12px;font:inherit;font-size:13px;cursor:pointer}
.seg button.on{background:var(--accent);color:#fff}
.btn{border:1px solid var(--line);background:var(--chip);color:var(--ink);border-radius:9px;padding:6px 11px;font:inherit;font-size:13px;cursor:pointer}
.btn:disabled{opacity:.5;cursor:default}
select.btn{padding:6px 8px}
.chip{background:var(--chip);border-radius:999px;padding:5px 11px;font-size:12.5px;color:var(--muted)}
.chip b{color:var(--ink)}
.oyn{display:none;align-items:center;gap:8px;flex-wrap:wrap;padding:10px 18px;border-bottom:1px solid var(--line);background:var(--panel)}
.oyn.on{display:flex}.oyn input[type=range]{flex:1;min-width:160px;accent-color:var(--accent)}
.ana{display:grid;grid-template-columns:minmax(0,1fr) 370px;gap:16px;padding:16px 18px;max-width:1500px;margin:0 auto}
@media(max-width:980px){.ana{grid-template-columns:minmax(0,1fr)}}
.ana>div{min-width:0}
@media(max-width:560px){.ana{padding:12px 10px}.ust{padding:12px 12px}.oyn{padding:8px 12px}.salon svg{min-width:600px}.alt-bilgi{padding:0 12px 30px}}
.salon{border-radius:16px;background:radial-gradient(120% 90% at 50% 10%,var(--salon2),var(--salon1));overflow-x:auto;
border:1px solid #3A2770;position:relative}
.salon svg{display:block;width:100%;min-width:620px;height:auto}
.not{position:absolute;left:14px;top:12px;right:14px;color:#D9CCFF;font-size:12.5px;pointer-events:none}
.kart{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin-bottom:14px}
.kart h2{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 8px;font-weight:700}
.sk{display:flex;align-items:center;gap:10px;padding:8px 6px;border-radius:10px;cursor:pointer;border-bottom:1px solid var(--line)}
.sk:last-child{border-bottom:0}.sk:hover{background:var(--chip)}
.sk .no{width:18px;color:var(--muted);font-size:12px;text-align:right}
.sk .ad{flex:1;min-width:0}.sk .ad b{font-size:14px}.sk .ad .m{color:var(--muted);font-size:11.5px;margin-top:2px;line-height:1.35}
.sk .g{font-size:17px;font-weight:700;text-align:right;white-space:nowrap}.sk .g small{display:block;font-size:11px;font-weight:500;color:var(--muted)}
.pos{color:var(--pos)}.neg{color:var(--neg)}
.dur{font-size:10.5px;border-radius:6px;padding:1px 6px;margin-left:4px;vertical-align:1px}
.dur.p{background:#1B8A5222;color:var(--pos)}.dur.n{background:#8880a022;color:var(--muted)}.dur.d{background:#C2412F22;color:var(--neg)}.dur.m{background:#D9A11B22;color:#B7860B}
.sans{font-size:12px;color:var(--muted);margin-top:8px;line-height:1.45}
.akis{max-height:360px;overflow-y:auto;font-size:12.5px}
.ol{display:flex;gap:8px;padding:6px 2px;border-bottom:1px dashed var(--line);line-height:1.35}
.ol .t{color:var(--muted);white-space:nowrap;font-size:11.5px;min-width:42px}
.ol.bk{background:#D9A11B14}
.bek{font-size:12.5px;line-height:1.5;margin-bottom:8px}
.alt-bilgi{max-width:1500px;margin:0 auto;padding:0 18px 40px;color:var(--muted);font-size:13px;line-height:1.55}
.alt-bilgi .kural{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;margin:10px 0}
.alt-bilgi .kural div{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 12px;color:var(--ink)}
.uyari{background:var(--chip);border-radius:12px;padding:10px 14px;color:var(--ink)}
.perde{position:fixed;inset:0;background:#0008;display:none;align-items:flex-start;justify-content:center;padding:30px 12px;overflow-y:auto;z-index:9}
.perde.on{display:flex}
.pen{background:var(--panel);color:var(--ink);border-radius:16px;max-width:720px;width:100%;min-width:0;padding:16px 18px;border:1px solid var(--line)}
.pen h3{margin:0 0 4px;font-size:18px}.pen .kapat{float:right}
.pen table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px}
.pen th,.pen td{padding:5px 6px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}.pen th{color:var(--muted);font-weight:600}
.pen .tb{overflow-x:auto}
.pen .ist{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.pen .ist div{background:var(--chip);border-radius:10px;padding:6px 10px;font-size:12px;color:var(--muted)}.pen .ist b{display:block;color:var(--ink);font-size:15px}
.r{text-align:right!important}
/* salon */
.akan{stroke-dasharray:4 7;animation:ak 1.6s linear infinite}
@keyframes ak{to{stroke-dashoffset:-22}}
.yan{animation:yan 1.2s ease-in-out infinite alternate}
@keyframes yan{from{opacity:.35}to{opacity:1}}
.rb{cursor:pointer}.rb:hover .etk rect{stroke-width:2.2}
.parla{stroke-width:3!important;opacity:1!important}
.band{fill:#8E88A8;opacity:.18}
.etk-t{font-size:10px;font-weight:800;fill:#140C2A}
.sk .not2{font-size:11px;color:var(--muted);margin-top:3px;font-style:italic}
.uyar6{background:#D9A11B18;border-radius:10px;padding:7px 10px;font-size:12px;margin:0 0 8px;line-height:1.4}
.bkb{margin:10px 0 2px;padding:6px 8px;border-radius:9px;background:#60A5FA14;font-size:12px;color:var(--muted)}
.bkb b{color:var(--ink)}
.sk.bir .g{font-size:15px}
.isi{overflow-x:auto;font-size:11px}
.isi table{border-collapse:collapse}
.isi th,.isi td{padding:3px 4px;text-align:right;white-space:nowrap;border-bottom:1px solid var(--line)}
.isi th{color:var(--muted);font-weight:600;position:sticky;top:0;background:var(--panel)}
.isi td.ad,.isi th.ad{text-align:left;position:sticky;left:0;background:var(--panel);z-index:1;max-width:150px;overflow:hidden;text-overflow:ellipsis}
.isi td.c{min-width:40px;color:var(--ink)}
.kac{background:var(--chip);border-radius:10px;padding:8px 10px;font-size:12.5px;line-height:1.5;margin:8px 0}
.pen td.ned{white-space:normal;min-width:160px;color:var(--muted);font-size:11.5px}
.donnot{display:none;padding:8px 18px 10px;border-bottom:1px solid var(--line);background:var(--panel);color:var(--muted);font-size:12.5px;line-height:1.5}
.donnot.on{display:block}.donnot b{color:var(--ink)}
.ozel{display:none;align-items:center;gap:6px;flex-wrap:wrap}.ozel.on{display:inline-flex}
.ozel input{border:1px solid var(--line);background:var(--chip);color:var(--ink);border-radius:9px;padding:5px 7px;font:inherit;font-size:13px;color-scheme:light dark}
@media(max-width:560px){.donnot{padding:8px 12px 10px}.oyn input[type=range]{min-width:100%;order:9}}
</style></head><body>
<div class="ust"><div><h1>🏢 İşlem Odası</h1><div class="alt">Sanal parayla kural robotları · <a href="index.html">← Panoya dön</a></div></div>
<div class="sag"><div class="seg"><button id="m_canli" class="on" onclick="mod('canli')">● Canlı</button><button id="m_rep" onclick="mod('rep')">⟲ Tekrar oynat</button></div>
<span class="chip" id="gun">yükleniyor…</span></div></div>
<div class="oyn" id="oyn"><select class="btn" id="don" onchange="donSec(this.value)" title="Hangi dönemi oynatayım?" aria-label="Dönem"></select>
<span class="ozel" id="ozel"><input type="date" id="oz_a" aria-label="Başlangıç"> → <input type="date" id="oz_b" aria-label="Bitiş"><button class="btn" onclick="ozelUygula()">Uygula</button></span>
<button class="btn" id="b_oyn" onclick="oynat()">▶ Oynat</button>
<select class="btn" id="hiz" onchange="HIZ=+this.value" title="Hız: saniyede kaç işlem günü"><option value="1">1x</option><option value="5" selected>5x</option><option value="20">20x</option><option value="60">60x</option></select>
<input type="range" id="sur" min="0" max="0" value="0" oninput="git(+this.value)" aria-label="Gün">
<span class="chip" id="rgun"></span></div>
<div class="donnot" id="donnot"></div>
<div class="ana"><div><div class="salon" id="salon"><svg id="sv" viewBox="-700 -185 1500 940" role="img" aria-label="İzometrik işlem salonu: robot masaları, borsa tahtası, Risk Bekçisi"></svg><div class="not" id="not"></div></div>
<div class="kart" style="margin-top:14px"><h2>Aylık getiri ısı tablosu</h2><div class="sans" id="isi_not" style="margin:0 0 6px"></div><div class="isi" id="isi"></div></div></div>
<div><div class="kart"><h2>Skor tablosu</h2><div id="uyar6"></div><div id="skor"></div><div class="sans" id="sans"></div></div>
<div class="kart"><h2>Olay akışı</h2><div id="bek"></div><div class="akis" id="akis"></div></div></div></div>
<div class="alt-bilgi"><div class="uyari">⚠️ <b>Sanal para; yatırım tavsiyesi değil.</b> Robotlar panonun kurallarını sanal 100.000 TL ile deniyor; gerçek emir yok, portföyünle ilgisi yok. Kararlar her işlem günü kesin kapanıştan (18:30) sonra verilir, alım-satım <b>ertesi işlem gününün açılış fiyatından</b> yazılır; her yönde %__KOM__ komisyon + 1 fiyat adımı kayma düşülür, lot tam sayı, kilitli tabanda satılamaz, kilitli tavanda alınamaz. Getiri tek başına bir şey söylemez: BIST 100 farkına, en büyük düşüşe, işlem sayısına ve 🎲 şans bandına birlikte bak. Bu hisse evreninde rastgele seçim bile çoğu zaman BIST 100'ü yendi — 'endeksi yendi' tek başına başarı değil. Geçmişte iyi giden kural gelecekte de iyi gitmeyebilir.</div>
<div class="kural" id="kurallar"></div>
<div>🛡️ <b>Risk Bekçisi</b> (Endeksçi hariç): alımda tek hisseye kasanın en fazla %__TEK__'u; sonradan kasanın %__KRP__'ini aşan hissenin fazlası satılır; kasa bir günde %__GZ__+ eridiyse ertesi gün yeni alım yok; kasa zirvesinden %__TD__+ düşerse robot durdurulur — pozisyonları satılır, __DG__ işlem günü yeni alım yapmaz. <b>Bekçi kâr aracı değil, emniyet kemeri:</b> araştırmada (2022-26) robot başına 4 yılda 0-2 kez devreye girdi, getiriye etkisi dönemden döneme değişti. <b>Tekrar oynatma:</b> aynı kurallar geçmiş yılların gerçek fiyatlarıyla (Yahoo verisinin elverdiği kadar, ~5 yıl), her gün sadece o güne kadarki veriyle oynatıldı. Robotlar tek bir uzun oyunda kesintisiz çalışır; seçtiğin dönem bu oyunun bir kesitidir (dönem başındaki kasa 100.000 TL sayılır, o gün elde olan hisseler dahil). Hisse listesi bugünkü liste olduğu için (sonradan batan/çıkan hisseler yok) geriye gittikçe sonuçlar biraz iyimser. <b>🎲 şans bandı:</b> Rastgele robotun __SANS__ farklı zarla aralığı (%5-%95). <b>Şans yüzdeliği:</b> robotun her alımı aynı gün rastgele bir hisseyle değiştirilseydi (200 deneme) robot bu denemelerin yüzde kaçından iyiydi. <b>💰 Birikim köşesi:</b> Faizci (TL mevduat, TCMB politika faizi, stopajlı), Altıncı (gram altın), Dolarcı (dolar), Dengeci (üçte bir mevduat/altın/BIST 100) hisse seçmez; sıralamaya girmez, 'paranı hiç borsaya koymasaydın?' sorusunun kıyasıdır. Bekçi bunlara uygulanmaz. <b>Reel getiri:</b> getirinin TÜFE'ye göre düzeltilmişi; TÜFE dönemin başladığı aydan <b>son açıklanan aya kadar</b> bileşik (ay içi başlangıç tam ay sayılır; son ay henüz açıklanmadıysa dönem sonunun birkaç haftası enflasyonsuz kalır). <b>Temettü:</b> canlıda hak kullanım günü net temettü (%85) kasaya girer; tekrar oynatmada Yahoo'nun temettü düzeltmeli fiyatları kullanılır (temettü brüt olarak fiyata yeniden yatırılmış sayılır, %15 stopaj düşülmez — hisse robotlarına hafif iyimserlik; BIST 100 fiyat endeksinde temettü yok). 🧠 Yapay zekâ ekibi henüz yok (yakında).</div></div>
<div class="perde" id="perde" onclick="if(event.target===this)kapat()"><div class="pen" id="pen"></div></div>
<script>
var ROB=__ROBOTLAR__, AYAR=__AYAR__;
var CANLI=null,REP=null,REP_YUK=false,MOD='canli',I=0,OYNUYOR=false,HIZ=5,ZAM=null,SON_ADIM=0,ACIK=null;
var ANA='https://boranzz.github.io/Bist-signal/',KAYNAK='',DON=null,SANS=null,SANS_YUK=false,BCACHE={};
var RID=ROB.map(function(r){return r.id;}),RB={};ROB.forEach(function(r){RB[r.id]=r;});
var NS='http://www.w3.org/2000/svg',U=46;
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function sy(x,n){if(x==null||isNaN(x))return '—';return Number(x).toLocaleString('tr-TR',{minimumFractionDigits:n||0,maximumFractionDigits:n||0});}
function yz(x,n){if(x==null||isNaN(x))return '—';return (x>=0?'+':'−')+'%'+sy(Math.abs(x),n==null?1:n);}
function pz(x){if(x==null||isNaN(x))return '—';return (x>=0?'+':'−')+sy(Math.abs(x),1)+' puan';}
function cl(x){return x==null||isNaN(x)?'':(x>=0?'pos':'neg');}
function tr(t){return t?t.slice(8,10)+'.'+t.slice(5,7)+'.'+t.slice(0,4):'';}
function trk(t){return t?t.slice(8,10)+'.'+t.slice(5,7):'';}
function adim(p){var s=[[20,.01],[50,.02],[100,.05],[250,.1],[500,.25],[1000,.5],[2500,1]];for(var i=0;i<s.length;i++)if(p<s[i][0])return s[i][1];return 2.5;}
/* ---------- izometrik çizim (kendi çizimimiz) ---------- */
function P(x,y,z){return [(x-y)*U,(x+y)*U/2-(z||0)*U];}
function pts(a){return a.map(function(p){return p[0].toFixed(1)+','+p[1].toFixed(1);}).join(' ');}
function el(ad,at,ust){var e=document.createElementNS(NS,ad);for(var k in at)e.setAttribute(k,at[k]);if(ust)ust.appendChild(e);return e;}
function kutu(g,x,y,z,w,d,h,ust,sol,sag,op){
 el('polygon',{points:pts([P(x,y+d,z+h),P(x+w,y+d,z+h),P(x+w,y+d,z),P(x,y+d,z)]),fill:sol,opacity:op||1},g);
 el('polygon',{points:pts([P(x+w,y,z+h),P(x+w,y+d,z+h),P(x+w,y+d,z),P(x+w,y,z)]),fill:sag,opacity:op||1},g);
 el('polygon',{points:pts([P(x,y,z+h),P(x+w,y,z+h),P(x+w,y+d,z+h),P(x,y+d,z+h)]),fill:ust,opacity:op||1},g);}
function zeminYazi(g,x,y,metin,renk,boy){var p=P(x,y,0);var t=el('text',{transform:'matrix(1,0.5,-1,0.5,'+p[0]+','+p[1]+')','font-size':boy||15,'font-weight':700,fill:renk,'letter-spacing':'3','font-family':'ui-monospace,Consolas,monospace'},g);t.textContent=metin;return t;}
function bolge(g,x,y,w,d,renk,kesik){el('polygon',{points:pts([P(x,y),P(x+w,y),P(x+w,y+d),P(x,y+d)]),fill:renk+'10',stroke:renk,'stroke-opacity':.55,'stroke-width':1.4,'stroke-dasharray':kesik?'7 6':'none'},g);}
var MASA={kirilimci:[1.0,2.0],siki:[3.7,2.0],erkenci:[6.4,2.0],momentumcu:[9.1,2.0],dipavcisi:[1.0,5.4],uzunvadeci:[3.7,5.4],rsi:[6.4,5.4],
 kirilimci20:[9.1,5.4],rastgele:[12.6,2.2],endeksci:[12.6,5.4],bekci:[14.0,8.9],ai1:[1.6,9.0],ai2:[4.6,9.0],
 faizci:[1.0,12.1],altinci:[3.7,12.1],dolarci:[6.4,12.1],dengeci:[9.1,12.1]};
var KESIR={XU100:1,ALTIN:1,USD:1},MAKAS={ALTIN:.01,USD:.005},TF=null;
var W=16.8,D=14.4,H=3.8,TAHTA=[5.0,12.6],TAHTA_ON=[8.8,0.8];
var FIG={};
function robotCiz(g,id,renk,ad,em,hayalet,tahmini){
 var m=MASA[id]||[0,0],x=m[0],y=m[1];
 var kok=el('g',{'class':hayalet?'':'rb','data-id':id},g);
 if(!hayalet)kok.addEventListener('click',function(){kartAc(id);});
 var f=P(x+0.95,y-0.15,0);
 var fg=el('g',{transform:'translate('+f[0]+','+f[1]+')'},kok);
 var ic=el('g',{},el('g',{transform:'scale(1.25)'},fg));
 el('ellipse',{cx:0,cy:0,rx:15,ry:6,fill:'#000',opacity:.28},ic);
 if(hayalet){el('rect',{x:-11,y:-36,width:22,height:28,rx:9,fill:'none',stroke:'#8E7BC9','stroke-dasharray':'3 3'},ic);el('rect',{x:-12,y:-58,width:24,height:19,rx:7,fill:'none',stroke:'#8E7BC9','stroke-dasharray':'3 3'},ic);}
 else{
 el('rect',{x:-8,y:-12,width:6,height:12,rx:2.5,fill:'#9C95B8'},ic);el('rect',{x:2,y:-12,width:6,height:12,rx:2.5,fill:'#9C95B8'},ic);
 el('rect',{x:-17,y:-33,width:6,height:16,rx:3,fill:'#CFCBE3'},ic);el('rect',{x:11,y:-33,width:6,height:16,rx:3,fill:'#CFCBE3'},ic);
 el('rect',{x:-11,y:-37,width:22,height:27,rx:9,fill:'#EDEAF7',stroke:'#B8B1D6','stroke-width':1},ic);
 el('circle',{cx:0,cy:-24,r:3.6,fill:renk},ic);
 el('line',{x1:0,y1:-58,x2:0,y2:-66,stroke:'#CFCBE3','stroke-width':2},ic);
 FIG[id+'_isik']=el('circle',{cx:0,cy:-68,r:3.4,fill:renk},ic);
 el('rect',{x:-13,y:-58,width:26,height:20,rx:7,fill:'#F7F5FF',stroke:'#B8B1D6','stroke-width':1},ic);
 el('rect',{x:-10,y:-53,width:20,height:9,rx:4.5,fill:'#1B1036'},ic);
 el('circle',{cx:-4,cy:-48.5,r:2,fill:renk},ic);el('circle',{cx:4,cy:-48.5,r:2,fill:renk},ic);
 if(id==='bekci')el('path',{d:'M0,-31 l7,3 v5 c0,5 -4,8 -7,9 c-3,-1 -7,-4 -7,-9 v-5 z',fill:renk,opacity:.9},ic);}
 kutu(kok,x,y,0,1.9,1.1,0.42,hayalet?'#3B2C6B':'#3E2E78',hayalet?'#2A1F50':'#2C2058',hayalet?'#231A45':'#22194A',hayalet?.45:1);
 if(!hayalet){var a=P(x,y+1.1,0.42),b=P(x+1.9,y+1.1,0.42);el('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:renk,'stroke-width':2,opacity:.85},kok);}
 var mx=x+0.12,my=y+0.45;
 el('polygon',{points:pts([P(mx+0.42,my+0.1,0.42),P(mx+0.5,my+0.1,0.42),P(mx+0.5,my+0.1,0.62),P(mx+0.42,my+0.1,0.62)]),fill:'#1A1236'},kok);
 el('polygon',{points:pts([P(mx,my,1.22),P(mx+0.92,my,1.22),P(mx+0.92,my,0.62),P(mx,my,0.62)]),fill:hayalet?'#2A2050':'#120B26',stroke:hayalet?'#4A3B80':renk,'stroke-width':1.2,opacity:hayalet?.5:1},kok);
 if(!hayalet){var mp=P(mx+0.07,my,1.03);var mt=el('text',{transform:'matrix(1,0.5,0,1,'+mp[0]+','+mp[1]+')','font-size':10,'font-weight':700,fill:'#7CF29A','font-family':'ui-monospace,Consolas,monospace'},kok);mt.textContent='';FIG[id+'_ekran']=mt;
  FIG[id+'_sp']=el('polyline',{points:'',fill:'none',stroke:renk,'stroke-width':1.2,opacity:.9},kok);FIG[id+'_spb']=[mx+0.07,my,0.68];}
 FIG[id]={g:fg,ic:ic,ev:f,kok:kok};
 if(hayalet)return;
 var tg=el('g',{'class':'etk',transform:'translate('+f[0]+','+(f[1]-98)+')'},kok);
 var gen=(ad.length+3)*7.4+22;
 var kut=el('rect',{x:-gen/2,y:-12,width:gen,height:22,rx:11,fill:'#140C2A',stroke:renk,'stroke-width':1.3},tg);
 var t=el('text',{x:-gen/2+12,y:4,'font-size':12.5,'font-weight':650,fill:'#F3EEFF'},tg);t.textContent=(em?em+' ':'')+ad;
 try{var ol=t.getComputedTextLength();if(ol>0){gen=ol+44;kut.setAttribute('x',-gen/2);kut.setAttribute('width',gen);t.setAttribute('x',-gen/2+12);}}catch(e){}
 FIG[id+'_roz']=el('circle',{cx:gen/2-11,cy:-1,r:6.5,fill:'#6F6890',stroke:'#140C2A','stroke-width':1.5},tg);
 FIG[id+'_rozt']=el('text',{x:gen/2-11,y:2.6,'font-size':8.5,'font-weight':800,fill:'#fff','text-anchor':'middle'},tg);
 if(tahmini){var tt=el('g',{transform:'translate(0,-20)'},tg);el('rect',{x:-30,y:-9,width:60,height:14,rx:7,fill:'#F97316'},tt);var tx=el('text',{x:0,y:2,'text-anchor':'middle','class':'etk-t'},tt);tx.textContent='TAHMİNİ';}
}
function sahne(){
 var sv=document.getElementById('sv');sv.innerHTML='';
 var defs=el('defs',{},sv);var lg=el('linearGradient',{id:'zg',x1:0,y1:0,x2:1,y2:1},defs);el('stop',{offset:0,'stop-color':'#2C1A5C'},lg);el('stop',{offset:1,'stop-color':'#1C1140'},lg);
 var g=el('g',{},sv);
 el('polygon',{points:pts([P(0,0,0),P(W,0,0),P(W,0,H),P(0,0,H)]),fill:'#241552',opacity:.75,stroke:'#4B3392'},g);
 el('polygon',{points:pts([P(0,0,0),P(0,D,0),P(0,D,H),P(0,0,H)]),fill:'#1E1146',opacity:.8,stroke:'#4B3392'},g);
 for(var i=1;i<W;i+=2){var a=P(i,0,0),b=P(i,0,H);el('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:'#3A2675','stroke-width':1},g);}
 el('polygon',{points:pts([P(0,0),P(W,0),P(W,D),P(0,D)]),fill:'url(#zg)',stroke:'#5A3DA8','stroke-width':1.5},g);
 for(var x=1;x<W;x++){var a=P(x,0),b=P(x,D);el('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:'#3B2A72','stroke-width':.7},g);}
 for(var y=1;y<D;y++){var a=P(0,y),b=P(W,y);el('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],stroke:'#3B2A72','stroke-width':.7},g);}
 var wp=P(0,9.4,3.0);var wt=el('text',{transform:'matrix(1,-0.5,0,1,'+wp[0]+','+wp[1]+')','font-size':17,'font-weight':800,fill:'#B596FF','letter-spacing':'2'},g);wt.textContent='🏢 İŞLEM ODASI';
 var wp2=P(0,9.4,2.5);var wt2=el('text',{transform:'matrix(1,-0.5,0,1,'+wp2[0]+','+wp2[1]+')','font-size':11.5,fill:'#8E7BC9'},g);wt2.textContent='sanal para · kural robotları';
 var tg=el('g',{},g),t0=TAHTA[0],t1=TAHTA[1];
 el('polygon',{points:pts([P(t0,0.02,1.0),P(t1,0.02,1.0),P(t1,0.02,3.6),P(t0,0.02,3.6)]),fill:'#0C0720',stroke:'#7C5CFF','stroke-width':2},tg);
 var hp=P(t0+0.25,0.02,3.25);var ht=el('text',{transform:'matrix(1,0.5,0,1,'+hp[0]+','+hp[1]+')','font-size':13,'font-weight':800,fill:'#B596FF','letter-spacing':'2','font-family':'ui-monospace,Consolas,monospace'},tg);ht.textContent='BORSA TAHTASI';FIG.tahta_bas=ht;
 FIG.tahta=[];for(var k=0;k<5;k++){var lp=P(t0+0.25,0.02,2.83-k*0.35);var lt=el('text',{transform:'matrix(1,0.5,0,1,'+lp[0]+','+lp[1]+')','font-size':11.5,fill:'#DCD3FF','font-family':'ui-monospace,Consolas,monospace'},tg);FIG.tahta.push(lt);}
 bolge(g,0.6,1.3,11.2,5.9,'#B596FF',false);zeminYazi(g,0.8,7.05,'KURAL ROBOTLARI','#8E7BC9',13);
 bolge(g,12.2,1.5,2.9,5.8,'#5BD6FF',false);zeminYazi(g,12.35,7.15,'KIYAS','#5BD6FF',13);
 bolge(g,13.6,8.1,2.8,3.0,'#FFC94D',false);zeminYazi(g,13.75,10.95,'RİSK','#FFC94D',12);
 bolge(g,0.6,8.2,7.0,3.0,'#8E7BC9',true);zeminYazi(g,0.8,11.05,'YAPAY ZEKÂ EKİBİ · YAKINDA','#7A68B4',11);
 bolge(g,0.6,11.4,11.2,2.7,'#60A5FA',false);zeminYazi(g,0.8,13.95,'💰 BİRİKİM KÖŞESİ · KIYAS','#60A5FA',12);
 FIG.hat={};
 RID.forEach(function(id){if(RB[id].grup==='birikim')return;var m=MASA[id],a=P(m[0]+0.95,m[1]+0.55),b=P(m[0]+0.95,TAHTA_ON[1]),c=P(TAHTA_ON[0],TAHTA_ON[1]);
  FIG.hat[id]=el('polyline',{points:pts([a,b,c]),fill:'none',stroke:RB[id].renk,'stroke-width':1.6,opacity:.34,'class':'akan'},g);});
 FIG.bhat={};
 RID.forEach(function(id){if(!RB[id].bekci)return;var m=MASA[id],b=MASA.bekci,a=P(b[0]+0.95,b[1]+0.55),c=P(m[0]+1.6,m[1]+0.9);
  FIG.bhat[id]=el('line',{x1:a[0],y1:a[1],x2:c[0],y2:c[1],stroke:'#FFC94D','stroke-width':1.1,opacity:.25,'stroke-dasharray':'2 6'},g);});
 var liste=RID.map(function(id){return [id,RB[id]];}).concat([['bekci',{renk:'#FFC94D',ad:'Risk Bekçisi',em:'🛡️'}],['ai1',{h:1}],['ai2',{h:1}]]);
 liste.sort(function(a,b){var p=MASA[a[0]],q=MASA[b[0]];return (p[0]+p[1])-(q[0]+q[1]);});
 var mg=el('g',{},g);liste.forEach(function(r){robotCiz(mg,r[0],r[1].renk||'#8E7BC9',r[1].kisa||r[1].ad||'',r[1].em||'',r[1].h,r[1].tahmini);});
 var ap=P(4.2,9.2,0),ag=el('g',{transform:'translate('+ap[0]+','+(ap[1]-92)+')'},g);
 el('rect',{x:-118,y:-14,width:236,height:26,rx:13,fill:'#140C2A',stroke:'#8E7BC9','stroke-dasharray':'5 4'},ag);
 var at=el('text',{x:0,y:4,'font-size':12.5,'font-weight':650,fill:'#B9A6FF','text-anchor':'middle'},ag);at.textContent='🧠 Yapay zekâ ekibi — yakında';
}
/* ---------- veri: canlı (oda.json) ve tekrar oynatma (oda_replay.json) tek görünüme ---------- */
function mdd(seri){var t=-1e18,m=0;for(var i=0;i<seri.length;i++){var v=seri[i];if(v==null)continue;if(v>t)t=v;var d=v/t-1;if(d<m)m=d;}return m*100;}
function istat(df,kasa,f){ // df: [tarih,rid,yon(A/S/M/F/T),kod,adet,fiyat,neden,kz%,kzTL,kismi,not,maliyet{m,b,s,net}]; f: dönem ölçeği (canlıda 1)
 var al=0,kap=0,kaz=0,mal=0,mk=0,bs=0,st=0,tem=0,kzl=[],kzy=[];
 df.forEach(function(x){var y=x[2],c=x[11]||{};
  if(y==='A'||y==='S'){var tut=x[4]*x[5];
   if(MAKAS[x[3]]){mk+=c.m||0;bs+=c.b||0;}else mal+=tut*AYAR.kom+(KESIR[x[3]]?0:x[4]*adim(x[5]));
   if(y==='A')al++;else{if(x[8]!=null)kzl.push(x[8]);if(!x[9]){kap++;if(x[7]>0)kaz++;if(x[7]!=null)kzy.push(x[7]);}}}
  else if(y==='F')st+=c.s||0;else if(y==='T'){st+=c.s||0;tem+=c.net||0;}});
 kzl.sort(function(a,b){return b-a;});var ilk3=kzl.slice(0,3).reduce(function(s,v){return s+Math.max(0,v);},0);
 return {islem:al,kapanan:kap,kazanan:kaz,maliyet:mal*(f||1),makas:mk*(f||1),bsmv:bs*(f||1),stopaj:st*(f||1),temettu:tem*(f||1),
  kzort:kzy.length?kzy.reduce(function(a,b){return a+b;},0)/kzy.length:null,ilk3:kzl.length>=3?((kasa-ilk3)/AYAR.bas-1)*100:null};}
function tufeKum(tf,bas,son){if(!tf||!bas||!son)return null;var a=bas.slice(0,7),b=son.slice(0,7),c=1,ay=[];
 Object.keys(tf).sort().forEach(function(k){if(k>=a&&k<=b){c*=1+tf[k]/100;ay.push(k);}});
 return ay.length?{o:(c-1)*100,a:ay[0],b:ay[ay.length-1]}:null;}
function ayTr(k){var A=['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara'];return A[+k.slice(5,7)-1]+' '+k.slice(0,4);}
function reelAl(g,bas,son){var t=tufeKum(TF,bas,son);if(!t)return null;return {r:((1+g/100)/(1+t.o/100)-1)*100,t:t};}
function tufeEt(t){return t?'TÜFE '+ayTr(t.a)+' – '+ayTr(t.b)+' '+yz(t.o,0)+' (son açıklanan aya kadar)':'TÜFE: bu dönem için henüz açıklanan ay yok';}
function kacanOzet(r){var k=r.kac||[],y=k.filter(function(x){return x.n==='y';}),n=k.filter(function(x){return x.n==='n';});
 var kp=k.filter(function(x){return x.kap;}),ort=kp.length?kp.reduce(function(s,x){return s+x.r;},0)/kp.length:null;
 return {say:r.islem+y.length+n.length,yuva:y.length,nakit:n.length,kapanan:kp.length,ort:ort};}
function dfCanli(e,id){var y={AL:'A',SAT:'S',MEV:'M',FAIZ:'F',TEM:'T'}[e.yon]||'?',c=null,n=e.not||null;
 if(e.makas!=null||e.bsmv!=null)c={m:e.makas||0,b:e.bsmv||0};if(y==='F')c={s:e.stopaj,br:e.brut};if(y==='T')c={s:e.stopaj,net:e.net};
 if(y==='S'&&n&&!Array.isArray(n))n=[n.tp,n.iz,n.k,n.kb||0];
 return [e.t,id,y,e.kod,y==='M'?e.adet:(y==='T'?e.adet:(e.adet||0)),y==='M'?e.oran:(y==='T'?e.hisse_basi:(e.fiyat||0)),e.neden||'',y==='S'?e.kz_yuzde:null,y==='S'?e.kz:null,!!e.kismi,n,c];}
function isgalci(liste){return liste.sort(function(a,b){return b.gun-a.gun;}).slice(0,3);}
function canliGor(){var C=CANLI;if(!C)return null;var xs=C.xu.map(function(x){return x[1];}),an=C.anlik,xt={};
 C.xu.forEach(function(x,j){xt[x[0]]=j;});TF=(C.makro&&C.makro.tufe)||(REP&&REP.makro&&REP.makro.tufe)||null;
 var v={t:C.son_tarih,bas:C.bas,canli:true,r:{},olay:C.olay.slice().reverse(),tlist:C.xu.map(function(x){return x[0];}),xseri:xs.slice(),anlik:an?an.t:null};
 if(an&&an.xu)v.xseri.push(an.xu);
 v.xu=v.xseri.length>1?(v.xseri[v.xseri.length-1]/v.xseri[0]-1)*100:0;v.gun=C.xu.length;
 var hepsi=[];
 RID.forEach(function(id){var k=C.robot[id];if(!k)return;var seri=k.seri.map(function(s){return s[1];}),seriG=seri.slice();var kasa=an&&an.k&&an.k[id]!=null?an.k[id]:k.deger;if(an)seri.push(kasa);
  var df=k.defter.map(function(e){return dfCanli(e,id);});
  hepsi=hepsi.concat(df.filter(function(x){return x[2]==='A'||x[2]==='S';}));var s=istat(df,kasa);
  var b0=k.seri.length?k.seri[0][0]:(C.son_tarih||C.bas),o=xt[b0]!=null?xt[b0]:v.xseri.length-1,xr=(v.xseri[v.xseri.length-1]/v.xseri[o]-1)*100;
  var dol=k.seri.filter(function(q){return q.length>2;}),yv=RB[id].yuva;
  var kac=(k.atla||[]).map(function(a){return {t:a[0],kod:a[1],n:a[2]==='yuva'?'y':'n',r:a[3]!=null?a[3]:null,kap:a[4]===1};});
  var kn=(k.atla_n||[]).reduce(function(s,a){return s+a[1];},0);
  var tut={},isg=[];k.defter.forEach(function(e){if(e.yon==='AL')tut[e.kod]=e.t;else if(e.yon==='SAT'&&!e.kismi&&tut[e.kod]){isg.push({kod:e.kod,gun:k.seri.filter(function(q){return q[0]>=tut[e.kod]&&q[0]<e.t;}).length,r:e.kz_yuzde});delete tut[e.kod];}});
  Object.keys(k.poz).forEach(function(kod){var p=k.poz[kod];if(!KESIR[kod])isg.push({kod:kod,gun:p.gun,r:(p.fiyat/p.maliyet-1)*100,acik:true});});
  v.r[id]={kasa:kasa,seri:seri,durum:k.durdu>0?(k.durdu_neden==='dusus_aktif'?'durdu':'mola'):'aktif',bek:k.bekleyen||[],df:df,mdd:mdd(seri),seriG:seriG,bas:b0,xu:xr,
   poz:Object.keys(k.poz).map(function(kod){var p=k.poz[kod];return {kod:kod,adet:p.adet,fiyat:p.maliyet,tarih:p.tarih,son:p.fiyat,gun:p.gun};}),
   mev:k.mevduat||null,kac:kac,kn:kn,isg:isgalci(isg),dolu:yv&&dol.length?dol.filter(function(q){return q[2]>=yv;}).length/dol.length*100:null,
   islem:s.islem,kapanan:s.kapanan,kazanan:s.kazanan,maliyet:s.maliyet,makas:s.makas,bsmv:s.bsmv,stopaj:s.stopaj,temettu:s.temettu,kzort:s.kzort,ilk3:s.ilk3};});
 hepsi.sort(function(a,b){return a[0]<b[0]?-1:a[0]>b[0]?1:0;});v.defter=hepsi;v.bugun=C.son_tarih;return v;}
function repRobot(id){for(var j=0;j<REP.robot.length;j++)if(REP.robot[j].id===id)return REP.robot[j];return null;}
function repGor(i){var R=REP;if(!R||!DON)return null;var a=DON.a,son=R.gun.length-1;TF=(R.makro&&R.makro.tufe)||null;
 var v={t:R.gun[i],bas:R.gun[a],gun:i-a+1,canli:false,r:{},olay:[],defter:[]};
 v.xu=(R.xu[i]/R.xu[a]-1)*100;v.xseri=R.xu.slice(a,i+1);v.tlist=R.gun.slice(a,i+1);
 RID.forEach(function(id){var rr=repRobot(id);if(!rr)return;var f=AYAR.bas/rr.d[a],poz={},df=[],al={},isg=[],mev=null;
  rr.i.forEach(function(x){if(x[0]>i)return;var t=R.gun[x[0]],ic=x[0]>=a,y=x[1];
   if(y==='A'){var c=x[6]?{m:x[6][0],b:x[6][1]}:null;
    if(poz[x[2]]&&KESIR[x[2]]){var q=poz[x[2]];q.fiyat=(q.adet*q.fiyat+x[3]*x[4])/(q.adet+x[3]);q.adet+=x[3];}
    else poz[x[2]]={kod:x[2],adet:x[3],fiyat:x[4],tarih:t,gi:x[0]};
    al[x[2]]=poz[x[2]].fiyat;if(ic)df.push([t,id,'A',x[2],x[3],x[4],'',null,null,false,x[5]||null,c]);}
   else if(y==='S'){var kis=x[6]==='kr'||x[6]==='dg',baz=(al[x[2]]||x[4])*(1+AYAR.kom)*x[3],kztl=baz*x[5]/100*f;
    if(ic)df.push([t,id,'S',x[2],x[3],x[4],(R.neden[x[6]]||x[6]),x[5],kztl,kis,x[7]||null,x[8]?{m:x[8][0]}:null]);
    if(kis&&poz[x[2]])poz[x[2]].adet-=x[3];else{if(poz[x[2]]&&!KESIR[x[2]])isg.push({kod:x[2],gun:x[0]-poz[x[2]].gi,r:x[5],bit:x[0]});delete poz[x[2]];}}
   else if(y==='M'){mev={ana:x[2],t:t,oran:x[3]};if(ic)df.push([t,id,'M','MEVDUAT',x[2],x[3],'',null,null,false,null,null]);}
   else if(y==='F'){if(ic)df.push([t,id,'F','MEVDUAT',0,0,'',null,null,false,null,{br:x[2],s:x[3]}]);}});
  var seri=rr.d.slice(a,i+1).map(function(x){return x*f;}),kasa=rr.d[i]*f,ds=(rr.dur||'').charAt(i),s=istat(df,kasa,f);
  var yv=RB[id].yuva,pd=(rr.p||'').slice(a,i+1),dl=null;
  if(yv&&pd.length){var c2=0;for(var j=0;j<pd.length;j++)if(parseInt(pd.charAt(j),36)>=yv)c2++;dl=c2/pd.length*100;}
  var kac=(rr.k||[]).filter(function(x){return x[0]>=a&&x[0]<=i;}).map(function(x){var kap=x[4]>=0&&x[4]<=i;return {t:R.gun[x[0]],g:x[0],kod:x[1],n:x[2],r:kap?x[3]:null,kap:kap};});
  var kn=(rr.kn||[]).reduce(function(s,x){return x[0]>=a&&x[0]<=i?s+x[1]:s;},0);
  isg=isg.filter(function(q){return q.bit>=a;});
  Object.keys(poz).forEach(function(k){var p=poz[k];if(!KESIR[k])isg.push({kod:k,gun:i-p.gi,r:null,acik:true});});
  v.r[id]={kasa:kasa,seri:seri,durum:ds==='d'?'durdu':(ds==='m'?'mola':'aktif'),poz:Object.keys(poz).map(function(k){var p=poz[k];p.gun=i-p.gi;return p;}),bek:[],
   islem:s.islem,kapanan:s.kapanan,kazanan:s.kazanan,maliyet:s.maliyet,makas:s.makas,bsmv:s.bsmv,stopaj:s.stopaj,temettu:s.temettu,kzort:s.kzort,ilk3:s.ilk3,
   mdd:mdd(seri),df:df,bas:R.gun[a],xu:v.xu,mev:mev,kac:kac,kn:kn,isg:isgalci(isg),dolu:dl,
   sans:(rr.sans&&DON.b===son)?rr.sans[DON.id]:null};
  v.defter=v.defter.concat(df.filter(function(x){return x[2]==='A'||x[2]==='S';}));});
 v.defter.sort(function(a,b){return a[0]<b[0]?-1:a[0]>b[0]?1:0;});
 var k0=Math.max(a,i-30),bas=R.gun[k0],ol=[];
 v.defter.forEach(function(x){if(x[0]<bas)return;ol.push([x[0],x[1],x[2]==='A'?(x[3]+' aldı: '+sy(x[4],KESIR[x[3]]?2:0)+(x[3]==='ALTIN'?' gr':'')+' × '+sy(x[5],2)+' TL'):(x[3]+(x[9]?' kısmen':'')+' sattı ('+x[6]+') '+yz(x[7]))]);});
 RID.forEach(function(id){var r=v.r[id];if(!r||!r.kac)return;var gun={};r.kac.forEach(function(x){if(x.g>=k0)(gun[x.t]=gun[x.t]||[]).push(x.kod);});
  Object.keys(gun).forEach(function(t){var L=gun[t];ol.push([t,id,'⛔ '+L.slice(0,6).join(', ')+(L.length>6?' +'+(L.length-6):'')+(L.length>1?' roketleri':' roketi')+' kaçtı: kasa dolu (yuva ya da nakit yok)']);});});
 (R.olay||[]).forEach(function(o){if(o[0]<=i&&o[0]>=k0)ol.push([R.gun[o[0]],o[1],o[2]]);});
 ol.sort(function(a,b){return a[0]<b[0]?1:a[0]>b[0]?-1:0;});v.olay=ol.slice(0,150);v.bugun=R.gun[i];
 var B=bantAl();if(B){v.bantS=B;v.bant=[B.p5[i-a],B.p50[i-a],B.p95[i-a]];}
 return v;}
/* ---------- dönem seçici: uzun oyunun dilimi (dönem başı kasa = 100.000 TL) ---------- */
function donemBul(id){for(var k=0;k<REP.donem.length;k++)if(REP.donem[k].id===id)return REP.donem[k];return null;}
function gunSira(t,ileri){var g=REP.gun,lo=0,hi=g.length-1;if(ileri){if(t>g[hi])return hi;while(lo<hi){var m=(lo+hi)>>1;if(g[m]<t)lo=m+1;else hi=m;}return lo;}
 if(t<g[0])return 0;while(lo<hi){var m=(lo+hi+1)>>1;if(g[m]>t)hi=m-1;else lo=m;}return lo;}
function donKur(id){var son=REP.gun.length-1,m=/^ozel:(\d{4}-\d\d-\d\d):(\d{4}-\d\d-\d\d)$/.exec(id||'');
 if(m){var a=gunSira(m[1],true),b=gunSira(m[2],false);if(b-a>=19){DON={id:'ozel',a:a,b:b,ad:'Özel'};return true;}return false;}
 var d=donemBul(id);if(!d)return false;DON={id:d.id,a:d.a,b:son,ad:d.ad};return true;}
function donArayuz(){var sel=document.getElementById('don'),h='';
 REP.donem.forEach(function(d){h+='<option value="'+d.id+'">'+esc(d.ad)+'</option>';});sel.innerHTML=h+'<option value="ozel">Özel…</option>';sel.value=DON.id;
 var oz=document.getElementById('ozel'),ia=document.getElementById('oz_a'),ib=document.getElementById('oz_b');
 ia.min=ib.min=REP.gun[0];ia.max=ib.max=REP.gun[REP.gun.length-1];ia.value=REP.gun[DON.a];ib.value=REP.gun[DON.b];
 oz.className='ozel'+(DON.id==='ozel'?' on':'');
 var s=document.getElementById('sur');s.min=DON.a;s.max=DON.b;s.value=I;donNot();}
function donNot(){var R=REP,y=Math.round(R.gun.length/250);
 var h='📅 <b>'+tr(R.gun[DON.a])+' → '+tr(R.gun[DON.b])+'</b> ('+(DON.b-DON.a+1)+' işlem günü). Robotlar <b>'+tr(R.gun[0])+'</b>\'den beri (~'+y+' yıl) tek bir oyunda kesintisiz çalışıyor; seçtiğin dönem bu oyunun kesiti: dönem başındaki kasa 100.000 TL sayılır, o gün elde olan hisseler de dahil. '+
  'Veri '+tr(R.veri_bas)+'\'te başlıyor; ilk '+R.isinma+' işlem günü göstergelerin (200 günlük ortalama vb.) ısınmasına ayrıldı, oynatma bu yüzden daha geriden başlamıyor.'+
  '<br>⚠️ <b>Dönemin başlangıç günü sonucu çok değiştirir:</b> araştırmada 1 yıllık dönemin başı 20 farklı güne kaydırılınca 🎲 Rastgele %−4 ile %+137 arasında çıktı. Tek dönemin sıralamasına güvenme; birkaç dönemi karşılaştır.';
 document.getElementById('donnot').innerHTML=h;}
function donSec(id){if(!REP)return;durdur();
 if(id==='ozel'){document.getElementById('ozel').className='ozel on';return;}
 if(!donKur(id))return;I=DON.b;donArayuz();donHash();guncelle(false);}
function ozelUygula(){var a=document.getElementById('oz_a').value,b=document.getElementById('oz_b').value;
 if(!a||!b||a>=b||!donKur('ozel:'+a+':'+b)){document.getElementById('donnot').innerHTML='⚠️ Başlangıç bitişten önce olmalı ve arada en az 20 işlem günü bulunmalı ('+tr(REP.gun[0])+' → '+tr(REP.gun[REP.gun.length-1])+' arası).';return;}
 durdur();I=DON.b;donArayuz();donHash();guncelle(false);}
function donHash(){try{var h='#rep&don='+(DON.id==='ozel'?'ozel:'+REP.gun[DON.a]+':'+REP.gun[DON.b]:DON.id);history.replaceState(null,'',h);}catch(e){}}
function yuzdelik(a,q){var x=(a.length-1)*q,i=Math.floor(x),f=x-i;return i+1<a.length?a[i]+(a[i+1]-a[i])*f:a[i];}
function bantAl(){var R=REP;if(!DON)return null;
 for(var k=0;k<R.donem.length;k++)if(R.donem[k].a===DON.a&&R.bant[R.donem[k].id])return R.bant[R.donem[k].id];
 if(BCACHE[DON.a])return BCACHE[DON.a];if(!SANS){sansYukle();return null;}
 var a=DON.a,n=SANS.r.length,L=R.gun.length-a,c=[],o={p5:[],p50:[],p95:[]};for(var j=0;j<n;j++)c.push(1);
 for(var t=0;t<L;t++){var col=[];for(var j=0;j<n;j++){if(t)c[j]*=1+SANS.r[j][a+t]/1e4;col.push(c[j]);}col.sort(function(x,y){return x-y;});
  o.p5.push(AYAR.bas*yuzdelik(col,.05));o.p50.push(AYAR.bas*yuzdelik(col,.5));o.p95.push(AYAR.bas*yuzdelik(col,.95));}
 o.n=n;BCACHE[a]=o;return o;}
function sansYukle(){if(SANS_YUK||SANS===false)return;SANS_YUK=true;var ad=REP.sans_dosya||'oda_replay_sans.json';
 fetch(KAYNAK+ad).then(function(r){if(!r.ok)throw 0;return r.json();})
 .then(function(d){if(!d||d.gun0!==REP.gun[0]||d.gun_n!==REP.gun.length)throw 0;SANS=d;})
 .catch(function(){SANS=false;}).then(function(){SANS_YUK=false;if(MOD==='rep')guncelle(false);});}
function gor(){return MOD==='canli'?canliGor():repGor(I);}
function sansEtiket(y){if(y==null)return null;if(y>=95)return ['şansla açıklanması zor','pos'];if(y>=50)return ['üst yarıda ama şans olabilir',''];return ['rastgele seçimden iyi değil','neg'];}
function uzunSatir(id){var rr=REP&&repRobot(id);if(!rr||!REP.donem||(MOD==='rep'&&DON&&DON.a===0&&DON.b===REP.gun.length-1))return '';
 var d=rr.d,y=Math.round(d.length/250),sn=rr.sans&&rr.sans.tum;
 return 'Aynı kural ~'+y+' yılda ('+tr(REP.gun[0])+' →): '+yz((d[d.length-1]/d[0]-1)*100,0)+', en büyük düşüş '+yz(mdd(d),0)+(sn?', şans yüzdeliği '+sn.yuzde:'');}
/* ---------- çizim güncelle ---------- */
function rozet(id,v){var r=v.r[id],c,t;if(!r)return;if(r.durum==='durdu'){c='#E5484D';t='■';}else if(r.durum==='mola'){c='#E2A400';t='‖';}else if(r.poz.length){c='#2FB36D';t=String(r.poz.length);}else{c='#6F6890';t='·';}
 FIG[id+'_roz'].setAttribute('fill',c);FIG[id+'_rozt'].textContent=t;}
function guncelle(anim){var v=gor();if(!v)return;
 var gunEl=document.getElementById('gun');
 if(MOD==='canli')gunEl.innerHTML=v.t?('Canlı · <b>'+tr(v.t)+'</b> kapanışı · '+v.gun+'. gün'+(v.anlik?' · gün içi '+esc(v.anlik.slice(11)):'')):'Canlı · <b>başlıyor</b>';
 else{gunEl.innerHTML='Tekrar · <b>'+tr(v.t)+'</b>';document.getElementById('rgun').textContent=(I-DON.a+1)+'/'+(DON.b-DON.a+1)+' işlem günü';}
 var not=document.getElementById('not');
 not.innerHTML=(MOD==='canli'&&!v.t)?'Canlı oda <b>'+tr(v.bas)+'</b> akşamı açılıyor: robotlar ilk kararlarını kesin kapanıştan (18:30) sonra verir, ilk alımlar ertesi işlem gününün açılışında yazılır. O zamana kadar <b>⟲ Tekrar oynat</b> ile geçmiş yılları izleyebilirsin.':'';
 RID.forEach(function(id){var r=v.r[id];if(!r)return;var g=(r.kasa/AYAR.bas-1)*100;var e=FIG[id+'_ekran'];e.textContent=yz(g);e.setAttribute('fill',g>=0?'#7CF29A':'#FF8A7A');rozet(id,v);
  var s=r.seri.slice(-40),mn=Math.min.apply(null,s),mx=Math.max.apply(null,s),b=FIG[id+'_spb'];
  FIG[id+'_sp'].setAttribute('points',s.length>1?pts(s.map(function(x,k){return P(b[0]+0.78*k/(s.length-1),b[1],b[2]+(mx>mn?0.2*(x-mn)/(mx-mn):0.1));})):'');
  if(FIG.hat[id])FIG.hat[id].setAttribute('opacity',r.durum==='durdu'?.1:.34);if(FIG.bhat[id])FIG.bhat[id].setAttribute('opacity',r.durum==='durdu'?.9:(r.durum==='mola'?.6:.25));});
 var dur=RID.filter(function(id){return v.r[id]&&v.r[id].durum==='durdu';}).length,mol=RID.filter(function(id){return v.r[id]&&v.r[id].durum==='mola';}).length;
 FIG.bekci_roz.setAttribute('fill',dur?'#E5484D':(mol?'#E2A400':'#2FB36D'));FIG.bekci_rozt.textContent=dur?String(dur):(mol?'‖':'✓');
 FIG.bekci_ekran.textContent=dur?dur+' durdu':(mol?mol+' mola':'tamam');FIG.bekci_ekran.setAttribute('fill',dur?'#FF8A7A':'#7CF29A');
 var bug=v.defter.filter(function(x){return x[0]===v.bugun;});FIG.tahta_bas.textContent='BORSA TAHTASI · '+trk(v.bugun||v.bas);
 for(var k=0;k<5;k++){var x=bug[k];FIG.tahta[k].textContent=x?(RB[x[1]].em+' '+(x[2]==='A'?'AL ':'SAT ')+x[3]+' '+sy(x[5],2)+(x[7]!=null?' '+yz(x[7]):'')):(k===0&&!bug.length?(v.t?'bugün işlem yok':'ilk işlemler ilk kapanıştan sonra'):'');
  FIG.tahta[k].setAttribute('fill',x?(x[2]==='A'?'#7CF29A':'#FF9A8A'):'#8E7BC9');}
 if(bug.length>5)FIG.tahta[4].textContent='… +'+(bug.length-4)+' işlem daha';
 skorCiz(v);akisCiz(v);isiCiz(v);
 if(anim){var yapan={};bug.forEach(function(x){yapan[x[1]]=(yapan[x[1]]||[]).concat([x]);});Object.keys(yapan).forEach(function(id){yuru(id,yapan[id]);});}
 if(ACIK&&document.getElementById('perde').classList.contains('on'))kartAc(ACIK);}
function skorSatir(v,id,no){var r=v.r[id],b=RB[id],g=(r.kasa/AYAR.bas-1)*100,fark=g-r.xu,bir=b.grup==='birikim';
 var d=r.durum==='durdu'?'<span class="dur d">durduruldu</span>':(r.durum==='mola'?'<span class="dur m">mola</span>':(bir?'':(r.poz.length?'<span class="dur p">'+r.poz.length+' pozisyon</span>':'<span class="dur n">nakitte</span>')));
 if(b.tahmini)d+=' <span class="dur m">TAHMİNİ</span>';
 var isa=r.kapanan?'%'+sy(100*r.kazanan/r.kapanan,0)+' ('+r.kazanan+'/'+r.kapanan+')':'—';
 var se=r.sans?sansEtiket(r.sans.yuzde):null,re=reelAl(g,r.bas,v.t);
 var m=bir?('BIST 100\'e göre <span class="'+cl(fark)+'">'+pz(fark)+'</span> · en büyük düşüş '+yz(r.mdd)+(re?' · reel <span class="'+cl(re.r)+'">'+yz(re.r)+'</span>':'')):
  ('BIST 100\'e göre <span class="'+cl(fark)+'">'+pz(fark)+'</span> · en büyük düşüş '+yz(r.mdd)+(re?' · reel <span class="'+cl(re.r)+'">'+yz(re.r)+'</span>':'')+'<br>'+r.islem+' alım · isabet '+isa+' · '+v.gun+' gün'+
  (r.ilk3!=null?' · en iyi 3 işlem hariç '+yz(r.ilk3):'')+(se?'<br>🎲 şans yüzdeliği '+r.sans.yuzde+': <span class="'+se[1]+'">'+se[0]+'</span>':''));
 if(v.canli&&r.bas&&r.bas>v.bas)m+='<br><i>'+tr(r.bas)+'\'den beri (sonradan katıldı)</i>';
 return '<div class="sk'+(bir?' bir':'')+'" onclick="kartAc(\''+id+'\')"><div class="no">'+no+'</div><div class="ad"><b>'+b.em+' '+esc(b.ad)+'</b>'+d+
  '<div class="m">'+m+'</div>'+(uzunSatir(id)?'<div class="not2">'+esc(uzunSatir(id))+'</div>':'')+'</div>'+
  '<div class="g '+cl(g)+'">'+yz(g)+'<small>'+sy(r.kasa)+' TL</small></div></div>';}
function skorCiz(v){var ids=RID.filter(function(id){return v.r[id];}),sir=function(a,b){return v.r[b].kasa-v.r[a].kasa;};
 var yar=ids.filter(function(id){return RB[id].grup!=='birikim';}).sort(sir),bir=ids.filter(function(id){return RB[id].grup==='birikim';}).sort(sir);
 document.getElementById('uyar6').innerHTML=(v.gun<126)?'<div class="uyar6">⏳ '+esc(AYAR.pencere)+' Şu an '+v.gun+'. işlem günü.</div>':'';
 var h='';yar.forEach(function(id,k){h+=skorSatir(v,id,k+1);});
 if(bir.length){h+='<div class="bkb">💰 <b>Birikim köşesi</b> — kıyas satırları, sıralamaya girmez: paran hiç borsaya girmeseydi?</div>';bir.forEach(function(id){h+=skorSatir(v,id,'·');});}
 document.getElementById('skor').innerHTML=h;
 var s='BIST 100 aynı dönemde <b class="'+cl(v.xu)+'">'+yz(v.xu)+'</b>. ',tt=tufeKum(TF,v.bas,v.t);
 s+='<b>Reel</b> = '+tufeEt(tt)+' ile düzeltilmiş getiri. ';
 if(v.bant)s+='🎲 <b>Şans bandı</b> (Rastgele robotun '+(v.bantS&&v.bantS.n?v.bantS.n:AYAR.sans)+' farklı zarı, dönem başında 100.000 TL): %5 '+yz((v.bant[0]/AYAR.bas-1)*100)+' · ortanca '+yz((v.bant[1]/AYAR.bas-1)*100)+' · %95 '+yz((v.bant[2]/AYAR.bas-1)*100)+'. Bu bandın içindeki robot şanstan ayrılmıyor.';
 else if(v.canli)s+='🎲 Şans bandı ve şans yüzdeliği tekrar oynatmada görünür; canlıda kıyas 🎲 Rastgele robot.';
 else s+=(SANS===false?'🎲 Bu dönemin şans bandı alınamadı.':'🎲 Şans bandı hesaplanıyor…');
 if(!v.canli&&DON&&DON.id==='ozel')s+=' Şans yüzdeliği sadece hazır dönemlerde (bugüne kadar) hesaplı; özel dönemde şans bandı '+(v.bantS&&v.bantS.n?v.bantS.n:100)+' zarla.';
 document.getElementById('sans').innerHTML=s;}
function isiCiz(v){var el2=document.getElementById('isi');if(!el2)return;var tl=v.tlist||[],n=tl.length;
 if(n<2){el2.innerHTML='<div style="color:var(--muted)">Ay sonu verisi henüz yok.</div>';document.getElementById('isi_not').innerHTML='';return;}
 var ay=[],son={};for(var j=0;j<n;j++){var k=tl[j].slice(0,7);if(!(k in son))ay.push(k);son[k]=j;}
 function aylik(seri){var o=tl.length-seri.length,out={},once=null;ay.forEach(function(k){var j=son[k]-o;if(j<0){return;}var b=once==null?seri[0]:seri[once];out[k]=(seri[j]/b-1)*100;once=j;});return out;}
 var X=aylik(v.xseri.slice(0,n)),sat=[],ids=RID.filter(function(id){return v.r[id]&&(v.r[id].seriG||v.r[id].seri).length>1;});
 var h='<table><tr><th class="ad">Robot</th>';ay.forEach(function(k){h+='<th>'+ayTr(k).replace(' 20',' \'')+'</th>';});h+='<th>Endeksi yendiği ay</th></tr>';
 function hucre(x){if(x==null||isNaN(x))return '<td class="c"></td>';var a=Math.min(1,Math.abs(x)/15)*0.55+0.06;return '<td class="c" style="background:'+(x>=0?'rgba(27,138,82,':'rgba(194,65,47,')+a.toFixed(2)+')">'+(x>=0?'+':'−')+sy(Math.abs(x),0)+'</td>';}
 ids.forEach(function(id){var A=aylik((v.r[id].seriG||v.r[id].seri).slice(0,n)),yen=0,top=0;h+='<tr><td class="ad">'+RB[id].em+' '+esc(RB[id].kisa||RB[id].ad)+'</td>';
  ay.forEach(function(k){h+=hucre(A[k]);if(A[k]!=null&&X[k]!=null){top++;if(A[k]>X[k])yen++;}});
  h+='<td>'+(top?'%'+sy(100*yen/top,0)+' <span style="color:var(--muted)">('+yen+'/'+top+')</span>':'—')+'</td></tr>';});
 h+='<tr><td class="ad"><b>BIST 100</b></td>';ay.forEach(function(k){h+=hucre(X[k]);});h+='<td></td></tr></table>';
 el2.innerHTML=h;el2.scrollLeft=el2.scrollWidth;
 document.getElementById('isi_not').innerHTML='Her hücre o ayın getirisi (%, ay sonu kasasına göre; ilk ve son ay kısmi olabilir). Son sütun: robotun BIST 100\'ü geçtiği ay oranı. Tablo sağa kayar; en yeni ay sağda.';}
function kim(w){return w==='bekci'?'🛡️ Risk Bekçisi':(RB[w]?RB[w].em+' '+RB[w].ad:esc(w));}
function akisCiz(v){var h='',bek=[];
 if(v.canli){RID.forEach(function(id){((v.r[id]||{}).bek||[]).forEach(function(o){bek.push(RB[id].em+' '+(o.yon==='AL'?'AL ':'SAT ')+esc(o.kod));});});}
 document.getElementById('bek').innerHTML=bek.length?'<div class="bek">⏭️ <b>Bekleyen emirler</b> (bir sonraki işlem gününün açılış fiyatından yazılır, kayıt akşam): '+bek.join(' · ')+'</div>':'';
 v.olay.slice(0,80).forEach(function(o){h+='<div class="ol'+(o[1]==='bekci'?' bk':'')+'"><span class="t">'+trk(o[0])+'</span><span><b>'+kim(o[1])+'</b> · '+esc(o[2])+'</span></div>';});
 document.getElementById('akis').innerHTML=h||'<div class="ol"><span>Henüz olay yok.</span></div>';}
function notMetin(x,id){var n=x[10],t=RB[id].tur;if(!n||!n.length)return '';
 if(x[2]==='A'){var o=n[0],s='';
  if(t==='kirilim'&&o!=null)s='20 günlük zirve '+sy(o,2)+' kırıldı';else if(t==='erken'&&o!=null)s='zirveye %'+sy(o,1)+' kalmıştı';
  else if(t==='dip'&&o!=null)s='destek '+sy(o,2)+' TL\'den tepki';else if(t==='rsi'&&o!=null)s='RSI '+sy(o,1);
  else if(t==='momentum'&&o!=null)s='6 ay getirisi '+yz(o,0);else if(t==='uzun')s='🌱 uzun vade AL';else if(t==='rastgele')s='rastgele seçim';
  var ad=t==='kirilim'?'roket':(t==='rastgele'?'rastgele aday':'aday');
  return s+(s?' · ':'')+'o gün '+n[1]+' '+ad+', '+n[2]+' boş yuva, sırası '+n[3];}
 var p=[];if(n[0]!=null)p.push('tepe '+sy(n[0],2));if(n[1]!=null)p.push('iz '+sy(n[1],2));if(n[2]!=null)p.push('karar kapanışı '+sy(n[2],2));if(n[3])p.push('🔒 kilitli tabanda '+n[3]+' gün bekledi');return p.join(' · ');}
/* ---------- yürüme: işlem yapan robot borsa tahtasına gidip döner ---------- */
var YURUYOR={};
function yuru(id,isl){var F=FIG[id];if(!F)return;var isik=FIG[id+'_isik'];isik.setAttribute('class','yan');setTimeout(function(){isik.removeAttribute('class');},1800);
 var h=FIG.hat[id];if(h){h.classList.add('parla');setTimeout(function(){h.classList.remove('parla');},1500);}
 if(YURUYOR[id]||(MOD==='rep'&&HIZ>=20))return;var sure=Math.max(500,Math.min(2200,2400/Math.max(1,HIZ/2)));
 YURUYOR[id]=1;var a=F.ev,m=MASA[id],b=P(TAHTA_ON[0]+(RID.indexOf(id)-6)*0.4,TAHTA_ON[1]+0.15,0);
 var yol=[a,P(m[0]+0.95,TAHTA_ON[1]+0.15,0),b];
 var bal=el('g',{},F.g);var al=isl.filter(function(x){return x[2]==='A';}).length,sat=isl.length-al;
 var yzi=(al?'AL '+al:'')+(al&&sat?' · ':'')+(sat?'SAT '+sat:'');var w=yzi.length*6.6+14;
 el('rect',{x:-w/2,y:-104,width:w,height:17,rx:6,fill:al?'#1E7A4C':'#9B3427'},bal);var bt=el('text',{x:0,y:-92,'font-size':10.5,'font-weight':700,fill:'#fff','text-anchor':'middle'},bal);bt.textContent=yzi;
 var par=[],toplam=0;for(var i=1;i<yol.length;i++){var d=Math.hypot(yol[i][0]-yol[i-1][0],yol[i][1]-yol[i-1][1]);par.push(d);toplam+=d;}
 var t0=null;function ad(t){if(!t0)t0=t;var u=(t-t0)/sure;if(u>=1){F.g.setAttribute('transform','translate('+a[0]+','+a[1]+')');F.ic.setAttribute('transform','');bal.remove();delete YURUYOR[id];return;}
  var q=u<0.5?u*2:(1-u)*2,s=q*toplam,j=0;while(j<par.length-1&&s>par[j]){s-=par[j];j++;}var f=par[j]?Math.min(1,s/par[j]):0;
  var x=yol[j][0]+(yol[j+1][0]-yol[j][0])*f,y=yol[j][1]+(yol[j+1][1]-yol[j][1])*f;
  F.g.setAttribute('transform','translate('+x+','+y+')');F.ic.setAttribute('transform','translate(0,'+(-Math.abs(Math.sin(t/90))*3).toFixed(1)+')'+(u<0.5?'':' scale(-1,1)'));
  requestAnimationFrame(ad);}
 requestAnimationFrame(ad);}
/* ---------- robot kartı ---------- */
function cizgi(seri,xs,bant){var w=640,h=180,n=seri.length;if(n<2)return '<div style="color:var(--muted);font-size:12.5px">Kasa grafiği için en az 2 gün gerekli.</div>';
 var x0=xs.filter(function(x){return x;})[0];var xk=xs.map(function(x){return x&&x0?AYAR.bas*x/x0:null;});
 var hep=seri.concat(xk.filter(function(x){return x!=null;}));if(bant){hep=hep.concat(bant.p5.slice(0,n),bant.p95.slice(0,n));}
 var mn=Math.min.apply(null,hep),mx=Math.max.apply(null,hep);if(mx===mn){mx+=1;mn-=1;}
 function X(i){return 52+(w-62)*i/(n-1);}function Y(v){return 10+(h-34)*(1-(v-mn)/(mx-mn));}
 function yolu(a){var s='',b=false;a.forEach(function(v,i){if(v==null){b=false;return;}s+=(b?'L':'M')+X(i).toFixed(1)+','+Y(v).toFixed(1);b=true;});return s;}
 var g='<svg viewBox="0 0 '+w+' '+h+'" style="width:100%;height:auto">';
 [mn,(mn+mx)/2,mx].forEach(function(v){g+='<line x1="52" x2="'+(w-10)+'" y1="'+Y(v)+'" y2="'+Y(v)+'" stroke="var(--line)"/><text x="48" y="'+(Y(v)+4)+'" font-size="10" text-anchor="end" fill="var(--muted)">'+sy(v/1000,0)+' bin</text>';});
 if(bant){var ust='',alt='';for(var i=0;i<n;i++){ust+=(i?'L':'M')+X(i).toFixed(1)+','+Y(bant.p95[i]).toFixed(1);}for(var i=n-1;i>=0;i--){alt+='L'+X(i).toFixed(1)+','+Y(bant.p5[i]).toFixed(1);}
  g+='<path d="'+ust+alt+'Z" class="band"/><path d="'+yolu(bant.p50.slice(0,n))+'" fill="none" stroke="#8E88A8" stroke-width="1" stroke-dasharray="2 3"/>';}
 g+='<line x1="52" x2="'+(w-10)+'" y1="'+Y(AYAR.bas)+'" y2="'+Y(AYAR.bas)+'" stroke="var(--muted)" stroke-dasharray="3 4"/>';
 g+='<path d="'+yolu(xk)+'" fill="none" stroke="#8E7BC9" stroke-width="1.5" stroke-dasharray="5 4"/><path d="'+yolu(seri)+'" fill="none" stroke="var(--accent)" stroke-width="2.2"/>';
 g+='<text x="54" y="'+(h-6)+'" font-size="10.5" fill="var(--muted)">— robot kasası · - - BIST 100 (aynı 100.000 TL ile)'+(bant?' · gri bant: 🎲 şans bandı (%5-%95)':'')+'</text></svg>';return g;}
function kartAc(id){var v=gor();if(!v)return;ACIK=id;var pen=document.getElementById('pen'),h;
 if(id==='bekci'){h='<button class="btn kapat" onclick="kapat()">✕</button><h3>🛡️ Risk Bekçisi</h3><p style="color:var(--muted);font-size:13px;line-height:1.5">Endeksçi ve 💰 birikim robotları hariç tüm robotları izler: alımda tek hisseye kasanın en fazla %'+AYAR.tek+'\'u; sonradan kasanın %'+AYAR.krp+'\'ini aşan hissenin fazlası satılır (pozisyon kapanmaz, yeni yuva açmaz); kasa bir günde %'+AYAR.gz+'+ eridiyse ertesi gün yeni alım yok (mola); kasa zirvesinden %'+AYAR.td+'+ düşerse robotu durdurur — pozisyonları ertesi açılışta satılır, '+AYAR.dg+' işlem günü yeni alım yapmaz.<br><b>Kâr aracı değil, emniyet kemeri.</b></p><div class="tb"><table><tr><th>Tarih</th><th>Olay</th></tr>';
  v.olay.filter(function(o){return o[1]==='bekci';}).forEach(function(o){h+='<tr><td>'+tr(o[0])+'</td><td style="white-space:normal">'+esc(o[2])+'</td></tr>';});
  pen.innerHTML=h+'</table></div>';document.getElementById('perde').classList.add('on');return;}
 var r=v.r[id],b=RB[id];if(!r)return;var g=(r.kasa/AYAR.bas-1)*100,se=r.sans?sansEtiket(r.sans.yuzde):null,bir=b.grup==='birikim',re=reelAl(g,r.bas,v.t);
 h='<button class="btn kapat" onclick="kapat()">✕</button><h3>'+b.em+' '+esc(b.ad)+(b.tahmini?' <span class="dur m">TAHMİNİ</span>':'')+(bir?' <span class="dur n">kıyas</span>':'')+'</h3><div style="color:var(--muted);font-size:13px;line-height:1.5">'+esc(b.kural)+'</div>';
 if(b.not)h+='<div class="uyar6" style="margin-top:8px">'+esc(b.not)+'</div>';
 h+='<div class="ist"><div>Kasa<b>'+sy(r.kasa)+' TL</b></div><div>Getiri<b class="'+cl(g)+'">'+yz(g)+'</b></div><div>Reel getiri<b class="'+(re?cl(re.r):'')+'">'+(re?yz(re.r):'—')+'</b></div><div>BIST 100\'e göre<b class="'+cl(g-r.xu)+'">'+pz(g-r.xu)+'</b></div><div>En büyük düşüş<b>'+yz(r.mdd)+'</b></div>';
 if(!bir)h+='<div>Alım<b>'+r.islem+'</b></div><div>İsabet<b>'+(r.kapanan?'%'+sy(100*r.kazanan/r.kapanan,0):'—')+'</b></div><div>Gün<b>'+v.gun+'</b></div><div>En iyi 3 işlem hariç<b>'+(r.ilk3!=null?yz(r.ilk3):'—')+'</b></div>';
 if(r.maliyet>0.5||!bir)h+='<div>Komisyon + kayma<b>'+sy(r.maliyet)+' TL</b></div>';
 if(r.makas>0.5)h+='<div>Makas<b>'+sy(r.makas)+' TL</b></div>';if(r.bsmv>0.5)h+='<div>BSMV<b>'+sy(r.bsmv)+' TL</b></div>';
 if(r.stopaj>0.5||b.tur==='faiz'||b.tur==='denge')h+='<div>Stopaj ('+(r.temettu>0?'temettü':'faiz')+')<b>'+sy(r.stopaj)+' TL</b></div>';
 if(r.temettu>0.5)h+='<div>Temettü (net)<b>'+sy(r.temettu)+' TL</b></div>';
 if(!bir)h+='<div>Durum<b>'+(r.durum==='durdu'?'durduruldu':(r.durum==='mola'?'mola':'aktif'))+'</b></div>';
 h+='</div><div style="font-size:12px;color:var(--muted);margin:-4px 0 6px">Reel: '+esc(tufeEt(re?re.t:null))+'. '+(v.canli&&r.bas>v.bas?'Bu robot canlıya '+tr(r.bas)+'\'de katıldı; getiri ve BIST 100 farkı o günden.':'')+'</div>';
 if(se)h+='<div style="font-size:13px;margin:4px 0 8px">🎲 <b>Şans yüzdeliği '+r.sans.yuzde+'</b> — <span class="'+se[1]+'">'+se[0]+'</span>. Her alımı aynı gün rastgele hisseyle değiştirilmiş '+AYAR.sans+' ikizin bu dönemdeki %5-%95 aralığı '+yz(r.sans.p5)+' … '+yz(r.sans.p95)+' (ortanca '+yz(r.sans.med)+').</div>';
 if(uzunSatir(id))h+='<div style="font-size:13px;margin:4px 0 8px">📜 '+esc(uzunSatir(id))+'</div>';
 h+=cizgi(r.seri,v.xseri.slice(-r.seri.length),bir?null:(v.bantS||null));
 if(!v.canli)h+='<div style="color:var(--muted);font-size:12px">Dönem başındaki kasa 100.000 TL\'ye ölçeklendi (uzun oyunun kesiti); işlem adetleri uzun oyundaki gerçek adetler, satış sonucu ilk alış fiyatına göre.</div>';
 if(!bir){var ko=kacanOzet(r);h+='<div class="kac">';
  if(b.tur==='kirilim'){h+='🚀 <b>Kaçırılan roketler:</b> bu dönemde <b>'+ko.say+'</b> roket geldi, <b>'+r.islem+'</b>\'i alındı, <b>'+ko.yuva+'</b>\'i yuva dolu diye, <b>'+ko.nakit+'</b>\'i nakit kalmadığı için (para hisselerde; eskiden kırıntı alım yapılıyordu) atlandı. ';
   if(ko.kapanan)h+='Atlananlardan kapanmış '+ko.kapanan+' tanesinin ortalama sonucu (v3\'ün kendi işlemi: ertesi açılış → %20 iz stop) <b class="'+cl(ko.ort)+'">'+yz(ko.ort)+'</b>'+(r.kzort!=null?'; robotun bu dönemde kapattığı işlemlerin ortalaması <b class="'+cl(r.kzort)+'">'+yz(r.kzort)+'</b>':'')+'. ';
   else if(ko.yuva)h+='Atlananların hiçbiri henüz kapanmadı. ';}
  else if(r.kn)h+='⛔ Bu dönemde <b>'+r.kn+'</b> aday sinyal yuvalar dolu olduğu için alınamadı. ';
  if(r.dolu!=null)h+='Yuvaların <b>dolu olduğu gün oranı %'+sy(r.dolu,0)+'</b>. ';
  if(r.isg&&r.isg.length)h+='<br>En uzun yuva işgalcileri: '+r.isg.map(function(q){return '<b>'+esc(q.kod)+'</b> '+q.gun+' gün'+(q.r!=null?' ('+yz(q.r)+(q.acik?', açık':'')+')':(q.acik?' (açık)':''));}).join(' · ');
  if(b.tur==='kirilim'&&r.kac&&r.kac.length){var sk=r.kac.slice(-8).reverse();if(sk.length)h+='<br>Son kaçanlar: '+sk.map(function(x){return trk(x.t)+' '+esc(x.kod)+(x.r!=null?' '+yz(x.r):(x.kap?'':' (açık)'));}).join(' · ');}
  h+='</div>';}
 h+='<h4 style="margin:12px 0 2px">Açık pozisyonlar ('+r.poz.length+')</h4>';
 if(r.mev)h+='<div style="font-size:13px;margin:2px 0 6px">🏦 TL mevduat: '+(v.canli?sy(r.mev.ana)+' TL anapara, ':'')+'son açılış/yenileme '+tr(r.mev.t)+', yıllık %'+sy(r.mev.oran*(v.canli?100:1),2)+(v.canli?', stopaj %'+sy(r.mev.st*100,1):'')+' (32 günde bir faiziyle yenilenir)</div>';
 if(r.poz.length){h+='<div class="tb"><table><tr><th>Varlık</th><th class="r">Adet</th><th>Alış</th><th class="r">Alış fiyatı</th>'+(v.canli?'<th class="r">Son</th><th class="r">Getiri</th>':'')+'<th class="r">Gün</th></tr>';
  r.poz.forEach(function(p){var gg=p.son?(p.son/p.fiyat-1)*100:null;h+='<tr><td><b>'+esc(p.kod)+'</b></td><td class="r">'+sy(p.adet,KESIR[p.kod]?2:0)+(p.kod==='ALTIN'?' gr':'')+'</td><td>'+tr(p.tarih)+'</td><td class="r">'+sy(p.fiyat,2)+'</td>'+(v.canli?'<td class="r">'+sy(p.son,2)+'</td><td class="r '+cl(gg)+'">'+yz(gg)+'</td>':'')+'<td class="r">'+(p.gun!=null?p.gun:'')+'</td></tr>';});
  h+='</table></div>';}else if(!r.mev)h+='<div style="color:var(--muted);font-size:13px">Nakitte.</div>';
 if(v.canli&&r.bek&&r.bek.length)h+='<div style="font-size:13px;margin-top:6px">⏭️ Bekleyen emirler (sonraki açılıştan): '+r.bek.map(function(o){return (o.yon==='AL'?'AL ':'SAT ')+esc(o.kod);}).join(' · ')+'</div>';
 var df=r.df.slice().reverse().slice(0,40),YN={A:'AL',S:'SAT',M:'MEVDUAT',F:'FAİZ',T:'TEMETTÜ'};
 h+='<h4 style="margin:12px 0 2px">İşlem geçmişi (son '+df.length+')</h4>';
 if(df.length){h+='<div class="tb"><table><tr><th>Tarih</th><th></th><th>Varlık</th><th class="r">Adet</th><th class="r">Fiyat</th><th>Neden</th><th class="r">Sonuç</th></tr>';
  df.forEach(function(x){var y=x[2],c=x[11]||{},ned=esc(x[6]),nt=notMetin(x,id),son2=x[7]!=null?yz(x[7]):'';
   if(y==='M'){ned='32 gün, yıllık %'+sy(x[5],2);}
   if(y==='F'){ned='vade doldu: brüt faiz '+sy(c.br)+' TL, stopaj '+sy(c.s)+' TL';}
   if(y==='T'){ned='net '+sy(c.net)+' TL (stopaj '+sy(c.s)+' TL)';}
   if(c.m)nt=(nt?nt+' · ':'')+'makas '+sy(c.m)+' TL'+(c.b?', BSMV '+sy(c.b)+' TL':'');
   h+='<tr><td>'+tr(x[0])+'</td><td class="'+(y==='A'||y==='M'?'pos':(y==='S'?'neg':''))+'">'+(YN[y]||y)+'</td><td><b>'+esc(x[3])+'</b></td><td class="r">'+(y==='F'?'':sy(x[4],y==='M'?0:(KESIR[x[3]]?2:0)))+'</td><td class="r">'+(y==='F'||y==='M'?'':sy(x[5],2))+'</td><td class="ned">'+ned+(nt?(ned?'<br>':'')+esc(nt):'')+'</td><td class="r '+cl(x[7])+'">'+son2+'</td></tr>';});
  h+='</table></div>';}else h+='<div style="color:var(--muted);font-size:13px">Henüz işlem yok.</div>';
 h+='<p style="color:var(--muted);font-size:12px;margin-top:10px">Satış sonucu komisyon ve kayma (altın/dolarda makas) düşülmüş nettir. Sanal para; yatırım tavsiyesi değil.</p>';
 pen.innerHTML=h;document.getElementById('perde').classList.add('on');}
function kapat(){ACIK=null;document.getElementById('perde').classList.remove('on');}
/* ---------- mod / oynatma ---------- */
function mod(m){MOD=m;document.getElementById('m_canli').className=m==='canli'?'on':'';document.getElementById('m_rep').className=m==='rep'?'on':'';
 document.getElementById('oyn').className='oyn'+(m==='rep'?' on':'');document.getElementById('donnot').className='donnot'+(m==='rep'?' on':'');durdur();
 if(m==='rep'&&!REP){document.getElementById('gun').textContent='tekrar oynatma verisi yükleniyor…';repYukle();return;}
 guncelle(m==='canli');}
function repAl(kok){return fetch(kok+'oda_replay.json').then(function(r){if(!r.ok)throw 0;return r.json();})
 .then(function(d){if(!d||!(d.v>=2)||!d.donem)throw 0;KAYNAK=kok;return d;});}
function repYukle(){if(REP_YUK)return;REP_YUK=true;
 repAl('').catch(function(){return repAl(ANA);})
 .then(function(d){REP=d;var hd=/don=([a-z0-9:-]+)/.exec(location.hash);if(!(hd&&donKur(hd[1]))&&!donKur(REP.varsayilan))donKur('tum');
  var h=/rep=(\d+)/.exec(location.hash);I=h?Math.min(DON.a+(+h[1]),DON.b):DON.b;donArayuz();
  if(MOD==='rep')guncelle(!!h);else guncelle(false);hashKart();})
 .catch(function(){REP_YUK=false;if(MOD==='rep')document.getElementById('gun').textContent='tekrar oynatma verisi alınamadı';});}
function git(i){if(!DON)return;I=Math.max(DON.a,Math.min(DON.b,i));document.getElementById('sur').value=I;guncelle(false);}
function adimla(t){if(!OYNUYOR)return;if(!SON_ADIM)SON_ADIM=t;
 if(t-SON_ADIM>=1000/HIZ){SON_ADIM=t;if(I>=DON.b){durdur();return;}I++;document.getElementById('sur').value=I;guncelle(true);}
 ZAM=requestAnimationFrame(adimla);}
function oynat(){if(!REP||!DON)return;if(OYNUYOR){durdur();return;}if(I>=DON.b)I=DON.a;OYNUYOR=true;SON_ADIM=0;document.getElementById('b_oyn').textContent='⏸ Durdur';ZAM=requestAnimationFrame(adimla);}
function durdur(){OYNUYOR=false;if(ZAM)cancelAnimationFrame(ZAM);ZAM=null;var b=document.getElementById('b_oyn');if(b)b.textContent='▶ Oynat';}
function kurallar(){var h='',G=[['yaris','Kural robotları (yarışmacı)'],['kiyas','Kıyas: şans ve endeks'],['birikim','💰 Birikim köşesi (sıralamaya girmez)']];
 G.forEach(function(gg){ROB.forEach(function(r){if(r.grup!==gg[0])return;h+='<div><b>'+r.em+' '+esc(r.ad)+'</b>'+(r.tahmini?' <span class="dur m">TAHMİNİ</span>':'')+' <span class="dur n">'+esc(gg[1])+'</span><br>'+esc(r.kural)+(r.not?'<br><i style="color:var(--muted)">'+esc(r.not)+'</i>':'')+'</div>';});});
 document.getElementById('kurallar').innerHTML=h;}
function hashKart(){var h=/kart=([a-z0-9]+)/.exec(location.hash);if(h&&(RB[h[1]]||h[1]==='bekci'))kartAc(h[1]);}
function basla(){sahne();kurallar();var sl=document.getElementById('salon');if(sl.scrollWidth>sl.clientWidth)sl.scrollLeft=(sl.scrollWidth-sl.clientWidth)*0.45;
 fetch('oda.json?v='+Date.now(),{cache:'no-store'}).then(function(r){if(!r.ok)throw 0;return r.json();})
 .then(function(d){CANLI=d;if(MOD==='canli'){guncelle(true);hashKart();}repYukle();})
 .catch(function(){document.getElementById('gun').textContent='canlı veri yok';document.getElementById('not').innerHTML='Canlı oda verisi (oda.json) okunamadı. <b>⟲ Tekrar oynat</b> ile geçmiş yılları izleyebilirsin.';repYukle();});}
document.addEventListener('keydown',function(e){if(e.key==='Escape')kapat();});
basla();if(/^#rep/.test(location.hash))mod('rep');
</script></body></html>
"""
# ===== ŞABLON SONU =====


def _sayfa():
    B = BEKCI
    ayar = {"bas": BASLANGIC, "kom": KOMISYON, "tek": round(B["tek_hisse"] * 100), "krp": round(B["kirp"] * 100),
            "gz": round(B["gunluk_zarar"] * 100), "td": round(B["dusus"] * 100), "dg": B["dusus_bekle"],
            "sans": SANS_N, "pencere": PENCERE_NOT}
    return (_SABLON.replace("__ROBOTLAR__", json.dumps(robot_meta(), ensure_ascii=False))
            .replace("__AYAR__", json.dumps(ayar, ensure_ascii=False))
            .replace("__KOM__", f"{KOMISYON * 100:.1f}".replace(".", ",")).replace("__KRP__", str(ayar["krp"]))
            .replace("__TEK__", str(ayar["tek"])).replace("__GZ__", str(ayar["gz"])).replace("__TD__", str(ayar["td"]))
            .replace("__DG__", str(ayar["dg"])).replace("__SANS__", str(SANS_N)))


ODA_SAYFA = _sayfa()
