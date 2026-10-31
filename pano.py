# -*- coding: utf-8 -*-
"""Etkileşimli pano: satıra tıkla -> grafik + o hisseye özel yorum + TradingView linki."""
import json
import os
from html import escape
import pandas as pd

# Hangi GitHub deposu: Actions GITHUB_REPOSITORY verir (arkadaşın kopyasında onun deposu); yerelde varsayılan.
REPO = os.environ.get("GITHUB_REPOSITORY") or "BoranZZ/Bist-signal"

RENK = {"AL": "al", "NÖTR": "notr", "SAT": "sat"}


def _simdi():
    """Türkiye saati (Actions sunucusu UTC'de çalışır)."""
    return pd.Timestamp.now(tz="Europe/Istanbul").strftime("%d.%m.%Y %H:%M")


def _med(xs):
    xs = sorted(x for x in xs if x)
    return xs[len(xs) // 2] if xs else None


# 📊 bilanço tepkisi araştırma notu (scratchpad strateji2 + panobilgi/t2_bt.py: ana liste 2017-26, KAP tarihli 3.483 olay; alış tepkinin
# ertesi açılışı, 60 işlem günü sonra kapanış, BIST 100'e göre). JS BT_NOT ile aynı metin.
BT_NOT = {"g": "Geçmişte (ana liste, 2017-26) güçlü tepki verenler sonraki 60 günde endeksi %56 oranında geçti (normal tepkide %49) — zayıf bir eğilim.",
          "z": "Geçmişte (ana liste, 2017-26) zayıf tepki verenler sonraki 60 günde endeksi %46 oranında geçti (normal tepkide %49) — fark küçük.",
          "n": "Geçmişte (ana liste, 2017-26) normal tepkide (−5…+5 puan) sonraki 60 günde endeksi geçme oranı %49."}


# ⚠️ Manipülasyon rozeti (tarama.manip_rozet: 5 işaretten ≥2'si). Metinler JS mnIsaret / MN_NOT ile aynı (MN_NOT şablona gömülür).
# Sayılar: 10.10.2026 araştırması (~2,7 kat) + scratchpad rozet/t2_fiyat.py (10y pkl 286 hisse 2018-26, sadece 3 fiyat işareti, 5 günde bir
# hisse-gün: ≥2 işarette sonraki 60 işlem gününde kilitli taban günü %11-13, diğerlerinde %2-3; 2018 dışında her yıl aynı yönde).
MN_NOT = ("Geçmişte bu işaretlerden 2 ya da daha fazlasını taşıyan hisselerde kilitli tabanda (alıcı yokken) satamama riski birkaç kat "
          "yüksekti: 10.10.2026 araştırmasında ~2,7 kat; 2018-26 fiyat testinde sonraki 60 günde kilitli taban görülme oranı %11-13 "
          "(diğer hisselerde %2-3). Alım yasağı ya da sinyal değil; AL/SAT kuralı değişmez. Elindeyse pozisyonu küçük tut, iz stop'u sıkı takip et.")
# Dürüstlük notu (sayfanın en altı). Sayılar scratchpad rozet/t0_durustluk.py: canlı v3 + 🔐 kâr kilidi, backtest.py motoru, 10y 286 hisse
# (2017-10 → 2026-10-16, MANIPULE hariç 2.050 işlem): %30 zararla (2022-26 %34; %13'ü −%20'den kötü), kârla kapananların çoğu +%10'un altında
# (%41; kâr kilidi çıkışı %43), en iyi %10'luk işlemler toplam net kârın %85'i (2022-26 %93), geri kalanların ortalaması +%3,3 (2022-26 +%1,0).
DURUST_NOT = ("Sinyallerin yaklaşık üçte biri zararla kapanır (bazıları %20'den fazla); kârla kapananların çoğu da küçük kârdır "
              "(🔐 kâr kilidiyle ~+%5). Kârın çoğu az sayıdaki büyük yükselişten gelir: geçmiş testte (2017-26) en iyi %10'luk "
              "işlemler toplam kârın ~%85'ini getirdi. Geçmiş sonuçlar geleceği garanti etmez, yatırım tavsiyesi değildir.")


# 📉 'Sistemin normal kötü günleri' (bilgi kartı). Sayılar backtest.kotu_gunler ile: canlı v3 + 🔐 kâr kilidi, backtest.py motoru, 10y pkl
# 286 hisse MANIPULE hariç (2017-10 → 2026-10-16, 2.050 işlem; 10 eşit yuvaya giren 289 işlem), scratchpad panoarac/t1_kotugun.py.
# ufuk: 10 yuvalı portföyün günlük getirileri durağan blok bootstrap (ort. 20 gün, 3.000 yol): dd50/dd90 = en büyük düşüşün %50 / kötü %10
# dilimi, tdd90 = aynı ölçü geçmişin gerçek kayan pencerelerinden (kontrol), g50/g10 getiri, n = o sürede ort. kapanan işlem, s50/s90 =
# en uzun art arda zarar serisi (gerçek kayan pencereler). karne: TÜM v3 işlemleri çıkış sırasıyla, ardışık n işlemlik dilimlerin ortalama
# net sonucu (%5/%50/%95) ve en uzun zarar serisi (%50/%90). Kural değişirse (sinyal.KAR_KILIT_*, v3) t1_kotugun.py ile yeniden ölç.
KOTU_GUN = {"bas": "2017-10-18", "son": "2026-10-19", "islem": 2050, "yuva_islem": 289, "tarihi_dd": -33.3, "ufuk": [
    {"ay": 1, "dd50": -4.7, "dd90": -10.4, "tdd90": -10.3, "g50": 2.6, "g10": -6.4, "n": 3, "s50": 0, "s90": 2},
    {"ay": 3, "dd50": -9.4, "dd90": -18.1, "tdd90": -18.7, "g50": 8.9, "g10": -7.5, "n": 8, "s50": 1, "s90": 3},
    {"ay": 6, "dd50": -13.2, "dd90": -22.7, "tdd90": -23.4, "g50": 20.1, "g10": -6.5, "n": 16, "s50": 2, "s90": 3},
    {"ay": 12, "dd50": -18.1, "dd90": -29.1, "tdd90": -31.5, "g50": 48.8, "g10": -0.9, "n": 32, "s50": 3, "s90": 3}],
    "karne": {"n": [5, 10, 15, 20, 30, 40, 60, 80, 100, 150, 200],
              "o5": [-11.1, -8.5, -5.4, -4.7, -2.4, -1.4, -0.0, 0.6, 1.5, 5.2, 7.5],
              "o50": [6.8, 9.4, 9.5, 9.9, 10.8, 11.7, 13.1, 14.3, 14.3, 14.7, 15.8],
              "o95": [87.5, 76.9, 79.0, 77.2, 79.6, 79.7, 82.4, 82.4, 79.1, 68.7, 66.5],
              "s50": [1, 1, 2, 2, 3, 3, 4, 4, 4, 5, 5], "s90": [3, 4, 4, 4, 5, 5, 6, 6, 6, 7, 7]}}
KG_MIN = 5   # canlı karnede bundan az kapanan v3 işlemi varsa kıyas yapılmaz


def _tr1(x, isaret=True):
    """−4.7 → '−%4,7' (Türkçe yüzde)."""
    if x is None:
        return "—"
    s = f"{abs(x):.1f}".replace(".", ",")
    return ("−" if x < 0 else ("+" if isaret and x > 0 else "")) + "%" + s


def _ara(n, xs, ys):
    """KG_N tablosunda doğrusal ara değer (uçlarda sabit)."""
    if n <= xs[0]:
        return ys[0]
    for i in range(1, len(xs)):
        if n <= xs[i]:
            return ys[i - 1] + (ys[i] - ys[i - 1]) * (n - xs[i - 1]) / (xs[i] - xs[i - 1])
    return ys[-1]


def kotu_gun_kiyas(kapali, kg=KOTU_GUN):
    """Canlı karne (gecmis.json, sadece 'kural: v3' kapananlar) geçmişin aynı uzunluktaki dilimleriyle: ortalama sonuç %5-%95
    aralığında mı, en uzun art arda zarar serisi %90 sınırını aşıyor mu. Karne sonucu komisyonsuz (sinyal günü kapanışından),
    backtest net (ertesi açılış + %0,2/yön) — fark ~0,4 puan, kıyası değiştirmez. Döner: durum 'az' | 'icinde' | 'alt' | 'ust'."""
    ka = sorted((r for r in (kapali or []) if r.get("kural") == "v3" and r.get("sonuc") is not None),
                key=lambda r: (r.get("cikis_tarih") or "", r.get("kod") or ""))
    n = len(ka)
    x = [float(r["sonuc"]) for r in ka]
    m = c = son = 0
    for v in x:
        c = c + 1 if v <= 0 else 0
        m = max(m, c)
    son = c
    out = {"n": n, "ort": round(sum(x) / n, 1) if n else None, "seri": m, "son_seri": son, "bas": ka[0]["giris_tarih"] if ka else None}
    if n < KG_MIN:
        out["durum"] = "az"
        return out
    k = kg["karne"]
    o5, o50, o95 = (round(_ara(n, k["n"], k[a]), 1) for a in ("o5", "o50", "o95"))
    s90 = int(-(-_ara(n, k["n"], k["s90"]) // 1))   # yukarı yuvarla (cömert sınır)
    out.update({"o5": o5, "o50": o50, "o95": o95, "s90": s90})
    out["durum"] = "alt" if (out["ort"] < o5 or m > s90) else ("ust" if out["ort"] > o95 else "icinde")
    return out


def kotu_gun_html(kiyas, kg=KOTU_GUN):
    """📉 kartı (statik; sayılar KOTU_GUN). Canlı karne satırı kotu_gun_kiyas'tan."""
    sat = "".join(
        f"<tr><td>{u['ay']} ay</td><td class='num neg'>{_tr1(u['dd50'])}</td><td class='num neg'>{_tr1(u['dd90'])}</td>"
        f"<td class='num'>{_tr1(u['g10'])}</td><td class='num'>{u['s50'] if u['s50'] == u['s90'] else str(u['s50']) + '–' + str(u['s90'])}</td></tr>" for u in kg["ufuk"])
    k = kiyas or {"durum": "az", "n": 0}
    if k["durum"] == "az":
        kn = (f"Canlı karnede henüz {k['n']} kapanan 🚀 v3 işlemi var; kıyas için en az {KG_MIN} gerekiyor."
              if k["n"] else "Canlı karnede henüz kapanan 🚀 v3 işlemi yok; ilk işlemler kapanınca burada kıyas görünecek.")
        cls = ""
    else:
        ne = {"icinde": "✅ <b>şu an normal aralıkta</b>", "alt": "⚠️ <b>şu an normal aralığın dışında (kötü tarafta)</b>",
              "ust": "📈 <b>normal aralığın iyi tarafında</b>"}[k["durum"]]
        kn = (f"Canlı karne ({k['n']} kapanan 🚀 işlem): ortalama sonuç <b>{_tr1(k['ort'])}</b>, en uzun art arda zarar <b>{k['seri']}</b> işlem. "
              f"Geçmişte aynı uzunluktaki dilimlerin %90'ında ortalama {_tr1(k['o5'])} ile {_tr1(k['o95'])} arasıydı, art arda zarar en çok "
              f"{k['s90']} işlem → {ne}."
              + (" Bu 'sistem bozuldu' demek değil (geçmişte de böyle dilimler %5-10 sıklıkla vardı) ama dikkat işareti: pozisyonları küçük tut, "
                 "iz stop'lara uy." if k["durum"] == "alt" else ""))
        cls = " uyar" if k["durum"] == "alt" else ""
    return (f'<div class="kart kotugun{cls}" id="kotugun"><h3>📉 Sistemin normal kötü günleri</h3>'
            f"<p>Bu sistemle para kaybedilen haftalar ve aylar <b>normaldir</b>. Aşağıdaki aralıklar 10 eşit parçalı portföyün (🚀 v3 + 🔐) "
            f"{kg['bas'][:4]}-{kg['son'][:4]} geçmiş işlemlerinin günlük sonuçları binlerce kez yeniden karıştırılarak bulundu.</p>"
            f'<div class="sar"><table class="kgt"><thead><tr><th>Süre</th><th class="num" title="Yarı yarıya: bu süre içinde zirveden en büyük düşüş">Tipik en büyük düşüş</th>'
            f'<th class="num" title="10 dönemden birinde bundan daha kötü">Kötü ama normal (10\'da 1)</th>'
            f'<th class="num" title="10 dönemden birinde getiri bundan kötü">Getiri (10\'da 1 kötü)</th>'
            f'<th class="num" title="Bu sürede kapanan işlemlerde en uzun art arda zarar: tipik – 10\'da 1">Art arda zararlı işlem</th></tr></thead><tbody>{sat}</tbody></table></div>'
            f'<p class="kgkarne">{kn}</p>'
            f'<p class="sgun">Geçmişin en büyük düşüşü {_tr1(kg["tarihi_dd"])} (2020). Nakit faizi yok; bugünkü hisse listesiyle test edildi (gerçek kötü günler '
            f"biraz daha kötü olabilir); geçmiş geleceği garanti etmez. Art arda zarar sayısı karıştırmadan değil, geçmişin gerçek dönemlerinden (portföyün kapattığı işlemler, ayda ~3). Bilgi, "
            f"kural değil — AL/SAT değişmez.</p></div>")


def birikim_serisi(replay="oda_replay.json", canli="oda.json"):
    """💵 Portföy vs altın / dolar / mevduat / TÜFE: İşlem Odası'nın 💰 birikim robotlarının günlük kasa değeri (🥇 Altıncı = gram altın,
    💵 Dolarcı = USD/TRY, 🏦 Faizci = TCMB politika faiziyle 32 günlük mevduat, stopaj sonrası) — iki tarih arasındaki oranları o varlığın
    getirisi (alıştaki makas sabit, oranda sadeleşir). Kaynak oda_replay.json (elle, ~5 yıl) + oda.json (canlı, replay'in son gününden
    sonrası aynı günün oranıyla eklenir). TÜFE aylık (oda.json makro, yoksa replay). Dosya yoksa / bozuksa None (pano not yazar)."""
    try:
        with open(replay, encoding="utf-8") as f:
            r = json.load(f)
        gun = r["gun"]
        rob = {x["id"]: x["d"] for x in r["robot"]}
        idler = ("altinci", "dolarci", "faizci")
        if not all(i in rob and len(rob[i]) == len(gun) for i in idler):
            return None
        t = list(gun[1:])   # ilk gün alım günü (makas/BSMV düşer) — oranlar ertesi günden
        seri = {i: [round(float(v)) for v in rob[i][1:]] for i in idler}
        tf = (r.get("makro") or {}).get("tufe") or {}
        try:
            with open(canli, encoding="utf-8") as f:
                o = json.load(f)
            tf = ((o.get("makro") or {}).get("tufe")) or tf
            cs = {i: {x[0]: x[1] for x in ((o.get("robot") or {}).get(i) or {}).get("seri") or []} for i in idler}
            son = t[-1]
            if all(son in cs[i] and cs[i][son] for i in idler):
                yeni = sorted(d for d in cs["altinci"] if d > son and all(d in cs[i] for i in idler))
                for i in idler:
                    k = seri[i][-1] / cs[i][son]
                    seri[i] += [round(cs[i][d] * k) for d in yeni]
                t += yeni
        except Exception:
            pass
        return {"t": t, "a": seri["altinci"], "u": seri["dolarci"], "m": seri["faizci"], "tf": tf}
    except Exception:
        return None


def _tarih_tam(t):
    """'2026-09-25' → '25.09.2026'"""
    return f"{t[8:10]}.{t[5:7]}.{t[:4]}"


def manip_isaret(x):
    """⚠️ Tek manipülasyon işaretinin metni [tür, tarih, değer] (JS mnIsaret ile aynı)."""
    k, t, v = x
    if k == "tv":
        return f"{v} gün art arda tavan ({_tarih_tam(t)})"
    if k == "x3":
        return f"60 günde {str(v).replace('.', ',')} kat yükseliş ({_tarih_tam(t)})"
    if k == "ts":
        return f"hisseye özel taban serisi: 15 günde {v} taban ({_tarih_tam(t)})"
    if k == "vb":
        return f"Borsa İstanbul VBTS (volatilite bazlı tedbir) kararı ({_tarih_tam(t)})"
    return f"SPK tedbir kararı ({_tarih_tam(t)})"


def pano_uret(sonuclar, ornek=False, uyari=None, piyasa=None, yeni_arzlar=None, endeks=None, gunici=None, genislik=None, kapali=None):
    tarih = _simdi()
    al = sum(1 for s in sonuclar if s["sinyal"] == "AL")
    guclu = sum(1 for s in sonuclar if s.get("guclu"))
    fk_med = _med(s.get("fk") for s in sonuclar)
    pddd_med = _med(s.get("pddd") for s in sonuclar)

    oncelik = {"AL": 0, "NÖTR": 1, "SAT": 2}
    sonuclar = sorted(sonuclar, key=lambda s: (oncelik[s["sinyal"]], not s.get("yeni"), not s.get("guclu"), -s["puan"]))

    rows = []
    veri = {}
    for s in sonuclar:
        k = s["kod"]
        deg = s.get("degisim")
        dcls = "pos" if (deg or 0) >= 0 else "neg"
        dtxt = f"{'+' if (deg or 0) >= 0 else ''}{deg}%" if deg is not None else "—"
        fkm = "ucuz" if (s.get("fk") and fk_med and s["fk"] < fk_med) else ("pahali" if s.get("fk") else "")
        pdm = "ucuz" if (s.get("pddd") and pddd_med and s["pddd"] < pddd_med) else ("pahali" if s.get("pddd") else "")
        ok = {"ucuz": "▼", "pahali": "▲", "": ""}
        yildiz = ' <span class="yildiz" title="AL+: göstergeler AL, F/K ve PD/DD görece ucuz">AL+</span>' if s.get("guclu") else ""
        ycls = {"AL": "yal", "SAT": "ysat", "NÖTR": "ynotr"}[s["sinyal"]]
        yenirz = f' <span class="yeni {ycls}">YENİ</span>' if s.get("yeni") else ""
        sdrz = ""
        if s.get("destek_tepki") and s["sinyal"] == "SAT":
            # SAT sürerken destek tepkileri backtest'te çoğunlukla (~%68) 20 günde kırıldı: olumlu gösterme
            sdrz += ' <span class="sdb destekzayif" title="SAT sürerken destekte tepki — 5 yıllık backtest\'te bu desteklerin ~%68\'i 20 gün içinde kırıldı">Destekte (SAT sürüyor)</span>'
        elif s.get("destek_tepki"):
            sdrz += ' <span class="sdb destek" title="Fiyat geçmiş bir desteğe indi ve yukarı dönmeye başladı">Destekten tepki</span>'
        if s.get("direnc_yakin"):
            sdrz += ' <span class="sdb direnc" title="Fiyat geçmişte satış gelen bir tepe seviyesine yakın">Dirence yaklaşıyor</span>'
        if s.get("hacim_teyit"):
            sdrz += f' <span class="hacimb" title="AL günü hacmi 20 günlük ortalamanın {s.get("hacim_kat")} katı">📈 hacim</span>'
        if s.get("oynak"):
            sdrz += f' <span class="patlakb" title="60 günlük günlük oynaklık %{s.get("vol60")} (> %5): aşırı oynak, AL mesajı gönderilmez">⚡ oynak</span>'
        if s.get("patlak"):
            sdrz += f' <span class="patlakb" title="Son 15 günde {s.get("taban15")} kez ~%10 düştü (taban serisi)">⚠ taban serisi</span>'
        kt = s.get("kt")
        if kt:   # 🔒 taban serisi öncesi erken aşama (seri başlayınca analiz_et kt'yi boşaltır, 'taban serisi' öncelikli)
            sdrz += (f' <span class="patlakb" title="{kt["seri"]} gündür taban, {"bugün" if kt.get("kilitli_bugun") else "dün"} gün boyu işlem '
                     f'neredeyse yok (kilitli). Geçmişte benzerlerinin ~%60&#39;ı 4+ tabana uzadı (normalde ~%9). Kilitli tabanda satış '
                     f'emri çoğu zaman gerçekleşmez. Kesin değil">🔒 kilitli taban</span>')
        tz = s.get("tuzak")
        if tz:
            sdrz += f' <span class="gun1b" title="{tz["tarih"]}: düşen trend %{tz["gunluk"]} yükselişle kırıldı. Tüm borsada bu kırılımların %56&#39;sı 15 günde geri düştü; kırılımda almak rastgele günden kötü sonuç verdi">🪤 tuzak riski</span>'
        mn = s.get("mn")
        if mn:   # ⚠️ manipülasyon işaretleri (≥2/5) — bilgi, alım yasağı değil
            mnb = escape("Manipülasyon işaretleri (%d/5): " % mn["n"] + "; ".join(manip_isaret(x) for x in mn["i"]))
            sdrz += (f' <span class="patlakb" title="{mnb}. Kilitli tabanda satamama riski yüksek; alım yasağı değil">'
                     '⚠️ manipülasyon işareti</span>')
        th = s.get("tahta") or {}
        if th.get("seviye") == "sisme" and (th.get("yuk20") or 0) < 0:   # çöküş sonrası tepki tavanları: 'şişme' yanıltıcı (metin; tetik aynı)
            sdrz += f' <span class="patlakb" title="{"; ".join(th["neden"])}, ama 20 günde {th["yuk20"]:+.0f}% — çöküş sonrası sert tavan-taban dalgalanması">🎈 sert dalgalanma</span>'
        elif th.get("seviye") == "sisme":
            sdrz += f' <span class="patlakb" title="{"; ".join(th["neden"])} — tahtacı şişirmesi olabilir">🎈 şişme</span>'
        elif th.get("seviye") == "dagitim":
            sdrz += f' <span class="gun1b" title="{th["neden"][0]}">⚠️ dağıtım</span>'
        od = s.get("od")
        if od:
            sdrz += (f' <span class="gun1b" title="Son {od["u"]} günde {od["r"]:+.1f}% (BIST 100 {od["xu"]:+.1f}%), hacim ortalamanın '
                     f'{od["hk"]} katı; benzer hisseler bu kadar düşmedi. Geçmişte bu durumdakilerin sonraki 20 günde ~%38&#39;i endeksi geçti '
                     f'(normalde ~%46); 2022-23 düşük faizde fark yoktu. Bilgi, sinyal değil">🔻 özel düşüş</span>')
        if s.get("arz"):
            sdrz += ' <span class="arzb" title="Son 12 ayın halka arzı">ARZ</span>'
        tk = s.get("tk") or {}
        if tk.get("bugun"):
            sdrz += f' <span class="tkb yeni" title="Bugün trend şablonunda 20 günlük zirve kırıldı — v3 AL">🚀 KIRILIM</span>'
        elif tk.get("durum") == "AL" and (tk.get("gun") or 0) <= 5:
            # backtest: sinyalden 5 gün içinde girmek sinyal günüyle neredeyse aynı (ort +%19 vs +%20)
            sdrz += f' <span class="tkb" title="{tk.get("gun")} gün önce 🚀 AL geldi ({tk.get("giris_tarih")}, o günden beri {tk.get("degisim")}%). İlk 5 gün içinde girmek backtest\'te sinyal günüyle neredeyse aynı sonuç verdi. İz stop {tk.get("stop")} TL">🚀 AL {tk.get("gun")}g önce</span>'
        elif tk.get("durum") == "AL":
            # 20+ gün sonra girmek belirgin kötü (40 gün sonra isabet %35) — yeni alım sinyali değil
            sdrz += f' <span class="tkb izle" title="Yeni alım sinyali DEĞİL: {tk.get("giris_tarih")} günkü 🚀 AL hâlâ sürüyor ({tk.get("degisim")}%, iz stop {tk.get("stop")} TL). Backtest: sinyalden 20+ gün sonra girmek belirgin kötü; yeni alım için bir sonraki kırılımı bekle">trendde · {tk.get("gun")}g</span>'
        elif tk.get("sablon") and tk.get("kirilima_uzak") is not None and 0 < tk["kirilima_uzak"] <= 3:
            sdrz += f' <span class="tkb izle" title="Trend şablonunda; 20 günlük zirveye (%{tk["kirilima_uzak"]} yukarıda, {tk.get("kirilim_seviye")} TL) yakın — kapanışla aşarsa v3 AL">👀 kırılıma %{tk["kirilima_uzak"]}</span>'
        uv = s.get("uv") or {}
        if uv.get("durum") == "AL":
            sdrz += f' <span class="uvsb" title="Uzun vade AL: {uv.get("tarih")} tarihinden beri">🌱 UV</span>'
        bil = s.get("bilanco") or {}
        if bil.get("kalan_gun") is not None and 0 <= bil["kalan_gun"] <= 7:
            ne = "Yahoo takvimi" if (bil.get("sonraki") or {}).get("kaynak") == "yahoo" else "SPK son teslim tarihi (daha erken açıklanabilir)"
            sdrz += f' <span class="bilb" title="Sonraki bilanço: {bil["sonraki"]["tarih"]} ({ne}) — açıklama günü fiyat sert oynayabilir">📅 bilanço</span>'
        tm = s.get("temettu") or {}
        if tm.get("ex_kalan") is not None and tm["ex_kalan"] <= 7:
            sdrz += f' <span class="bilb" title="Temettü hak kullanım: {tm["ex_tarih"]} — o sabah fiyat temettü kadar düşük açılır">💰 temettü</span>'
        if s.get("bayrak"):
            sdrz += f' <span class="bayrakb" title="Boğa bayrağı kırılımı (direk %{s["bayrak"]["direk"]}, {s["bayrak"]["bayrak_gun"]} günlük bayrak)">🚩</span>'
        bt = s.get("bt") or {}
        if bt.get("s") in ("g", "z"):   # 📊 bilanço tepkisi (ana liste; tepki gününden sonra 60 işlem günü)
            sdrz += (f' <span class="bilb" title="{bt["d"]} bilançosu sonrası 2 günde BIST 100&#39;e göre {bt["r"]:+.1f} puan '
                     f'({bt["j"]} / {bt["j1"]}). {BT_NOT[bt["s"]]} Bilgi, sinyal değil">📊 {"güçlü" if bt["s"] == "g" else "zayıf"} tepki</span>')
        g = s.get("guc") or {}
        gucs = f'<span class="gucb g{g["puan"]}">{g["puan"]}/{g["toplam"]}</span>' if g else "—"
        rs = s.get("rs")
        rss = f'<span class="rsb{" rsy" if rs >= 80 else ""}">{rs}</span>' if rs is not None else "—"
        if s.get("momentum"):
            sdrz += ' <span class="momb" title="Ayın güçlüleri: son 6 ayın en güçlü %20&#39;si (bilgi, AL sinyali değil)">📈 ayın güçlüsü</span>'
        lot = s.get("lot")
        lott = f"{lot}" if (lot and s["sinyal"] == "AL") else "—"
        nk = s.get("notr_kaynak") if s["sinyal"] == "NÖTR" else None
        ncls = {"AL": " notr-al", "SAT": " notr-sat"}.get(nk, "")
        ntit = {"AL": " title=\"AL'den NÖTR'e döndü\"", "SAT": " title=\"SAT'tan NÖTR'e döndü\""}.get(nk, "")
        sgun = s.get("sinyal_gun")
        sgunt = f"{sgun}g" if sgun else "—"
        iz = s.get("iz") or {}
        izs = iz.get("stop", "—") if (iz and not iz.get("cikti")) else "—"   # v2: iz stop (açık AL dalgası)
        rows.append(
            f'<tr data-kod="{k}" onclick="ac(\'{k}\')">'
            f'<td class="favtd"><button class="fav" onclick="event.stopPropagation();favDegis(\'{k}\')" title="Favorilere ekle">☆</button></td>'
            f'<td class="kod">{k}</td>'
            f'<td class="num">{s.get("fiyat","—")}</td>'
            f'<td class="num {dcls}">{dtxt}</td>'
            f'<td><span class="pill {RENK[s["sinyal"]]}{ncls}"{ntit}>{s["sinyal"]}</span>{yildiz}{yenirz}{sdrz}</td>'
            f'<td class="num sgun">{sgunt}</td>'
            f'<td class="num uyum">{s.get("uyum","—")}</td>'
            f'<td class="num">{gucs}</td><td class="num">{rss}</td><td class="vd"></td>'
            f'<td class="num">{s.get("rsi") if s.get("rsi") is not None else "—"}</td>'
            f'<td class="num">{s.get("fk") if s.get("fk") is not None else "—"}<span class="tag {fkm}">{ok[fkm]}</span></td>'
            f'<td class="num">{s.get("pddd") if s.get("pddd") is not None else "—"}<span class="tag {pdm}">{ok[pdm]}</span></td>'
            f'<td class="num stop">{izs}</td>'
            f'<td class="num lot">{lott}</td></tr>'
        )
        veri[k] = {
            "kod": k, "fiyat": s.get("fiyat"), "degisim": deg, "sinyal": s["sinyal"],
            "guclu": bool(s.get("guclu")), "yeni": bool(s.get("yeni")), "sd": s.get("sd"),
            "destek_tepki": bool(s.get("destek_tepki")), "direnc_yakin": bool(s.get("direnc_yakin")),
            "rsi": s.get("rsi"), "fk": s.get("fk"), "pddd": s.get("pddd"), "favok": s.get("favok"),
            "stop": s.get("stop"), "giris_stop": s.get("giris_stop"), "lot": s.get("lot"), "iz": s.get("iz"),
            "oynak": bool(s.get("oynak")), "vol60": s.get("vol60"), "trend": bool(s.get("trend")), "trend_asagi": bool(s.get("trend_asagi")), "v2_uygun": bool(s.get("v2_uygun")),
            "hedef": s.get("hedef"), "sinyal_gun": s.get("sinyal_gun"), "notr_kaynak": s.get("notr_kaynak"),
            "sinyal_tarih": s.get("sinyal_tarih"), "sinyal_degisim": s.get("sinyal_degisim"),
            "uyum": s.get("uyum"), "detay": s.get("detay", []), "ek": s.get("ek", []),
            "gerekce": s.get("gerekce", []), "yorum": s.get("yorum", ""),
            "spark": s.get("spark", {}),
            "al_stop": s.get("al_stop"), "al_tarih": s.get("al_tarih"), "hacim_kat": s.get("hacim_kat"),
            "hacim_teyit": bool(s.get("hacim_teyit")), "taban15": s.get("taban15"), "patlak": bool(s.get("patlak")), "tahta": s.get("tahta"), "tuzak": s.get("tuzak"),
            "arz": s.get("arz"), "sektor": s.get("sektor"), "endustri": s.get("endustri"), "mom20": s.get("mom20"), "uv": s.get("uv"), "bayrak": s.get("bayrak"), "bilanco": s.get("bilanco"), "temettu": s.get("temettu"), "kap": s.get("kap"), "tk": s.get("tk"), "tkg": s.get("tkg"), "guc": s.get("guc"), "momentum": bool(s.get("momentum")), "mom6": s.get("mom6"), "bolunme": s.get("bolunme"),
            "rs": s.get("rs"),
            "hv": s.get("hv"), "kg": s.get("kg"), "od": s.get("od"), "vd": s.get("vd"),
        }
        if s.get("kt"):   # 🔒 sadece olan hissede (index.html şişmesin)
            veri[k]["kt"] = s["kt"]
        if s.get("bt"):   # 📊 bilanço tepkisi (ana liste, son 60 işlem günü) — sadece olan hissede
            veri[k]["bt"] = s["bt"]
        if s.get("zr"):   # son 4 çeyrekte zarar (dönem adı) — sadece olan hissede
            veri[k]["zr"] = s["zr"]
        if s.get("mn"):   # ⚠️ manipülasyon işaretleri — sadece olan hissede
            veri[k]["mn"] = s["mn"]

    banner = ""
    if ornek:
        banner += '<div class="banner ornek">ÖRNEK VERİ — gerçek sürüm piyasa saatinde ~15 dk\'da bir güncellenir.</div>'
    if piyasa and piyasa.get("zayif"):
        banner += (f'<div class="banner uy">⚠️ <b>Piyasa zayıf:</b> BIST 100 ({piyasa["endeks"]:,}) 50 günlük ortalamasının '
                   f"%{abs(piyasa['fark'])} altında. 5 yıllık backtest'te bu dönemlerde gelen AL'ler belirgin şekilde "
                   f'daha kötü sonuç verdi — yeni alımlarda temkinli ol.</div>').replace(",", ".")
    if uyari:
        banner += f'<div class="banner uy">⚠️ {uyari}</div>'

    arzrows = []
    for z in sorted(yeni_arzlar or [], key=lambda z: z["tarih"], reverse=True):
        g = z.get("getiri")
        gcls = "pos" if (g or 0) >= 0 else "neg"
        uyar = f' <span class="patlakb">⚠ {z["taban15"]} taban/15 gün</span>' if z["taban15"] >= 4 else ""
        arzrows.append(
            f'<tr><td class="kod">{z["kod"]}{uyar}</td><td>{z["tarih"]}</td>'
            f'<td class="num">{z["arz_fiyat"] if z["arz_fiyat"] else "—"}</td><td class="num">{z["fiyat"]}</td>'
            f'<td class="num {gcls}">{("+" if (g or 0) >= 0 else "") + str(g) + "%" if g is not None else "—"}</td>'
            f'<td class="num sgun">{z["eksik_gun"]} işlem günü</td></tr>')
    arzblok = ""
    if arzrows:
        arzblok = ('<h2 class="bolum">Yeni halka arzlar <span class="bolumalt">— sinyal için henüz yeterli geçmiş yok</span></h2>'
                   '<div class="sar"><table class="pf"><thead><tr><th>Hisse</th><th>İşlem başlangıcı</th>'
                   '<th class="num">Arz fiyatı</th><th class="num">Güncel</th><th class="num">Arzdan beri</th>'
                   '<th class="num">Sinyale kalan</th></tr></thead><tbody>' + "".join(arzrows) + '</tbody></table></div>')

    html = _SABLON
    kk = kk_metinleri()
    kgk = kotu_gun_kiyas(kapali)
    for a, b in [("__KKSOZ__", kk["soz"]), ("__KKCUMLE__", kk["cumle"]), ("__KKGRAFIK__", kk["grafik"]), ("__KK__", kk["js"]),
                 ("__TARIH__", tarih), ("__REPO__", REPO), ("__AL__", str(al)), ("__GUCLU__", str(guclu)),
                 ("__TOPLAM__", str(len(sonuclar))),
                 ("__TKBUGUN__", str(sum(1 for s in sonuclar if (s.get("tk") or {}).get("bugun")))),
                 ("__TK5__", str(sum(1 for s in sonuclar if (s.get("tk") or {}).get("durum") == "AL" and ((s.get("tk") or {}).get("gun") or 0) <= 5))), ("__BANNER__", banner),
                 ("__MNNOT__", json.dumps(MN_NOT, ensure_ascii=False)), ("__DURUST__", escape(DURUST_NOT, quote=False)),
                 ("__ROWS__", "".join(rows)), ("__ARZ__", arzblok),
                 ("__XU__", json.dumps(endeks)), ("__PIYASA__", json.dumps(piyasa)),
                 ("__GI__", json.dumps(gunici, ensure_ascii=False, separators=(",", ":"))),
                 ("__GEN__", json.dumps(genislik, separators=(",", ":"))), ("__KGK__", json.dumps(kgk, ensure_ascii=False)),
                 ("__KOTUGUN__", kotu_gun_html(kgk)), ("__KS__", json.dumps(birikim_serisi(), separators=(",", ":"))),
                 ("__DATA__", json.dumps(veri, ensure_ascii=False))]:
        html = html.replace(a, b)
    return html


def kk_metinleri():
    """🔐 kâr kilidi metinleri (sabitler sinyal.KAR_KILIT_ESIK / KAR_KILIT_SEVIYE'den; kural kapalıysa hepsi boş, JS KK = null)."""
    from sinyal import kar_kilit_ayar, kar_kilit_arastirma
    kk, ar = kar_kilit_ayar(), kar_kilit_arastirma()
    if not kk:
        return {"soz": "", "cumle": "", "grafik": "", "karne": "", "js": "null"}
    e, sv = (f"{round(x * 100, 1):g}".replace(".", ",") for x in kk)
    return {
        "js": json.dumps([round(kk[0] * 100, 1), round(kk[1] * 100, 1)]),
        "soz": (f'<div class="sz"><span class="tkb">🔐 kâr kilidi</span><span>🚀 pozisyonda kapanış bir kez alış fiyatının +%{e} üstüne '
                f'çıktıysa, iz stop en az alış +%{sv} olur (normal %20 iz stop daha yüksekse o geçerli). Amaç: kâr gören işlemi zarara '
                f'döndürmeden kapatmak. ' + (f'10 yıllık testte (286 hisse) kârla kapanan işlem oranı %52 → {ar["isabet"].split(" / ")[0]}; '
                f"bedeli: bazı büyük yükselişlerin başında +%{sv}'te satılıyor (kilitle kapananların ~{ar['buyuk']}'ü eski kuralla "
                f"+%30'un üstünde biterdi), her işleme eşit para koyan toplam kâr biraz düşük ({ar['sepet']} → eski kuralın yüzdesi). "
                if ar else f"Bedeli: bazı büyük yükselişlerin başında +%{sv}'te satılabilir. ") + "Grafikte ▼ SAT "
                f'işaretinin üstünde 🔐 yazar.</span></div>'),
        "cumle": f" 🔐 Kâr kilidi: kapanışta alışın +%{e} üstü bir kez görüldüyse stop en az alış +%{sv} olur.",
        "grafik": f" Kapanış alışın +%{e} üstünü görünce 🔐 kâr kilidi devreye girer: mor çizgi en az alış +%{sv}'te durur.",
        "karne": (f" 🔐 <b>Kâr kilidi</b> (canlı kurala Ekim 2026'da eklendi, <b>ileriye dönük</b>): bu tarihten sonra açılan kayıtlarda "
                  f'kesin kapanışta kayıt fiyatının +%{e} üstü görülürse stop en az kayıt fiyatı +%{sv} olur (tabloda 🔐). Daha önce '
                  f'açılmış kayıtlar (açık olanlar dahil) eski %20 iz stop kuralıyla kapanır; geçmiş kayıtlar yeniden yazılmadı.'),
    }


def gecmis_uret(acik, kapali, ozet):
    """Sinyal geçmişi sayfası: açık pozisyonlar + kapanmış sinyaller + karne."""
    def eski(r):
        e = "" if r.get("kural") == "v3" else ' <span class="eskib" title="Eski (v3 öncesi) kurallarla açılmış kayıt">eski kural</span>'
        if r.get("kk"):
            e += f' <span title="🔐 kâr kilidi {r["kk"]} tarihinde devreye girdi: stop en az kayıt fiyatı +%{round(r["kar_kilit"][1] * 100, 1):g}">🔐</span>'
        return e

    def satirlar(kayitlar, acikmi):
        out = []
        for r in sorted(kayitlar, key=lambda x: x.get("giris_tarih", ""), reverse=True):
            if acikmi:
                s = r.get("anlik")
                scls = "pos" if (s or 0) >= 0 else "neg"
                stxt = f"{'+' if (s or 0) >= 0 else ''}{s}%" if s is not None else "—"
                out.append(f'<tr><td class="kod">{r["kod"]}{eski(r)}</td><td>{r["giris_tarih"]}</td>'
                           f'<td class="num">{r["giris_fiyat"]}</td><td class="num">{r.get("guncel","—")}</td>'
                           f'<td class="num {scls}">{stxt}</td><td class="num stop">{r["stop"]}</td></tr>')
            else:
                s = r.get("sonuc")
                scls = "pos" if (s or 0) >= 0 else "neg"
                stxt = f"{'+' if (s or 0) >= 0 else ''}{s}%" if s is not None else "—"
                out.append(f'<tr><td class="kod">{r["kod"]}{eski(r)}</td><td>{r["giris_tarih"]}</td>'
                           f'<td class="num">{r["giris_fiyat"]}</td><td>{r.get("cikis_tarih","—")}</td>'
                           f'<td class="num">{r.get("cikis_fiyat","—")}</td>'
                           f'<td class="num {scls}">{stxt}</td><td>{r.get("sebep","—")}</td></tr>')
        return "".join(out) or '<tr><td colspan="7" style="color:#6B7079">Kayıt yok.</td></tr>'

    html = _GECMIS
    reps = {
        "__ISABET__": str(ozet.get("isabet", "—")), "__KAPANAN__": str(ozet.get("kapanan", 0)),
        "__ORT__": str(ozet.get("ort", "—")), "__ACIK__": str(ozet.get("acik", 0)),
        "__ACIKROWS__": satirlar(acik, True), "__KAPALIROWS__": satirlar(kapali, False),
        "__TARIH__": _simdi(), "__KKKARNE__": kk_metinleri()["karne"],
        "__ESKI__": (lambda e: (f'<div class="not">Eski (v3 öncesi) kurallarla açılmış kayıtlar yukarıdaki kartlara dahil değil: '
                                f'{e["kapanan"]} kapanan (isabet %{e["isabet"]}, ortalama %{e["ort"]}), {e["acik"]} açık. '
                                f'Tablolarda "eski kural" etiketiyle görünürler.</div>') if (e["kapanan"] or e["acik"]) else "")(ozet.get("eski") or {"kapanan": 0, "acik": 0}),
    }
    for a, b in reps.items():
        html = html.replace(a, b)
    return html


_SABLON = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>BIST Sinyal Panosu</title>
<style>
:root{--bg:#FAFAF8;--ink:#16181D;--muted:#6B7079;--line:#E6E7E4;--accent:#0E4D45;
--al:#1B7F4B;--notr:#9A7A12;--sat:#B4362E;--pos:#1B7F4B;--neg:#B4362E;--panel:#FFF}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
font-feature-settings:"tnum" 1;-webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto;padding:26px 18px 60px}
header{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:14px;
border-bottom:1px solid var(--line);padding-bottom:18px}
h1{font-size:19px;margin:0;font-weight:650}.tarih{color:var(--muted);font-size:12.5px;margin-top:4px}
.ozet{display:flex;gap:22px;text-align:right}
.ozet .b{font-size:38px;font-weight:680;line-height:1;color:var(--accent);letter-spacing:-.02em}
.ozet .b.g{color:var(--al)}.ozet .l{color:var(--muted);font-size:12px;margin-top:3px}
.ipucu{margin-top:14px;color:var(--muted);font-size:12.5px}
.banner{margin:14px 0 0;padding:10px 14px;border-radius:8px;font-size:13px}
.banner.ornek{background:#FBF3E4;border:1px solid #EBD9B0;color:#7A5B10}
.banner.uy{background:#FBECEA;border:1px solid #E6C3BD;color:#8A2F26}
.sar{margin-top:18px;overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--panel)}
table{width:100%;border-collapse:collapse;font-size:13.5px;min-width:720px}
#t td:nth-child(1),#t th:nth-child(1){position:sticky;left:0;z-index:1;background:var(--panel)}#t td:nth-child(2),#t th:nth-child(2){position:sticky;left:38px;z-index:1;background:var(--panel);box-shadow:1px 0 0 var(--line)}#t tr.favrow td:nth-child(1),#t tr.favrow td:nth-child(2){background:#FFFBEB}#t tbody tr:hover td{background:#F2F5F3}
th,td{padding:11px 12px;text-align:left;white-space:nowrap}
th{position:sticky;top:0;background:var(--panel);color:var(--muted);font-weight:600;font-size:12px;
border-bottom:1px solid var(--line);cursor:pointer;user-select:none}th:hover{color:var(--ink)}
tbody tr{border-bottom:1px solid var(--line);cursor:pointer}tbody tr:last-child{border-bottom:none}
tbody tr:hover,tbody tr:hover td{background:#F2F5F3}
.kod{font-weight:650}.num{text-align:right;font-variant-numeric:tabular-nums}
.stop{color:var(--sat)}.lot{font-weight:650}.pos{color:var(--pos)}.neg{color:var(--neg)}
.pill{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:650}
.pill.al{background:#E4F2E9;color:var(--al)}.pill.notr{background:#F1EFE8;color:var(--notr)}.pill.sat{background:#F7E7E5;color:var(--sat)}
.pill.notr-al{background:#FBF0C4;color:#7A5F00}.pill.notr-sat{background:#FDE1CC;color:#B0480C}
.yildiz{color:#C7962B}.tag{font-size:10px;margin-left:5px}.tag.ucuz{color:var(--al)}.tag.pahali{color:var(--sat)}
.yeni{color:#fff;font-size:9.5px;font-weight:700;padding:2px 6px;border-radius:5px;margin-left:6px;letter-spacing:.03em}
.yeni.yal{background:#1B7F4B}.yeni.ysat{background:#B4362E}.yeni.ynotr{background:#9A7A12}
.sdb{color:#fff;font-size:9.5px;font-weight:700;padding:2px 6px;border-radius:5px;margin-left:5px}
.sdb.destek{background:#3A6EA5}.sdb.direnc{background:#B7791F}.sdb.destekzayif{background:#8A94A6}
.hacimb,.gun1b,.patlakb,.arzb{font-size:9.5px;font-weight:700;padding:2px 6px;border-radius:5px;margin-left:5px;white-space:nowrap}
.hacimb{background:#E4F2E9;color:#1B7F4B}.gun1b{background:#FDE1CC;color:#B0480C}.patlakb{background:#B4362E;color:#fff}
.arzb{background:#EEE8F7;color:#5B3E96}
.bolum{font-size:16px;margin:28px 0 0}.bolumalt{font-size:12.5px;color:var(--muted);font-weight:500}
.pozkutu{margin:0 0 14px;border:2px solid var(--accent);border-radius:12px;padding:12px 15px;font-size:13.2px;line-height:1.6;background:#F6FAF8}
.pozkutu .pbas{font-weight:700;color:var(--accent);margin-bottom:4px}.pozkutu .pk{margin-top:3px}
.arzkutu{margin:0 0 14px;border:1px solid #D9CFEB;background:#F8F5FC;border-radius:10px;padding:10px 14px;font-size:13px;line-height:1.55}
.patlakkutu{margin:0 0 14px;border:1px solid #E6C3BD;background:#FBECEA;color:#8A2F26;border-radius:10px;padding:10px 14px;font-size:13px}
.sdkutu{margin:0 0 14px;border:1px solid var(--line);border-radius:10px;padding:11px 14px;font-size:13px;line-height:1.55}
.sdsat+.sdsat{margin-top:4px}.sdnot{margin-top:8px;padding:8px 10px;border-radius:8px;font-size:12.5px}
.sdnot.destek{background:#EAF1F8;color:#28507A}.sdnot.direnc{background:#FBF3E4;color:#7A5B10}
.sdyok{margin-top:6px;color:var(--muted);font-size:12.5px}.sdyontem{margin-top:8px;color:var(--muted);font-size:11.5px}
.tarih a{color:var(--accent);font-weight:600;text-decoration:none}.tarih a:hover{text-decoration:underline}
.sgun{color:var(--muted)}
.pfsag{display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:8px 12px}
.sektorb{margin-left:8px;font-size:11.5px;background:#EEF1F5;color:#4A5568;padding:2px 8px;border-radius:999px}
.pfdag{margin-top:8px;font-size:12.5px;color:var(--muted)}.pfdag.uyar{color:#8A2F26;background:#FBECEA;border:1px solid #E6C3BD;border-radius:8px;padding:8px 11px}
.pfuv{display:flex;align-items:center;gap:5px;font-size:13px;color:var(--ink);cursor:pointer}
.uvb{background:#E8EEF7;color:#28507A;font-size:9.5px;font-weight:700;padding:2px 5px;border-radius:5px;margin-left:5px}
.alkutu{margin-top:14px;border:1px solid var(--line);border-radius:10px;padding:10px 13px;background:#FCFCFB}
.alsat{font-size:13px;margin:3px 0;display:flex;align-items:center;gap:8px;flex-wrap:wrap}.aloneri{margin-top:8px;padding-top:6px;border-top:1px dashed var(--line)}.alkur{padding:4px 10px!important;font-size:12px}
.sade{margin:10px 0 12px;border:1px solid #DCE3EE;background:#F6F8FB;border-radius:10px;padding:11px 14px;font-size:13.3px;line-height:1.6}.sade .ss+.ss{margin-top:5px}.nedenkutu .ns{margin:3px 0}.nedenkutu a{color:var(--accent)}
.favtd{width:26px;padding-right:0!important}.fav{border:0;background:none;cursor:pointer;font-size:15px;line-height:1;padding:2px;color:#C7962B}tr.favrow td{background:#FFFBEB}.tabcubuk{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:0 0 10px}#ara{flex:1 1 180px;max-width:260px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;font-size:13px}.sfav{font-size:13px;display:flex;gap:5px;align-items:center;cursor:pointer}.mfav{margin-left:8px;border:1px solid var(--line);background:var(--panel);border-radius:7px;padding:3px 9px;font-size:12px;cursor:pointer}
.bugun{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:0 0 16px}.bugun h2{font-size:15px;margin:0 0 8px}.bgs{font-size:13.2px;line-height:1.6;margin:0 0 5px}.bgk{font-weight:700;color:var(--accent);text-decoration:none}
.mozet{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:2px 0 12px}.mozet span{margin-left:0!important}
.momb{background:#E8F0FB;color:#1F4E8C;font-size:9.5px;font-weight:700;padding:2px 6px;border-radius:5px;margin-left:5px;white-space:nowrap}
.gucb{display:inline-block;min-width:30px;text-align:center;font-size:11px;font-weight:700;padding:2px 5px;border-radius:5px;background:#F1F1EE;color:#555}.gucb.g5,.gucb.g6,.gucb.g7{background:#E4F2E9;color:#14633A}.gucb.g0,.gucb.g1,.gucb.g2{background:#FBECEA;color:#8A2F26}
.sozluk{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin:12px 0 18px}.szgrup{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 15px}.szgrup h3{margin:0 0 8px;font-size:13.5px}.sz{display:flex;gap:9px;align-items:baseline;font-size:12.6px;line-height:1.5;margin:0 0 7px;color:var(--muted)}.sz>span:first-child,.sz>b{flex:0 0 auto;min-width:112px;color:var(--ink)}.sz>span:first-child{margin-left:0}
.guckutu .gs{display:flex;gap:8px;font-size:12.8px;line-height:1.5;margin:2px 0}.guckutu .gs b{min-width:150px}
.tkb{background:#FFF1E0;color:#8A4B00;font-size:9.5px;font-weight:700;padding:2px 6px;border-radius:5px;margin-left:5px;white-space:nowrap}.tkb.yeni{background:#8A4B00;color:#fff}.tkb.izle{background:#F3F3F1;color:#555}
.rsb{display:inline-block;min-width:24px;text-align:center;font-size:11px;font-weight:700;padding:2px 4px;border-radius:5px;background:#F1F1EE;color:#555}.rsb.rsy{background:#E4F2E9;color:#14633A}
.bilb{background:#EEF1F8;color:#2F4A7A;font-size:9.5px;font-weight:700;padding:2px 6px;border-radius:5px;margin-left:5px;white-space:nowrap}
.bilkutu{margin:0 0 14px;border:1px solid var(--line);border-radius:10px;padding:10px 14px;font-size:13px;line-height:1.55}
.bilkutu svg{display:block;width:100%;max-width:420px;height:auto;margin-top:6px}
.uvsb{background:#E4F2E9;color:#14633A;font-size:9.5px;font-weight:700;padding:2px 6px;border-radius:5px;margin-left:5px;white-space:nowrap}
.bayrakb{font-size:11px;margin-left:4px}
td.vd{white-space:nowrap;font-size:12px}.vu,.va,.vy{font-style:normal;font-weight:700}.vu{color:#1B7F4B}.va{color:#B4362E}.vy{color:var(--muted);font-weight:400}
.uvkutu{margin:0 0 14px;border:1px solid #CFE3D6;background:#F4FAF6;border-radius:10px;padding:10px 14px;font-size:13px;line-height:1.55}
.pfbulut{font-size:12px;color:var(--muted);margin:-2px 0 8px}.pfbulut a{color:var(--accent);font-weight:600}
.pfbulut.ok{color:var(--pos)}.pfbulut.hata{color:var(--neg)}.pfduz{color:var(--accent)!important}
.kurlist{margin:8px 0;padding-left:20px;font-size:12.5px}.kurlist li{margin:3px 0}.pfform input:disabled{background:#F1F1EE}
.pfekle{border:1px solid var(--accent);background:var(--accent);color:#fff;font-weight:600;font-size:12.5px;padding:6px 12px;border-radius:8px;cursor:pointer}
.pfform{display:none;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.pfform input{border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:13px;font-family:inherit}
.pfform #pfalis{width:150px}.pfkiyas{margin:10px 0 0;font-size:13px;line-height:1.55;border:1px solid var(--line);border-radius:10px;padding:9px 13px;background:var(--panel)}.pfxu{display:block;font-size:10.5px;color:var(--muted)}
.pfform #pfkod{width:150px}.pfform #pfadet,.pfform #pfmal{width:120px}
.pfkaydet{border:none;background:var(--al);color:#fff;font-weight:600;padding:8px 14px;border-radius:8px;cursor:pointer}
.pfipt{border:1px solid var(--line);background:#fff;color:var(--muted);padding:8px 12px;border-radius:8px;cursor:pointer}
.pfsil{border:none;background:#F1EFEA;color:var(--sat);width:26px;height:26px;border-radius:6px;cursor:pointer;font-size:12px}
.zaman{margin:12px 0 4px;background:#F3F7F5;border:1px solid #DCE8E2;border-radius:10px;padding:11px 14px;font-size:13px;line-height:1.55}
.zaman .cikis{margin-top:6px;color:var(--muted);font-size:12.5px}
.aciklama{margin-top:32px;display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}
.kart{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:15px 17px}
.kart h3{margin:0 0 6px;font-size:13.5px}.kart p{margin:0;color:var(--muted);font-size:12.8px;line-height:1.55}
.kotugun{margin-top:12px}.kotugun.uyar{border-color:#E6C3BD;background:#FFF8F6}.kotugun .sar{margin:10px 0 8px}.kotugun p.sgun{font-size:11.5px;margin-top:6px}.kgkarne{color:var(--ink)!important}
table.kgt{min-width:0;font-size:12.5px}.kgt th,.kgt td{padding:7px 10px}.kgt th{white-space:normal}
@media(max-width:560px){.kgt th,.kgt td{padding:6px 5px;font-size:11.5px}}
.genb{display:flex;flex-wrap:wrap;align-items:center;gap:4px 12px}.genb>span{flex:1 1 260px;min-width:0}.gencz{flex:none;max-width:100%}
.lotkutu{margin:12px 0;padding:11px 13px;border:1px solid var(--line);border-radius:10px;background:var(--panel)}.lotform{flex-wrap:wrap;gap:8px;margin:6px 0 4px}
.lotform label{display:flex;flex-direction:column;font-size:11.5px;color:var(--muted);gap:3px}.lotform input,.lotform select{width:140px;max-width:100%}
.lotform select{border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:13px;font-family:inherit;background:#fff}.lotsonuc .pk{margin:4px 0;font-size:12.8px;line-height:1.5}.pfkiyas.uyar{border-color:#E6C3BD;background:#FBECEA}
.durust{margin-top:12px;padding:13px 16px;border:1px solid var(--line);border-left:4px solid #B7791F;border-radius:10px;background:#FFFBF2;color:#5B4A2A;font-size:12.6px;line-height:1.6;overflow-wrap:anywhere}
.uyari{margin-top:28px;padding:13px 16px;border:1px solid var(--line);border-radius:10px;background:#fff;color:var(--muted);font-size:12.2px;line-height:1.6}
.odabtn{display:inline-block;margin-left:10px;vertical-align:2px;font-size:12.5px;font-weight:650;color:#fff;background:#6D3FD8;border-radius:999px;padding:4px 11px;text-decoration:none}.odabtn:hover{background:#5A2FC0}.glink{color:var(--accent);font-weight:600;text-decoration:none}.glink:hover{text-decoration:underline}
.pfbox{margin-top:18px}
.pfbas{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:8px}
.pfbas h2{margin:0;font-size:16px}.pftop{font-weight:650;font-size:14px}.pftop.pos{color:var(--pos)}.pftop.neg{color:var(--neg)}
table.pf{min-width:900px}
.pfy.bos{padding:12px 14px;border:1px dashed var(--line);border-radius:10px;color:var(--muted);font-size:12.8px;background:#fff}
.pfy.bos code{background:#F1F1EE;padding:2px 5px;border-radius:4px;font-size:12px}
.pfuy{color:var(--sat);font-size:11px;font-weight:600;margin-left:6px}
/* modal */
.ust{position:fixed;inset:0;background:rgba(20,22,26,.45);display:none;align-items:center;justify-content:center;padding:16px;z-index:9}
.ust.acik{display:flex}
.modal{background:#fff;border-radius:16px;max-width:640px;width:100%;max-height:92vh;overflow:auto;padding:22px}
.mh{display:flex;align-items:center;justify-content:space-between;gap:12px}
.mh .sol{display:flex;align-items:center;gap:10px}.mh h2{margin:0;font-size:20px}
.kapa{border:none;background:#F1F1EE;width:32px;height:32px;border-radius:8px;font-size:18px;cursor:pointer;color:var(--muted)}
.mfiyat{margin-top:6px;font-size:14px;color:var(--muted)}
.grafik{position:relative;margin:16px 0;border:1px solid var(--line);border-radius:10px;padding:8px;background:#FCFCFB}
.grbilgi{position:absolute;top:8px;background:rgba(255,255,255,.95);border:1px solid var(--line);border-radius:8px;padding:5px 9px;font-size:11.5px;line-height:1.45;pointer-events:none;white-space:nowrap;box-shadow:0 2px 6px rgba(0,0,0,.06)}
.metr{display:grid;grid-template-columns:repeat(auto-fit,minmax(95px,1fr));gap:10px;margin:6px 0 14px}
.metr .m{background:#F7F7F4;border-radius:9px;padding:9px 11px}.metr .m .l{color:var(--muted);font-size:11px}.metr .m .v{font-weight:650;font-size:15px;margin-top:2px}
.yorum{background:#F3F7F5;border:1px solid #DCE8E2;border-radius:10px;padding:13px 15px;font-size:13.5px;line-height:1.6}
.btnler{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}
.btn{display:inline-block;padding:10px 14px;border-radius:9px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid var(--line);color:var(--ink);background:#fff}
.btn.p{background:var(--accent);color:#fff;border-color:var(--accent)}
.leg{display:flex;gap:14px;font-size:11px;color:var(--muted);margin-top:4px;padding-left:8px}
.leg span::before{content:"";display:inline-block;width:10px;height:2px;margin-right:5px;vertical-align:middle}
.leg .c1::before{background:#16181D}.leg .c2::before{background:#0E4D45}.leg .c3::before{background:#C7962B}.leg .c4::before{background:#B4362E}
.leg .c5::before{background:#3A6EA5}.leg .c6::before{background:#B7791F}.leg .c7::before{background:repeating-linear-gradient(90deg,#7A3E9D 0 5px,transparent 5px 7px)}
.leg{flex-wrap:wrap}.leg .lm::before{display:none}
.tkson{font-size:12.8px;line-height:1.5;margin:2px 4px 6px}.kilc{display:block;font-size:11px;color:#8A2F26;white-space:normal;font-weight:600;text-align:left}.kkc{display:block;font-size:11px;color:#7A3E9D;white-space:normal;font-weight:600;text-align:left}.graralik{display:flex;gap:6px;margin:0 4px 6px}
.grb{border:1px solid var(--line);background:#fff;border-radius:7px;padding:3px 10px;font-size:12px;cursor:pointer;color:var(--muted)}.grb.on{background:var(--accent);border-color:var(--accent);color:#fff}
.tkgs{overflow-x:auto;margin:6px 0 2px}table.rk{min-width:0;font-size:12.5px}table.rk th,table.rk td{padding:6px 8px}.tkgs tbody tr{cursor:default}.tkgs tbody tr:hover,.tkgs tbody tr:hover td{background:none}
.rkkutu .sar{margin-top:8px}.rkkutu table.rk{min-width:640px}#roket{border:1px solid var(--line);border-radius:7px;padding:4px 6px;font-size:13px;background:#fff}
.uyum{font-weight:650;color:var(--accent)}
.uyroz{background:#EEF4F1;color:var(--accent);font-size:11.5px;font-weight:650;padding:2px 8px;border-radius:999px}
.gbas{font-size:13px;font-weight:650;margin:4px 0 8px}
.gliste{display:grid;grid-template-columns:1fr;gap:7px;margin-bottom:12px}
.gi{display:flex;align-items:flex-start;gap:10px;background:#F7F7F4;border-radius:9px;padding:8px 11px}
.gi .pill{flex:none}.gt{display:flex;flex-direction:column;line-height:1.3}.gt b{font-size:12.5px}.gt span{font-size:11.5px;color:var(--muted)}
.ekler{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.ekb{background:#FBF7EE;border:1px solid #EADFC7;border-radius:8px;padding:5px 9px;font-size:11.5px;color:#7A5B10}
@media(max-width:560px){.ozet .b{font-size:30px}}
/* 📒 İşlem Defterim */
.pfsat{border:1px solid #BFDDC9;background:#E4F2E9;color:#14633A;font-weight:650;font-size:11.5px;padding:4px 8px;border-radius:6px;cursor:pointer;font-family:inherit}
.pfacik{margin-top:6px;font-size:11.8px;color:var(--muted);line-height:1.5}
.dfbox{margin-top:18px;border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:0 14px}
.dfbox>summary{cursor:pointer;list-style:none;display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px;padding:13px 0}
.dfbox>summary::-webkit-details-marker{display:none}
.dfbox>summary::before{content:"▸";color:var(--muted);font-size:13px}.dfbox[open]>summary::before{content:"▾"}
.dfbaslik{font-size:16px;font-weight:650}.dfozet{font-size:12.5px;color:var(--muted)}
.dfic{padding:0 0 14px;min-width:0}
.dfodak{border:1px solid #DCE3EE;background:#F6F8FB;border-radius:10px;padding:10px 13px;font-size:12.8px;line-height:1.55;margin:0 0 10px}
.dfcubuk{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 10px}
.dfcubuk input{flex:1 1 150px;max-width:230px;min-width:0;padding:7px 10px;border:1px solid var(--line);border-radius:8px;font-size:13px;font-family:inherit}
.dfcubuk select{border:1px solid var(--line);border-radius:8px;padding:7px 8px;font-size:13px;background:#fff;max-width:100%;font-family:inherit}
.dfbtn{border:1px solid var(--line);background:#fff;color:var(--ink);padding:7px 11px;border-radius:8px;cursor:pointer;font-size:12.5px;font-family:inherit}
.dfbtn.p{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}.dfbtn.tehlike{color:var(--sat)}.dfbtn.kucuk{padding:3px 8px;font-size:11.5px}
.dfkartlar{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:0 0 12px}
.dfk{border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:#FCFCFB;min-width:0}
.dfk .l{font-size:11.5px;color:var(--muted)}.dfk .v{font-size:19px;font-weight:680;margin-top:2px;overflow-wrap:anywhere}.dfk .a{font-size:11.5px;color:var(--muted);margin-top:2px;line-height:1.4}
.dfgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:12px;margin:12px 0}
.dfpanel{border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:#FCFCFB;min-width:0}
.dfpanel h3{margin:0 0 6px;font-size:13.5px}.dfpanel svg{display:block;width:100%;height:auto}
.dftakbas{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px;font-size:13px}
.dftak{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:3px}
.dftak .dgb{font-size:10.5px;color:var(--muted);text-align:center;padding:2px 0}
.dftak .dgk{min-height:44px;border:1px solid var(--line);border-radius:6px;padding:3px;font-size:10px;line-height:1.25;background:#fff;overflow:hidden;min-width:0}
.dftak .dgk.bos{border:none;background:none}.dftak .dgk.kaz{background:#E4F2E9;border-color:#BFDDC9;color:#14633A}.dftak .dgk.zar{background:#F7E7E5;border-color:#E6C3BD;color:#8A2F26}.dftak .dgk.be{background:#F1EFE8}
.dftak .dgk.bugun{outline:2px solid var(--accent);outline-offset:-1px}.dftak .dgn{font-weight:650;color:var(--muted)}.dftak .dgt{font-weight:700;overflow-wrap:anywhere}
table.df{min-width:860px;font-size:13px}table.df td,table.df th{padding:8px 9px}
.dfroz{display:inline-block;font-size:10.5px;font-weight:650;padding:2px 6px;border-radius:5px;margin:1px 3px 1px 0;white-space:nowrap;background:#F1F1EE;color:#555}
.dfroz.iyi{background:#E4F2E9;color:#14633A}.dfroz.kot{background:#FDE1CC;color:#B0480C}
tr.dfdetay td{white-space:normal;background:#FAFAF8;font-size:12.5px;line-height:1.6;cursor:default}tr.dfdetay:hover td{background:#FAFAF8}
.dfdk{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:4px 16px;max-width:1000px}.dfmetin{white-space:pre-wrap;overflow-wrap:anywhere}
.dfat{font-size:12.5px;line-height:1.55}.dfat table{min-width:0;font-size:12px}.dfat th,.dfat td{padding:4px 6px;white-space:normal}.dfat td.num,.dfat th.num{white-space:nowrap}.dfat tbody tr{cursor:default}
.dfaz{color:var(--muted)}
.dfcik{margin:12px 0 0;padding:10px 13px;border-radius:10px;background:#F3F7F5;border:1px solid #DCE8E2;font-size:12.8px;line-height:1.6}.dfcik ul{margin:4px 0 0;padding-left:18px}
.dfsans{margin-top:8px;padding:9px 12px;border-radius:9px;background:#FFFBF2;border:1px solid #EADFC7;color:#5B4A2A;font-size:12.3px;line-height:1.55}
.dfform{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:12px}
.dfform label{display:flex;flex-direction:column;gap:3px;font-size:12px;color:var(--muted);min-width:0}
.dfform input,.dfform select,.dfform textarea{border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:13px;font-family:inherit;color:var(--ink);background:#fff;width:100%;min-width:0}
.dfform input:disabled{background:#F1F1EE}.dfform textarea{min-height:58px;resize:vertical}.dfform .tam{grid-column:1/-1}.dfform .ipucu2{font-size:11.5px;color:var(--muted);line-height:1.45}
.dfonay{display:inline-flex;flex-wrap:wrap;gap:4px;align-items:center;font-size:12px}
@media(max-width:480px){.dfform{grid-template-columns:1fr}.dfk .v{font-size:17px}}
</style>
</head><body><div class="wrap">
<header><div><h1>BIST Sinyal Panosu <a class="odabtn" href="oda.html" title="Sanal parayla kural robotları: panonun kurallarını 100.000 sanal TL ile deniyorlar (yatırım tavsiyesi değil)">🏢 İşlem Odası</a></h1><div class="tarih">Son güncelleme: __TARIH__ · <a href="#" onclick="yenile();return false" title="Sayfanın en son halini getirir (önbelleği atlar)">↻ Yenile</a> · <a href="https://github.com/__REPO__/actions/workflows/tarama.yml" target="_blank" rel="noopener" title="GitHub'da 'Run workflow' ile taramayı hemen başlat; 3-5 dk sonra Yenile'ye bas">Taramayı şimdi başlat ↗</a></div></div>
<div class="ozet">
<div><div class="b">__TKBUGUN__</div><div class="l">bugün 🚀 AL</div></div>
<div><div class="b g">__TK5__</div><div class="l">son 5 günde 🚀 AL · __TOPLAM__ hisse taranıyor</div></div>
</div></header>
<div class="ipucu">İncelemek için bir satıra tıkla → grafik, oranlar ve o hisseye özel yorum açılır. Sütun başlığına tıklayınca sıralanır. · <a class="glink" href="gecmis.html">Sinyal Geçmişi →</a></div>
__BANNER__
<div id="bugun" class="bugun"></div>
<div class="pfbox">
  <div class="pfbas"><h2>Portföyüm</h2><div class="pfsag"><span id="pftop" class="pftop"></span><button class="pfekle" onclick="pfFormAc()">+ Ekle</button></div></div>
  <div id="pfbulut" class="pfbulut"></div>
  <div id="pfkur" class="zaman" hidden></div>
  <div id="pfnot" class="zaman" hidden></div>
  <div id="pfform" class="pfform">
    <input id="pfkod" placeholder="Hisse (örn. THYAO)" list="pfkodlar" autocomplete="off">
    <datalist id="pfkodlar"></datalist>
    <input id="pfadet" type="number" min="1" placeholder="Adet">
    <input id="pfmal" type="number" step="any" min="0" placeholder="Maliyet (TL)">
    <input id="pfalis" type="date" title="Alış tarihi (isteğe bağlı): girersen portföyün aynı parayla aynı gün BIST 100 almakla kıyaslanır">
    <input id="pfneden" maxlength="500" placeholder="Neden aldım? (isteğe bağlı)" title="İsteğe bağlı: alım nedenin / planın. Bu cihazda ve GitHub'daki DEFTER kaydında tutulur (Telegram'a ve herkese açık dosyalara gitmez); satarken 📒 deftere kendiliğinden gelir" style="flex:1 1 220px;min-width:0">
    <label class="pfuv" title="Uzun vadeli tuttuğun hisse: kısa vadeli SAT sinyalleri bilgi olarak gelir, çıkış yerine karar çizgisi (ana destek) gösterilir"><input id="pfuzun" type="checkbox"> Uzun vade</label>
    <button id="pfkaydetbtn" class="pfkaydet" onclick="pfKaydet()">Ekle</button>
    <button class="pfipt" onclick="pfFormKapat()">İptal</button>
  </div>
  <div id="pflist"></div>
</div>
<details class="dfbox" id="dfbox" ontoggle="dfAcikKaydet()"><summary><span class="dfbaslik">📒 İşlem Defterim</span><span id="dfozet" class="dfozet"></span></summary>
<div class="dfic">
  <div id="dfbulut" class="pfbulut"></div>
  <div id="dfnot" class="zaman" hidden></div>
  <div class="dfodak">🎯 <b>Defterin amacı</b> sadece ne kadar kazandığını görmek değil: <b>hangi koşullarda iyi, hangilerinde kötü işlem yaptığını</b> anlamak. Portföyünde <b>Sattım</b>'a basınca işlem buraya yazılır. Duygunu, planına uyup uymadığını ve kaliteyi dürüstçe işaretle; alış ve satış günü sistemin (🚀) ne dediğini ve aynı günlerde BIST 100'ün ne yaptığını pano kendisi ekler. <b>Kalite sonuca göre değil karara göre</b>: zararla kapanan planlı işlem A olabilir, kârla kapanan dürtüsel işlem C. Yatırım tavsiyesi değildir.</div>
  <div class="dfcubuk"><input id="dfara" type="search" placeholder="🔍 Hisse ya da notta ara" autocomplete="off" oninput="dfRender()">
   <select id="dfsonuc" onchange="dfRender()" title="Sonuca göre süz"><option value="">Tüm sonuçlar</option><option value="kaz">Kazançlar</option><option value="zar">Zararlar</option><option value="be">Başa baş (±%0,5)</option></select>
   <select id="dfsin" onchange="dfRender()" title="Alış günü sistemde 🚀 AL var mıydı?"><option value="">Sinyal: hepsi</option><option value="uy">🚀 AL'de aldıklarım</option><option value="uymaz">Sinyalsiz / geç aldıklarım</option><option value="erken">Erken çıktıklarım</option></select>
   <button class="dfbtn p" onclick="dfFormAc('yeni')" title="Portföye hiç girmemiş eski bir işlemi elle ekle">+ Geçmiş işlem</button>
   <button class="dfbtn" onclick="dfCsvIndir()" title="Excel'de açılır (Türkçe, noktalı virgüllü)">⬇ CSV yedeği</button>
   <button class="dfbtn" onclick="document.getElementById('dfdosya').click()" title="CSV'den ekle: mevcut kayıtlar silinmez, aynı kayıt (id) varsa atlanır">⬆ İçe aktar</button><input id="dfdosya" type="file" accept=".csv,text/csv" hidden onchange="dfCsvOku(this)">
   <button class="dfbtn tehlike" onclick="dfTemizleSor()">Defteri temizle</button></div>
  <div id="dfkartlar" class="dfkartlar"></div>
  <div id="dfgovde"></div>
</div>
</details>
<div class="tabcubuk"><input id="ara" placeholder="🔍 Hisse ara (örn. THY)" autocomplete="off" oninput="tabloDuzen()"><label class="sfav"><input id="sadecefav" type="checkbox" onchange="tabloDuzen()"> ⭐ Sadece favoriler <span id="favsay"></span></label><label class="sfav" title="Son N işlem gününde 🚀 AL almış hisseler: sinyal günü, girişten beri getiri, BIST 100'e göre fark; iz stop ile kapananlar da dahil">🚀 Son roketler <select id="roket" onchange="tabloDuzen()"><option value="0">kapalı</option><option value="5">5 gün</option><option value="20">20 gün</option><option value="60">60 gün</option></select></label><span class="sgun">☆'ya basınca hisse favorilere eklenir ve en üste çıkar.</span></div>
<div id="roketkutu" hidden></div>
<div class="sar" id="tsar"><table id="t"><thead><tr>
<th data-t="f" title="Favori">⭐</th><th data-t="s">Hisse</th><th class="num" data-t="n">Fiyat</th><th class="num" data-t="n">Değişim</th><th data-t="s">Sinyal</th>
<th class="num" data-t="n">Sinyalde</th><th class="num" data-t="n">Uyum</th><th class="num" data-t="n" title="7 iyi göstergeden kaçı olumlu (kısa vadeli güç)">Güç</th><th class="num" data-t="n" title="RS puanı 0-99: son 1 yılın getirisi (son 3 aya ağırlıklı) taranan hisseler içinde kaçıncı yüzdelikte — bilgi, filtre değil">RS</th><th data-t="v" title="Günlük / Haftalık / Aylık trend oku (bilgi, sinyal değil)">Vade</th><th class="num" data-t="n">RSI</th><th class="num" data-t="n">F/K</th><th class="num" data-t="n">PD/DD</th><th class="num" data-t="n">Stop</th><th class="num" data-t="n">Öneri lot</th>
</tr></thead><tbody>__ROWS__</tbody></table></div>
__ARZ__
<h2 class="bolum">İşaretler ne demek? <span class="bolumalt">— tablodaki ve hisse penceresindeki tüm rozetler</span></h2>
<div class="sozluk">
<div class="szgrup"><h3>Alım sinyali (v3)</h3>
<div class="sz"><span class="tkb yeni">🚀 KIRILIM</span><span>Bugün AL: hisse güçlü trenddeyken (fiyat 50/150/200 günlük ortalamaların üstünde, 52 hafta zirvesine yakın) son 20 günün zirvesini ilk kez aştı. Telegram'a gelen AL budur. Çıkış: tepe kapanışın %20 altı (iz stop).__KKCUMLE__</span></div>__KKSOZ__
<div class="sz"><span class="tkb">🚀 AL 3g önce</span><span>AL birkaç gün önce geldi. Testte ilk 5 gün içinde almak, sinyal günüyle neredeyse aynı sonucu verdi.</span></div>
<div class="sz"><span class="tkb izle">trendde · 25g</span><span>Eski AL hâlâ sürüyor ama <b>yeni alım sinyali değil</b>: 20+ gün sonra girmek testte belirgin kötüydü. Elindeyse iz stop'a kadar tut.</span></div>
<div class="sz"><span class="tkb izle">🚀 Son roketler</span><span>Tablonun üstündeki filtre: son 5 / 20 / 60 işlem gününde 🚀 AL almış hisseler; sinyal günü, girişten beri getiri, BIST 100'e göre fark. İz stop ile kapananlar da listede (sadece iyi gidenleri göstermek yanıltıcı olur). Eski sinyaller yeni alım sinyali değil.</span></div>
<div class="sz"><span class="tkb">⚠️ çok yükselmiş</span><span>Hisse penceresinde 🚀 AL notu: sinyal günü fiyat 52 hafta dibinin 5+ katı ya da 6 ayda 3+ kat. Geçmişte bu tür girişlerin ~%13'ü %30+ kayıpla kapandı (diğerlerinde ~%1), en büyük kazananların bir kısmı da bu grupta. AL engellenmez; pozisyon büyüklüğüne dikkat.</span></div>
<div class="sz"><span class="tkb">📏 sıkı çizgi</span><span>Hisse penceresinde, açık 🚀 pozisyonda hisse girişten beri çok yükseldiyse (52 hafta dibinin 5+ katı ya da 6 ayda 3+ kat): son 26 günün en yüksek ve en düşük fiyatının ortası (Ichimoku 'kijun'; grafikte pembe kesikli). Altında kapanış geçmişte bazen çöküşün habercisi oldu (sonraki 20 günde ~%5 taban serisi, ~%11 %25+ düşüş), ama ~%20'sinde fiyat %25+ yükselmeye devam etti. Kural değil, bilgi; asıl çıkış iz stop. Portföydeyse altında kapanış 'Bugün ne var?' kartında ve akşam özetinde yazar.</span></div>
<div class="sz"><span class="tkb izle">👀 kırılıma %2</span><span>Trend şablonunda, 20 günlük zirveye yakın: yakında AL gelebilir (bunların ~%76'sı 10 gün içinde kırıyor). Beklemeden almak ek fayda sağlamadı.</span></div>
</div>
<div class="szgrup"><h3>Uyarılar (dikkat)</h3>
<div class="sz"><span class="patlakb">🔒 kilitli taban</span><span>2 gündür taban ve bugün gün boyu işlem neredeyse yok (fiyat tabana yapışık, alıcı yok). Geçmişte (2021-26, 587 hisse) benzerlerinin ~%60'ı 15 günde 4+ tabana uzadı (normalde ~%9); 'taban serisi' uyarısından ~2 gün önce gelir. Kilitli tabanda satış emri çoğu zaman gerçekleşmez. Piyasanın çöktüğü günde (BIST 100 −%4 ve altı) başlayan serileri yakalamaz. Kesin değil; AL mesajı gönderilmez.</span></div>
<div class="sz"><span class="patlakb">🎈 şişme</span><span>Tahtacı şişirmesi olabilir: kısa sürede çok tavan / fiyat ikiye katlandı / aşırı şişkin ve oynak. 20 günde %25+ çakılma olasılığı normalin 7-8 katı. AL mesajı gönderilmez. Aynı işaret düşüşten sonraki tepki tavanlarında da çıkar (20 günde hâlâ eksideyse '🎈 sert dalgalanma' yazar).</span></div>
<div class="sz"><span class="patlakb">⚠️ manipülasyon işareti</span><span>Şu 5 işaretten en az 2'si var: son 120 günde 3+ gün art arda tavan; son 120 günde fiyat 60 günde 3 katına çıktı; son 250 günde hisseye özel taban serisi (15 günde 4+ taban); son 60 günde Borsa İstanbul VBTS (volatilite bazlı tedbir) kararı; son 365 günde SPK tedbir kararı (son ikisi KAP'tan). Geçmişte bu hisselerde kilitli tabanda satamama riski birkaç kat yüksekti (10.10.2026 araştırması ~2,7 kat; 2018-26 testinde 60 günde kilitli taban %11-13, diğerlerinde %2-3). Bilgi: alım yasağı değil, AL/SAT kuralı değişmez; pozisyonu küçük tut.</span></div>
<div class="sz"><span class="gun1b">⚠️ dağıtım</span><span>Hacim patlarken fiyat 10 günlük zirvenin %8+ altında: büyük satıcı malı dağıtıyor olabilir (çakılma olasılığı ~4 kat).</span></div>
<div class="sz"><span class="gun1b">🔻 özel düşüş</span><span>Son 5 ya da 20 günde endeksten belirgin fazla (10 / 20 puan) ve yüksek hacimle düştü; benzer hisseler bu kadar düşmedi. Geçmişte bu durumdakilerin sonraki 20 günde ~%38'i endeksi geçti (normalde ~%46); 2022-23 düşük faiz döneminde fark yoktu. Bilgi, sinyal değil.</span></div>
<div class="sz"><span class="gun1b">🪤 tuzak riski</span><span>Dipteki hisse düşen trendi %4+ yükselişle kırdı. Grafikte "AL" gibi görünür ama tüm borsada bu kırılımların %56'sı 15 günde geri düştü; kırılımda almak rastgele günden kötüydü.</span></div>
<div class="sz"><span class="patlakb">⚠ taban serisi</span><span>Son 15 günde 4+ kez ~%10 düştü (fon krizi tipi çöküş). AL mesajı gönderilmez.</span></div>
<div class="sz"><span class="patlakb">⚡ oynak</span><span>Son 60 günde günlük oynaklık %5'ten fazla (spekülatif). v3 AL vermez.</span></div>
<div class="sz"><span class="sdb direnc">Dirence yaklaşıyor</span><span>Fiyat geçmişte satış gelen bir tepeye yakın.</span></div>
<div class="sz"><span class="sdb destekzayif">Destekte (SAT sürüyor)</span><span>SAT sürerken desteğe geldi; bu desteklerin ~%68'i 20 günde kırıldı.</span></div>
</div>
<div class="szgrup"><h3>Bilgi</h3>
<div class="sz"><span class="momb">📈 ayın güçlüsü</span><span>Son 6 ayın en güçlü %20'si (fiyat 200 günlük ortalamanın üstünde). Her ay yenilenir, Telegram'a liste gelir. AL sinyali değil; v3 ile yarı yarıya kullanım testte iyiydi.</span></div>
<div class="sz"><span class="rsb rsy">85</span><span><b>RS</b> sütunu (göreli güç, 0-99): son 1 yılın getirisi, son 3 aya ağırlık vererek (0,4 × 3 ay + 0,2 × 6, 9 ve 12 ay), taranan tüm hisseler içinde kaçıncı yüzdelikte. 85 = hisselerin ~%85'inden güçlü; 1 yıldan kısa geçmişte boş. Geçmişte 🚀 alımlarında RS 80 ve üstü olanlar ortalama +%30, diğerleri +%19 kazandırdı (isabetleri biraz düşük). Filtre olarak kullanmak işe yaramadı: bilgi, filtre değil.</span></div>
<div class="sz"><span class="bilb">📊 güçlü tepki</span><span><b>Bilanço tepkisi</b> (sadece BIST 100 + ek liste): şirketin finansal raporu KAP'ta ilk yayınlandıktan sonraki 2 günde hisse BIST 100'den 5 puan ya da daha fazla iyi gitti (📊 zayıf tepki: 5+ puan kötü). Tepki gününden sonra 60 işlem günü görünür; hisse penceresinde tarih ve tepki yazar. Geçmişte güçlü tepki verenler sonraki 60 günde endeksi %56 oranında geçti (normal tepkide %49, zayıfta %46) — zayıf bir eğilim; küçük hisselerde görülmedi. Alım/satım sinyali değil.</span></div>
<div class="sz"><span>🧾</span><span><b>Son 4 çeyrekte zarar</b>: hisse penceresinin 🚀 kutusunda not (son 4 çeyreğin net kârı toplamı sıfır ya da eksi; kaynak İş Yatırım mali tabloları, veri yoksa not çıkmaz). Geçmişte zarardaki şirketlerdeki 🚀 alımları ortalama +%17, kârlı şirketlerde +%23 getirdi; bunları atmak portföyü iyileştirmedi. Filtre değil, Telegram'a girmez.</span></div>
<div class="sz"><span class="gucb g5">5/7</span><span><b>Güç</b> sütunu: 7 iyi göstergeden kaçı olumlu (şablon, Ichimoku, 55 gün zirve, para akışı, ADX, EMA 10/30, RSI). Yüksek puan sonraki ~1 ayda endeksten iyi gitmeye işaret etti; alım sinyali değil.</span></div>
<div class="sz"><span>⏱️ Gün içi</span><span>Hisse penceresinde: 15 dk / 1 saat / 4 saat mumlarında trend (20 ve 50 mumluk üssel ortalama), RSI ve son 3 mumda zirve/dip kırılımı. Sadece durum, AL/SAT değil: testte büyük hisselerde sonraki 1-5 gün için anlamlı ipucu vermedi; RSI 30 altı 'ucuz' demek değil.</span></div>
<div class="sz"><span class="uvsb">🌱 UV</span><span>Uzun vade AL: yükselen trendde 50 günlük ortalamaya geri çekilip döndü. Çıkış: 2 gün 200 günlük ortalamanın altı.</span></div>
<div class="sz"><span class="sdb destek">Destekten tepki</span><span>Fiyat eski bir dibe indi ve yukarı dönüyor.</span></div>
<div class="sz"><span class="hacimb">📈 hacim</span><span>Gösterge AL'i günü hacim 20 gün ortalamasının 1,5 katından fazla (bilgi).</span></div>
<div class="sz"><span class="bayrakb">🚩</span><span>Boğa bayrağı kırılımı (bilgi).</span></div>
<div class="sz"><span class="bilb">📅 bilanço</span><span>7 gün içinde bilanço açıklanacak: o gün fiyat sert oynayabilir.</span></div>
<div class="sz"><span class="bilb">💰 temettü</span><span>7 gün içinde temettü hak kullanımı: o sabah fiyat temettü kadar düşük açılır.</span></div>
<div class="sz"><span class="arzb">ARZ</span><span>Son 12 ayın halka arzı.</span></div>
<div class="sz"><span class="yildiz">AL+</span><span>AL+: göstergeler AL ve F/K ile PD/DD grup ortancasının altında (görece ucuz).</span></div>
<div class="sz"><span>✂️</span><span>Hisse penceresinde: bedelsiz/bölünme oldu, fiyatlar düzeltildi; portföydeyse maliyetini güncelle.</span></div>
</div>
<div class="szgrup"><h3>Sütunlar</h3>
<div class="sz"><b>Sinyal</b><span>5 göstergenin oylaması (SuperTrend, MACD, ortalamalar, RSI, Stokastik): AL / NÖTR / SAT. Bilgi amaçlı; AL mesajı 🚀'den gelir. Sarı NÖTR = AL'den döndü, turuncu = SAT'tan döndü.</span></div>
<div class="sz"><b>Sinyalde</b><span>Bu sinyal kaç gündür sürüyor.</span></div>
<div class="sz"><b>Uyum</b><span>5 oylama göstergesinden kaçı AL diyor.</span></div>
<div class="sz"><b>Güç</b><span>7 iyi göstergeden kaçı olumlu (yukarıda).</span></div>
<div class="sz"><b>RS</b><span>Göreli güç puanı 0-99 (yukarıda); 80 ve üstü yeşil.</span></div>
<div class="sz"><b>Vade</b><span><i class="vu">G↑</i> <i class="vu">H↑</i> <i class="va">A↓</i> = günlük / haftalık / aylık trend oku. ↑ fiyat ortalamanın üstünde ve ortalama yükseliyor, ↓ altında ve yükselmiyor, → arada. Günlük: 50 günlük ort.; haftalık: son biten haftanın kapanışı ve 30 haftalık ort.; aylık: son biten ay ve 10 aylık ort. (11 aydan kısa geçmişte —). Bilgi, sinyal değil: geçmişte (2016-2026) üçü de ↓ olanlar sonraki 2-6 ayda çoğunlukla endeksin gerisinde kaldı ama fark küçük; üçü de ↑ olmak tek başına alım sinyali değil.</span></div>
<div class="sz"><b>Stop</b><span>İz stop: AL'den beri tepe kapanışın %20 altı. Kapanış altına inerse çık.__KKCUMLE__</span></div>
<div class="sz"><b>Öneri lot</b><span>Stop yerse portföyünün belirlediğin yüzdesini kaybedeceğin lot.</span></div>
</div>
</div>
<div class="aciklama">
<div class="kart"><h3>📖 Sistemi nasıl kullanırım?</h3><p><b>1.</b> 🚀 AL Telegram'a 17:30'dan sonra gelir: hisse güçlü trendde son 20 günün zirvesini aştı. İstersen o gün kapanışa kadar, istersen sonraki 5 gün içinde alırsın (testte fark küçük). Kapanışta tutmazsa 18:30'dan sonra "↩️ iptal" gelir.<br><b>2.</b> Parayı ~10 eşit parçaya böl; tek hisseye yüklenme.<br><b>3.</b> Aldıktan sonra tek kural <b>📍 iz stop</b>: AL'den beri en yüksek kapanışın %20 altı. Kapanış bunun altına inerse çık. Gün içi sarkma yetmez, kapanış belirler.__KKCUMLE__<br><b>4.</b> Sabah ☀️ mesajında portföyünün seviyeleri, gün içinde 📍 önemli olaylar, akşam 💼 özet gelir.<br><b>5.</b> 🎈 / ⚠️ / 🪤 uyarıları olan hisselerde dikkatli ol; SAT, NÖTR ve destek/direnç bilgi amaçlıdır.</p></div>
<div class="kart"><h3>📈 Grafik nasıl okunur?</h3><p>Hisseye tıklayınca açılan grafikte: <b>siyah çizgi</b> fiyat (son 6 ay). <b>Yeşil / sarı çizgi</b> 20 / 50 günlük ortalama: fiyat ikisinin üstündeyse kısa vadede güçlü. <b>Kırmızı çizgi</b> SuperTrend (gösterge sinyali). <b>Mavi / turuncu kesikli</b> destek / direnç. <b style="color:#1B7F4B">▲ AL</b> Telegram'a gelen 🚀 AL günü, <b style="color:#B4362E">▼ SAT</b> iz stop'la çıkış günü, <b>mor kesikli çizgi</b> o pozisyonun iz stop'u: fiyat yükseldikçe yukarı çıkar, hiç aşağı inmez.__KKGRAFIK__ <b style="color:#D6336C">Pembe ince kesikli</b> çizgi 📏 sıkı çizgi (sadece çok yükselmiş 🚀 pozisyonda; bilgi, kural değil). Grafiğin üstünde son AL/SAT özeti; <b>1 yıl</b> düğmesi daha eski kısmı haftalık gösterir. Altta o hissenin <b>sinyal geçmişi</b> tablosu var. Parmağını/fareni grafikte gezdirince o günün fiyatı ve iz stop'u görünür.</p></div>
<div class="kart"><h3>Piyasa filtresi</h3><p>BIST 100, 50 günlük ortalamasının altındaysa üstte "Piyasa zayıf" uyarısı çıkar. 5 yıllık backtest'te bu dönemlerde gelen AL'ler belirgin şekilde daha kötü sonuç verdi.</p></div>
<div class="kart"><h3>Çıkış ve hedef</h3><p><b>📍 İz stop</b>: AL'den beri görülen en yüksek kapanışın %20 altı; fiyat yükseldikçe yukarı taşınır, kapanış altına inerse "çık".__KKCUMLE__ SAT sinyali tek başına çıkış değildir (gece testleri: SAT'ta çıkmak yükseliş piyasasında kazancı eritiyordu; iz stop 2023'te −%6 yerine +%45). <b>🎯 İzleme</b>: en yakın direnç — geçmişte satış gelen tepe. Hedef satış emri değil, izleme noktasıdır: 5 yıllık backtest'te hedefte kısmi satış, SAT/stop'a kadar tutmaktan belirgin şekilde kötü sonuç verdi.</p></div>
<div class="kart"><h3>NÖTR: sarı mı turuncu mu?</h3><p><span class="pill notr notr-al">NÖTR</span> <b>Sarı = AL'den döndü.</b> Elindeyse tut; iz stop kırılırsa çık. Yeni alım yapma.<br><span class="pill notr notr-sat">NÖTR</span> <b>Turuncu = SAT'tan döndü.</b> Düşüş yavaşladı ama henüz alım sinyali değil; AL'i bekle. (5 yıllık backtest: NÖTR'de satmak ya da turuncuda almak, beklemekten kötü sonuç verdi.)</p></div>
<div class="kart"><h3>Öneri lot (risk yönetimi)</h3><p>Stop yerse portföyünün sadece belirlediğin yüzdeyi (örn. %1) kaybedeceğin lot sayısı: (portföy×risk%)÷(fiyat−stop).</p></div>
<div class="kart"><h3>RSI</h3><p>0–100 momentum. 30 altı aşırı satım, 70 üstü aşırı alım. Sağlıklı yükseliş 45–68 bandında.</p></div>
<div class="kart"><h3>MACD</h3><p>İki ortalamanın farkı. MACD sinyali yukarı keserse momentum boğaya döndü — klasik al tetiği.</p></div>
<div class="kart"><h3>F/K</h3><p>Fiyat ÷ yıllık kâr. Mutlak eşik yok; ▼ grup medyanının altında (görece ucuz). Enflasyonda yanıltıcı olabilir, tek başına karar değil.</p></div>
<div class="kart"><h3>PD/DD</h3><p>Borsa değeri ÷ defter değeri. 1 = defter değerine eşit. ▼ görece ucuz.</p></div>
<div class="kart"><h3>FD/FAVÖK</h3><p>Şirketin toplam değeri (FD) ÷ FAVÖK. Şirketin faaliyet kârına göre kaç kat pahalı/ucuz fiyatlandığını gösterir. Düşükse görece ucuz.</p></div>
<div class="kart"><h3>Destek / Direnç</h3><p>Son 120 günün dip ve tepe noktaları. <b>Destekten tepki</b>: fiyat eski bir dibe indi ve yukarı dönüyor. <b>Dirence yaklaşıyor</b>: fiyat geçmişte satış gelen bir tepeye yakın, temkinli ol. Hisseye tıklayınca seviyeleri görürsün.</p></div>
</div>
<div class="uyari">Yatırım tavsiyesi değildir. Göstergeler geçmişe bakar, geleceği garanti etmez; bu araç yalnızca sistemli karar vermeye yardımcı olur. Veriler ~15 dk gecikmeli olabilir. Kararların sorumluluğu sana aittir.</div>
__KOTUGUN__
<div class="durust"><b>Dürüst olalım:</b> __DURUST__</div>
</div>

<div class="ust" id="ust" onclick="if(event.target===this)kapat()"><div class="modal" id="modal"></div></div>
<div class="ust" id="dfust" onclick="if(event.target===this)dfFormKapat()"><div class="modal" id="dfmodal" role="dialog" aria-label="İşlem defteri kaydı"></div></div>
<script>
const DATA=__DATA__;
const XU=__XU__;
const PIYASA=__PIYASA__;  // BIST 100: son 2 yıl günlük, öncesi haftalık — portföy-endeks kıyası
const GI=__GI__;
const GEN=__GEN__;  // 🌡️ piyasa genişliği, son 60 işlem günü (tarama.piyasa_genisligi): t, s50/s200 (% üstünde), z/d (52h zirve/dip sayısı), n
const KGK=__KGK__;  // 📉 canlı karne ↔ 'normal kötü günler' kıyası (pano.kotu_gun_kiyas)
const KS=__KS__;  // 💵 altın / dolar / mevduat günlük endeksi + aylık TÜFE (pano.birikim_serisi; İşlem Odası birikim robotları), yoksa null
const MN_NOT=__MNNOT__;  // ⚠️ manipülasyon rozeti açıklaması (pano.MN_NOT)
const KK=__KK__;  // 🔐 kâr kilidi [eşik %, seviye %] (sinyal.KAR_KILIT_*), kural kapalıysa null — çizgi değerleri Python'dan hazır gelir
const t=document.getElementById('t');
[...t.tBodies[0].rows].forEach(function(r){var c=r.querySelector('td.vd');if(c)c.innerHTML=vdHucre((DATA[r.dataset.kod]||{}).vd);});
t.querySelectorAll('th').forEach((th,i)=>{th.addEventListener('click',()=>{
if(th.dataset.t==='f'){t._sirali=false;tabloDuzen();return;}
const tb=t.tBodies[0],rows=[...tb.rows],num=th.dataset.t==='n',asc=th._asc=!th._asc;
if(th.dataset.t==='v'){rows.sort((a,b)=>asc?vdSkor(a)-vdSkor(b):vdSkor(b)-vdSkor(a));t._sirali=true;rows.forEach(r=>tb.appendChild(r));tabloDuzen();return;}
rows.sort((a,b)=>{let x=a.cells[i].innerText.replace('%','').replace('+',''),y=b.cells[i].innerText.replace('%','').replace('+','');
if(num){x=parseFloat(x)||-1e9;y=parseFloat(y)||-1e9;return asc?x-y:y-x;}return asc?x.localeCompare(y,'tr'):y.localeCompare(x,'tr');});
t._sirali=true;rows.forEach(r=>tb.appendChild(r));tabloDuzen();});});


// --- ⭐ Favoriler: cihazda + GitHub'daki FAVORILER variable'ında (portföyle aynı anahtar). Favoriler tabloda en üstte,
// kendi içinde sunucunun sırasıyla (AL → NÖTR → SAT); sütuna göre sıralayınca da üstte kalır.
var FAV_KEY='favoriler_v1';
function favOku(){try{return JSON.parse(localStorage.getItem(FAV_KEY))||[]}catch(e){return[]}}
function favYaz(a){try{localStorage.setItem(FAV_KEY,JSON.stringify(a))}catch(e){}
 if(!ghAnahtar())return;
 var v={name:'FAVORILER',value:JSON.stringify(a)};
 ghIstek('PATCH','/actions/variables/FAVORILER',v).then(function(r){return r.status===404?ghIstek('POST','/actions/variables',v):r;}).catch(function(){});
}
function favBulutOku(){
 if(!ghAnahtar())return;
 ghIstek('GET','/actions/variables/FAVORILER').then(function(r){
  if(r.status===404){if(favOku().length)favYaz(favOku());return;}
  if(!r.ok)return;
  return r.json().then(function(j){var a=[];try{a=JSON.parse(j.value);}catch(e){}
   if(Array.isArray(a)&&a.length){try{localStorage.setItem(FAV_KEY,JSON.stringify(a))}catch(e){}tabloDuzen();}});
 }).catch(function(){});
}
function favDegis(k){var a=favOku(),i=a.indexOf(k);if(i>=0)a.splice(i,1);else a.push(k);favYaz(a);tabloDuzen();bugunRender();
 var d=document.getElementById('mfav');if(d)d.textContent=a.indexOf(k)>=0?'⭐ Favorilerde':'☆ Favorilere ekle';}
var _SIRA=null;  // sunucunun ilk sırası (AL → NÖTR → SAT)
function tabloDuzen(){
 var tb=t.tBodies[0],rows=[...tb.rows],fav=favOku();
 if(!_SIRA){_SIRA={};rows.forEach(function(r,i){_SIRA[r.dataset.kod]=i;});}
 var q=(document.getElementById('ara').value||'').trim().toLocaleUpperCase('tr'),sf=document.getElementById('sadecefav').checked;
 rows.forEach(function(r){var k=r.dataset.kod,f=fav.indexOf(k)>=0;r.classList.toggle('favrow',f);
  var b=r.querySelector('.fav');if(b){b.textContent=f?'⭐':'☆';b.title=f?'Favorilerden çıkar':'Favorilere ekle';}
  r.hidden=(q&&k.indexOf(q)<0)||(sf&&!f);});
 if(!t._sirali)rows.sort(function(a,b){return _SIRA[a.dataset.kod]-_SIRA[b.dataset.kod];});
 var f1=rows.filter(function(r){return fav.indexOf(r.dataset.kod)>=0;}),f2=rows.filter(function(r){return fav.indexOf(r.dataset.kod)<0;});
 f1.concat(f2).forEach(function(r){tb.appendChild(r);});
 var n=document.getElementById('favsay');if(n)n.textContent=fav.length?'('+fav.length+')':'';
 var rs=document.getElementById('roket'),N=rs?+rs.value:0,rk=document.getElementById('roketkutu'),ts=document.getElementById('tsar');
 if(rk&&ts){rk.hidden=!N;ts.hidden=!!N;rk.innerHTML=N?roketHtml(N,q,sf,fav):'';}
}

// --- 📋 Bugün ne var? — tek bakışta: piyasa, yeni 🚀 AL'ler, portföy ve favori uyarıları (hepsi cihazda hesaplanır)
function _kl(k){return '<a href="#" class="bgk" onclick="ac(\''+k+'\');return false">'+k+'</a>';}
// ⚠️ Manipülasyon işaretleri (d.mn = {i:[[tür,tarih,değer],...], n}; Python pano.manip_isaret ile aynı metin)
function mnTarih(t){return t.slice(8,10)+'.'+t.slice(5,7)+'.'+t.slice(0,4);}
function mnIsaret(x){var k=x[0],t=mnTarih(x[1]),v=x[2];
 if(k==='tv')return v+' gün art arda tavan ('+t+')';
 if(k==='x3')return '60 günde '+String(v).replace('.',',')+' kat yükseliş ('+t+')';
 if(k==='ts')return 'hisseye özel taban serisi: 15 günde '+v+' taban ('+t+')';
 if(k==='vb')return 'Borsa İstanbul VBTS (volatilite bazlı tedbir) kararı ('+t+')';
 return 'SPK tedbir kararı ('+t+')';}
function mnMetin(mn){return mn?'⚠️ <b>Manipülasyon işareti</b> (5 işaretten '+mn.n+' tanesi var): '+mn.i.map(mnIsaret).join('; ')+'. <b>Kilitli tabanda satamama riski yüksek; alım yasağı değil.</b> '+MN_NOT:'';}
function bugunUyari(k,d,p){  // bir hisse için dikkat notları
 var u=[];if(!d)return u;
 if(d.kt)u.push('🔒 kilitli taban');   // en üstte: satış emri gerçekleşmeyebilir / çöküş
 if(d.patlak)u.push('⚠ taban serisi');
 if(p&&d.iz&&d.iz.cikti&&!p.uzun)u.push('📉 iz stop kırıldı');
 else if(p&&!p.uzun){var pl=pozPlan(d,p);if(pl.stop&&!pl.asildi&&pl.stopUzak>-3)u.push('iz stop\'a %'+Math.abs(pl.stopUzak).toFixed(1)+' kaldı');}
 if(p&&p.uzun){var pu=pozPlan(d,p);if(pu.karar&&!pu.kararAsildi&&pu.kararUzak>-3)u.push('🧭 karar çizgisine %'+Math.abs(pu.kararUzak).toFixed(1)+' kaldı');}
 if(p&&d.sd&&d.sd.destek&&d.fiyat&&d.sd.destek.fiyat/d.fiyat-1>-0.02)u.push('👉 desteğe %'+Math.abs((d.sd.destek.fiyat/d.fiyat-1)*100).toFixed(1)+' ('+d.sd.destek.fiyat+')');
 if(p&&d.tk&&d.tk.durum==='AL'&&scAlt(d.tk.sc).length)u.push('📏 sıkı çizginin altında kapandı ('+scAlt(d.tk.sc).map(gunAy).join(', ')+')');
 if(p&&d.trend_asagi)u.push('📉 trend aşağı');
 if(d.tahta&&d.tahta.seviye==='sisme')u.push(thDalga(d.tahta)?'🎈 sert dalgalanma':'🎈 şişme');
 if(d.tahta&&d.tahta.seviye==='dagitim')u.push('⚠️ dağıtım');
 if(d.tuzak)u.push('🪤 tuzak riski');
 if(d.mn)u.push('⚠️ manipülasyon işareti ('+d.mn.n+'/5)');
 if(p&&d.od)u.push('🔻 hisseye özel düşüş ('+d.od.u+' gün)');
 if(d.bilanco&&d.bilanco.kalan_gun!=null&&d.bilanco.kalan_gun>=0&&d.bilanco.kalan_gun<=7)u.push('📅 bilanço '+d.bilanco.kalan_gun+' gün sonra');
 if(d.temettu&&d.temettu.ex_kalan!=null&&d.temettu.ex_kalan<=7)u.push('💰 temettü '+d.temettu.ex_kalan+' gün sonra');
 if(d.bolunme&&(Date.now()-new Date(d.bolunme).getTime())<30*864e5)u.push('✂️ bölünme ('+d.bolunme+'): maliyetini güncelle');
 return u;
}
// 🌡️ Piyasa genişliği (GEN, tarama.piyasa_genisligi) — 'Bugün ne var?' kartında PIYASA satırının altında. Bilgi.
function genCizgi(){
 var W=150,H=34,n=GEN.t.length;if(n<2)return '';
 function yol(a,renk){var p=[];a.forEach(function(v,i){if(v==null)return;p.push((i/(n-1)*W).toFixed(1)+','+(H-2-v/100*(H-4)).toFixed(1));});
  return p.length>1?'<polyline fill="none" stroke="'+renk+'" stroke-width="1.6" points="'+p.join(' ')+'"/>':'';}
 return '<svg class="gencz" viewBox="0 0 '+W+' '+H+'" width="'+W+'" height="'+H+'" role="img" aria-label="Son '+n+' işlem günü"><title>Son '+n+' işlem günü ('+trTarih(GEN.t[0])+' – '+trTarih(GEN.t[n-1])+'): koyu çizgi 50 günlük, açık çizgi 200 günlük ortalamanın üstündeki hisse oranı (alt kenar %0, üst %100)</title>'+
  '<line x1="0" x2="'+W+'" y1="'+(H/2)+'" y2="'+(H/2)+'" stroke="#E6E7E4" stroke-dasharray="3 3"/>'+yol(GEN.s200,'#9AA0A8')+yol(GEN.s50,'#0E4D45')+'</svg>';
}
function genHtml(){
 if(!GEN||!GEN.t||!GEN.t.length)return '';
 var i=GEN.t.length-1,f=function(x){return x==null?'—':'%'+Math.round(x);};
 var a=GEN.s50[i],b=GEN.s200[i],a0=GEN.s50[Math.max(0,i-20)];
 var yon=(a!=null&&a0!=null)?(a-a0>=10?' (20 günde arttı)':(a-a0<=-10?' (20 günde azaldı)':'')):'';
 return '<div class="bgs genb"><span>🌡️ <b>Piyasa genişliği</b> ('+GEN.n[i]+' hisse): 50 günlük ortalamasının üstünde <b>'+f(a)+'</b>'+yon+', 200 günlüğün üstünde <b>'+f(b)+'</b> · 52 haftanın zirvesinde <b>'+GEN.z[i]+'</b>, dibinde <b>'+GEN.d[i]+'</b> hisse'+
  '<span class="sgun"> — bilgi: geçmiş testte AL\'e filtre olarak katkı vermedi.</span></span>'+genCizgi()+'</div>';
}
// 🧮 Kaç lot? (hisse penceresi) — sermaye + risk yüzdesi bu cihazda (localStorage) hatırlanır; hiçbir yere gönderilmez.
var LOT_KEY='lot_ayar_v1';
function lotAyar(){try{return JSON.parse(localStorage.getItem(LOT_KEY))||{}}catch(e){return {}}}
function lotStop(k,d,giris){  // stop kaynağı: portföydeyse portföyün iz stop'u, açık 🚀 pozisyonda onun iz stop'u (🔐 dahil), değilse girişin %20 altı
 var p=pfOku().filter(function(x){return x.kod===k;})[0];
 if(p&&!p.uzun&&d.fiyat!=null){var pl=pozPlan(d,p);if(pl.stop&&!pl.izCikti)return {s:pl.stop,ne:'portföyündeki iz stop'+(pl.kilit?' 🔐':'')};}
 var t=d.tk;if(t&&t.durum==='AL'&&t.stop)return {s:t.stop,ne:'açık 🚀 pozisyonun iz stop\'u'+(t.kilit?' (🔐 kâr kilidi dahil)':'')};
 return {s:Math.round(giris*0.8*100)/100,ne:'yeni 🚀 girişinde başlangıç iz stop\'u: girişin %20 altı'};
}
function lotHtml(k,d){
 if(d.fiyat==null)return '';
 var a=lotAyar(),r=a.r||1;
 var sec=[0.5,1,1.5,2].map(function(x){return '<option value="'+x+'"'+(x==r?' selected':'')+'>%'+String(x).replace('.',',')+'</option>';}).join('');
 return '<div class="lotkutu"><div class="gbas">🧮 Kaç lot?</div>'+
  '<div class="pfform lotform" style="display:flex"><label>Sermayen (TL)<input id="lotsermaye" type="number" min="0" step="any" placeholder="örn. 100000" value="'+(a.s||'')+'" oninput="lotHesap(\''+k+'\')"></label>'+
  '<label title="Stop olursa sermayenin en çok yüzde kaçını kaybetmeye razısın? Genelde %1-2 önerilir">İşlem başına risk<select id="lotrisk" onchange="lotHesap(\''+k+'\')">'+sec+'</select></label>'+
  '<label>Giriş fiyatı<input id="lotgiris" type="number" min="0" step="any" value="'+d.fiyat+'" oninput="lotHesap(\''+k+'\')"></label></div>'+
  '<div id="lotsonuc" class="lotsonuc"></div></div>';
}
function lotHesap(k){
 var d=DATA[k],el=document.getElementById('lotsonuc');if(!d||!el)return;
 var S=parseFloat(document.getElementById('lotsermaye').value),r=parseFloat(document.getElementById('lotrisk').value)||1,g=parseFloat(document.getElementById('lotgiris').value);
 try{localStorage.setItem(LOT_KEY,JSON.stringify({s:S>0?S:null,r:r}));}catch(e){}
 if(!(S>0)||!(g>0)){el.innerHTML='<span class="sgun">Sermayeni yaz: kaç lot alacağını ve stop olursa ne kadar kaybedeceğini hesaplayayım (sadece bu cihazda saklanır).</span>';return;}
 var st=lotStop(k,d,g),per=g-st.s,kom=0.004,tl=function(x){return Math.round(x).toLocaleString('tr-TR')+' TL';},yz=function(x){return '%'+x.toFixed(1).replace('.',',');};
 var h='<div class="pk">📍 Stop: <b>'+st.s+' TL</b> ('+st.ne+')'+(per>0?', girişin '+yz(per/g*100)+' altında.':'.')+'</div>';
 if(per<=0){el.innerHTML=h+'<div class="pk neg">Stop giriş fiyatının üstünde ya da eşit (fiyat stop\'un altına inmiş olabilir): risk hesabı yapılamaz. Kurala göre bu fiyattan yeni alım yapılmaz.</div>';return;}
 var riskTl=S*r/100,birim=per+g*kom,lr=Math.floor(riskTl/birim),cap=Math.floor(S/(g*1.002)),lot=Math.min(lr,cap);
 if(lot>0){var tut=lot*g,ky=lot*birim;
  h+='<div class="pk">🎯 <b>Risk yöntemi (%'+String(r).replace('.',',')+')</b>: <b>'+lot+' lot</b> ≈ '+tl(tut)+' (sermayenin '+yz(tut/S*100)+'). Stop olursa kayıp ≈ <b class="neg">'+tl(ky)+'</b> (sermayenin '+yz(ky/S*100)+', komisyon dahil).'+
   (lr>cap?' <span class="sgun">Risk sınırı daha fazlasına izin veriyor ama sermaye bu kadarına yetiyor.</span>':'')+
   (tut>S*0.25?' <span class="pfuy">Tek hisseye sermayenin %25\'inden fazlası gidiyor: stop yakın olduğu için lot büyüdü; çeşitlilik azalır.</span>':'')+'</div>';}
 else h+='<div class="pk">🎯 Risk yöntemi: bu sermaye ve riskle 1 lot bile alınamıyor (1 lotun stop riski '+tl(birim)+').</div>';
 var l10=Math.floor(S/10/(g*1.002));
 h+=l10>0?'<div class="pk">🧩 <b>10 eşit yuva</b> (sistemin kuralı: parayı 10 eşit parçaya böl): <b>'+l10+' lot</b> ≈ '+tl(l10*g)+'. Stop olursa kayıp ≈ <b class="neg">'+tl(l10*birim)+'</b> (sermayenin '+yz(l10*birim/S*100)+').</div>'
  :'<div class="pk">🧩 10 eşit yuva: sermayenin 1/10\'u bu hisseden 1 lota yetmiyor.</div>';
 h+='<div class="pk sgun">Fiyat ~15 dk gecikmeli; gerçek giriş fiyatı farklı olur. Komisyon/kayma her yönde ~%0,2 varsayıldı. Tabanda kilitlenme ya da boşluklu açılışta kayıp stop\'tan büyük olabilir. Bilgi, yatırım tavsiyesi değil.</div>';
 el.innerHTML=h;
}
// 🔗 Portföy korelasyonu (istemci): son 120 işlem gününün günlük getirileri (grafik verisi DATA[k].spark, iki hissenin ortak günleri)
function _getiri(k){var sp=(DATA[k]||{}).spark;if(!sp||!sp.c||!sp.t)return null;var m={};for(var i=1;i<sp.c.length;i++)if(sp.c[i]!=null&&sp.c[i-1])m[sp.t[i]]=sp.c[i]/sp.c[i-1]-1;return m;}
function korelasyon(x,y,gun){
 var t=Object.keys(x).filter(function(k){return k in y;}).sort().slice(-(gun||120));if(t.length<40)return null;
 var n=t.length,ma=0,mb=0;t.forEach(function(k){ma+=x[k];mb+=y[k];});ma/=n;mb/=n;
 var sab=0,sa=0,sb=0;t.forEach(function(k){var a=x[k]-ma,b=y[k]-mb;sab+=a*b;sa+=a*a;sb+=b*b;});
 return (sa>0&&sb>0)?{r:sab/Math.sqrt(sa*sb),n:n}:null;
}
function pfKorelasyon(a){
 var kod=[],w={},top=0;a.forEach(function(p){var d=DATA[p.kod];if(!d||d.fiyat==null)return;if(!(p.kod in w)){kod.push(p.kod);w[p.kod]=0;}w[p.kod]+=p.adet*d.fiyat;top+=p.adet*d.fiyat;});
 if(kod.length<2||!top)return null;
 var g={};kod.forEach(function(k){g[k]=_getiri(k);});
 var cift=[],tam=true,s=0;
 for(var i=0;i<kod.length;i++){s+=Math.pow(w[kod[i]]/top,2);for(var j=i+1;j<kod.length;j++){
  var c=(g[kod[i]]&&g[kod[j]])?korelasyon(g[kod[i]],g[kod[j]],120):null;
  if(!c){tam=false;continue;}
  cift.push({a:kod[i],b:kod[j],r:c.r,n:c.n,sek:!!(DATA[kod[i]].endustri&&DATA[kod[i]].endustri===DATA[kod[j]].endustri)});
  s+=2*w[kod[i]]/top*w[kod[j]]/top*c.r;}}
 cift.sort(function(x,y){return y.r-x.r;});
 return {n:kod.length,cift:cift,yuksek:cift.filter(function(c){return c.r>=0.7;}),etkin:(tam&&s>0)?1/s:null};
}
function korHtml(a,dag){
 var k=pfKorelasyon(a);if(!k)return '';
 if(!k.cift.length)return '<div class="pfkiyas sgun">🔗 Hisselerin birbirine benzerliği için yeterli ortak fiyat geçmişi yok.</div>';
 var r2=function(x){return x.toFixed(2).replace('.',',');};
 var et=k.etkin!=null?' Değer ağırlıklarıyla portföy fiyat hareketinde <b>~'+k.etkin.toFixed(1).replace('.',',')+' bağımsız hisse</b> gibi ('+k.n+' hisse var).':'';
 if(!k.yuksek.length)return '<div class="pfkiyas">🔗 <b>Birlikte hareket</b>: son ~6 ayda hiçbir hisse çifti güçlü benzer değil (en yüksek '+k.cift[0].a+'–'+k.cift[0].b+' '+r2(k.cift[0].r)+'; güçlü = 0,70+) ✅.'+et+'<span class="pfxu">Korelasyon: son 120 işlem gününün günlük getirileri (−1 ters, 0 ilgisiz, +1 aynı). Bilgi, kural değil.</span></div>';
 var ayni=k.yuksek.filter(function(c){return c.sek;}).length,ustSek=a.length>=2&&dag&&dag.length&&dag[0][1]>40;
 return '<div class="pfkiyas uyar">🔗 <b>Birlikte hareket uyarısı</b>: '+k.yuksek.slice(0,4).map(function(c){return '<b>'+c.a+'–'+c.b+'</b> '+r2(c.r)+(c.sek?' (aynı sektör)':'');}).join(' · ')+(k.yuksek.length>4?' · +'+(k.yuksek.length-4)+' çift':'')+
  '. Bu hisseler son ~6 ayda çoğu gün aynı yöne gitti: kötü günde birlikte düşerler.'+et+
  (ustSek?' Sektör yoğunlaşmasıyla birlikte riskin büyük kısmı tek kaynağa toplanmış.':(ayni<k.yuksek.length?' Farklı sektörde olsalar da aynı etkene (faiz, kur, endeks) bağlı olabilirler.':''))+
  '<span class="pfxu">Korelasyon: son 120 işlem gününün günlük getirileri (0,70+ güçlü benzerlik). Geçmiş benzerlik değişebilir; bilgi, kural değil.</span></div>';
}
// 💵 Portföy vs altın / dolar / mevduat / TÜFE (KS = İşlem Odası birikim robotlarının günlük değeri; alış tarihi `tarih` olan pozisyonlar)
function ksIdx(t){if(!KS||!t||t<KS.t[0])return -1;var lo=0,hi=KS.t.length-1,i=-1;while(lo<=hi){var m=(lo+hi)>>1;if(KS.t[m]<=t){i=m;lo=m+1;}else hi=m-1;}return i;}
function tufeKumPf(tf,bas,son){if(!tf||!bas||!son)return null;var a=bas.slice(0,7),b=son.slice(0,7),c=1,ay=[];
 Object.keys(tf).sort().forEach(function(k){if(k>=a&&k<=b){c*=1+tf[k]/100;ay.push(k);}});
 return ay.length?{o:(c-1)*100,a:ay[0],b:ay[ay.length-1]}:null;}
function pfBirikim(a){
 if(!KS)return {yok:true};
 var son=KS.t.length-1,bugun=new Date().toISOString().slice(0,10),mal=0,deg=0,al=0,us=0,mv=0,tu=0,n=0,eski=0,tarihsiz=0,tum=true,tuAy=null;
 a.forEach(function(p){var d=DATA[p.kod];if(!d||d.fiyat==null)return;
  if(!p.tarih){tarihsiz++;return;}var i=ksIdx(p.tarih);if(i<0){eski++;return;}
  var m=p.adet*p.maliyet,t=tufeKumPf(KS.tf,p.tarih,bugun);n++;mal+=m;deg+=p.adet*d.fiyat;
  al+=m*KS.a[son]/KS.a[i];us+=m*KS.u[son]/KS.u[i];mv+=m*KS.m[son]/KS.m[i];
  if(t){tu+=m*(1+t.o/100);if(!tuAy||t.b<tuAy)tuAy=t.b;}else{tu+=m;tum=false;}});
 if(!n)return {yok:false,n:0,tarihsiz:tarihsiz,eski:eski};
 var y=function(v){return (v/mal-1)*100;};
 return {n:n,tarihsiz:tarihsiz,eski:eski,pf:y(deg),al:y(al),us:y(us),mv:y(mv),tu:y(tu),reel:(deg/tu-1)*100,veri:KS.t[son],tuAy:tuAy,tufeTam:tum};
}
function ayYil(k){return AYLAR[+k.slice(5,7)-1]+' '+k.slice(0,4);}
function trTarihY(s){var p=s.split('-');return (+p[2])+' '+AYLAR[+p[1]-1]+' '+p[0];}
function birikimHtml(a){
 var b=pfBirikim(a);if(b.yok)return '';
 var x=[];if(b.tarihsiz)x.push(b.tarihsiz+' hissede alış tarihi yok');if(b.eski)x.push(b.eski+' hissenin alış tarihi '+trTarihY(KS.t[0])+' öncesi (veri yok)');var notu=x.join(', ');
 if(!b.n)return '<div class="pfkiyas sgun">💵 <b>Enflasyon / altın / dolar / mevduat kıyası</b> için hisseyi düzenle (✎) ve <b>alış tarihini</b> gir'+(b.eski?' ('+notu+')':'')+' — aynı paranın o günden beri altında, dolarda ve mevduatta ne olacağını gösteririm.</div>';
 var c=function(v){return '<b class="'+(v>=0?'pos':'neg')+'">'+pyz(v)+'</b>';};
 var en=[['altın',b.al],['dolar',b.us],['mevduat',b.mv]].sort(function(p,q){return q[1]-p[1];})[0];
 return '<div class="pfkiyas">💵 <b>Paran ne kazandı?</b>'+(b.n<a.length?' (alış tarihi girilen '+b.n+'/'+a.length+' hisse)':'')+': portföy '+c(b.pf)+' · aynı parayla aynı günlerde 🥇 gram altın '+c(b.al)+' · 💵 dolar '+c(b.us)+' · 🏦 mevduat '+c(b.mv)+' · 🧾 TÜFE '+c(b.tu)+'.'+
  ' Enflasyondan arındırılmış (reel) portföy getirisi '+c(b.reel)+' → alım gücün <b>'+(b.reel>=0?'korundu':'azaldı')+'</b>'+(b.pf>=en[1]?'; üç birikim seçeneğinden de iyi.':'; en iyisi '+en[0]+' olurdu.')+
  '<span class="pfxu">Altın, dolar ve mevduat İşlem Odası\'nın 💰 birikim robotlarından (gram altın, USD/TRY, TCMB politika faiziyle 32 günlük mevduat, stopaj sonrası; gerçek banka faizi farklı olabilir; alım-satım makası yok sayıldı; veri '+trTarihY(b.veri)+'). TÜFE alış ayından '+(b.tuAy?'son açıklanan aya ('+ayYil(b.tuAy)+')':'bugüne')+' kadar (alış ayı tam sayılır)'+(b.tufeTam?'':'; bazı alışlar için henüz açıklanan ay yok')+'. Temettü dahil değil.'+(notu?' Kıyas dışı: '+notu+'.':'')+'</span></div>';
}
function bugunRender(){
 var el=document.getElementById('bugun');if(!el)return;
 var h='<h2>📋 Bugün ne var?</h2>';
 if(PIYASA)h+='<div class="bgs">'+(PIYASA.zayif?'⚠️ <b>Piyasa zayıf</b>: BIST 100 50 günlük ortalamasının %'+Math.abs(PIYASA.fark)+' altında. Bu dönemde 🚀 AL gelmez (kural gereği); acele alım yapma.':'✅ <b>Piyasa normal</b>: BIST 100 50 günlük ortalamasının üstünde; 🚀 AL sinyalleri gelebilir.')+'</div>';
 var al=Object.keys(DATA).filter(function(k){var t=DATA[k].tk;return t&&(t.bugun||(t.durum==='AL'&&t.gun<=5));})
  .sort(function(a,b){return DATA[a].tk.gun-DATA[b].tk.gun;});
 h+=genHtml();
 if(KGK&&KGK.durum==='alt')h+='<div class="bgs">📉 <b>Canlı karne normal aralığın dışında</b> (kötü tarafta): son '+KGK.n+' kapanan 🚀 işlemin ortalaması '+pyz(KGK.ort)+', en uzun art arda zarar '+KGK.seri+'. <a href="#kotugun" class="glink">→ sistemin normal kötü günleri</a></div>';
 h+='<div class="bgs">🚀 <b>Yeni AL</b> (son 5 gün): '+(al.length?al.map(function(k){var t=DATA[k].tk;return _kl(k)+(t.bugun?' <span class="tkb yeni">bugün</span>':' <span class="sgun">'+t.gun+'g önce</span>');}).join(' · '):'yok')+' <a href="#" class="glink" onclick="roketAc(20);return false">→ son 20 günün tüm 🚀 sinyalleri</a></div>';
 var pf=pfOku(),ps=[];
 pf.forEach(function(p){var u=bugunUyari(p.kod,DATA[p.kod],p);if(u.length)ps.push(_kl(p.kod)+': '+u.join(', '));});
 h+='<div class="bgs">💼 <b>Portföyün</b>: '+(pf.length?(ps.length?ps.join(' · '):'dikkat gerektiren bir şey yok ✅'):'<span class="sgun">henüz hisse eklemedin</span>')+'</div>';
 var fv=favOku().filter(function(k){return !pf.some(function(p){return p.kod===k;});}),fs=[];
 fv.forEach(function(k){var d=DATA[k];if(!d)return;var u=bugunUyari(k,d,null);var t=d.tk;
  if(t&&(t.bugun||(t.durum==='AL'&&t.gun<=5)))u.unshift('🚀 AL');
  if(t&&t.durum!=='AL'&&t.sablon&&t.kirilima_uzak!=null&&t.kirilima_uzak>0&&t.kirilima_uzak<=3)u.push('👀 kırılıma %'+t.kirilima_uzak);
  if(u.length)fs.push(_kl(k)+': '+u.join(', '));});
 if(favOku().length)h+='<div class="bgs">⭐ <b>Favorilerin</b>: '+(fs.length?fs.join(' · '):'önemli bir değişiklik yok')+'</div>';
 el.innerHTML=h;
}
function sinyalCls(d){if(d.sinyal==='AL')return 'al';if(d.sinyal==='SAT')return 'sat';
 return 'notr'+(d.notr_kaynak==='AL'?' notr-al':d.notr_kaynak==='SAT'?' notr-sat':'');}
// Büyük grafik: fiyat/tarih eksenleri, ▲ AL (🚀 v3) ve ▼ SAT (iz stop) işaretleri, iz stop çizgisi, destek/direnç, fare/dokunma ile değer.
// '6 ay' görünümü günlük (gün sırasına göre); '1 yıl' görünümünde grafik penceresinden önceki ~6 ay haftalık kapanış (sp.w) ve
// x ekseni tarihe göre (haftalık ve günlük kısım aynı ölçekte).
var GR={W:600,H:260,L:6,R:54,T:10,B:24},_gr=null,_PX=null,_grAralik='6a';
var AYLAR=['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara'];
function trTarih(s){var p=s.split('-');return (+p[2])+' '+AYLAR[+p[1]-1];}
function grX(i,n){return _PX?_PX[i]:GR.L+(n>1?i/(n-1):0)*(GR.W-GR.L-GR.R);}
function grY(v,mn,mx){return GR.T+(1-(v-mn)/(mx-mn||1))*(GR.H-GR.T-GR.B);}
function cizgi(vals,color,mn,mx,w){
 var pts=[],n=vals.length;
 for(var i=0;i<n;i++){if(vals[i]==null)continue;pts.push(grX(i,n).toFixed(1)+','+grY(vals[i],mn,mx).toFixed(1));}
 return '<polyline fill="none" stroke="'+color+'" stroke-width="'+w+'" points="'+pts.join(' ')+'"/>';
}
function cizgiParca(vals,color,mn,mx,w,dash){  // boşluklarda (null) kopan çizgi: her pozisyon ayrı parça
 var g='',pts=[],n=vals.length;
 for(var i=0;i<=n;i++){if(i<n&&vals[i]!=null){pts.push(grX(i,n).toFixed(1)+','+grY(vals[i],mn,mx).toFixed(1));continue;}
  if(pts.length>1)g+='<polyline fill="none" stroke="'+color+'" stroke-width="'+w+'"'+(dash?' stroke-dasharray="'+dash+'"':'')+' points="'+pts.join(' ')+'"/>';pts=[];}
 return g;
}
function yatay(v,color,mn,mx,ad){
 var y=grY(v,mn,mx).toFixed(1);
 return '<line x1="'+GR.L+'" x2="'+(GR.W-GR.R)+'" y1="'+y+'" y2="'+y+'" stroke="'+color+'" stroke-width="1.2" stroke-dasharray="5 4"/>'+
  '<text x="'+(GR.W-GR.R+4)+'" y="'+(+y+3.5)+'" font-size="10" fill="'+color+'" font-weight="600">'+v+'</text>';
}
function adimlar(mn,mx){  // okunur eksen değerleri
 var aralik=(mx-mn)/4,us=Math.pow(10,Math.floor(Math.log10(aralik||1))),k=[1,2,2.5,5,10].find(function(x){return x*us>=aralik;})*us;
 var v=[],b=Math.ceil(mn/k)*k;for(var x=b;x<=mx+1e-9;x+=k)v.push(Math.round(x*100)/100);return v;
}
function grGun(s,k){return new Date(Date.parse(s+'T00:00:00Z')+k*864e5).toISOString().slice(0,10);}
function grIsaret(tur,x,y,baslik,kk){  // ▲ AL (yeşil, fiyatın altında) / ▼ SAT (kırmızı, üstünde); grafik kenarına taşarsa ters tarafa
 var alt=GR.H-GR.B,ust=GR.T,g='<g><title>'+baslik+'</title>';
 if(tur==='G'){var a=y+29>alt;var d=a?-1:1,y0=y+6*d,y1=y+14*d;
  g+='<path d="M'+x.toFixed(1)+' '+y0.toFixed(1)+'L'+(x-5).toFixed(1)+' '+y1.toFixed(1)+'L'+(x+5).toFixed(1)+' '+y1.toFixed(1)+'Z" fill="#1B7F4B"/>'+
   '<text x="'+x.toFixed(1)+'" y="'+(a?y-17:y+24).toFixed(1)+'" font-size="9" font-weight="700" fill="#1B7F4B" text-anchor="middle" stroke="#fff" stroke-width="2.5" paint-order="stroke">AL</text>';}
 else{var b=y-26<ust;var e=b?-1:1,z0=y-6*e,z1=y-14*e;
  g+='<path d="M'+x.toFixed(1)+' '+z0.toFixed(1)+'L'+(x-5).toFixed(1)+' '+z1.toFixed(1)+'L'+(x+5).toFixed(1)+' '+z1.toFixed(1)+'Z" fill="#B4362E"/>'+
   '<text x="'+x.toFixed(1)+'" y="'+(b?y+24:y-17).toFixed(1)+'" font-size="9" font-weight="700" fill="#B4362E" text-anchor="middle" stroke="#fff" stroke-width="2.5" paint-order="stroke">SAT'+(kk?' 🔐':'')+'</text>';}
 return g+'</g>';
}
function grafik(sp,sd,ar,tkg){
 if(!sp||!sp.c) return '<div style="color:#6B7079;font-size:13px">Grafik verisi yok.</div>';
 var ds=sd&&sd.destek?sd.destek.fiyat:null,dr=sd&&sd.direnc?sd.direnc.fiyat:null;
 if(sp.sc&&!sp.scg){sp.scg=new Array(sp.c.length).fill(null);sp.sc[1].forEach(function(v,k){sp.scg[sp.sc[0]+k]=v;});}  // 📏 sıkı çizgi parçası → gün dizisi
 if(sp.iz&&!sp.izg){sp.izg=new Array(sp.c.length).fill(null);sp.izk=new Array(sp.c.length).fill(0);sp.iz.forEach(function(p){p[1].forEach(function(v,k){sp.izg[p[0]+k]=v;});
  if(p.length>2)for(var q=p[2];q<p[1].length;q++)sp.izk[p[0]+q]=1;});}  // 3. eleman: 🔐 kâr kilidinin devreye girdiği parça içi sıra  // iz stop parçaları → gün dizisi
 var uz=ar==='1y'&&sp.w&&sp.w.length&&sp.w0,m=uz?sp.w.length:0,bos=new Array(m).fill(null);
 var c=sp.c,s20=sp.s20,s50=sp.s50,st=sp.st,izg=sp.izg,izk=sp.izk,scg=sp.scg,tt=sp.t,tk=sp.tk||'',eski=[];
 if(uz){var wt=[];for(var q=0;q<m;q++)wt.push(grGun(sp.w0,7*q+4));   // haftalık nokta: o haftanın cuması
  c=sp.w.concat(sp.c);tt=wt.concat(sp.t);tk=new Array(m+1).join('.')+tk;
  s20=s20?bos.concat(s20):null;s50=s50?bos.concat(s50):null;st=st?bos.concat(st):null;izg=izg?bos.concat(izg):null;izk=izk?bos.concat(izk):null;scg=scg?bos.concat(scg):null;
  (tkg||[]).forEach(function(x){   // grafik penceresinden eski işlemler (haftalık kısım): işaret işlemin kendi fiyatında
   if(x[0]<sp.t[0]&&x[0]>=wt[0])eski.push(['G',x[0],x[1]]);
   if(x[2]&&x[2]<sp.t[0]&&x[2]>=wt[0])eski.push([(x[4]&2)?'K':'C',x[2],x[3]]);});}
 var n=c.length;
 if(uz){var t0=Date.parse(tt[0]),t1=Date.parse(tt[n-1]);_PX=tt.map(function(s){return GR.L+(Date.parse(s)-t0)/((t1-t0)||1)*(GR.W-GR.L-GR.R);});}else _PX=null;
 var hepsi=c.concat(s20||[],s50||[],izg||[],scg||[],[ds,dr],eski.map(function(e){return e[2];})).filter(function(x){return x!=null;});
 var mn=Math.min.apply(null,hepsi),mx=Math.max.apply(null,hepsi),pay=(mx-mn)*0.04;mn-=pay;mx+=pay;
 _gr={c:c,t:tt,s20:s20,s50:s50,izg:izg,izk:izk,scg:scg,tk:tk,m:m,px:_PX,mn:mn,mx:mx,n:n};
 var g='<svg id="grsvg" viewBox="0 0 '+GR.W+' '+GR.H+'" width="100%" style="display:block;touch-action:pan-y" onmousemove="grHover(event)" ontouchstart="grHover(event)" ontouchmove="grHover(event)" onmouseleave="grCik()">';
 adimlar(mn,mx).forEach(function(v){var y=grY(v,mn,mx).toFixed(1);
  g+='<line x1="'+GR.L+'" x2="'+(GR.W-GR.R)+'" y1="'+y+'" y2="'+y+'" stroke="#ECEDEA" stroke-width="1"/>'+
     '<text x="'+(GR.W-GR.R+4)+'" y="'+(+y+3.5)+'" font-size="10" fill="#8A8F98">'+v+'</text>';});
 for(var k=0;k<5;k++){var i=Math.round(k*(n-1)/4),x=grX(i,n);
  g+='<text x="'+x.toFixed(1)+'" y="'+(GR.H-6)+'" font-size="10" fill="#8A8F98" text-anchor="'+(k===0?'start':k===4?'end':'middle')+'">'+trTarih(tt[i])+(uz&&k===0?' '+tt[i].slice(2,4):'')+'</text>';}
 if(uz&&m)g+='<line x1="'+grX(m,n).toFixed(1)+'" x2="'+grX(m,n).toFixed(1)+'" y1="'+GR.T+'" y2="'+(GR.H-GR.B)+'" stroke="#E6E7E4" stroke-width="1"/>'+
   '<text x="'+(grX(m,n)-4).toFixed(1)+'" y="'+(GR.T+9)+'" font-size="9" fill="#A0A4AB" text-anchor="end">← haftalık · günlük →</text>';
 if(ds!=null)g+=yatay(ds,'#3A6EA5',mn,mx);
 if(dr!=null)g+=yatay(dr,'#B7791F',mn,mx);
 if(s50)g+=cizgi(s50,'#C7962B',mn,mx,1.2);
 if(s20)g+=cizgi(s20,'#0E4D45',mn,mx,1.2);
 if(st)g+=cizgi(st,'#B4362E',mn,mx,1.1);
 if(izg)g+=cizgiParca(izg,'#7A3E9D',mn,mx,1.4,'6 3');
 if(izg&&izk)for(var q=0;q<n;q++)if(izk[q]&&!(q>0&&izk[q-1])&&izg[q]!=null)   // 🔐 kâr kilidinin devreye girdiği gün: çizginin üstünde küçük kilit
  g+='<text x="'+grX(q,n).toFixed(1)+'" y="'+(grY(izg[q],mn,mx)-4).toFixed(1)+'" font-size="10" text-anchor="middle"><title>🔐 kâr kilidi devrede: stop en az alış +%'+(KK?kkSay(KK[1]):'')+'</title>🔐</text>';
 if(scg)g+=cizgiParca(scg,'#D6336C',mn,mx,1,'2 3');
 g+=cizgi(c,'#16181D',mn,mx,1.8);
 for(var j=0;j<n;j++){var a=tk.charAt(j);if((a!=='G'&&a!=='C'&&a!=='K')||c[j]==null)continue;   // Telegram'daki 🚀 AL ve iz stop / 🔐 kâr kilidi çıkışı
  g+=grIsaret(a==='K'?'C':a,grX(j,n),grY(c[j],mn,mx),(a==='G'?'▲ AL (🚀 kırılım): ':a==='K'?'▼ SAT (🔐 kâr kilidi): ':'▼ SAT (iz stop): ')+trTarih(tt[j])+' · '+c[j]+' TL',a==='K');}
 if(eski.length){var e0=Date.parse(tt[0]),e1=Date.parse(tt[n-1]);eski.forEach(function(e){
  var ex=GR.L+(Date.parse(e[1])-e0)/((e1-e0)||1)*(GR.W-GR.L-GR.R);
  g+=grIsaret(e[0]==='K'?'C':e[0],ex,grY(e[2],mn,mx),(e[0]==='G'?'▲ AL (🚀 kırılım): '+trTarih(e[1])+' · giriş ':(e[0]==='K'?'▼ SAT (🔐 kâr kilidi): ':'▼ SAT (iz stop): ')+trTarih(e[1])+' · ')+e[2]+' TL',e[0]==='K');});}
 g+='<line id="grcizgi" x1="0" x2="0" y1="'+GR.T+'" y2="'+(GR.H-GR.B)+'" stroke="#16181D" stroke-width="0.8" stroke-dasharray="3 3" visibility="hidden"/>'+
    '<circle id="grnokta" r="3.5" fill="#16181D" visibility="hidden"/></svg><div id="grbilgi" class="grbilgi" hidden></div>';
 return g;
}
function grHover(e){
 if(!_gr)return;var svg=document.getElementById('grsvg');if(!svg)return;
 var p=e.touches?e.touches[0]:e,r=svg.getBoundingClientRect(),x=(p.clientX-r.left)/r.width*GR.W;
 var n=_gr.n,i;
 if(_gr.px){i=0;for(var j=1;j<n;j++)if(Math.abs(_gr.px[j]-x)<Math.abs(_gr.px[i]-x))i=j;}
 else i=Math.max(0,Math.min(n-1,Math.round((x-GR.L)/(GR.W-GR.L-GR.R)*(n-1))));
 var G=_gr;if(G.c[i]==null)return;
 var xx=G.px?G.px[i]:GR.L+(n>1?i/(n-1):0)*(GR.W-GR.L-GR.R),yy=grY(G.c[i],G.mn,G.mx),cz=document.getElementById('grcizgi'),nk=document.getElementById('grnokta'),b=document.getElementById('grbilgi');
 cz.setAttribute('x1',xx);cz.setAttribute('x2',xx);cz.setAttribute('visibility','visible');
 nk.setAttribute('cx',xx);nk.setAttribute('cy',yy);nk.setAttribute('visibility','visible');
 var ta={G:' · ▲ AL (🚀)',C:' · ▼ SAT (iz stop)',K:' · ▼ SAT (🔐 kâr kilidi)'}[(G.tk||'').charAt(i)]||'';
 b.innerHTML='<b>'+(i<G.m?'hafta sonu ':'')+trTarih(G.t[i])+' '+G.t[i].slice(0,4)+'</b> · '+G.c[i]+' TL'+ta+
  (G.izg&&G.izg[i]!=null?'<br><span style="color:#7A3E9D">İz stop '+G.izg[i]+(G.izk&&G.izk[i]?' 🔐':'')+'</span>':'')+(G.scg&&G.scg[i]!=null?(G.izg&&G.izg[i]!=null?' · ':'<br>')+'<span style="color:#D6336C">Sıkı çizgi '+G.scg[i]+'</span>':'')+
  (G.s20&&G.s20[i]!=null?'<br><span style="color:#0E4D45">SMA20 '+G.s20[i]+'</span>':'')+(G.s50&&G.s50[i]!=null?' · <span style="color:#C7962B">SMA50 '+G.s50[i]+'</span>':'');
 b.hidden=false;b.style.left=Math.min(Math.max(xx/GR.W*100,2),70)+'%';
}
function grCik(){['grcizgi','grnokta'].forEach(function(id){var el=document.getElementById(id);if(el)el.setAttribute('visibility','hidden');});var b=document.getElementById('grbilgi');if(b)b.hidden=true;}
function grAralikSec(k,a){  // 6 ay / 1 yıl düğmesi
 var d=DATA[k];if(!d)return;_grAralik=a;var el=document.getElementById('grkutu');if(el)el.innerHTML=grafik(d.spark,d.sd,a,d.tkg);
 ['6a','1y'].forEach(function(x){var b=document.getElementById('gra'+x);if(b)b.className='grb'+(x===a?' on':'');});
}
// --- 🚀 v3 işlem geçmişi: d.tkg = sinyal.tk_gecmis → [sinyal (kırılım) günü, giriş (ertesi açılış), çıkış günü|null, çıkış|null]
function tkGun(d,t){var tt=(d.spark||{}).t||[],i=tt.indexOf(t);return i<0?null:tt.length-1-i;}  // sinyal kaç işlem günü önce (rozetlerdeki tk.gun ile aynı); ~6 aydan eskiyse null
function xuSon(){return (XU&&XU.c&&XU.c.length)?XU.c[XU.c.length-1]:null;}
function tkIslem(d,x){  // tek işlem: getiri (komisyonsuz) ve aynı günlerde BIST 100 (sinyal günü kapanışından çıkış günü / son kapanışa)
 var acik=x[2]==null,son=acik?d.fiyat:x[3],r=(x[1]&&son!=null)?(son/x[1]-1)*100:null;
 var x0=xuDeger(x[0]),x1=acik?xuSon():xuDeger(x[2]),xr=(x0&&x1)?(x1/x0-1)*100:null;
 return {t:x[0],g:x[1],ct:x[2],c:x[3],acik:acik,son:son,r:r,xu:xr,fark:(r!=null&&xr!=null)?r-xr:null,gun:tkGun(d,x[0]),kil:!!(x[4]&1),kk:!!(x[4]&2),kka:!!(x[4]&4)};  // x[4] bit: 1 kilitli taban, 2 🔐 ile çıkış, 4 açık + 🔐 devrede
}
function kkSay(x){return String(x).replace('.',',');}
function kkKisa(){return KK?'🔐 kâr kilidi: kapanışta +%'+kkSay(KK[0])+' görülünce stop en az alış +%'+kkSay(KK[1]):'';}
function izNeden(o){  // stop nereden geliyor: %20 iz mi, 🔐 kâr kilidi mi (o: tk ya da d.iz; alanlar sinyal._kk_alanlar)
 if(o&&o.kilit&&o.kilit_seviye!=null&&o.iz20!=null&&o.kilit_seviye>=o.iz20)return '🔐 kâr kilidi: +%'+kkSay(o.kk[0])+' görüldü, stop en az alış +%'+kkSay(o.kk[1]);
 var t='AL\'den beri tepe '+o.tepe+' TL\'nin %20 altı';
 if(o.kilit)t+='; 🔐 kâr kilidi devrede (en az '+o.kilit_seviye+' TL)';
 else if(o.kilit_esik_fiyat!=null)t+='; kapanış '+o.kilit_esik_fiyat+' TL\'yi görürse 🔐 stop en az '+o.kilit_seviye+' TL';
 return t;}
var KK_CIKIS=' <span class="kkc" title="Bu işlemde kapanış alışın üstünde bir kâr eşiğini görmüştü; stop en az alış fiyatının biraz üstündeydi (kâr kilidi) ve o seviyenin altında kapanışla çıkıldı">🔐 kâr kilidiyle çıktı</span>';
var KIL_CIKIS=' <span class="kilc" title="Çıkış günü kilitli tabandı (gün boyu işlem neredeyse yok): o gün satış emri çoğu zaman gerçekleşmez; gerçek çıkış sonraki ilk açılışta, genelde daha aşağıdan olurdu">🔒 tabanda alıcı yoktu, bu fiyattan satılamamış olabilir</span>';
function tTam(s){if(!s)return '—';var y=(XU&&XU.t&&XU.t.length)?XU.t[XU.t.length-1].slice(0,4):'';return trTarih(s)+(s.slice(0,4)!==y?' '+s.slice(0,4):'');}
function tlS(x){return x==null?'—':(+x).toLocaleString('tr-TR',{maximumFractionDigits:2})+' TL';}
function tkY(x){return x==null?'—':pyz(x);}
function tkP(x){return x==null?'—':(x>=0?'+':'−')+Math.abs(x).toFixed(1).replace('.',',')+' puan';}
function tkC(x){return x==null?'':(x>=0?'pos':'neg');}
function tkSonHtml(d){  // grafiğin üstünde tek satır: son 🚀 AL ya da son SAT (iz stop)
 var a=d.tkg||[],t=d.tk||{};
 if(!a.length)return '<div class="tkson sgun">🚀 '+(t.kisa?'Henüz 🚀 sinyali olamaz: kural en az 1 yıllık (250 işlem günü) fiyat geçmişi ister.':'Son ~2 yılda 🚀 AL sinyali yok.')+'</div>';
 var x=tkIslem(d,a[a.length-1]),h;
 if(x.acik&&t.bugun)h='▲ <b>Bugün 🚀 AL</b> — kapanış '+tlS(x.g)+'; kurala göre giriş yarın açılışta. Çıkış: tepe kapanışın %20 altı (iz stop).'+(KK?' '+kkKisa()+'.':'');
 else if(x.acik)h='▲ <b>Son 🚀 AL: '+tTam(x.t)+'</b> · giriş '+tlS(x.g)+' → şu an <b class="'+tkC(x.r)+'">'+tkY(x.r)+'</b> (pozisyon açık'+(t.stop!=null?' · iz stop '+tlS(t.stop)+(t.kilit?' 🔐':''):'')+')'+
   (x.gun!=null&&x.gun>5?' <span class="sgun">· '+x.gun+' işlem günü önceydi; yeni alım sinyali değil</span>':'');
 else h='▼ <b>Son SAT ('+(x.kk?'🔐 kâr kilidi':'iz stop')+'): '+tTam(x.ct)+'</b> · '+tlS(x.c)+'; o işlemde <b class="'+tkC(x.r)+'">'+tkY(x.r)+'</b> <span class="sgun">(🚀 AL '+tTam(x.t)+', giriş '+tlS(x.g)+')</span>'+(x.kil?KIL_CIKIS:'');
 return '<div class="tkson">'+h+'</div>';
}
function tkGecmisHtml(d){  // hisse penceresi: bu hissenin son v3 işlemleri (bilgi)
 var a=(d.tkg||[]).slice().reverse();if(!a.length)return '';
 var bas=((d.spark||{}).t||[])[0]||'',ev=false;
 var h='<div class="bilkutu">🚀 <b>Sinyal geçmişi</b> <span class="sgun">— v3 kuralının bu hissedeki son '+a.length+' işlemi (canlı kural geçmişe uygulandı)</span>'+
  '<div class="tkgs"><table class="rk"><thead><tr><th>🚀 AL (sinyal)</th><th class="num">Giriş</th><th>Çıkış</th><th class="num">Getiri</th><th class="num" title="Aynı günlerde BIST 100 getirisine göre fark">BIST 100\'e göre</th></tr></thead><tbody>';
 a.forEach(function(x){var s=tkIslem(d,x),es=x[0]<bas;if(es)ev=true;
  h+='<tr><td>'+tTam(s.t)+(es?' <span class="sgun" title="6 aydan eski: aşağıdaki nota bak">≈</span>':'')+'</td><td class="num">'+tlS(s.g)+'</td>'+
   '<td>'+(s.acik?'<span class="tkb izle">açık</span> şu an '+tlS(s.son)+(s.kka?' 🔐':''):tTam(s.ct)+' · '+tlS(s.c)+(s.kil?KIL_CIKIS:'')+(s.kk?KK_CIKIS:''))+'</td>'+
   '<td class="num '+tkC(s.r)+'">'+tkY(s.r)+'</td><td class="num '+tkC(s.fark)+'">'+tkP(s.fark)+'</td></tr>';});
 h+='</tbody></table></div><div class="pk sgun">Giriş: sinyalin ertesi günü açılış; çıkış: iz stop'+(KK?' (ya da 🔐 kâr kilidi: kapanışta +%'+kkSay(KK[0])+' görüldükten sonra alış +%'+kkSay(KK[1])+')':'')+' kırılan günün kapanışı; komisyonsuz. Liste çıkışı son 2 yıl içinde olan ya da hâlâ açık işlemleri gösterir (pano 4 yıllık veriyle çalışır: kuralın 1 yıllık ısınması ve önceden açık kalan pozisyonlar doğru hesaplanır)'+
  (ev?'; ≈ işaretli işlemler 6 aydan eski (grafiğin günlük kısmında değil; 2 yıldan eski günlerde BIST 100 farkı haftalık veriyle yaklaşık)':'')+
  '. <b>Tek hissenin geçmiş işlemleri geleceğini göstermez</b>; kural tek hissede değil, yüzlerce hissede birlikte test edildi.</div></div>';
 return h;
}
// --- 🚀 Son roketler filtresi: son N işlem gününde 🚀 AL almış hisseler — kapananlar (iz stop) DAHİL (seçim yanlılığı olmasın)
function roketListe(N){
 var o=[];Object.keys(DATA).forEach(function(k){var d=DATA[k];(d.tkg||[]).forEach(function(x){var g=tkGun(d,x[0]);
  if(g!=null&&g<=N){var s=tkIslem(d,x);s.kod=k;o.push(s);}});});
 o.sort(function(a,b){return a.t<b.t?1:(a.t>b.t?-1:(a.kod<b.kod?-1:1));});
 return o;
}
function roketOzet(o){  // tarama dışı araştırmadaki Python hesabıyla aynı (ortalama / medyan / artıda / endeksi geçen)
 var r=o.map(function(s){return s.r;}).filter(function(v){return v!=null;}),f=o.map(function(s){return s.fark;}).filter(function(v){return v!=null;});
 var ort=function(a){return a.length?a.reduce(function(x,y){return x+y;},0)/a.length:null;};
 var med=function(a){if(!a.length)return null;var b=a.slice().sort(function(x,y){return x-y;}),h=b.length>>1;return b.length%2?b[h]:(b[h-1]+b[h])/2;};
 return {n:o.length,acik:o.filter(function(s){return s.acik;}).length,arti:r.filter(function(v){return v>0;}).length,ort:ort(r),med:med(r),
  fort:ort(f),fmed:med(f),gecen:f.filter(function(v){return v>0;}).length,fn:f.length};
}
function roketHtml(N,q,sf,fav){
 var o=roketListe(N).filter(function(s){return (!q||s.kod.indexOf(q)>=0)&&(!sf||fav.indexOf(s.kod)>=0);}),z=roketOzet(o);
 var h='<div class="bugun rkkutu"><h2>🚀 Son '+N+' işlem gününün sinyalleri</h2>';
 if(!o.length)return h+'<div class="bgs">Bu dönemde 🚀 AL yok'+(q||sf?' (arama/favori süzgecine uyan)':'')+'.</div></div>';
 h+='<div class="bgs"><b>'+z.n+' sinyal</b> ('+z.acik+' hâlâ açık, '+(z.n-z.acik)+' iz stop'+(KK?' / 🔐 kâr kilidi':'')+' ile kapandı) · artıda <b>'+z.arti+'/'+z.n+'</b> · ortalama <b class="'+tkC(z.ort)+'">'+tkY(z.ort)+'</b> · medyan <b class="'+tkC(z.med)+'">'+tkY(z.med)+'</b>'+
  (z.fn?' · BIST 100\'e göre ortalama <b class="'+tkC(z.fort)+'">'+tkP(z.fort)+'</b>, medyan '+tkP(z.fmed)+', endeksi geçen '+z.gecen+'/'+z.fn:'')+'</div>';
 h+='<div class="bgs sgun">Getiri: sinyalin ertesi açılışından bugüne (açıksa) ya da iz stop çıkışına; komisyonsuz. Kapananlar da listede — sadece iyi gidenleri göstermek yanıltıcı olur. Kısa dönemde birkaç hisse ortalamayı sürükler; bir dönemin iyi gitmesi sonrakini göstermez.'+
  (N>5?' <b>Eski satırlar yeni alım sinyali değil:</b> testte sinyalden 20+ gün sonra girmek geçmişte belirgin daha kötüydü (sinyal günü ort. +%20 / isabet %52; 20 gün sonra +%15 / %47; 40 gün sonra +%8 / %35).':'')+'</div>';
 h+='<div class="sar"><table class="rk"><thead><tr><th>Hisse</th><th>🚀 Sinyal günü</th><th class="num">Giriş</th><th class="num">Şimdi / çıkış</th><th class="num">Getiri</th><th class="num">BIST 100</th><th class="num">Fark</th><th>Durum</th></tr></thead><tbody>';
 o.forEach(function(s){var dur;
  if(!s.acik)dur='<span class="tkb izle">kapandı '+tTam(s.ct)+'</span>';
  else if(s.gun===0)dur='<span class="tkb yeni">🚀 bugün</span>';
  else if(s.gun<=5)dur='<span class="tkb">🚀 AL '+s.gun+'g önce</span>';
  else dur='<span class="tkb izle">trendde · '+s.gun+'g</span>';
  h+='<tr onclick="ac(\''+s.kod+'\')"><td class="kod">'+s.kod+'</td><td>'+tTam(s.t)+' <span class="sgun">'+(s.gun===0?'bugün':s.gun+'g önce')+'</span></td><td class="num">'+tlS(s.g)+'</td>'+
   '<td class="num">'+tlS(s.son)+(s.kil?KIL_CIKIS:'')+(s.kk?KK_CIKIS:'')+'</td><td class="num '+tkC(s.r)+'">'+tkY(s.r)+'</td><td class="num">'+tkY(s.xu)+'</td><td class="num '+tkC(s.fark)+'">'+tkP(s.fark)+'</td><td>'+dur+'</td></tr>';});
 return h+'</tbody></table></div></div>';
}
function roketAc(n){var s=document.getElementById('roket');if(!s)return;s.value=String(n);tabloDuzen();var k=document.getElementById('roketkutu');if(k&&k.scrollIntoView)k.scrollIntoView({behavior:'smooth',block:'start'});}
function sdHtml(d){
 const sd=d.sd;if(!sd)return '';
 const sat=(ad,s,tur)=>{
  if(!s)return '<div class="sdsat"><b>'+ad+':</b> son '+sd.gun+' günde fiyatın '+(tur==='dip'?'altında':'üstünde')+' belirgin bir '+tur+' yok.</div>';
  const yon=s.uzaklik<0?'altında':'üstünde';
  const test=s.test>1?' · bu bölge '+s.test+' kez test edildi ('+s.tarihler.join(', ')+')':'';
  return '<div class="sdsat"><b>'+ad+': '+s.fiyat+' TL</b> — '+s.tarih+' tarihli '+tur+', fiyatın %'+Math.abs(s.uzaklik)+' '+yon+test+'</div>';
 };
 let h='<div class="sdkutu"><div class="gbas">Destek / Direnç</div>'+sat('Destek',sd.destek,'dip')+sat('Direnç',sd.direnc,'tepe');
 if(sd.tepki)h+='<div class="sdnot destek"><b>Destekten tepki:</b> fiyat son 5 günde '+sd.destek.fiyat+' TL desteğine indi ve yukarı dönmeye başladı (bugünkü kapanış dünküden yüksek). Destek tutarsa olumlu; bu seviyenin altında kapanış gelirse bu okuma geçersiz olur.</div>';
 if(sd.tepki&&d.sinyal==='SAT')h+='<div class="sdnot direnc"><b>⚠ Çelişki — SAT sürerken destekte tepki:</b> 5 yıllık backtest\'te bu durumda desteklerin yaklaşık <b>%68\'i 20 gün içinde kırıldı</b>; düşüş trendinde destek tepkisi çoğu zaman kısa bir soluklanma oldu. '+
   '<b>Karar çizgisi: '+(Math.round(sd.destek.fiyat*(1-sd.tol/100)*100)/100)+' TL</b> — bunun altında kapanış desteğin kırıldığını gösterir. Destek tutar ve sinyal AL\'e dönerse tablo değişir.</div>';
 if(sd.yaklas)h+='<div class="sdnot direnc"><b>Dirence yaklaşıyor:</b> fiyat '+sd.direnc.fiyat+' TL direncine %'+sd.tol+'\'den daha yakın. Geçmişte bu seviyede satış geldi; aşamazsa geri dönebilir. Kapanışla net aşarsa direnç desteğe dönüşebilir.'+
   (d.sinyal==='AL'?' <i>Not: 5 yıllık backtest\'te dirence yakınken gelen AL\'ler kötü sonuç vermedi — çoğu zaman kırılım denemesiydi.</i>':'')+'</div>';
 if(!sd.tepki&&!sd.yaklas)h+='<div class="sdyok">Fiyat şu an bir desteğe tepki vermiyor ve bir dirence yakın değil.</div>';
 h+='<div class="sdyontem">Nasıl bulunur: son '+sd.gun+' günün dip ve tepe noktaları (iki yanındaki 5 günün en düşüğü/en yükseği). Son 10 günde oluşanlar sayılmaz. Etiket için seviye en az '+(sd.min_test||2)+' kez test edilmiş olmalı. "Yakın" eşiği bu hisse için %'+sd.tol+' (hissenin oynaklığına göre).</div></div>';
 return h;
}
function yenile(){location.href=location.pathname+'?t='+Date.now();}
function yzd(x){return (x>=0?'+':'−')+Math.abs(x).toFixed(1)+'%';}
function tlf(x){return (x>=0?'+':'−')+Math.round(Math.abs(x)).toLocaleString('tr-TR')+' TL';}
// tarama.py pozisyon_plani() ile aynı mantık
function kararCizgisi(d){var sd=d.sd;return (sd&&sd.destek)?Math.round(sd.destek.fiyat*(1-sd.tol/100)*100)/100:null;}
function pozPlan(d,p){
 var f=d.fiyat,m=p.maliyet,a=p.adet,pl={f:f,m:m,a:a,kz:(f-m)*a,kzy:(f/m-1)*100,sat:d.sinyal==='SAT',stop:null,hedefler:[],uzun:!!p.uzun};
 if(pl.uzun){   // uzun vade: stop yerine karar çizgisi (ana destek); kısa vadeli sinyal bilgi amaçlı
  pl.karar=kararCizgisi(d);if(pl.karar){pl.kararUzak=(pl.karar/f-1)*100;pl.kararAsildi=f<pl.karar;}
  var dru=d.sd&&d.sd.direnc;if(dru&&dru.fiyat>f)pl.hedefler.push([dru.fiyat,'en yakın direnç ('+dru.tarih+' tepesi)']);
  return pl;
 }
 // v2: çıkış iz stop (AL'den beri tepe kapanışın %20 altı); SAT bilgi amaçlı
 var iz=d.iz,stop;
 if(iz&&iz.cikti){pl.izCikti=iz.cikis_tarih;pl.kilitCik=!!iz.kilit_cik;stop=null;}
 else if(iz){stop=iz.stop;pl.iz=true;pl.tepe=iz.tepe;pl.izNeden=izNeden(iz);pl.kilit=!!iz.kilit;}
 else stop=d.al_stop||d.stop;
 pl.stop=stop;
 if(stop){pl.stopUzak=(stop/f-1)*100;pl.stopKz=(stop-m)*a;pl.asildi=f<=stop;}
 var dr=d.sd&&d.sd.direnc;if(dr&&dr.fiyat>f)pl.hedefler.push([dr.fiyat,'en yakın direnç ('+dr.tarih+' tepesi)']);
 return pl;
}
function pozHtml(k,d){
 var p=pfOku().filter(function(x){return x.kod===k;});if(!p.length||d.fiyat==null)return '';
 var ad=0,top=0;p.forEach(function(x){ad+=x.adet;top+=x.adet*x.maliyet;});
 var uzun=p.some(function(x){return x.uzun;});
 var pl=pozPlan(d,{adet:ad,maliyet:top/ad,uzun:uzun}),h='<div class="pozkutu"><div class="pbas">💼 Senin pozisyonun'+(uzun?' · uzun vade':'')+'</div>'+
  '<div>'+ad+' adet, maliyet '+pl.m.toFixed(2)+' TL → şu an <b class="'+(pl.kz>=0?'pos':'neg')+'">'+yzd(pl.kzy)+' ('+tlf(pl.kz)+')</b></div>';
 if(pl.uzun){
  if(pl.sat)h+='<div class="pk">ℹ️ Kısa vadede trend aşağı (SAT). Uzun vade pozisyonun için bilgi amaçlı.</div>';
  h+=pl.karar?(pl.kararAsildi?'<div class="pk neg">🧭 <b>Fiyat karar çizgisinin ('+pl.karar+' TL) altında</b> — ana destek kırıldı; pozisyonu gözden geçirme noktası.</div>'
     :'<div class="pk">🧭 <b>Karar çizgisi: '+pl.karar+' TL</b> — '+yzd(pl.kararUzak)+' aşağıda. Ana destek ('+d.sd.destek.fiyat+' TL, '+d.sd.destek.test+' kez test edildi) bunun altında kapanışla kırılmış sayılır.</div>')
    :'<div class="pk">🧭 Fiyatın altında belirgin bir destek yok (son 120 günün dibinde).</div>';
  pl.hedefler.forEach(function(x){h+='<div class="pk">🎯 İzleme: <b>'+x[0]+' TL</b> — '+x[1]+', '+yzd((x[0]/pl.f-1)*100)+' yukarıda.</div>';});
  return h+'<div class="pk sgun">Uzun vade: kısa vadeli AL/SAT sinyalleri bilgi amaçlıdır. Backtest\'te güçlü yükseliş dönemlerinde büyük hisselerde al-tut, sinyale göre girip çıkmaktan belirgin şekilde iyi sonuç verdi. Karar çizgisinin altında kapanış, pozisyonu yeniden düşünme noktasıdır.</div></div>';
 }
 if(pl.sat)h+='<div class="pk">ℹ️ Kısa vadeli SAT sinyali — çıkış kuralı iz stop; SAT tek başına "çık" demek değil.</div>';
 if(pl.izCikti)h+='<div class="pk neg">📍 <b>'+(pl.kilitCik?'🔐 Kâr kilidi stop\'u ':'İz stop ')+pl.izCikti+' tarihinde kırıldı</b> — kurala göre çıkış zamanı geçti.</div>';
 else if(pl.stop&&pl.iz)h+='<div class="pk">📍 <b>İz stop: '+pl.stop+' TL</b> ('+pl.izNeden+') — '+yzd(pl.stopUzak)+' aşağıda. Buraya inerse sonuç: <b class="'+(pl.stopKz>=0?'pos':'neg')+'">'+tlf(pl.stopKz)+'</b>'+(pl.stopKz>=0?' (yine kârda)':'')+'</div>';
 else if(pl.stop){
  h+=pl.asildi?'<div class="pk neg">📍 <b>Fiyat çıkış seviyesinin ('+pl.stop+' TL) altında</b> — sistemin kuralına göre çıkış zamanı.</div>'
   :'<div class="pk">📍 <b>Çıkış (stop): '+pl.stop+' TL</b> — '+yzd(pl.stopUzak)+' aşağıda. Buraya inerse sonuç: <b class="'+(pl.stopKz>=0?'pos':'neg')+'">'+tlf(pl.stopKz)+'</b>'+(pl.stopKz>=0?' (yine kârda)':'')+'</div>';
 }
 pl.hedefler.forEach(function(x,i){h+='<div class="pk">🎯 <b>'+(i+1)+'. hedef: '+x[0]+' TL</b> — '+x[1]+', '+yzd((x[0]/pl.f-1)*100)+' yukarıda.'+
   (x[1].indexOf('direnç')>=0?' Burada satış baskısı gelebilir; aşarsa yükseliş hızlanabilir.':' (Tahmin değil, izleme noktası.)')+'</div>';});
 if(pl.hedefler.length)h+='<div class="pk sgun">ℹ️ Hedefler satış emri değil, izleme noktası. 5 yıllık backtest\'te hedefte kısmi satış yapmak, pozisyonu SAT/stop gelene kadar tutmaktan belirgin şekilde kötü sonuç verdi — büyük kazançlar erken kesildi.</div>';
 var kural='Kural: kapanış iz stop\'un altına inerse çık. İz stop, fiyat yükseldikçe yukarı taşınır; '+(KK?kkKisa()+'; ':'')+'SAT sinyali tek başına çıkış değildir.';
 return h+'<div class="pk">'+kural+'</div></div>';
}
function gucHtml(d){
 var g=d.guc;if(!g)return '';
 var h='<div class="bilkutu guckutu">💪 <b>Güç: '+g.puan+'/'+g.toplam+'</b> — 7 iyi göstergeden kaçı şu an olumlu.';
 g.detay.forEach(function(x){h+='<div class="gs"><span>'+(x.durum===true?'✅':(x.durum===false?'❌':'—'))+'</span><b>'+x.ad+'</b><span class="sgun">'+x.aciklama+'</span></div>';});
 if(d.momentum)h+='<div class="cikis">📈 <b>Ayın güçlülerinde</b> (son 6 ay '+(d.mom6>=0?'+':'')+d.mom6+'%).</div>';
 return h+'<div class="pk sgun">5 yıllık testte puan yükseldikçe sonraki ~1 ayda endekse göre getiri arttı; 2-3 ay sonrası için tutarlı değil ve v3 AL\'lerini seçmeye yaramadı. Alım sinyali değil, güç bilgisi.</div></div>';
}
function modalOzet(k,d){  // tek satır: v3 durumu · güç · uyarılar · portföy
 var p=[],t=d.tk||{};
 if(t.bugun)p.push('<span class="tkb yeni">🚀 bugün AL</span>');
 else if(t.durum==='AL')p.push(t.gun<=5?'<span class="tkb">🚀 AL '+t.gun+'g önce</span>':'<span class="tkb izle">trendde · '+t.gun+'g</span>');
 else if(t.sablon&&t.kirilima_uzak!=null&&t.kirilima_uzak>0&&t.kirilima_uzak<=3)p.push('<span class="tkb izle">👀 kırılıma %'+t.kirilima_uzak+'</span>');
 else p.push('<span class="sgun">🚀 AL yok</span>');
 if(d.guc)p.push('<span class="gucb g'+d.guc.puan+'">💪 '+d.guc.puan+'/'+d.guc.toplam+'</span>');
 if(d.momentum)p.push('<span class="momb">📈 ayın güçlüsü</span>');
 if(d.bt&&(d.bt.s==='g'||d.bt.s==='z'))p.push('<span class="bilb">📊 '+(d.bt.s==='g'?'güçlü':'zayıf')+' bilanço tepkisi</span>');
 var pf=pfOku().filter(function(x){return x.kod===k;})[0];
 bugunUyari(k,d,pf||null).forEach(function(u){p.push('<span class="gun1b">'+u+'</span>');});
 if(pf){var kz=(d.fiyat/pf.maliyet-1)*100;p.push('<span class="sgun">💼 portföyde '+(kz>=0?'+':'')+kz.toFixed(1)+'%</span>');}
 return '<div class="mozet">'+p.join(' ')+'</div>';
}
// --- 📅 Vadeler (günlük/haftalık/aylık trend oku) ve ⏱️ gün içi görünüm: BİLGİ, sinyal değil (sinyal.vade_durum, gunici.py)
var VD_ASAGI='Geçmişte (2016-2026) üç vadenin de aşağı olduğu hisseler sonraki 2-6 ayda çoğunlukla endeksin gerisinde kaldı (endeksi yenme ~%35-45; aynı dönemlerde tüm hisselerde ~%41-56). Fark küçük, kesin değil.';
var VD_YUKARI='Durum bilgisi; tek başına alım sinyali değil.';
var GI_NOT='Testte büyük hisselerde sonraki 1-5 gün için anlamlı ipucu vermedi. RSI 30 altı kısa vadede \'ucuz\' demek değil: 2 yılda bu hisseler sonraki 5 günde ortalama hisseden geride kaldı.';
var GK_EK={67:'\'si',71:'\'i',74:'\'ü',77:'\'si',76:'\'sı',79:'\'u',85:'\'i',88:'\'i'};  // tarama.GK_EK ile aynı
var GK_NOT='Geçmişte kapanışta tutan kırılımda kapanış seansında almak ertesi sabaha göre ort. +0,8 puan iyiydi; ertesi gün geri çekilme ya da limit emirle beklemek belirgin kötüydü (en güçlüler kaçtı).';
function gkMetin(o){return 'Gün içi kırılım: geçmişte bu saatte görünen kırılımların ~%'+o+(GK_EK[o]||'')+' kapanışta tuttu.';}
function vdOk(x){return x==null?'—':(x===1?'↑':(x===-1?'↓':'→'));}
function vdCls(x){return x===1?'vu':(x===-1?'va':'vy');}
function vdHucre(v){if(!v)return '—';return ['G','H','A'].map(function(h,i){return '<i class="'+vdCls(v[i])+'">'+h+vdOk(v[i])+'</i>';}).join(' ');}
function vdSkor(r){var v=(DATA[r.dataset.kod]||{}).vd;if(!v)return -9;return v.reduce(function(a,x){return a+(x||0);},0);}
function tkEksik(t){var m={ilk:'kırılım bugün ilk değil: dünkü kapanış da 20 günlük zirvenin üstündeydi, kural sadece ilk kırılım gününü sayar (yeni AL için fiyatın önce zirvenin altına inip yeniden aşması gerekir)',
  oynak:'son 60 günde günlük oynaklık %5\'in üstünde (⚡ oynak hissede v3 AL vermez)',piyasa:'BIST 100 50 günlük ortalamasının altında (piyasa filtresi: piyasa zayıfken v3 AL vermez)',
  cikis:'bugün iz stop çıkışı oldu, aynı gün yeni giriş sayılmaz'};
 return (t.eksik||[]).map(function(x){return m[x];}).filter(Boolean).join('; ');}
function vadeHtml(k,d){
 var v=d.vd,g=(typeof GI!=='undefined'&&GI&&GI.v)?GI.v[k]:null;if(!v&&!g)return '';
 var h='<div class="zaman">';
 if(v){
  h+='<div>📅 <b>Vadeler</b> (bilgi, sinyal değil): '+['Günlük','Haftalık','Aylık'].map(function(a,i){return a+' <b class="'+vdCls(v[i])+'">'+vdOk(v[i])+'</b>';}).join(' · ')+'</div>';
  if(v[0]===-1&&v[1]===-1&&v[2]===-1)h+='<div class="cikis">'+VD_ASAGI+'</div>';
  else if(v[0]===1&&v[1]===1&&v[2]===1)h+='<div class="cikis">'+VD_YUKARI+'</div>';
  h+='<div class="cikis sgun">↑ fiyat ortalamanın üstünde ve ortalama yükseliyor, ↓ altında ve yükselmiyor, → arada. Günlük: 50 günlük ort. (10 gün önceye göre) · Haftalık: son biten haftanın kapanışı, 30 haftalık ort. · Aylık: son biten ayın kapanışı, 10 aylık ort.'+(v[2]==null?' Aylık için en az 11 aylık geçmiş gerekir.':'')+'</div>';
 }
 if(g){
  var ad=['15dk','1s','4s'],kr=['5 saatlik','20 saatlik','~10 günlük'],p=[];
  for(var i=0;i<3;i++){var tr=g[3*i],r=g[3*i+1],z=g[3*i+2];
   if(tr==null&&r==null){p.push(ad[i]+' —');continue;}
   p.push(ad[i]+' <b class="'+vdCls(tr)+'">'+vdOk(tr)+'</b>'+(r!=null?' · RSI '+r:'')+(z===1?' · '+kr[i]+' zirve kırıldı':(z===-1?' · '+kr[i]+' dip kırıldı':'')));}
  h+='<div'+(v?' style="margin-top:6px"':'')+'>⏱️ <b>Gün içi görünüm</b> (sadece durum, AL/SAT değil): '+p.join(' | ')+' <span class="sgun">('+GI.t+(GI.tam?', seans sonu':'')+')</span></div>';
  h+='<div class="cikis sgun">Trend ↑: 20 mumluk üssel ortalama 50 mumluğun üstünde ve fiyat 50 mumluğun üstünde; ↓ tersi; aksi →. Kırılım: son 3 mumda önceki 20 mumun zirvesi/dibi aşıldı. '+GI_NOT+'</div>';
 }
 return h+'</div>';
}
// --- RS puanı · 📊 bilanço tepkisi · zarardaki şirket (BİLGİ; AL/SAT'ı ve Telegram'ı değiştirmez) — metinler pano.BT_NOT ile aynı
var BT_NOT={g:'Geçmişte (ana liste, 2017-26) güçlü tepki verenler sonraki 60 günde endeksi %56 oranında geçti (normal tepkide %49) — zayıf bir eğilim.',
  z:'Geçmişte (ana liste, 2017-26) zayıf tepki verenler sonraki 60 günde endeksi %46 oranında geçti (normal tepkide %49) — fark küçük.',
  n:'Geçmişte (ana liste, 2017-26) normal tepkide (−5…+5 puan) sonraki 60 günde endeksi geçme oranı %49.'};
function rsEk(n){  // '%85'inden' — Türkçe iyelik + ayrılma eki (sayının okunuşuna göre)
 var b=n%10,o=Math.floor(n/10)%10;
 if(b)return ['','inden','sinden','ünden','ünden','inden','sından','sinden','inden','undan'][b];
 return ['ından','undan','sinden','undan','ından','sinden','ından','inden','inden','ından'][o];}
function rsSatir(d){
 if(d.rs==null)return '';
 return '<div class="cikis">📈 <b>RS '+d.rs+'</b> — son 1 yılda (son 3 aya ağırlıklı) panodaki hisselerin %'+d.rs+'\''+rsEk(d.rs)+' güçlü. <span class="sgun">Araştırma: 🚀 alımlarında RS ≥ 80 olanlar ort. +%30, diğerleri +%19 kazandırdı; filtre değil, bilgi.</span></div>';}
function zararSatir(d){
 if(!d.zr)return '';
 return '<div class="cikis">🧾 <b>Son 4 çeyrekte zarar</b> (son dönem '+d.zr+'; 4 çeyreğin net kâr toplamı ≤ 0; kaynak İş Yatırım) — geçmişte zarardaki şirketlerde 🚀 alımları ort. +%17, kârlı şirketlerde +%23 getirdi. Filtre değil, sinyal yine geçerli.</div>';}
function btTarih(s){return s.slice(8,10)+'.'+s.slice(5,7);}
function btHtml(d){
 var b=d.bt;if(!b)return '';
 var h='<div class="bilkutu">📊 <b>Bilanço tepkisi';
 if(b.r!=null){
  var v=(b.r>=0?'+':'−')+Math.abs(b.r).toFixed(1).replace('.',',');
  h+=': '+(b.s==='g'?'güçlü':(b.s==='z'?'zayıf':'normal'))+'</b> — '+b.d+' bilançosu KAP\'ta yayınlandı ('+btTarih(b.y)+' '+b.y.slice(11)+'). Sonraki 2 işlem gününde ('+btTarih(b.j)+' ve '+btTarih(b.j1)+' kapanışı, bir önceki kapanışa göre) hisse BIST 100\'e göre <b class="'+(b.r>=0?'pos':'neg')+'">'+v+' puan</b>.'+
   '<div class="cikis sgun">'+BT_NOT[b.s]+' Güçlü: +5 puan ve üstü, zayıf: −5 puan ve altı. Tepki gününden sonra 60 işlem günü görünür (kalan '+Math.max(0,60-b.g)+' gün). Bilgi, sinyal değil.</div>';
 }else h+='</b>';
 if(b.b)h+='<div class="cikis">⏳ '+b.b.d+' bilançosu KAP\'ta yayınlandı ('+btTarih(b.b.y)+' '+b.b.y.slice(11)+'); tepki ölçümü (açıklamayı izleyen 2 işlem gününün kesin kapanışı, BIST 100\'e göre) henüz tamamlanmadı — bekleniyor.</div>';
 return h+'</div>';
}
function tkHtml(d){
 var t=d.tk;if(!t)return '';
 var h='<div class="uvkutu">🚀 <b>Trend kırılımı (v3 AL kuralı): ';
 if(t.bugun)h+='BUGÜN KIRILIM</b> — trend şablonundayken 20 günlük zirve ('+t.kirilim_seviye+' TL) aşıldı. Giriş ertesi açılış; çıkış: tepe kapanışın %20 altı (iz stop).'+(KK?' '+kkKisa()+'.':'')+
   (t.gk?'<div class="cikis">⏱️ <b>'+gkMetin(t.gk)+'</b> Kapanış henüz kesin değil (18:30); kapanışta seviyenin altına dönerse AL geçersiz.</div>':'')+
   '<div class="cikis">💡 '+GK_NOT+'</div>';
 else if(t.durum==='AL')h+=(t.gun<=5?'AL '+t.gun+' gün önce geldi</b>':'AL sürüyor, ama yeni alım sinyali değil</b>')+' — '+t.giris_tarih+' kırılımından beri '+t.gun+' işlem günü, '+(t.degisim>=0?'+':'')+t.degisim+'%. İz stop <b>'+t.stop+' TL</b> ('+(t.kk?izNeden(t):'tepe '+t.tepe+' TL, '+t.tepe_tarih)+').'+
   (t.gun<=5?' İlk 5 gün içinde girmek backtest\'te sinyal günüyle neredeyse aynı sonuç verdi.':' Backtest: sinyalden 20+ gün sonra girmek belirgin kötü (40 gün sonra girenlerin sadece %35\'i kârda) — elindeyse iz stop\'a kadar tut, yeni alım için bir sonraki kırılımı bekle.');
 else if(t.durum==='CIKTI'&&t.cikis_gun!=null&&t.cikis_gun<=20)h+='son işlem kapandı</b> — '+t.giris_tarih+' girişi, '+t.cikis_tarih+' '+(t.kilit_cik?'🔐 kâr kilidiyle':'iz stop ile')+' çıktı ('+(t.sonuc>=0?'+':'')+t.sonuc+'%).';
 else h+=(t.sablon?(t.kirilima_uzak!=null&&t.kirilima_uzak<0?'şablonda, fiyat kırılım seviyesinin üstünde ama AL yok</b> —':'şablonda, kırılım bekleniyor</b>'):'yok</b> — trend şablonu sağlanmıyor.');
 if(!t.bugun&&t.durum!=='AL'&&t.sablon&&t.kirilim_seviye){var eks=tkEksik(t);
  if(t.kirilima_uzak!=null&&t.kirilima_uzak<0)h+=' Fiyat 20 günlük zirvenin (<b>'+t.kirilim_seviye+' TL</b>) %'+Math.abs(t.kirilima_uzak).toFixed(1).replace('.',',')+' üstünde'+(eks?'. AL için eksik koşul: '+eks+'.':'; kapanışta üstünde kalırsa AL olur.');
  else h+=' Kapanış <b>'+t.kirilim_seviye+' TL</b> üstüne çıkarsa AL'+(t.kirilima_uzak!=null?' (%'+String(t.kirilima_uzak).replace('.',',')+' yukarıda)':'')+'.'+(eks?' Ancak şu an kırılım AL sayılmaz: '+eks+'.':'');}
 if(t.durum==='AL'&&t.uzama)h+='<div class="cikis">'+uzamaMetin(t.uzama).replace('⚠️ Çok yükselmiş hisse','⚠️ <b>Çok yükselmiş hisse</b>')+' <span class="sgun">(sinyal günü ölçüldü; bilgi — AL engellenmez)</span></div>';
 if(t.durum==='AL'&&t.sc)h+='<div class="cikis">'+scMetin(t.sc).replace(/^📏 (Sıkı çizgi[^(]*)/,'📏 <b>$1</b>')+' <span class="sgun">(kijun: son 26 günün en yüksek ve en düşük fiyatının ortası; grafikte pembe kesikli çizgi)</span></div>';
 h+=rsSatir(d)+zararSatir(d);
 h+='<div class="pk sgun">Şablon: fiyat > 50 > 150 > 200 günlük ortalama, 200 günlük yükseliyor, 52 hafta zirvesine en az %75 yakın, dibinden en az %30 yukarıda. 5 yıllık backtest\'te v2\'den iyi (200 rastgele denemenin %77-97\'sinde); yine de tavsiye değildir.</div>';
 return h+'</div>';
}
function uvHtml(d){
 var u=d.uv;if(!u)return '';
 var h='<div class="uvkutu">🌱 <b>Uzun vade sinyali: ';
 if(u.durum==='AL')h+='AL</b> — '+u.tarih+' tarihinden beri ('+u.gun+' işlem günü, '+(u.degisim>=0?'+':'')+u.degisim+'%). Yükselen trendde 50 günlük ortalamaya geri çekilip dönmüştü. Çıkış: 2 gün üst üste 200 günlük ortalamanın ('+u.sma200+' TL) altında kapanış.';
 else if(u.durum==='SAT'&&u.sma200&&d.fiyat>u.sma200)h+='hâlâ SAT</b> ('+u.tarih+'), ama fiyat o zamandan beri 200 günlük ortalamanın ('+u.sma200+' TL) üstüne döndü.'+
   (u.trend&&u.sma50?' Yeni 🌱 AL için 50 günlük ortalamaya ('+u.sma50+' TL) geri çekilme bekleniyor.':' 200 günlük ortalama henüz yükselmiyor; yeni 🌱 AL için önce yükselen trend gerekir.');
 else if(u.durum==='SAT')h+='SAT</b> — '+u.tarih+' tarihinde fiyat 200 günlük ortalamanın altına indi; uzun vadeli trend bozuk (200 günlük ort. '+u.sma200+' TL).';
 else h+='yok</b>.';
 if(u.durum!=='AL'&&u.durum!=='SAT'&&u.trend)h+=' Trend yükselişte; uzun vade AL için 50 günlük ortalamaya ('+u.sma50+' TL) geri çekilme bekleniyor.';
 if(d.bayrak)h+='<div class="cikis">🚩 <b>Bayrak kırılımı:</b> %'+d.bayrak.direk+' direkten sonra '+d.bayrak.bayrak_gun+' günlük bayrak yukarı kırıldı (bayrak dibi '+d.bayrak.bayrak_dip+' TL).</div>';
 return h+'</div>';
}
function bilSayi(x,p){var a=Math.abs(x),t=a>=1e9?(a/1e9).toFixed(1)+' mlr':(a>=1e6?(a/1e6).toFixed(0)+' mn':Math.round(a)+'');return (x<0?'−':'')+t+' '+(p==='TRY'?'TL':p);}
function bilYuz(x){return x>=0?'+%'+x:'−%'+(-x);}
function temHtml(d){
 var t=d.temettu;if(!t)return '';
 var h='<div class="cikis">💰 <b>Temettü:</b> ';
 if(t.son12)h+='son 12 ayda hisse başı <b>'+t.son12+' TL</b> ('+t.adet+' ödeme'+(t.verim!=null?', güncel fiyata göre verim <b>%'+t.verim+'</b>':'')+')'+(t.supheli?' <i>— verim çok yüksek görünüyor; arada bedelsiz olduysa veri şaşmış olabilir, KAP\'tan kontrol et</i>':'')+'.';
 else h+='son 12 ayda ödeme yok.';
 if(t.ex_tarih){var x=t.ex_tarih.split('-');h+=' Sonraki hak kullanım (Yahoo; KAP\'tan teyit et): <b>'+x[2]+'.'+x[1]+'.'+x[0]+'</b> ('+t.ex_kalan+' gün) — o sabah fiyat temettü kadar düşük açılır.';}
 return h+'</div>';
}
function bilHtml(d){
 var b=d.bilanco;if(!b)return d.temettu?'<div class="bilkutu">'+temHtml(d)+'</div>':'';
 var h='<div class="bilkutu">📊 <b>Bilanço ('+b.donem+')</b> — net kâr '+bilSayi(b.net,b.para);
 if(b.net_yuz!=null)h+=', geçen yılın aynı çeyreğine göre <b class="'+(b.net_yuz>=0?'pos':'neg')+'">'+bilYuz(b.net_yuz)+'</b>';
 else if(b.net_degisim)h+=' — <b class="'+(/kâra|azaldı/.test(b.net_degisim)?'pos':'neg')+'">'+b.net_degisim+'</b> (geçen yılın aynı çeyreğine göre)';
 if(b.satis_yuz!=null)h+=' · satış '+bilYuz(b.satis_yuz);
 h+='.'+temHtml(d);
 if(b.sonraki){var t=b.sonraki.tarih.split('-');h+='<div class="cikis">📅 Sonraki bilanço: <b>'+t[2]+'.'+t[1]+'.'+t[0]+'</b>'+(b.sonraki.kaynak==='yahoo'?' (Yahoo takvimi)':' (SPK son teslim günü — çoğu şirket daha erken açıklar)')+(b.kalan_gun!=null&&b.kalan_gun>=0?' · '+b.kalan_gun+' gün sonra':'')+'</div>';}
 if(b.gecikmis)h+='<div class="cikis">⚠ Son bilanço veri kaynağında görünmüyor (açıklanmamış ya da kaynak gecikmeli) — KAP\'tan kontrol et.</div>';
 var s=b.seri||[];
 if(s.length>=2){
  var W=420,H=120,ust=14,alt=18,mx=0;s.forEach(function(x){mx=Math.max(mx,Math.abs(x[1]));});
  var neg=s.some(function(x){return x[1]<0;}),pos=s.some(function(x){return x[1]>0;});
  var y0=neg&&pos?ust+(H-ust-alt)/2:(neg?ust:H-alt),olc=(neg&&pos?(H-ust-alt)/2:(H-ust-alt))/(mx||1),bw=W/s.length;
  var g='<svg viewBox="0 0 '+W+' '+H+'"><line x1="0" x2="'+W+'" y1="'+y0+'" y2="'+y0+'" stroke="#bbb"/>';
  s.forEach(function(x,i){var hh=Math.abs(x[1])*olc,y=x[1]>=0?y0-hh:y0,cx=i*bw+bw/2;
   g+='<rect x="'+(i*bw+bw*0.2)+'" y="'+y+'" width="'+(bw*0.6)+'" height="'+Math.max(hh,1)+'" fill="'+(x[1]>=0?'#1B7F4B':'#B4362E')+'" rx="2"/>'+
    '<text x="'+cx+'" y="'+(H-4)+'" font-size="10" text-anchor="middle" fill="#666">'+x[0]+'</text>'+
    '<text x="'+cx+'" y="'+(x[1]>=0?Math.max(y-3,10):Math.min(y+hh+11,H-alt-2))+'" font-size="9" text-anchor="middle" fill="#333">'+bilSayi(x[1],'').trim()+'</text>';});
  h+=g+'</svg><div class="pk sgun">Çeyreklik net kâr ('+(b.para==='TRY'?'TL':b.para)+').'+(b.para==='TRY'?' TL rakamlar enflasyon muhasebesiyle raporlanır; yıllık artışın bir kısmı enflasyondur.':' Şirket rakamlarını '+b.para+' ile raporluyor.')+' Bilgi amaçlı: kısa veri geçmişi yüzünden sinyale etkisi backtest edilemedi.</div>';
 }
 return h+'</div>';
}
function kapHtml(d){
 var L=d.kap;if(!L||!L.length)return '';
 var h='<div class="bilkutu">📰 <b>Son KAP bildirimleri</b>';
 L.forEach(function(b){var t=b.t.slice(8,10)+'.'+b.t.slice(5,7)+' '+b.t.slice(11);
  var oz=(b.ozet&&b.ozet!==b.konu)?' — '+b.ozet.replace(/</g,'&lt;'):'';
  h+='<div class="cikis"><span class="sgun">'+t+'</span> <a href="https://www.kap.org.tr/tr/Bildirim/'+b.id+'" target="_blank" rel="noopener"><b>'+b.konu.replace(/</g,'&lt;')+'</b></a>'+oz+'</div>';});
 return h+'<div class="pk sgun">Haberler çoğu zaman fiyata hızla yansır; bağlam içindir, sinyal değildir.</div></div>';
}
function arzHtml(d){
 var z=d.arz;if(!z)return '';
 var g=z.getiri==null?'':' · arzdan beri <b class="'+(z.getiri>=0?'pos':'neg')+'">'+(z.getiri>=0?'+':'')+z.getiri+'%</b>';
 return '<div class="arzkutu">🆕 <b>Halka arz:</b> '+z.tarih+' tarihinde işlem görmeye başladı'+(z.arz_fiyat?' · arz fiyatı <b>'+z.arz_fiyat+' TL</b>':' (bölünmeyle geldi, arz fiyatı yok)')+g+'</div>';
}
// --- 🔒 kilitli taban (sinyal.kilitli_taban) ve aşırı uzamış 🚀 notu — metinler tarama.kilit_metni / uzama_metni ile aynı
var KILIT_NOT='Geçmişte benzerlerinin ~%60\'ı 4+ tabana uzadı (normalde ~%9). Kilitli tabanda satış emri çoğu zaman gerçekleşmez. Kesin değil.';
var UZAMA_NOT='geçmişte bu tür 🚀 girişlerinin ~%13\'ü %30+ kayıpla kapandı (diğerlerinde ~%1; taban günlerinde satılamadığı varsayımıyla), en büyük kazananların bir kısmı da bu grupta. Pozisyon büyüklüğüne dikkat.';
function ktMetin(kt){
 if(!kt)return '';
 var m=kt.kilitli_bugun?kt.seri+' gündür taban, bugün gün boyu işlem neredeyse yok (kilitli)'+(kt.kesin===false?' — gün içi veri, kapanışta kesinleşir':'')
  :kt.seri+' gündür taban, dün gün boyu işlem neredeyse yoktu (kilitli)';
 return '🔒 kilitli taban: '+m+'. '+KILIT_NOT;
}
function uzamaMetin(u){
 if(!u)return '';var ne=[];
 if(u.dipkat&&u.dipkat>=5)ne.push('52 hafta dibinin '+String(u.dipkat).replace('.',',')+' katı');
 if(u.r6!=null&&u.r6>=200)ne.push('6 ayda +%'+u.r6);
 return '⚠️ Çok yükselmiş hisse ('+ne.join(', ')+'): '+UZAMA_NOT;
}
// --- 📏 sıkı çizgi (sinyal.siki_cizgi; tarama.SIKI_NOT / siki_alt / siki_metni / _sayi_tr ile aynı) — BİLGİ, kural değil
var SIKI_NOT='Çok yükselmiş hissede bu seviyenin altında kapanış geçmişte bazen çöküşün habercisi oldu: benzer durumlarda sonraki 20 günde ~%5\'inde taban serisi (4+ taban) geldi, ~%11\'inde fiyat %25+ düştü; ama ~%20\'sinde %25+ yükselmeye devam etti. Kural değil, bilgi; asıl çıkış iz stop.';
function sayiTr(x){var a=Math.abs(x).toFixed(2).replace(/0+$/,'').replace(/\.$/,''),p=a.split('.');return (x<0?'−':'')+p[0].replace(/\B(?=(\d{3})+(?!\d))/g,'.')+(p[1]?','+p[1]:'');}
function gunAy(t){return t.slice(8,10)+'.'+t.slice(5,7);}
function scAlt(sc){if(!sc)return [];var a=(sc.alt||[]).slice();if(a.length&&sc.bugun&&sc.kesin===false)a.pop();return a;}
function scMetin(sc){
 if(!sc)return '';var sv=sayiTr(sc.s)+' TL',a=scAlt(sc),simdi=!!(sc.bugun&&sc.kesin===false),al=sc.alt||[],m;
 m=a.length?'📏 Sıkı çizginin altında kapandı ('+a.map(gunAy).join(', ')+'). Sıkı çizgi şu an '+sv+' (kijun).':'📏 Sıkı çizgi: '+sv+' (kijun).';
 if(simdi)m+=' Fiyat şu an'+(a.length?' da':'')+' çizginin altında (gün içi; kapanışta kesinleşir).';
 if(sc.ilk&&a.indexOf(sc.ilk)<0&&!(simdi&&sc.ilk===al[al.length-1]))m+=' Daha önce'+(a.length||simdi?' de':'')+' altında kapanmıştı (ilk kez '+gunAy(sc.ilk)+').';
 if(sc.u)m+=' Hisse 🚀 girişinden sonra aşırı yükseldi (ilk kez '+gunAy(sc.u)+': 52 hafta dibinin 5+ katı ya da 6 ayda 3+ kat).';
 return m+' '+SIKI_NOT;
}
function thDalga(th){return !!(th&&th.seviye==='sisme'&&(th.yuk20||0)<0);}  // 🎈 tetiklendi ama 20 günde hâlâ eksi: çöküş sonrası tepki tavanları
// --- 💬 Sade anlat · 🔎 Neden yükseldi/düştü? · önerilen alarmlar — hepsi cihazda, panodaki veriden (yapay zekâ yok).
// Eşikler (bt/hareket, 299 hisse 2021-26): BIST 100'den ayrışma 1/5/20 günde ≥ 4/10/20 puan → günlerin ~%12-13'ü;
// hacim ortalamanın ≥ 1,5 katı → ~%12,5'i. Ayrışan günlerin ~%7-8'inde aynı sektör de aynı yönde gitmiş (sektörel).
var HR_ESIK={1:4,5:10,20:20},HR_HACIM=1.5,HR_HACIM2=2.5;   // tarama.HR_ESIK / HR_HACIM ile aynı
var OD_NOT='Geçmiş veride (2021-26, 299 hisse) bu durumdaki hisselerin sonraki 20 günde ancak ~%38\'i endeksi geçti (normalde ~%46); 2022-23 düşük faiz döneminde fark görülmedi. Kesin değil, bilgi.';
function pyz(x){return (x>=0?'+':'−')+'%'+Math.abs(x).toFixed(1).replace('.',',');}
function kat(x){return x.toFixed(1).replace('.',',');}
function hEsc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function spGetiri(sp,t0,t1){  // grafik verisinde t0 → t1 kapanış değişimi (%) ya da null
 if(!sp||!sp.t||!sp.c)return null;var i0=sp.t.indexOf(t0),i1=sp.t.indexOf(t1);
 if(i0<0||i1<0||sp.c[i0]==null||sp.c[i1]==null||!sp.c[i0])return null;return (sp.c[i1]/sp.c[i0]-1)*100;}
var _GRUP=null;
function grupAd(d){  // sektör kıyas grubu: tarama.kiyas_gruplari (benzer küçük endüstriler birleşik, en az 4 hisse) — yoksa kıyas yok
 return d.kg?['kg',d.kg]:null;}
function hareket(k,d){  // son 1/5/20 günlük hareketin bileşenleri: hisse, BIST 100, sektör, hacim, tavan/taban
 var sp=d.spark;if(!sp||!sp.c||sp.c.length<2)return null;
 var n=sp.c.length,t1=sp.t[n-1],g=grupAd(d),xuTamam=!!(XU&&XU.t&&XU.t[XU.t.length-1]>=t1),out={t1:t1,ufuk:[]};
 [1,5,20].forEach(function(u,j){
  if(n<=u)return;var t0=sp.t[n-1-u],r=spGetiri(sp,t0,t1);if(r==null)return;
  var x0=xuTamam?xuDeger(t0):null,x1=xuTamam?xuDeger(t1):null,xu=(x0&&x1)?(x1/x0-1)*100:null;
  var sek=null,sn=0,top=0;
  if(g)Object.keys(DATA).forEach(function(k2){if(k2===k)return;var y=DATA[k2];
   if(y.kg!==g[1])return;var rr=spGetiri(y.spark,t0,t1);if(rr==null)return;top+=rr;sn++;});
  if(sn>=2)sek=top/sn;
  var hk=(d.hv&&d.hv[j]!=null)?d.hv[j]:null,tavan=0,taban=0;
  for(var i=n-u;i<n;i++){if(sp.c[i]==null||sp.c[i-1]==null)continue;var ch=sp.c[i]/sp.c[i-1]-1;if(ch>=0.095)tavan++;if(ch<=-0.095)taban++;}
  var T=HR_ESIK[u],fark=xu==null?null:r-xu,tur;
  if(fark==null)tur='?';
  else if(Math.abs(fark)<T)tur='piyasa';
  else if(sek!=null&&Math.abs(r-sek)<T/2&&Math.abs(sek-xu)>=T/2&&(sek-xu)*fark>0)tur='sektor';
  else tur='ozel';
  out.ufuk.push({u:u,t0:t0,r:r,xu:xu,fark:fark,sek:sek,sn:sn,grup:g,hk:hk,tavan:tavan,taban:taban,tur:tur,
   dikkat:(fark!=null&&Math.abs(fark)>=T)||Math.abs(r)>=T||(hk!=null&&hk>=HR_HACIM)});
 });
 return out;}
function _gunFark(a,b){return Math.round((new Date(b.slice(0,10))-new Date(a.slice(0,10)))/864e5);}
function nedenHtml(k,d){
 var h=hareket(k,d);if(!h||!h.ufuk.length)return '';
 var sat=[],sakin=[],ek=[];
 h.ufuk.forEach(function(x){
  var ad=x.u===1?'son gün':'son '+x.u+' gün';
  if(!x.dikkat){sakin.push(ad+' '+pyz(x.r));return;}
  var T=HR_ESIK[x.u],gad=x.grup?hEsc(x.grup[1]):'',s='<b>'+(x.u===1?'Son gün':'Son '+x.u+' gün')+': '+pyz(x.r)+'</b>'+(x.u===1&&x.tavan?' (tavan)':'')+(x.u===1&&x.taban?' (taban)':'');
  if(x.xu!=null)s+=' · BIST 100 '+pyz(x.xu);
  if(x.tur==='piyasa')s+=Math.abs(x.r)>=T?' → <b>piyasayla birlikte</b> (endeks de benzer hareket etti).':' → endeksle uyumlu.';
  else if(x.tur==='sektor')s+=' → <b>sektörel</b>: benzer '+x.sn+' hissenin ('+gad+') ortalaması '+pyz(x.sek)+'.';
  else if(x.tur==='ozel')s+=' → <b>hisseye özel</b>: endeksten '+Math.abs(x.fark).toFixed(0)+' puan '+(x.fark>0?'daha iyi':'daha kötü')+(x.sek!=null?'; benzer hisseler ('+gad+', '+x.sn+' hisse) '+pyz(x.sek):'; karşılaştırılacak yeterli benzer hisse yok')+'.';
  if(x.hk!=null&&x.hk>=HR_HACIM)s+=' Hacim '+(x.u===1?'önceki 20 günün':'önceki 60 günün')+' ortalamasının <b>'+kat(x.hk)+' katı</b>'+(x.hk>=HR_HACIM2?' (çok yüksek)':'')+'.';
  else if(x.u>1&&x.hk!=null&&x.hk<0.7&&Math.abs(x.r)>=T)s+=' Hacim ortalamanın altında (ilgi sınırlı).';
  sat.push(s);
 });
 var u20=h.ufuk[h.ufuk.length-1],t0=u20.t0;
 if(u20.u>1&&(u20.tavan||u20.taban))ek.push('Son '+u20.u+' günde '+[u20.tavan?u20.tavan+' tavan':'',u20.taban?u20.taban+' taban':''].filter(Boolean).join(', ')+' (günlük ~%10 sınır).');
 var kp=(d.kap||[]).filter(function(b){return b.t.slice(0,10)>t0;}),ga=kp.filter(function(b){return /Geri Al/i.test(b.konu);}).length;
 kp.filter(function(b){return !/Geri Al/i.test(b.konu);}).slice(0,3).forEach(function(b){
  var gf=_gunFark(b.t,h.t1),oz=(b.ozet&&b.ozet!==b.konu)?' — '+hEsc(b.ozet.length>110?b.ozet.slice(0,110)+'…':b.ozet):'';
  ek.push('📰 '+(gf<=0?'Bugün':gf+' gün önce')+' ('+b.t.slice(8,10)+'.'+b.t.slice(5,7)+') KAP: <a href="https://www.kap.org.tr/tr/Bildirim/'+b.id+'" target="_blank" rel="noopener">'+hEsc(b.konu)+'</a>'+oz);});
 if(ga)ek.push('📰 Bu dönemde '+ga+' geri alım (şirketin kendi hissesini alması) bildirimi var.');
 if(d.bolunme&&d.bolunme>t0)ek.push('✂️ '+d.bolunme+' günü bedelsiz/bölünme: yüzdeler düzeltilmiş fiyatla hesaplandı.');
 var c=(d.spark||{}).c||[],n=c.length,son=c[n-1],onc=c.slice(0,n-1).filter(function(v){return v!=null;});
 if(onc.length>=60&&son>=Math.max.apply(null,onc))ek.push('🔝 Fiyat grafikteki son 6 ayın en yüksek kapanışında.');
 else if(onc.length>=60&&son<=Math.min.apply(null,onc))ek.push('🔻 Fiyat grafikteki son 6 ayın en düşük kapanışında.');
 else if(onc.length>=20){var s20=onc.slice(-20);if(son>Math.max.apply(null,s20))ek.push('↗️ Son 20 günün en yüksek kapanışı aşıldı'+((d.tk||{}).bugun?' (🚀 v3 AL kuralı bugün çalıştı).':'.'));
  else if(son<Math.min.apply(null,s20))ek.push('↘️ Son 20 günün en düşük kapanışının altına inildi.');}
 if(d.sd&&d.sd.tepki&&d.sd.destek)ek.push('🔵 Fiyat '+d.sd.destek.fiyat+' TL desteğine inip yukarı döndü.');
 if(d.sd&&d.sd.yaklas&&d.sd.direnc)ek.push('🟠 Fiyat '+d.sd.direnc.fiyat+' TL direncine yaklaştı.');
 // iz stop satırı: portföydeyse portföyün kullandığı iz (analiz_et: son giriş v3 ise v3'ünkü, değilse göstergeninki — pozPlan ile aynı);
 // değilse sadece 🚀 v3 işleminin iz stop çıkışı (Sinyal geçmişi tablosuyla aynı tarih)
 var pzb=pfBirlesik(k),tki=d.tk||{},izt=null;
 if(pzb&&!pzb.uzun){if(d.iz&&d.iz.cikti)izt=d.iz.cikis_tarih;}
 else if(!pzb&&tki.durum==='CIKTI')izt=tki.cikis_tarih;
 if(izt&&izt>t0)ek.push('📍 '+izt+' günü '+(pzb?'pozisyonunun':'🚀 v3 işleminin')+' iz stop\'u kırıldı.');
 var th=d.tahta||{};if(thDalga(th))ek.push('🎈 Sert tavan-taban dalgalanması var (yukarıdaki kutu).');else if(th.seviye==='sisme')ek.push('🎈 Şişme uyarısı var (yukarıdaki kutu).');else if(th.seviye==='dagitim')ek.push('⚠️ Dağıtım işareti var (yukarıdaki kutu).');
 if(d.tuzak)ek.push('🪤 Düşen trend kırılımı tuzak riski var (yukarıdaki kutu).');
 var x='<div class="bilkutu nedenkutu"><div class="gbas">🔎 Neden yükseldi / düştü?</div>';
 var xs=h.ufuk.map(function(u){return u.xu==null?'':(u.u===1?'son gün ':u.u+' gün ')+pyz(u.xu);}).filter(Boolean).join(', ');
 if(!sat.length&&!ek.length)return x+'<div>'+sakin.join(', ').replace(/^s/,'S')+(xs?' (BIST 100: '+xs+')':'')+' — endeksle uyumlu, dikkat çekici bir hareket yok.</div></div>';
 sat.forEach(function(s){x+='<div class="ns">'+s+'</div>';});
 if(sakin.length)x+='<div class="ns sgun">'+sakin.join(', ').replace(/^s/,'S')+': endeksle uyumlu, dikkat çekici değil.</div>';
 if(ek.length)x+='<div class="ns" style="margin-top:6px"><b>Aynı dönemde:</b></div>'+ek.map(function(s){return '<div class="ns">• '+s+'</div>';}).join('');
 var ozelH=h.ufuk.some(function(u){return u.dikkat&&u.tur==='ozel'&&u.r>0&&u.hk!=null&&u.hk>=HR_HACIM;});
 return x+'<div class="pk sgun">Bu kutu aynı dönemde olanları yan yana koyar; hareketin sebebini bilemez.'+(ozelH?' Geçmiş veride (2021-26, 299 hisse) hisseye özel, hacimli yükselişlerden sonraki 20 gün, rastgele bir günden belirgin farklı gitmedi — tek başına alım/satım işareti değildir.':'')+
  (d.od?' 🔻 Hisseye özel hacimli düşüş: '+OD_NOT:'')+'</div></div>';
}
function pfBirlesik(k){  // portföyde aynı hisse birden çok satırsa toplam adet + ağırlıklı maliyet
 var p=pfOku().filter(function(x){return x.kod===k;});if(!p.length)return null;
 var ad=0,top=0;p.forEach(function(x){ad+=x.adet;top+=x.adet*x.maliyet;});
 return {adet:ad,maliyet:top/ad,uzun:p.some(function(x){return x.uzun;})};}
function sadeHtml(k,d){
 if(d.fiyat==null)return '';
 var sp=d.spark||{},c=sp.c||[],n=c.length,f=d.fiyat,u=d.uv||{},s50=u.sma50,cm=[];
 var r60=(n>60&&c[n-61])?(f/c[n-61]-1)*100:null,r5=(n>5&&c[n-6])?(f/c[n-6]-1)*100:null;
 // (a) uzun vadeli yön — 📉 trend aşağı uyarısıyla aynı kural (fiyat < düşen 200 günlük ortalama)
 var o200='200 günlük ortalamanın (son ~10 ayın ortalama fiyatı)',o50='50 günlük ortalamanın (son ~2,5 ay)';
 var cok60=r60!=null&&r60<=-50;
 if(d.patlak||cok60)cm.push('💥 <b>Genel yön: çöküş.</b> '+(d.patlak?'Son 15 günde '+d.taban15+' kez taban (günlük ~%10 düşüş)':'')+(d.patlak&&cok60?', ':'')+(cok60?(d.patlak?'son':'Son')+' 3 ayda '+pyz(r60):'')+
  '. Bu hızda düşüşte ortalamalara dayalı yön okuması (yükseliş/düşüş trendi) anlamını yitirir.');
 else if(d.trend&&s50&&f>s50)cm.push('📈 <b>Genel yön: yükseliş.</b> Fiyat hem son ~2,5 ayın hem son ~10 ayın ortalama fiyatının (50 ve 200 günlük ortalama) üstünde; uzun vadeli ortalama da yükseliyor.');
 else if(d.trend)cm.push('📈 <b>Genel yön: yükseliş, ama son haftalarda geri çekiliyor.</b> Fiyat '+o200+' üstünde, '+o50+' altına indi.');
 else if(d.trend_asagi&&!(s50&&f>s50))cm.push('📉 <b>Genel yön: düşüş.</b> Fiyat hem son ~2,5 ayın hem son ~10 ayın ortalama fiyatının (50 ve 200 günlük ortalama) altında; uzun vadeli ortalama da düşüyor.');
 else if(d.trend_asagi)cm.push('📉 <b>Genel yön: düşüş, ama son haftalarda toparlanıyor.</b> Fiyat '+o50+' üstüne çıktı, düşen '+o200+' hâlâ altında.');
 else if(r60!=null&&r60>=10)cm.push('↗️ <b>Son 3 ayda yükseliyor</b> ('+pyz(r60)+'), ama uzun vadeli yön henüz net değil.');
 else if(r60!=null&&r60<=-10)cm.push('↘️ <b>Son 3 ayda düşüyor</b> ('+pyz(r60)+'), ama uzun vadeli yön henüz net değil.');
 else cm.push('➡️ <b>Fiyat yatay seyrediyor</b>'+(r60!=null?' (son 3 ayda '+pyz(r60)+')':'')+': belirgin bir yön yok.');
 // (b) kısa vade: alıcılar mı satıcılar mı (💪 güç puanı + gösterge oylamasıyla çelişmeyecek şekilde)
 var gp=d.guc?d.guc.puan:null,gt=d.guc?d.guc.toplam:7,hv5=d.hv?d.hv[1]:null,ak;
 if(gp!=null&&gp>=5&&d.sinyal!=='SAT')ak='💪 <b>Kısa vadede alıcılar güçlü:</b> '+gt+' göstergeden '+gp+' tanesi olumlu';
 else if(gp!=null&&gp<=2&&d.sinyal!=='AL')ak='🔻 <b>Kısa vadede satıcılar güçlü:</b> '+(gp?gt+' göstergeden sadece '+gp+' tanesi olumlu':gt+' göstergenin hiçbiri olumlu değil');
 else ak='⚖️ <b>Kısa vadede alıcılar ve satıcılar dengede:</b> göstergeler karışık'+(gp!=null?' ('+gt+' göstergeden '+gp+' tanesi olumlu)':'');
 if(hv5!=null&&hv5>=HR_HACIM&&r5!=null&&Math.abs(r5)>=3)ak+='; son 5 günde hacim ortalamanın '+kat(hv5)+' katıyken fiyat '+(r5>0?'yükseldi (alım ilgisi)':'düştü (satış baskısı)');
 cm.push(ak+'.');
 // (c) takip edilecek tek seviye: portföydeyse iz stop / karar çizgisi, değilse en yakın destek/direnç ya da kırılım seviyesi
 var p=pfBirlesik(k),sv=null,t=d.tk||{};
 if(p){var pl=pozPlan(d,p);
  if(pl.uzun){if(pl.karar)sv=pl.kararAsildi?'🧭 <b>Fiyat karar çizgisinin ('+pl.karar+' TL) altında.</b> Karar çizgisi, uzun vadeli pozisyonun için ana desteğin biraz altıdır; altında kapanış pozisyonu yeniden düşünme noktası.'
    :'🧭 <b>Senin için takip edilecek seviye: karar çizgisi '+pl.karar+' TL</b> ('+pyz(pl.kararUzak)+'). Bu, ana desteğin (geçmişte düşüşün durduğu fiyat) biraz altıdır; altında kapanış, desteğin kırıldığını gösterir.';}
  else if(pl.izCikti)sv='📍 <b>'+(pl.kilitCik?'🔐 Kâr kilidi stop\'u ':'İz stop ')+pl.izCikti+' tarihinde kırıldı.</b> İz stop, aldıktan sonraki en yüksek kapanışın %20 altıdır'+(KK?' (kapanışta +%'+kkSay(KK[0])+' görüldüyse en az alış +%'+kkSay(KK[1])+')':'')+'; sistemin kuralına göre çıkış zamanı geçti.';
  else if(pl.stop)sv=pl.asildi?'📍 <b>Fiyat çıkış seviyesinin ('+pl.stop+' TL) altında</b> — sistemin kuralına göre çıkış zamanı.'
    :'📍 <b>Senin için takip edilecek seviye: '+(pl.iz?'iz stop':'stop')+' '+pl.stop+' TL</b> ('+pyz(pl.stopUzak)+'). '+(pl.iz?'İz stop, aldıktan sonraki en yüksek kapanışın %20 altıdır ve fiyat yükseldikçe yukarı taşınır'+(pl.kilit?' (şu an 🔐 kâr kilidi devrede: en az alış +%'+kkSay(KK?KK[1]:5)+')':'')+'; ':'')+'kapanış bunun altına inerse sistemin kuralı "çık" der.';
 }
 if(!sv){
  var ds=d.sd&&d.sd.destek,dr=d.sd&&d.sd.direnc;
  if(t.sablon&&t.durum!=='AL'&&t.kirilim_seviye&&t.kirilima_uzak!=null&&t.kirilima_uzak>0&&t.kirilima_uzak<=3)
   sv='👀 <b>Takip edilecek seviye: '+t.kirilim_seviye+' TL</b> ('+pyz(t.kirilima_uzak)+' yukarıda): son 20 günün en yüksek kapanışı. Kapanış bunun üstüne çıkarsa sistemin 🚀 AL kuralı (trend kırılımı) çalışır'+(tkEksik(t)?' — ama şu an AL sayılmaz: '+tkEksik(t)+'.':'.');
  else{var ud=ds?Math.abs(ds.uzaklik):1e9,ur=dr?Math.abs(dr.uzaklik):1e9;
   if(ds&&ds.fiyat>=f){var kc=kararCizgisi(d);sv='🔵 <b>Fiyat '+ds.fiyat+' TL desteğinin hafif altına sarktı.</b> Destek, geçmişte düşüşün durduğu ve alıcıların geldiği fiyattır. Takip edilecek seviye: <b>'+kc+' TL</b> (desteğin biraz altı, '+pyz((kc/f-1)*100)+'); bunun altında kapanış desteğin kırıldığını gösterir.';}
   else if(Math.min(ud,ur)>15)sv='Fiyatın yakınında (±%15) belirgin bir destek ya da direnç yok'+(ds||dr?'; en yakını '+(ds&&ud<=ur?'destek '+ds.fiyat+' TL ('+pyz(ds.uzaklik)+')':'direnç '+dr.fiyat+' TL ('+pyz(dr.uzaklik)+')'):'')+'. Destek geçmişte düşüşün, direnç yükselişin durduğu fiyattır.';
   else if(ds&&ud<=ur)sv='🔵 <b>Takip edilecek seviye: destek '+ds.fiyat+' TL</b> ('+pyz(ds.uzaklik)+'). Destek, geçmişte düşüşün durduğu ve alıcıların geldiği fiyattır'+(ds.test>=2?' (bu bölge '+ds.test+' kez denendi)':'')+'; altında kapanış düşüşün sürebileceğini gösterir.';
   else if(dr)sv='🟠 <b>Takip edilecek seviye: direnç '+dr.fiyat+' TL</b> ('+pyz(dr.uzaklik)+'). Direnç, geçmişte yükselişin durduğu ve satıcıların çıktığı fiyattır; kapanışla aşılırsa yükseliş hızlanabilir, aşılamazsa geri dönebilir.';
   else sv='Son 6 ayda fiyatın yakınında belirgin bir destek ya da direnç yok.';}
 }
 cm.push(sv);
 // (d) en önemli tek uyarı
 var th=d.tahta||{},b=d.bilanco||{},tm=d.temettu||{},uy=null;
 // öncelik: 🔒 kilitli taban ve taban serisi en üstte (satış emrinin gerçekleşmeyebileceği / çöküş hâli), sonra 🎈
 if(d.kt)uy='🔒 <b>En önemli uyarı — kilitli taban:</b> '+ktMetin(d.kt).replace('🔒 kilitli taban: ','');
 else if(d.patlak)uy='⚠ <b>En önemli uyarı — taban serisi:</b> son 15 günde '+d.taban15+' kez ~%10 düştü (çöküş tipi hareket).'+(th.seviye==='sisme'?' Arada gelen tavanlar 🎈 işaretini de tetikledi: sert tavan-taban dalgalanması.':'');
 else if(thDalga(th))uy='🎈 <b>En önemli uyarı — sert tavan-taban dalgalanması:</b> düşüşten sonra kısa sürede çok tavan / çok oynak fiyat (20 günde hâlâ '+pyz(th.yuk20)+'); geçmişte bu işaretteki hisselerin ~%15-19\'u sonraki 20 günde %25+ düştü (normalde %2).';
 else if(th.seviye==='sisme')uy='🎈 <b>En önemli uyarı — şişme riski:</b> kısa sürede çok yükseldi; geçmişte bu durumdaki hisselerin ~%15-19\'u sonraki 20 günde %25+ düştü (normalde %2).';
 else if(th.seviye==='dagitim')uy='⚠️ <b>En önemli uyarı — dağıtım işareti:</b> hacim artarken fiyat son zirvesinden geriliyor; büyük satıcı elindekini satıyor olabilir.';
 else if(d.mn)uy='⚠️ <b>En önemli uyarı — manipülasyon işareti:</b> '+d.mn.i.map(mnIsaret).join('; ')+'. Bu tür hisselerde kilitli tabanda satamama riski yüksek (alım yasağı değil).';
 else if(d.tuzak)uy='🪤 <b>En önemli uyarı — tuzak riski:</b> dipteki hisse düşen trendi yukarı kırdı; geçmişte bu kırılımların yarısından fazlası 15 günde geri düştü.';
 else if(d.od)uy='🔻 <b>En önemli uyarı — hisseye özel hacimli düşüş:</b> son '+d.od.u+' günde '+pyz(d.od.r)+' (BIST 100 '+pyz(d.od.xu)+', hacim ortalamanın '+kat(d.od.hk)+' katı), benzer hisseler bu kadar düşmedi. '+OD_NOT;
 else if(b.kalan_gun!=null&&b.kalan_gun>=0&&b.kalan_gun<=7)uy='📅 <b>'+(b.kalan_gun?b.kalan_gun+' gün sonra':'Bugün')+' bilanço</b> açıklanabilir: o gün fiyat sert oynayabilir.';
 else if(tm.ex_kalan!=null&&tm.ex_kalan>=0&&tm.ex_kalan<=7)uy='💰 <b>'+(tm.ex_kalan?tm.ex_kalan+' gün sonra':'Bugün')+' temettü hak kullanımı:</b> o sabah fiyat temettü kadar düşük açılır (kayıp değil, ödeme).';
 else if(d.bolunme&&(Date.now()-new Date(d.bolunme).getTime())<30*864e5)uy='✂️ <b>'+d.bolunme+' günü bedelsiz/bölünme</b> oldu: grafik düzeltildi'+(p?'; maliyetini aracı kurumdaki yeni maliyetle güncelle.':'.');
 else if(d.oynak)uy='⚡ <b>Uyarı — çok oynak:</b> son 60 günde günlük oynaklık %'+d.vol60+'; fiyat kısa sürede sert gidip gelebilir.';
 if(uy)cm.push(uy);
 return '<div class="sade"><div class="gbas">💬 Sade anlat</div>'+cm.map(function(s){return '<div class="ss">'+s+'</div>';}).join('')+'<div class="pk sgun">Panodaki verilerden kurallarla yazılır; yatırım tavsiyesi değildir.</div></div>';
}
function alOneriler(k,d){  // önerilen alarmlar: portföydeyse iz stop / karar çizgisi, en yakın destek ve direnç, 🚀 kırılım seviyesi
 var o=[],sd=d.sd||{},f=d.fiyat,p=pfBirlesik(k),t=d.tk||{};if(f==null)return o;
 if(p){var pl=pozPlan(d,p);
  if(pl.uzun){if(pl.karar&&!pl.kararAsildi)o.push({yon:'alt',fiyat:pl.karar,not:'karar çizgisi'});}
  else if(pl.stop&&!pl.asildi&&!pl.izCikti)o.push({yon:'alt',fiyat:pl.stop,not:pl.iz?'iz stop':'stop'});}
 if(sd.destek&&sd.destek.fiyat<f)o.push({yon:'alt',fiyat:sd.destek.fiyat,not:'destek'});
 else if(sd.destek){var kc=kararCizgisi(d);if(kc&&kc<f)o.push({yon:'alt',fiyat:kc,not:'destek kırılımı (karar çizgisi)'});}
 if(sd.direnc&&sd.direnc.fiyat>f)o.push({yon:'ust',fiyat:sd.direnc.fiyat,not:'direnç'});
 if(t.sablon&&t.durum!=='AL'&&t.kirilim_seviye&&t.kirilim_seviye>f)o.push({yon:'ust',fiyat:t.kirilim_seviye,not:'kırılım (🚀 AL) seviyesi'});
 return o.filter(function(x,i){return o.findIndex(function(y){return y.yon===x.yon&&Math.abs(y.fiyat-x.fiyat)<0.005;})===i;});
}
function alAile(n){n=String(n||'');return /^destek/.test(n)?'destek':(/stop$/.test(n)?'stop':n);}
var AL_NOTLAR=['destek','direnç','stop','karar çizgisi','kırılım (🚀 AL) seviyesi'];   // önerilen alarm aileleri
function alEski(k,d,x){  // sadece önerilenden kurulmuş (notlu) alarm: aynı aile + yönde güncel öneri farklı seviyedeyse / yoksa eskimiş
 var ai=alAile(x.not);if(!x.not||AL_NOTLAR.indexOf(ai)<0)return null;
 var o=alOneriler(k,d).filter(function(y){return alAile(y.not)===ai&&y.yon===x.yon;})[0];
 if(o&&Math.abs(o.fiyat-x.fiyat)<0.005)return null;
 return {yeni:o||null};}
function alGuncelle(k,i){  // eskimiş alarmı güncel seviyeye taşı (güncel seviye zaten kuruluysa eskisi silinir)
 var d=DATA[k],a=alOku(),x=a[i];if(!d||!x)return;var e=alEski(k,d,x);if(!e||!e.yeni)return;
 if(a.some(function(y,j){return j!==i&&y.kod===k&&y.yon===e.yeni.yon&&Math.abs(y.fiyat-e.yeni.fiyat)<0.005;}))a.splice(i,1);
 else a[i]={kod:k,yon:e.yeni.yon,fiyat:e.yeni.fiyat,not:e.yeni.not};
 alYaz(a);ac(k);}
function alVar(k,yon,f){return alOku().some(function(x){return x.kod===k&&x.yon===yon&&Math.abs(x.fiyat-f)<0.005;});}
function alOneriKur(k,i){  // i: öneri sırası; 'hepsi' → kurulmamış tüm öneriler (aynı seviyeye ikinci alarm kurulmaz)
 var d=DATA[k];if(!d)return;var o=alOneriler(k,d),a=alOku();
 (i==='hepsi'?o:[o[i]]).forEach(function(x){if(x&&!a.some(function(y){return y.kod===k&&y.yon===x.yon&&Math.abs(y.fiyat-x.fiyat)<0.005;}))a.push({kod:k,yon:x.yon,fiyat:x.fiyat,not:x.not});});
 alYaz(a);ac(k);
}
function ac(k){
 const d=DATA[k];if(!d)return;
 const dcls=(d.degisim||0)>=0?'pos':'neg';const dtxt=d.degisim==null?'—':((d.degisim>=0?'+':'')+d.degisim+'%');
 const pill='<span class="pill '+sinyalCls(d)+'">'+d.sinyal+'</span>'+(d.guclu?' <span class="yildiz">AL+</span>':'');
 const m=(l,v)=>'<div class="m"><div class="l">'+l+'</div><div class="v">'+(v==null?'—':v)+'</div></div>';
 const lot=(d.lot&&d.sinyal==='AL')?d.lot+' lot':'—';
 const tv='https://www.tradingview.com/chart/?symbol=BIST%3A'+k;
 let gost='';
 (d.detay||[]).forEach(x=>{const cls=x.sinyal==='AL'?'al':(x.sinyal==='SAT'?'sat':'notr');
   gost+='<div class="gi"><span class="pill '+cls+'">'+x.sinyal+'</span><div class="gt"><b>'+x.ad+'</b><span>'+x.aciklama+'</span></div></div>';});
 let ekh='';(d.ek||[]).forEach(e=>{ekh+='<span class="ekb"><b>'+e.ad+':</b> '+e.aciklama+'</span>';});
 const uyum=d.uyum?('<span class="uyroz">'+d.uyum+' gösterge AL</span>'):'';
 // zamanlama + çıkış kuralı
 let zaman='';
 if(d.sinyal_gun!=null){
   const sd=d.sinyal_degisim;const sdc=(sd||0)>=0?'pos':'neg';
   const sdt=sd==null?'':(' · başlangıçtan beri <span class="'+sdc+'">'+((sd>=0?'+':'')+sd+'%')+'</span>');
   const yenirz=(d.yeni&&d.sinyal==='AL')?' <span class="yeni">YENİ</span>':'';
   const nk=(d.sinyal==='NÖTR'&&d.notr_kaynak)?(' — <b>'+(d.notr_kaynak==='AL'?'AL\'den':'SAT\'tan')+' döndü</b>'):'';
   zaman='<div class="zaman"><div><b>'+d.sinyal+'</b> sinyali: '+d.sinyal_tarih+' ('+d.sinyal_gun+' gündür)'+nk+yenirz+sdt+'</div>';
   if(d.sinyal==='NÖTR'&&d.notr_kaynak==='AL')zaman+='<div class="cikis">Elindeyse tut: iz stop kırılırsa çık. Yeni alım için AL\'i bekle.</div>';
   if(d.sinyal==='NÖTR'&&d.notr_kaynak==='SAT')zaman+='<div class="cikis">Düşüş yavaşladı ama henüz alım sinyali değil; AL\'i bekle.</div>';
   if(d.sinyal==='AL'&&d.hacim_kat!=null)zaman+='<div class="cikis">'+(d.hacim_teyit?'📈 <b>Hacim teyitli</b>: ':'Hacim: ')+'AL günü hacmi 20 günlük ortalamanın <b>'+d.hacim_kat+' katı</b>'+(d.hacim_teyit?' — ilgi artmış (backtest\'te tek başına belirgin üstünlük sağlamadı).':' (teyit için 1,5 kat gerekir).')+'</div>';
   if(d.sinyal==='SAT')zaman+='<div class="cikis">ℹ️ Kısa vadeli SAT. Çıkış kuralı iz stop'+(d.iz&&!d.iz.cikti?' (<b>'+d.iz.stop+' TL</b>)':'')+'; elindeyse SAT tek başına "çık" demek değil.</div>';
   if(d.sinyal==='AL'){
     const gs=(d.giris_stop!=null?d.giris_stop:d.stop);
     const izs=(d.iz&&!d.iz.cikti)?d.iz.stop:Math.round(d.fiyat*0.8*100)/100;
     zaman+='<div class="cikis">ℹ️ Göstergeler (oylama) AL diyor — bilgi. <b>AL mesajı 🚀 trend kırılımında gelir</b> (aşağıdaki kutu). Elindeyse çıkış: kapanış <b>iz stop '+izs+' TL</b>\'nin altına inerse.'+
       ((d.hedef&&!pfOku().some(function(x){return x.kod===k;}))?' · Örnek hedef (2R, mekanik referans): <b>'+d.hedef+' TL</b>':'')+'</div>';
   }
   zaman+='</div>';
 }
 document.getElementById('modal').innerHTML=
 '<div class="mh"><div class="sol"><h2>'+k+'</h2>'+pill+uyum+' <button class="mfav" id="mfav" onclick="favDegis(\''+k+'\')">'+(favOku().indexOf(k)>=0?'⭐ Favorilerde':'☆ Favorilere ekle')+'</button></div><button class="kapa" onclick="kapat()">✕</button></div>'+
 '<div class="mfiyat">'+(d.fiyat!=null?d.fiyat+' TL':'')+' <span class="'+dcls+'">'+dtxt+'</span>'+
   (d.sektor?' <span class="sektorb">'+d.sektor+(d.endustri&&d.endustri!==d.sektor?' · '+d.endustri:'')+'</span>':'')+'</div>'+
 sadeHtml(k,d)+
 modalOzet(k,d)+
 (d.kt?'<div class="patlakkutu">'+ktMetin(d.kt).replace('🔒 kilitli taban:','🔒 <b>Kilitli taban:</b>')+' <span class="sgun">Tanım: üst üste 2 taban (≤ −%9), 2. gün gün içi fiyat aralığı ≤ %0,15 (alıcı yok), BIST 100 iki gün de −%4\'ten iyi. Piyasanın çöktüğü günde başlayan serileri yakalamaz. Bu hisseden AL mesajı gönderilmez.</span></div>':'')+
 (d.patlak?'<div class="patlakkutu">⚠ <b>Taban serisi:</b> son 15 günde '+d.taban15+' kez ~%10 düştü. Fon krizi tipi çöküş olabilir; bu hisseden AL mesajı gönderilmez.</div>':'')+
 (d.tuzak?'<div class="patlakkutu">🪤 <b>Düşen trend kırılımı — tuzak riski:</b> '+d.tuzak.tarih+' günü hisse düşük seviyedeyken %'+d.tuzak.gunluk+' yükselişle düşen trend çizgisini kırdı ('+d.tuzak.kirilim_fiyat+' TL). Grafikte "AL" gibi görünür ama tüm borsada 5 yılda bu kırılımların <b>%56\'sı 15 gün içinde %5+ geri düştü</b>; kırılımda alıp 60 gün tutmak aynı hisselerde rastgele bir günden kötü sonuç verdi. Hacimli ya da güçlü kapanışlı olması tuzağı ayırmıyor.'+(d.tuzak.geri_dondu?' <b>Şu an kırılım fiyatının %5+ altına döndü.</b>':'')+'</div>':'')+
 (d.mn?'<div class="patlakkutu">'+mnMetin(d.mn)+' <span class="sgun">İşaretler: son 120 günde 3+ art arda tavan · son 120 günde 60 günde 3 kat yükseliş · son 250 günde hisseye özel taban serisi (15 günde 4+ taban, piyasa çöküş günleri sayılmaz) · son 60 günde VBTS kararı · son 365 günde SPK tedbir kararı (KAP).</span></div>':'')+
 ((d.tahta&&d.tahta.seviye)?'<div class="patlakkutu">'+(thDalga(d.tahta)?'🎈 <b>Sert tavan-taban dalgalanması (düşüş sonrası):</b> '+d.tahta.neden.join('; ')+', ama 20 günde hâlâ '+pyz(d.tahta.yuk20)+'. Tahtacı şişirmesiyle aynı işaret (kısa sürede çok tavan / çok oynak fiyat); bu durumdaki hisselerin ~%15-19\'u sonraki 20 günde %25+ düştü (normalde %2). Yeni alım için AL mesajı gönderilmez.':d.tahta.seviye==='sisme'?'🎈 <b>Şişme riski (tahtacı uyarısı):</b> '+d.tahta.neden.join('; ')+'. 5 yıllık veride bu durumdaki hisselerin ~%15-19\'u sonraki 20 günde %25+ çakıldı (normalde %2). Yeni alım için AL mesajı gönderilmez; elindeyse iz stop\'u sıkı takip et.':'⚠️ <b>Dağıtım işareti:</b> '+d.tahta.neden[0]+'. Büyük satıcı (tahtacı) malı dağıtıyor olabilir; bu durumdakilerin ~%10\'u 20 günde %25+ düştü (normalde %2).')+'</div>':'')+
 (d.bolunme?'<div class="arzkutu">✂️ <b>Bedelsiz/bölünme:</b> '+d.bolunme+' tarihinde fiyat tek günde sınırın ötesinde değişti; grafik ve göstergeler buna göre düzeltildi. Portföyündeyse maliyetini aracı kurumdaki yeni maliyetle güncelle.</div>':'')+
 '<div class="grafik">'+tkSonHtml(d)+((d.spark&&d.spark.w&&d.spark.w.length)?'<div class="graralik"><button id="gra6a" class="grb'+(_grAralik==='6a'?' on':'')+'" onclick="grAralikSec(\''+k+'\',\'6a\')">6 ay</button><button id="gra1y" class="grb'+(_grAralik==='1y'?' on':'')+'" onclick="grAralikSec(\''+k+'\',\'1y\')">1 yıl</button></div>':'')+
   '<div id="grkutu">'+grafik(d.spark,d.sd,_grAralik,d.tkg)+'</div><div class="leg"><span class="c1">Fiyat</span><span class="c2">SMA20</span><span class="c3">SMA50</span><span class="c4">SuperTrend</span>'+
   (d.sd&&d.sd.destek?'<span class="c5">Destek</span>':'')+(d.sd&&d.sd.direnc?'<span class="c6">Direnç</span>':'')+
   '<span class="c7">İz stop</span><span class="lm" style="color:#1B7F4B">▲ AL (🚀)</span><span class="lm" style="color:#B4362E">▼ SAT (iz stop'+(KK?' / 🔐':'')+')</span></div></div>'+
 nedenHtml(k,d)+
 zaman+vadeHtml(k,d)+
 pozHtml(k,d)+tkHtml(d)+lotHtml(k,d)+tkGecmisHtml(d)+gucHtml(d)+uvHtml(d)+
 sdHtml(d)+
 '<div class="metr">'+m('RSI',d.rsi)+m('F/K',d.fk)+m('PD/DD',d.pddd)+m('FD/FAVÖK',d.favok)+m('İz stop',d.iz&&!d.iz.cikti?d.iz.stop:'—')+m('Öneri lot',lot)+'</div>'+
 btHtml(d)+bilHtml(d)+kapHtml(d)+arzHtml(d)+
 '<div class="gbas">Göstergeler</div><div class="gliste">'+gost+'</div>'+
 (ekh?'<div class="ekler">'+ekh+'</div>':'')+
 '<div class="yorum">'+(d.yorum||d.gerekce.join(' · '))+'</div>'+
 alarmHtml(k,d)+
 '<div class="btnler"><a class="btn p" href="'+tv+'" target="_blank" rel="noopener">TradingView\'de tam ekran ↗</a></div>';
 document.getElementById('ust').classList.add('acik');
 if(document.getElementById('lotsonuc'))lotHesap(k);
}
function kapat(){document.getElementById('ust').classList.remove('acik');_gr=null;}
document.addEventListener('keydown',e=>{if(e.key==='Escape')kapat();});

var PF_KEY='portfoyum_v1',GH_KEY='gh_anahtar_v1',GH_REPO=(function(){var h=location.hostname,p=location.pathname.split('/')[1];return /\.github\.io$/.test(h)&&p?h.split('.')[0]+'/'+p:'__REPO__';})(),pfDuzenlenen=-1;
function pfOku(){try{return JSON.parse(localStorage.getItem(PF_KEY))||[]}catch(e){return[]}}
function pfYazYerel(a){try{localStorage.setItem(PF_KEY,JSON.stringify(a))}catch(e){}}
function pfYaz(a){pfYazYerel(a);pfBulutYaz(a);}
function pfNot(t){var n=document.getElementById('pfnot');n.innerHTML=t||'';n.hidden=!t;}
function pfFormAc(i){
 pfDuzenlenen=(typeof i==='number')?i:-1;var p=pfDuzenlenen>=0?pfOku()[i]:null;
 document.getElementById('pfkod').value=p?p.kod:'';document.getElementById('pfkod').disabled=!!p;
 document.getElementById('pfadet').value=p?p.adet:'';document.getElementById('pfmal').value=p?p.maliyet:'';document.getElementById('pfuzun').checked=!!(p&&p.uzun);document.getElementById('pfalis').value=(p&&p.tarih)||'';
 document.getElementById('pfneden').value=p?(dfOku().p[p.kod]||''):'';
 document.getElementById('pfkaydetbtn').textContent=p?'Kaydet':'Ekle';
 document.getElementById('pfform').style.display='flex';pfNot('');
 document.getElementById(p?'pfadet':'pfkod').focus();
}
function pfFormKapat(){document.getElementById('pfform').style.display='none';pfDuzenlenen=-1;}
function pfKaydet(){
 var k=(document.getElementById('pfkod').value||'').trim().toUpperCase();
 var ad=parseFloat(document.getElementById('pfadet').value);
 var ma=parseFloat(document.getElementById('pfmal').value);
 if(!k||!(ad>0)||!(ma>0)){pfNot('Hisse kodu, adet ve maliyet gir.');return;}
 var a=pfOku(),not='';
 var uz=document.getElementById('pfuzun').checked;
 var ta=document.getElementById('pfalis').value||'',xb=null;
 if(ta){var xv=xuDeger(ta);if(xv==null){pfNot('Alış tarihi endeks verisinden eski ya da ileri bir tarih; tarihi boş bırakabilirsin.');return;}xb=ad*ma/xv;}
 if(pfDuzenlenen>=0){
  var e=a[pfDuzenlenen],ayni=e&&e.adet===ad&&e.maliyet===ma&&(e.tarih||'')===ta;
  a[pfDuzenlenen]={kod:k,adet:ad,maliyet:ma,uzun:uz};
  if(ta){a[pfDuzenlenen].tarih=ta;a[pfDuzenlenen].xu_birim=(ayni&&e.xu_birim)?e.xu_birim:xb;}  // birleşik alımların birimi korunur
  not=k+' güncellendi.';}
 else{
  var j=a.findIndex(function(p){return p.kod===k;});
  if(j>=0){  // aynı hisseye ekleme: adet toplanır, maliyet ağırlıklı ortalama
   var p=a[j],top=p.adet+ad,ort=(p.adet*p.maliyet+ad*ma)/top;
   a[j]={kod:k,adet:top,maliyet:Math.round(ort*100)/100,uzun:!!(p.uzun||uz)};
   if(p.xu_birim&&xb){a[j].xu_birim=p.xu_birim+xb;a[j].tarih=(p.tarih&&p.tarih<ta)?p.tarih:ta;}  // ilk alış tarihi gösterilir
   not=k+' mevcut pozisyona eklendi: toplam '+top+' adet, ortalama maliyet '+a[j].maliyet.toFixed(2)+' TL.';
  }else{var y={kod:k,adet:ad,maliyet:ma,uzun:uz};if(ta){y.tarih=ta;y.xu_birim=xb;}a.push(y);}
 }
 var nd=(document.getElementById('pfneden').value||'').trim().slice(0,500),dfo=dfOku();  // 'neden aldım' PORTFOY'a DEĞİL deftere (DEFTER) yazılır: Actions'a gitmez
 if(nd!==(dfo.p[k]||'')&&(nd||pfDuzenlenen>=0)){if(nd)dfo.p[k]=nd;else delete dfo.p[k];dfYaz(dfo);}
 pfYaz(a);pfFormKapat();pfRender();pfNot(not);
}
function pfSil(i){var a=pfOku(),k=(a[i]||{}).kod;a.splice(i,1);pfYaz(a);dfPlanTemizle(k,a);pfRender();pfNot('');}  // kayıt tutmaz (yanlış girilen satır için)

// --- GitHub eşitleme: portföy repo'nun PORTFOY değişkenine yazılır, tarama (Telegram) oradan okur ---
function ghAnahtar(){try{return localStorage.getItem(GH_KEY)||''}catch(e){return''}}
function ghIstek(yontem,yol,govde){
 return fetch('https://api.github.com/repos/'+GH_REPO+yol,{method:yontem,headers:{'Authorization':'Bearer '+ghAnahtar(),
  'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'},body:govde?JSON.stringify(govde):undefined});
}
function pfBulutDurum(d,kod){
 var el=document.getElementById('pfbulut'),bag=' · <a href="#" onclick="ghKurulum();return false">Telegram\'a bağla</a>';
 var yetki=(kod===401||kod===403||kod===404);
 var t={yerel:'Bu cihazda saklanıyor; Telegram görmüyor'+bag,kaydediliyor:'☁ Kaydediliyor…',
  ok:'☁ Telegram ile eşit',
  hata:'⚠ GitHub\'a kaydedilemedi'+(kod?' ('+kod+')':'')+(yetki?' — anahtar geçersiz ya da yetkisi eksik'+bag:' — sonra tekrar dene')}[d];
 el.innerHTML=t;el.className='pfbulut '+d;
}
function pfBulutYaz(a){
 if(!ghAnahtar()){pfBulutDurum('yerel');return Promise.resolve(false);}
 var v={name:'PORTFOY',value:JSON.stringify(a)};pfBulutDurum('kaydediliyor');
 return ghIstek('PATCH','/actions/variables/PORTFOY',v)
  .then(function(r){return r.status===404?ghIstek('POST','/actions/variables',v):r;})
  .then(function(r){pfBulutDurum(r.ok?'ok':'hata',r.ok?0:r.status);return r.ok;})
  .catch(function(){pfBulutDurum('hata');return false;});
}
function pfBulutOku(){  // GitHub'daki portföy doluysa o esas alınır (başka cihazda yapılan değişiklikler gelsin)
 if(!ghAnahtar()){pfBulutDurum('yerel');return Promise.resolve(false);}
 pfBulutDurum('kaydediliyor');
 return ghIstek('GET','/actions/variables/PORTFOY').then(function(r){
  if(r.status===404){return pfBulutYaz(pfOku());}
  if(!r.ok){pfBulutDurum('hata',r.status);return false;}
  return r.json().then(function(j){
   var a=[];try{a=JSON.parse(j.value);}catch(e){}
   if(Array.isArray(a)&&a.length){pfYazYerel(a);pfRender();pfBulutDurum('ok');return true;}
   return pfBulutYaz(pfOku());
  });
 }).catch(function(){pfBulutDurum('hata');return false;});
}
// --- Fiyat alarmı: cihazda + GitHub'daki ALARMLAR variable'ında (portföyle aynı anahtar); tarama tetikleyince Telegram ---
var AL_KEY='alarmlar_v1';
function alOku(){try{return JSON.parse(localStorage.getItem(AL_KEY))||[]}catch(e){return[]}}
function alYaz(a){try{localStorage.setItem(AL_KEY,JSON.stringify(a))}catch(e){}
 if(!ghAnahtar())return Promise.resolve(false);
 var v={name:'ALARMLAR',value:JSON.stringify(a)};
 return ghIstek('PATCH','/actions/variables/ALARMLAR',v).then(function(r){return r.status===404?ghIstek('POST','/actions/variables',v):r;})
  .then(function(r){return r.ok;}).catch(function(){return false;});
}
function alBulutOku(){
 if(!ghAnahtar())return Promise.resolve(false);
 return ghIstek('GET','/actions/variables/ALARMLAR').then(function(r){return r.ok?r.json():null;}).then(function(j){
  if(!j)return false;var a=[];try{a=JSON.parse(j.value);}catch(e){}
  if(Array.isArray(a)){try{localStorage.setItem(AL_KEY,JSON.stringify(a))}catch(e){}return true;}return false;
 }).catch(function(){return false;});
}
function alarmHtml(k,d){
 var liste='';alOku().forEach(function(x,i){if(x.kod!==k)return;
  var es=alEski(k,d,x);
  liste+='<div class="alsat">🔔 '+(x.yon==='ust'?'<b>'+x.fiyat+' TL</b> üstüne çıkınca':'<b>'+x.fiyat+' TL</b> altına inince')+(x.not?' <span class="sgun">('+hEsc(x.not)+')</span>':'')+
   ' <button class="pfsil" title="Sil" onclick="alSil('+i+',\''+k+'\')">✕</button>'+
   (es?' <span class="pfuy">⚠ bu seviye artık güncel değil'+(es.yeni?' (güncel '+hEsc(es.yeni.not)+': '+es.yeni.fiyat+' TL)':'')+'</span>'+
     (es.yeni?' <button class="pfipt alkur" onclick="alGuncelle(\''+k+'\','+i+')">Güncelle</button>':''):'')+'</div>';});
 var on=alOneriler(k,d),oh='',kur=0;
 on.forEach(function(x,i){var kurulu=alVar(k,x.yon,x.fiyat);if(!kurulu)kur++;
  oh+='<div class="alsat"><span>'+(x.yon==='ust'?'⬆️':'⬇️')+' <b>'+x.not.charAt(0).toLocaleUpperCase('tr')+x.not.slice(1)+' '+x.fiyat+' TL</b> '+(x.yon==='ust'?'üstüne çıkınca':'altına inince')+' <span class="sgun">('+pyz((x.fiyat/d.fiyat-1)*100)+')</span></span>'+
   (kurulu?' <span class="sgun">✓ kurulu</span>':' <button class="pfipt alkur" onclick="alOneriKur(\''+k+'\','+i+')">🔔 Kur</button>')+'</div>';});
 if(on.length)oh='<div class="aloneri"><div class="cikis" style="margin:2px 0 4px"><b>Önerilen alarmlar</b> (tek tıkla kurulur):'+(kur>=2?' <button class="pfipt alkur" onclick="alOneriKur(\''+k+'\',\'hepsi\')">Hepsini kur ('+kur+')</button>':'')+'</div>'+oh+'</div>';
 return '<div class="alkutu"><div class="gbas">🔔 Fiyat alarmı</div>'+liste+oh+
  '<div class="pfform" style="display:flex;margin:6px 0 0"><input id="alfiyat" type="number" step="any" min="0" placeholder="Fiyat (TL)" style="width:120px">'+
  '<button class="pfipt" onclick="alEkle(\''+k+'\',\'ust\')">Üstüne çıkınca</button><button class="pfipt" onclick="alEkle(\''+k+'\',\'alt\')">Altına inince</button></div>'+
  '<div class="cikis" id="alnot">'+(ghAnahtar()?'Alarm tetiklenince Telegram\'a bir kez mesaj gelir (her 15 dakikalık taramada kontrol edilir).'
   :'Bu cihaz Telegram\'a bağlı değil: alarm sadece burada kayıtlı, bildirim gelmez. Portföyüm → <b>Telegram\'a bağla</b>.')+'</div></div>';
}
function alEkle(k,yon){
 var f=parseFloat(document.getElementById('alfiyat').value);
 if(!(f>0)){document.getElementById('alnot').textContent='Geçerli bir fiyat gir.';return;}
 if(alVar(k,yon,f)){document.getElementById('alnot').textContent='Bu alarm zaten kurulu.';return;}
 var a=alOku();a.push({kod:k,yon:yon,fiyat:f});alYaz(a);ac(k);
}
function alSil(i,k){var a=alOku();a.splice(i,1);alYaz(a);ac(k);}
function ghKurulum(){
 var k=document.getElementById('pfkur');k.hidden=false;
 k.innerHTML='<b>Portföyünü Telegram\'a bağla</b> (her cihazda bir kez)'+
  '<ol class="kurlist"><li>GitHub → profil resmi → <b>Settings</b> → <b>Developer settings</b> → <b>Personal access tokens</b> → <b>Fine-grained tokens</b> → <b>Generate new token</b></li>'+
  '<li>Token name: <code>portfoy</code> · Repository access: <b>Only select repositories</b> → <b>Bist-signal</b></li>'+
  '<li>Permissions → <b>Add permissions</b> → <b>Variables</b> → <b>Read and write</b> → <b>Generate token</b></li>'+
  '<li>Çıkan anahtarı aşağıya yapıştır. Anahtar sadece bu cihazda saklanır.</li></ol>'+
  '<div class="pfform" style="display:flex"><input id="ghgir" type="password" placeholder="github_pat_..." autocomplete="off" style="flex:1;min-width:200px">'+
  '<button class="pfkaydet" onclick="ghKaydet()">Bağla</button><button class="pfipt" onclick="document.getElementById(\'pfkur\').hidden=true">Kapat</button></div>'+
  '<div id="ghsonuc" class="cikis"></div>'+(ghAnahtar()?'<div class="cikis"><a href="#" onclick="ghKaldir();return false">Bu cihazdaki bağlantıyı kaldır</a></div>':'');
}
function ghKaydet(){
 var t=(document.getElementById('ghgir').value||'').trim(),s=document.getElementById('ghsonuc');
 if(!t){s.textContent='Anahtarı yapıştır.';return;}
 try{localStorage.setItem(GH_KEY,t);}catch(e){s.textContent='Tarayıcı anahtarı kaydetmeye izin vermedi.';return;}
 s.textContent='Deneniyor…';
 pfBulutOku().then(function(ok){
  if(ok){alBulutOku().then(function(v){if(!v)alYaz(alOku());});dfBulutOku();document.getElementById('pfkur').hidden=true;pfNot('✓ Bağlandı. Portföyündeki değişiklikler artık otomatik olarak Telegram mesajlarına yansıyacak.');}
  else{try{localStorage.removeItem(GH_KEY);}catch(e){}s.textContent='Olmadı: anahtar yanlış ya da "Variables: Read and write" yetkisi yok. Adımları kontrol edip tekrar dene.';pfBulutDurum('yerel');}
 });
}
function ghKaldir(){try{localStorage.removeItem(GH_KEY);}catch(e){}document.getElementById('pfkur').hidden=true;pfBulutDurum('yerel');dfBulutDurum('yerel');}

// tarama.py sektor_dagilimi() ile aynı: güncel değere göre endüstri payları
function xuDeger(t){  // t tarihindeki (ya da önceki son) BIST 100 kapanışı
 if(!XU||!t)return null;var lo=0,hi=XU.t.length-1,i=-1;
 if(t>new Date().toISOString().slice(0,10))return null;
 while(lo<=hi){var m=(lo+hi)>>1;if(XU.t[m]<=t){i=m;lo=m+1;}else hi=m-1;}
 return i>=0?XU.c[i]:null;
}
function pfKiyas(a){  // alış tarihi girilmiş pozisyonlar: portföy vs aynı para aynı günlerde BIST 100 (tarama.endeks_kiyas ile aynı)
 if(!XU)return null;var xs=XU.c[XU.c.length-1],mal=0,deg=0,xd=0,n=0;
 a.forEach(function(p){var d=DATA[p.kod];if(!p.xu_birim||!d||d.fiyat==null)return;n++;mal+=p.adet*p.maliyet;deg+=p.adet*d.fiyat;xd+=p.xu_birim*xs;});
 if(!n||mal<=0)return null;var pf=(deg/mal-1)*100,xu=(xd/mal-1)*100;return {n:n,pf:pf,xu:xu,fark:pf-xu};
}
function pfDagilim(a){
 var top=0,pay={};a.forEach(function(p){var d=DATA[p.kod];if(!d||d.fiyat==null)return;var v=p.adet*d.fiyat,ad=d.endustri||d.sektor||'Bilinmiyor';pay[ad]=(pay[ad]||0)+v;top+=v;});
 return top?Object.keys(pay).map(function(k){return [k,pay[k]/top*100];}).sort(function(x,y){return y[1]-x[1];}):[];
}
function pfRender(){
 var a=pfOku(),liste=document.getElementById('pflist'),top=document.getElementById('pftop');
 if(!a.length){liste.innerHTML='<div class="pfy bos">Henüz hisse yok. <b>+ Ekle</b> ile portföyünü oluştur.</div>';top.textContent='';return;}
 var toplam=0;
 var r='<div class="sar"><table class="pf"><thead><tr><th>Hisse</th><th class="num">Adet</th><th class="num">Maliyet</th><th class="num">Güncel</th><th class="num">K/Z %</th><th class="num">K/Z TL</th><th>Sinyal</th><th class="num" title="Fiyatın altındaki en yakın destek (son 120 günün dibi)">Destek</th><th class="num">Çıkış (stop)</th><th class="num">Hedef</th><th></th></tr></thead><tbody>';
 a.forEach(function(p,i){
  var d=DATA[p.kod]||{},f=d.fiyat;
  var kzy=(f!=null)?((f/p.maliyet-1)*100):null, kzt=(f!=null)?((f-p.maliyet)*p.adet):null;
  if(kzt!=null)toplam+=kzt;
  var sn=d.sinyal||'—',scls=d.sinyal?sinyalCls(d):'notr';
  var uy=(d.iz&&d.iz.cikti&&!p.uzun)?' <span class="pfuy">iz stop kırıldı</span>':'';
  var kzc=(kzy||0)>=0?'pos':'neg';
  r+='<tr onclick="ac(\''+p.kod+'\')"><td class="kod">'+p.kod+(p.uzun?'<span class="uvb" title="Uzun vade">UV</span>':'')+'</td><td class="num">'+p.adet+'</td><td class="num">'+p.maliyet+'</td>'+
     '<td class="num">'+(f!=null?f:'—')+'</td>'+
     '<td class="num '+kzc+'">'+(kzy!=null?((kzy>=0?'+':'')+kzy.toFixed(1)+'%'):'—')+
       (p.xu_birim&&XU?(function(){var xy=(p.xu_birim*XU.c[XU.c.length-1]/(p.adet*p.maliyet)-1)*100;return '<span class="pfxu" title="Aynı parayla '+p.tarih+' tarihinde BIST 100 alsaydın">XU100 '+(xy>=0?'+':'')+xy.toFixed(1)+'%</span>';})():'')+'</td>'+
     '<td class="num '+kzc+'">'+(kzt!=null?((kzt>=0?'+':'')+Math.round(kzt).toLocaleString('tr-TR')+' TL'):'—')+'</td>'+
     '<td><span class="pill '+scls+'">'+sn+'</span>'+uy+''+'</td>'+
     (function(){var ds=d.sd&&d.sd.destek;if(f==null||!ds)return '<td class="num">—</td>';var u=(ds.fiyat/f-1)*100;
       return '<td class="num" title="'+ds.tarih+' dibi'+(ds.test>=2?', '+ds.test+' kez test edildi':'')+'">'+(u>-2?'👉 ':'')+ds.fiyat+' <span class="sgun">'+yzd(u)+'</span></td>';})()+
     (function(){if(f==null)return '<td class="num">—</td><td class="num">—</td>';var pl=pozPlan(d,p),h=pl.hedefler.length?pl.hedefler[0][0]:null;
       if(pl.uzun)return '<td class="num stop">'+(pl.karar?(pl.kararAsildi?'<b>🧭 '+pl.karar+' ⚠</b>':'🧭 '+pl.karar+' <span class="sgun">'+yzd(pl.kararUzak)+'</span>'):'—')+'</td>'+
              '<td class="num pos">'+(h?h+' <span class="sgun">'+yzd((h/f-1)*100)+'</span>':'—')+'</td>';
       if(pl.izCikti)return '<td class="num stop"><b>kırıldı ⚠</b></td><td class="num">—</td>';
       return '<td class="num stop">'+(pl.stop?(pl.asildi?'<b>'+pl.stop+' ⚠</b>':pl.stop+' <span class="sgun">'+yzd(pl.stopUzak)+'</span>'):'—')+'</td>'+
              '<td class="num pos">'+(h?h+' <span class="sgun">'+yzd((h/f-1)*100)+'</span>':'—')+'</td>';})()+
     '<td class="num"><button class="pfsil pfduz" title="Düzenle" onclick="event.stopPropagation();pfFormAc('+i+')">✎</button> '+
     '<button class="pfsat" title="Sattım: satışı 📒 İşlem Defterim\'e yazar (kısmi satış da olur)" onclick="event.stopPropagation();dfFormAc(\'sat\','+i+')">Sattım</button> '+
     '<button class="pfsil" title="Sil (kayıt tutmaz — yanlış girilen satır için)" aria-label="Sil (kayıt tutmaz)" onclick="event.stopPropagation();pfSil('+i+')">✕</button></td></tr>';
 });
 r+='</tbody></table></div><div class="pfacik"><b>Sattım</b>: satışı 📒 İşlem Defterim\'e yazar (kısmi satışta kalan adet portföyde kalır) · <b>✕ Sil</b>: kayıt tutmaz, yanlış girilen satır için.</div>';
 var dag=pfDagilim(a);
 if(dag.length){
  var ust=a.length>=2&&dag[0][1]>40;
  r+='<div class="pfdag'+(ust?' uyar':'')+'">'+(ust?'⚠️ Portföyünün <b>%'+dag[0][1].toFixed(0)+'</b>\'i tek sektörde (<b>'+dag[0][0]+'</b>) — o sektördeki bir haber hepsini birlikte etkiler. ':'')+
     'Dağılım: '+dag.slice(0,5).map(function(x){return x[0]+' %'+x[1].toFixed(0);}).join(' · ')+'</div>';
 }
 r+=korHtml(a,dag);
 var ky=pfKiyas(a);
 if(ky){
  r+='<div class="pfkiyas">📈 <b>Endeksle kıyas</b>'+(ky.n<a.length?' (alış tarihi girilen '+ky.n+'/'+a.length+' hisse)':'')+': portföy <b class="'+(ky.pf>=0?'pos':'neg')+'">'+(ky.pf>=0?'+':'')+ky.pf.toFixed(1)+'%</b> · aynı parayla aynı günlerde BIST 100 alsaydın <b>'+(ky.xu>=0?'+':'')+ky.xu.toFixed(1)+'%</b> → endeksin <b class="'+(ky.fark>=0?'pos':'neg')+'">'+Math.abs(ky.fark).toFixed(1)+' puan '+(ky.fark>=0?'önünde':'gerisinde')+'</b>.'+
     '<span class="pfxu">Temettüler iki tarafta da dahil değil. Kıyas için hisse eklerken/düzenlerken alış tarihini gir.</span></div>';
 }else if(XU)r+='<div class="pfkiyas sgun">📈 Portföyünü BIST 100 ile kıyaslamak için hisseyi düzenle (✎) ve <b>alış tarihini</b> gir.</div>';
 r+=birikimHtml(a);
 liste.innerHTML=r;
 if(typeof bugunRender==='function')bugunRender();
 top.innerHTML='Toplam K/Z: <b class="'+(toplam>=0?'pos':'neg')+'">'+(toplam>=0?'+':'')+Math.round(toplam).toLocaleString('tr-TR')+' TL</b>';
}
// --- 📒 İşlem Defterim: kapanmış GERÇEK işlemler (kullanıcının kendi alım-satımı). Cihazda (defter_v1) + GitHub'daki DEFTER variable'ı
// (portföyle aynı anahtar, aynı çakışma mantığı: bulut esas, bu cihazdaki değişiklik daha yeniyse buluta yazılır).
// GİZLİLİK: DEFTER tarama.yml'e verilmez → Actions loguna, durum.json'a, index.html'e ASLA girmez; tüm hesap tarayıcıda.
// Kayıt (kısa anahtarlar, 48 KB variable sınırı için): i id, h hisse, a alış tarihi, s satış tarihi, n adet, m alış fiyatı, f satış fiyatı,
// k komisyon TL (toplam, isteğe bağlı), pl plan/neden, no not, d duygu, u plana uyum (e/h/k), q kalite (A/B/C), t kayıt zamanı (ms);
// otomatik: sa alışta sistem (al/tr/yok/?), ss satışta (erken/ayni/stopalti/cikti/yok/?), x aynı günlerde BIST 100 %, sg ilgili 🚀 sinyal günü,
// cg sistemin çıkış günü, cb çıkış bitleri (tkg: 1 kilitli taban, 2 🔐), st satış günü stop/karar çizgisi, gs gösterge SAT başlangıcı.
// Yerel bayraklar: kn = notları buluta sığmadı (bu cihazda), ky = kaydın tamamı sadece bu cihazda. Nesne: {v,u (son değişiklik ms),k,p {hisse: neden aldım}, pk}.
var DF_KEY='defter_v1',DF_ACIK_KEY='defter_acik_v1',DF_SINIR=46000,DF_BE=0.5,DF_MIN=3,dfMod=null,dfAy=null,dfSilId=null,dfAcikId=null,dfKesik=null;
var DF_SON=(XU&&XU.t&&XU.t.length)?XU.t[XU.t.length-1]:'';
var DF_DUYGU={sakin:['😌','Sakin','acele etmeden, planımla karar verdim'],emin:['💪','Emin','analizime güvendim'],fomo:['🏃','FOMO','kaçırma korkusu: yükseliyor diye kaçırmamak için girdim'],
 korku:['😨','Korku','düşer diye panikle karar verdim'],intikam:['😤','İntikam','önceki zararı hemen çıkarmak için girdim'],asiri:['🦚','Aşırı güven','"kesin olur" dedim, kurallarımı esnettim'],yorgun:['😴','Yorgun','dikkatim dağınıktı, dalgındım']};
var DF_PLAN={e:'Evet',h:'Hayır',k:'Kısmen'};
var DF_KALITE={A:'A — planlı, kurallarıma uygun',B:'B — idare eder, birkaç eksik',C:'C — dürtüsel, kuralsız'};
var DF_SA={al:['🚀 AL\'de aldın','AL\'de','iyi','Alış günü sistemin 🚀 AL sinyali vardı (sinyalden en fazla 5 işlem günü sonra)'],
 tr:['⏳ geç giriş','geç giriş','','Sistem pozisyondaydı ama 🚀 AL 5 işlem gününden eskiydi (yeni alım sinyali değildi)'],
 yok:['✋ sistem dışı','sistem dışı','kot','Alış günü bu hissede sistemin 🚀 AL\'i yoktu'],
 '?':['? bilinmiyor','bilinmiyor','','Alış tarihi girilmemiş ya da o tarih için sinyal verisi yok (son 2 yıl / son 6 işlem)']};
var DF_SS={erken:['⏩ erken çıkış','erken çıkış','kot','Sattığın gün sistem hâlâ AL\'deydi (iz stop kırılmamıştı)'],
 ayni:['✅ sistemle çıktın','sistemle çıktı','iyi','Sistem aynı gün çıkış verdi (iz stop / 🔐 kâr kilidi)'],
 stopalti:['✅ stop altında sattın','stop altında','iyi','Sattığın fiyat iz stop / karar çizgisinin altındaydı'],
 cikti:['⌛ geç çıkış','geç çıkış','kot','Sistem senden önce çıkış vermişti'],
 yok:['— sistem dışı','sistem dışı','','Tuttuğun sürede sistem bu hissede pozisyonda değildi'],
 '?':['? bilinmiyor','bilinmiyor','','O tarih için sinyal verisi yok']};
var DF_AYLAR=['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];

function dfBos(){return {v:1,u:0,k:[],p:{}};}
function dfOku(){try{var o=JSON.parse(localStorage.getItem(DF_KEY));if(o&&Array.isArray(o.k)){if(!o.p||typeof o.p!=='object')o.p={};return o;}}catch(e){}return dfBos();}
function dfYazYerel(o){try{localStorage.setItem(DF_KEY,JSON.stringify(o));return true;}catch(e){return false;}}
function dfYaz(o){o.u=Date.now();if(!dfYazYerel(o))dfNot('⚠ Tarayıcı kaydetmeye izin vermedi (gizli pencere / depolama dolu olabilir). <b>CSV yedeği</b> al.');dfBulutYaz(o);}
function dfNot(t){var n=document.getElementById('dfnot');if(!n)return;n.innerHTML=t||'';n.hidden=!t;}
function dfId(o){var id='';try{if(window.crypto&&crypto.randomUUID)id=crypto.randomUUID().replace(/-/g,'').slice(0,12);}catch(e){}
 if(!id)id=Date.now().toString(36)+Math.random().toString(36).slice(2,8);
 return (o&&o.k.some(function(r){return r.i===id;}))?dfId(o):id;}
function dfBugun(){var d=new Date();return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2);}
function dfGun(a,b){if(!a||!b)return null;return Math.round((Date.parse(b+'T00:00:00Z')-Date.parse(a+'T00:00:00Z'))/864e5);}
function dfTr(t){return t?t.slice(8,10)+'.'+t.slice(5,7)+'.'+t.slice(0,4):'—';}
function dfSayi(x,b){return (+x).toLocaleString('tr-TR',{maximumFractionDigits:b==null?4:b});}
function dfKZ(r){var mal=r.m*r.n,tl=(r.f-r.m)*r.n-(r.k||0),y=mal>0?tl/mal*100:0;return {tl:tl,y:y,s:Math.abs(y)<=DF_BE?'be':(tl>0?'kaz':'zar')};}
function dfEk(n){n=Math.round(Math.abs(n));if(n===100)return 'ünde';var b=n%10,o=Math.floor(n/10)%10;  // '%85'inde', '3'ünde' — Türkçe bulunma eki
 if(b)return ['','inde','sinde','ünde','ünde','inde','sında','sinde','inde','unda'][b];
 return ['ında','unda','sinde','unda','ında','sinde','ında','inde','inde','ında'][o];}
function dfSirala(x,y){return x.s<y.s?-1:x.s>y.s?1:((x.t||0)-(y.t||0));}  // eskiden yeniye
function dfPlanTemizle(k,pf){if(!k)return;var o=dfOku();if(o.p[k]&&!(pf||pfOku()).some(function(x){return x.kod===k;})){delete o.p[k];dfYaz(o);}}

// --- Otomatik alanlar: alış/satış günü sistem ne diyordu? (DATA.tkg = son 6 🚀 v3 işlemi, çıkışı son 2 yılda olan ya da açık)
function dfIsGunu(a,b){if(!XU)return null;var n=0;for(var i=XU.t.length-1;i>=0&&XU.t[i]>a;i--)if(XU.t[i]<=b)n++;return n;}
function dfSinyal(h,a,s,f,p){
 var d=DATA[h],o={sa:'?',ss:'?'},xa=a?xuDeger(a):null,xs=s?xuDeger(s):null;
 o.x=(xa&&xs&&a<=s)?Math.round((xs/xa-1)*1000)/10:null;
 if(!d)return o;
 var g=d.tkg||[],tk=d.tk||{},sinir=DF_SON?(+DF_SON.slice(0,4)-2)+DF_SON.slice(4):'9999',ilk=g.length>=6?g[0][0]:'0000';
 function kapsar(t){return !!t&&t>=sinir&&t>=ilk;}
 function acik(t){for(var i=g.length-1;i>=0;i--){var x=g[i];if(x[0]<=t&&(x[2]==null||t<x[2]))return x;}return null;}
 if(a){var ta=acik(a);
  if(ta){var n=dfIsGunu(ta[0],a);o.sa=(n!=null&&n<=5)?'al':'tr';o.sg=ta[0];}
  else if(kapsar(a))o.sa='yok';}
 if(s){
  var ts=acik(s),c=null;
  if(ts){o.ss='erken';if(!o.sg)o.sg=ts[0];}
  else{
   for(var i=g.length-1;i>=0;i--){var x=g[i];if(x[2]&&x[2]<=s&&(a?x[2]>a:dfGun(x[2],s)<=30)){c=x;break;}}
   if(c){o.ss=(c[2]===s)?'ayni':'cikti';o.cg=c[2];if(c[4]&3)o.cb=c[4]&3;if(!o.sg)o.sg=c[0];}
   else if(kapsar(a||s))o.ss='yok';
  }
  var yakin=DF_SON&&s>=DF_SON?true:(DF_SON&&dfGun(s,DF_SON)<=3);  // satış son veri gününe yakınsa bugünkü stop / sinyal geçerli
  if(yakin&&d.fiyat!=null){
   var st=null;
   if(p){var pl=pozPlan(d,p);st=pl.uzun?pl.karar:(pl.izCikti?null:pl.stop);if(!pl.uzun&&pl.izCikti&&(o.ss==='erken'||o.ss==='yok'||o.ss==='?'))o.ss='stopalti';}
   else if(tk.durum==='AL')st=tk.stop;
   if(st){o.st=st;if(f<st&&(o.ss==='erken'||o.ss==='yok'||o.ss==='?'))o.ss='stopalti';}
   if(d.sinyal==='SAT'&&d.sinyal_tarih&&d.sinyal_tarih<=s)o.gs=d.sinyal_tarih;
  }
 }
 return o;
}
function dfOtoKoy(r,o){['sa','ss','x','sg','cg','cb','st','gs'].forEach(function(k){if(o[k]==null||o[k]==='')delete r[k];else r[k]=o[k];});}
function dfRoz(r){
 var a=DF_SA[r.sa||'?']||DF_SA['?'],b=DF_SS[r.ss||'?']||DF_SS['?'];
 var at=a[3]+(r.sg?' · sinyal günü '+dfTr(r.sg):''),bt=b[3]+(r.cg?' · sistem çıkışı '+dfTr(r.cg)+((r.cb&2)?' (🔐 kâr kilidi)':''):'')+(r.st?' · satış günü stop '+dfSayi(r.st,2):'');
 return '<span class="dfroz '+a[2]+'" title="Alışta: '+hEsc(at)+'">'+a[0]+'</span><span class="dfroz '+b[2]+'" title="Satışta: '+hEsc(bt)+'">'+b[0]+'</span>';
}

// --- GitHub eşitleme (DEFTER variable'ı). 48 KB sınırı: sığmazsa en eski kayıtların notları, gerekirse kayıtların kendisi sadece bu cihazda kalır.
function dfBayt(s){try{return new TextEncoder().encode(s).length;}catch(e){return unescape(encodeURIComponent(s)).length;}}
function dfBulutHazirla(o){
 var k=o.k.map(function(r){var c={};for(var x in r)if(x!=='kn'&&x!=='ky')c[x]=r[x];return c;});
 var sira=k.slice().sort(dfSirala),ky={},kn={},pk=false;
 function js(){var b={v:1,u:o.u,k:k.filter(function(r){return !ky[r.i];}),p:pk?{}:o.p};if(pk)b.pk=1;return JSON.stringify(b);}
 var s=js(),i=0;
 while(dfBayt(s)>DF_SINIR&&i<sira.length){var r=sira[i++];if(r.pl||r.no){delete r.pl;delete r.no;r.kn=1;kn[r.i]=1;s=js();}}
 if(dfBayt(s)>DF_SINIR&&Object.keys(o.p).length){pk=true;s=js();}
 i=0;while(dfBayt(s)>DF_SINIR&&i<sira.length){ky[sira[i++].i]=1;s=js();}
 return {s:s,kn:kn,ky:ky,pk:pk};
}
function dfIsaretle(o,h){  // yerel bayraklar (sadece bilgi; u değişmez)
 var deg=false;o.k.forEach(function(r){var n=h.kn[r.i]?1:0,y=h.ky[r.i]?1:0;if((r.kn||0)!==n){if(n)r.kn=1;else delete r.kn;deg=true;}if((r.ky||0)!==y){if(y)r.ky=1;else delete r.ky;deg=true;}});
 if(deg)dfYazYerel(o);
 var nk=Object.keys(h.kn).length,yk=Object.keys(h.ky).length;dfKesik=(nk||yk||h.pk)?{kn:nk,ky:yk,pk:h.pk}:null;
}
function dfBulutDurum(d,kod){
 var el=document.getElementById('dfbulut');if(!el)return;
 var yetki=(kod===401||kod===403||kod===404);
 var t={yerel:'Bu cihazda saklanıyor. Başka cihazda da görmek için Portföyüm → <a href="#" onclick="ghKurulum();return false">Telegram\'a bağla</a> (aynı anahtar; defter Telegram\'a gönderilmez).',
  kaydediliyor:'☁ Kaydediliyor…',ok:'☁ GitHub\'daki gizli DEFTER kaydıyla eşit (Telegram\'a ve herkese açık dosyalara gitmez)',
  hata:'⚠ GitHub\'a kaydedilemedi'+(kod?' ('+kod+')':'')+(yetki?' — anahtar geçersiz ya da yetkisi eksik':' — sonra tekrar dene')+'. Kayıtlar bu cihazda duruyor.'}[d];
 if(d==='ok'&&dfKesik)t+=' <span class="pfuy">· defter büyüdü: '+(dfKesik.kn?'en eski '+dfKesik.kn+' işlemin notları':'')+(dfKesik.ky?(dfKesik.kn?', ':'')+dfKesik.ky+' işlemin tamamı':'')+(dfKesik.pk?(dfKesik.kn||dfKesik.ky?', ':'')+'"neden aldım" notları':'')+' GitHub sınırına (48 KB) sığmadı, sadece bu cihazda. CSV yedeği al.</span>';
 el.innerHTML=t;el.className='pfbulut '+d;
}
function dfBulutYaz(o){
 var h=dfBulutHazirla(o);dfIsaretle(o,h);
 if(!ghAnahtar()){dfBulutDurum('yerel');return Promise.resolve(false);}
 var v={name:'DEFTER',value:h.s};dfBulutDurum('kaydediliyor');
 return ghIstek('PATCH','/actions/variables/DEFTER',v).then(function(r){return r.status===404?ghIstek('POST','/actions/variables',v):r;})
  .then(function(r){dfBulutDurum(r.ok?'ok':'hata',r.ok?0:r.status);return r.ok;}).catch(function(){dfBulutDurum('hata');return false;});
}
function dfBirlestir(b,y){  // bulut esas; notu buluta sığmamış kayıtların notları ve sadece bu cihazdaki kayıtlar korunur
 var yy={};y.k.forEach(function(r){yy[r.i]=r;});
 var k=b.k.filter(function(r){return r&&r.i&&r.h;}).map(function(r){var l=yy[r.i];r=Object.assign({},r);
  if(r.kn&&l){if(l.pl)r.pl=l.pl;if(l.no)r.no=l.no;}return r;});
 var var_={};k.forEach(function(r){var_[r.i]=1;});
 y.k.forEach(function(r){if(r.ky&&!var_[r.i])k.push(r);});
 return {v:1,u:b.u||0,k:k,p:b.pk?(y.p||{}):(b.p||{})};
}
function dfBulutOku(){
 if(!ghAnahtar()){dfBulutDurum('yerel');return Promise.resolve(false);}
 dfBulutDurum('kaydediliyor');
 return ghIstek('GET','/actions/variables/DEFTER').then(function(r){
  var o=dfOku();
  if(r.status===404){if(o.k.length||Object.keys(o.p).length)return dfBulutYaz(o);dfBulutDurum('ok');return true;}
  if(!r.ok){dfBulutDurum('hata',r.status);return false;}
  return r.json().then(function(j){var b=null;try{b=JSON.parse(j.value);}catch(e){}
   if(!b||!Array.isArray(b.k))return dfBulutYaz(o);
   if((b.u||0)>=(o.u||0)){var m=dfBirlestir(b,o);dfYazYerel(m);dfIsaretle(m,dfBulutHazirla(m));dfRender();dfBulutDurum('ok');return true;}
   return dfBulutYaz(o);  // bu cihazdaki değişiklik daha yeni (ör. bağlantısızken yapıldı) → buluta yazılır
  });
 }).catch(function(){dfBulutDurum('hata');return false;});
}

// --- Form: 'sat' (portföy satırından), 'duz' (kayıt düzenle), 'yeni' (geçmiş işlemi elle ekle)
function dfSecenek(obj,sec,bos,fn){var h='<option value="">'+bos+'</option>';for(var k in obj)h+='<option value="'+k+'"'+(k===sec?' selected':'')+'>'+fn(k,obj[k])+'</option>';return h;}
function dfFormAc(mod,x){
 var o=dfOku(),r={},p=null,bug=dfBugun();
 if(mod==='sat'){p=pfOku()[x];if(!p)return;var d=DATA[p.kod]||{};
  r={h:p.kod,a:p.tarih||'',m:p.maliyet,s:bug,f:d.fiyat!=null?d.fiyat:'',n:p.adet,pl:o.p[p.kod]||''};}
 else if(mod==='duz'){r=o.k.filter(function(z){return z.i===x;})[0];if(!r)return;}
 else r={s:bug};
 dfMod={mod:mod,x:x,i:r.i||null};
 var dz=r.d&&DF_DUYGU[r.d];
 document.getElementById('dfmodal').innerHTML='<div class="mh"><div class="sol"><h2>'+(mod==='sat'?'Sattım: '+hEsc(r.h):mod==='duz'?'Kaydı düzenle: '+hEsc(r.h):'Geçmiş işlem ekle')+'</h2></div><button class="kapa" onclick="dfFormKapat()" aria-label="Kapat">×</button></div>'+
  '<div class="mfiyat">'+(mod==='sat'?'Kapanan işlem 📒 deftere yazılır'+(p?'; portföyde '+dfSayi(p.adet)+' adet var — daha azını yazarsan kalanı portföyde kalır.':'.'):mod==='yeni'?'Portföye girmemiş eski bir alım-satımı deftere ekle.':'Tarih/fiyat değişirse sistem bilgisi (🚀) yeniden hesaplanır.')+'</div>'+
  '<div class="dfform">'+
  '<label>Hisse<input id="dfh" value="'+hEsc(r.h||'')+'" list="pfkodlar" autocomplete="off" placeholder="örn. THYAO"'+(mod==='sat'?' disabled':'')+'></label>'+
  '<label>Adet<input id="dfn" type="number" step="any" min="0" value="'+(r.n!=null?r.n:'')+'"></label>'+
  '<label>Alış tarihi <span class="ipucu2">(bilmiyorsan boş bırak)</span><input id="dfa" type="date" value="'+(r.a||'')+'" max="'+bug+'"></label>'+
  '<label>Alış fiyatı (TL)<input id="dfm" type="number" step="any" min="0" value="'+(r.m!=null?r.m:'')+'"></label>'+
  '<label>Satış tarihi<input id="dfs" type="date" value="'+(r.s||'')+'" max="'+bug+'"></label>'+
  '<label>Satış fiyatı (TL)<input id="dff" type="number" step="any" min="0" value="'+(r.f!=null?r.f:'')+'"></label>'+
  '<label class="tam">Komisyon, toplam TL <span class="ipucu2">(isteğe bağlı; alış + satış komisyonu ve vergiler. Boş = 0 sayılır, kâr biraz iyimser görünür)</span><input id="dfk" type="number" step="any" min="0" value="'+(r.k||'')+'" placeholder="0"></label>'+
  '<label class="tam">İşlem öncesi plan / neden aldım? <span class="ipucu2">(isteğe bağlı)</span><textarea id="dfpl" maxlength="1000" placeholder="örn. 🚀 AL geldi, iz stop\'a kadar tutacaktım">'+hEsc(r.pl||'')+'</textarea></label>'+
  '<label class="tam">İşlem sonrası not / ne öğrendim? <span class="ipucu2">(isteğe bağlı)</span><textarea id="dfno" maxlength="1000" placeholder="örn. düşünce panikledim, stop\'u beklemedim">'+hEsc(r.no||'')+'</textarea></label>'+
  '<label>Baskın duygun<select id="dfd" onchange="dfDuyguAcik()">'+dfSecenek(DF_DUYGU,r.d,'— seçmedim —',function(k,v){return v[0]+' '+v[1];})+'</select><span id="dfdac" class="ipucu2">'+(dz?hEsc(dz[2]):'Dürüst ol: kimse görmüyor, amaç kendini tanımak.')+'</span></label>'+
  '<label>Planına uydun mu?<select id="dfu">'+dfSecenek(DF_PLAN,r.u,'— seçmedim —',function(k,v){return v;})+'</select></label>'+
  '<label>Kalite (karara göre, sonuca göre değil)<select id="dfq">'+dfSecenek(DF_KALITE,r.q,'— seçmedim —',function(k,v){return v;})+'</select></label>'+
  '<div class="tam ipucu2">Kaydedince pano kendisi ekler: alış günü sistemde 🚀 AL var mıydı, satış günü sistem hâlâ AL\'de miydi (erken çıkış) ya da stop altında mıydı, aynı günlerde BIST 100 ne yaptı, kaç gün tuttun. Hepsi bu cihazda hesaplanır.</div>'+
  '</div><div id="dfformnot" class="zaman" hidden></div>'+
  '<div class="btnler"><button class="pfkaydet" onclick="dfKaydet()">'+(mod==='sat'?'Satışı deftere yaz':'Kaydet')+'</button><button class="pfipt" onclick="dfFormKapat()">İptal</button></div>';
 document.getElementById('dfust').classList.add('acik');
 var ilk=document.getElementById(mod==='yeni'?'dfh':'dff');if(ilk)ilk.focus();
}
function dfDuyguAcik(){var v=document.getElementById('dfd').value,e=document.getElementById('dfdac');e.textContent=v&&DF_DUYGU[v]?DF_DUYGU[v][2]:'Dürüst ol: kimse görmüyor, amaç kendini tanımak.';}
function dfFormKapat(){document.getElementById('dfust').classList.remove('acik');dfMod=null;}
document.addEventListener('keydown',function(e){if(e.key==='Escape'&&dfMod)dfFormKapat();});
function dfDeger(id){var e=document.getElementById(id);return e?(e.value||'').trim():'';}
function dfKaydet(){
 var m=dfMod;if(!m)return;
 var hata=function(t){var n=document.getElementById('dfformnot');n.textContent=t;n.hidden=false;};
 var h=dfDeger('dfh').toLocaleUpperCase('tr').replace(/[^A-Z0-9ÇĞİÖŞÜ]/g,'').slice(0,12),a=dfDeger('dfa'),s=dfDeger('dfs'),bug=dfBugun();
 var n=parseFloat(dfDeger('dfn')),mf=parseFloat(dfDeger('dfm')),f=parseFloat(dfDeger('dff')),k=parseFloat(dfDeger('dfk'))||0;
 if(!h)return hata('Hisse kodunu yaz.');
 if(!(n>0))return hata('Adet sıfırdan büyük olmalı.');
 if(!(mf>0)||!(f>0))return hata('Alış ve satış fiyatını yaz.');
 if(!/^\d{4}-\d{2}-\d{2}$/.test(s))return hata('Satış tarihini seç.');
 if(s>bug)return hata('Satış tarihi bugünden sonra olamaz.');
 if(a&&a>s)return hata('Alış tarihi satış tarihinden sonra olamaz.');
 if(k<0)return hata('Komisyon eksi olamaz.');
 var o=dfOku(),pf=null,pa=null;
 if(m.mod==='sat'){pa=pfOku();pf=pa[m.x];if(!pf||pf.kod!==h)return hata('Portföy satırı değişmiş; pencereyi kapatıp yeniden dene.');
  if(n>pf.adet+1e-9)return hata('Portföyde '+dfSayi(pf.adet)+' adet var; daha fazlasını satamazsın.');}
 var eski=m.mod==='duz'?o.k.filter(function(z){return z.i===m.i;})[0]:null;
 if(m.mod==='duz'&&!eski)return hata('Kayıt bulunamadı (başka cihazda silinmiş olabilir).');
 var r=eski?Object.assign({},eski):{i:dfId(o),t:Date.now()};
 r.h=h;r.s=s;r.n=n;r.m=mf;r.f=f;if(a)r.a=a;else delete r.a;if(k)r.k=k;else delete r.k;
 [['pl','dfpl'],['no','dfno'],['d','dfd'],['u','dfu'],['q','dfq']].forEach(function(z){var v=dfDeger(z[1]);if(z[0]==='pl'||z[0]==='no')v=v.slice(0,1000);if(v)r[z[0]]=v;else delete r[z[0]];});
 if(r.pl||r.no)delete r.kn;
 if(!eski||eski.h!==h||(eski.a||'')!==(a||'')||eski.s!==s||eski.f!==f||eski.sa==null)dfOtoKoy(r,dfSinyal(h,a,s,f,pf));
 if(eski)o.k=o.k.map(function(z){return z.i===r.i?r:z;});else o.k.push(r);
 var kz=dfKZ(r),not=hEsc(h)+' '+(eski?'kaydı güncellendi.':'satışı deftere yazıldı: <b class="'+(kz.tl>=0?'pos':'neg')+'">'+tlf(kz.tl)+' ('+pyz(kz.y)+')</b>.');
 if(pf){  // portföyden düş: tamamı satıldıysa satır silinir, kısmi satışta adet (ve endeks birimi) orantılı azalır
  if(n>=pf.adet-1e-9){pa.splice(m.x,1);if(!pa.some(function(z){return z.kod===h;}))delete o.p[h];not+=' Portföyden çıkarıldı.';}
  else{var kal=Math.round((pf.adet-n)*1e6)/1e6;if(pf.xu_birim)pf.xu_birim=pf.xu_birim*kal/pf.adet;pf.adet=kal;not+=' Portföyde '+dfSayi(kal)+' adet kaldı.';}
  pfYaz(pa);pfRender();
 }
 dfYaz(o);dfFormKapat();dfAcikId=null;
 var bx=document.getElementById('dfbox');if(bx&&!bx.open){bx.open=true;}
 dfRender();
 var msg=not+' <a href="#dfbox" onclick="dfGoster();return false">📒 Deftere bak</a>';
 if(pf)pfNot(msg);else dfNot(msg);
}
function dfGoster(){var b=document.getElementById('dfbox');if(b){b.open=true;b.scrollIntoView({behavior:'smooth',block:'start'});}}
function dfAcikKaydet(){var b=document.getElementById('dfbox');try{localStorage.setItem(DF_ACIK_KEY,b&&b.open?'1':'0');}catch(e){}}
function dfSilSor(id){dfSilId=id;dfRender();}
function dfSil(id){var o=dfOku();o.k=o.k.filter(function(r){return r.i!==id;});dfSilId=null;if(dfAcikId===id)dfAcikId=null;dfYaz(o);dfRender();dfNot('Kayıt silindi.');}
function dfAc(id){dfAcikId=dfAcikId===id?null:id;dfRender();}
function dfTemizleSor(){var n=dfOku().k.length;if(!n){dfNot('Defter zaten boş.');return;}
 dfNot('Defterdeki <b>'+n+'</b> işlemin hepsi silinecek'+(ghAnahtar()?' (bu cihazdan ve GitHub\'dan)':'')+'. Önce <b>⬇ CSV yedeği</b> almanı öneririz. <span class="dfonay"><button class="dfbtn tehlike" onclick="dfTemizle()">Evet, hepsini sil</button><button class="dfbtn" onclick="dfNot(\'\')">Vazgeç</button></span>');}
function dfTemizle(){var o=dfOku();o.k=[];dfAcikId=null;dfSilId=null;dfYaz(o);dfRender();dfNot('Defter temizlendi.');}

// --- Süzgeç + çizim
function dfSuz(o){
 var q=(dfDeger('dfara')||'').toLocaleLowerCase('tr'),so=dfDeger('dfsonuc'),si=dfDeger('dfsin');
 return o.k.map(function(r){var z=Object.assign({},r);z._kz=dfKZ(r);z._g=dfGun(r.a,r.s);return z;}).filter(function(r){
  if(q&&(r.h+' '+(r.pl||'')+' '+(r.no||'')+' '+((DF_DUYGU[r.d]||[])[1]||'')).toLocaleLowerCase('tr').indexOf(q)<0)return false;
  if(so&&r._kz.s!==so)return false;
  if(si==='uy'&&r.sa!=='al')return false;
  if(si==='uymaz'&&r.sa!=='tr'&&r.sa!=='yok')return false;
  if(si==='erken'&&r.ss!=='erken')return false;
  return true;});
}
function dfKart(l,v,a,c){return '<div class="dfk"><div class="l">'+l+'</div><div class="v'+(c?' '+c:'')+'">'+v+'</div><div class="a">'+a+'</div></div>';}
function dfKartlar(L,hepsi){
 var el=document.getElementById('dfkartlar');
 if(!L.length){el.innerHTML='';return;}
 var net=0,ty=0,kaz=0,zar=0,be=0,en=null,ek=null,gun=0,gn=0;
 L.forEach(function(r){var z=r._kz;net+=z.tl;ty+=z.y;if(z.s==='kaz')kaz++;else if(z.s==='zar')zar++;else be++;if(!en||z.tl>en._kz.tl)en=r;if(!ek||z.tl<ek._kz.tl)ek=r;if(r._g!=null){gun+=r._g;gn++;}});
 var is=(kaz+zar)?kaz/(kaz+zar)*100:null,f=L.length<hepsi?' <span class="pfuy" style="margin:0">süzgeçli</span>':'';
 el.innerHTML=dfKart('Net kâr/zarar'+f,tlf(net),'kapanan işlemler'+(L.some(function(r){return r.k;})?', girilen komisyon düşülmüş':', komisyon girilmediyse düşülmedi'),net>=0?'pos':'neg')+
  dfKart('İsabet',is==null?'—':'%'+Math.round(is),kaz+' kazanç · '+zar+' zarar'+(be?' · '+be+' başa baş (±%0,5, sayılmaz)':''))+
  dfKart('İşlem sayısı',String(L.length),(gn?'ort. '+Math.round(gun/gn)+' gün tutuş':'tutuş süresi için alış tarihi gir')+(L.length<20?' · az işlem: sonuçlar şans olabilir':''))+
  dfKart('Ortalama sonuç',tlf(net/L.length),'işlem başı '+pyz(ty/L.length)+' (eşit ağırlık)',net>=0?'pos':'neg')+
  dfKart('En iyi işlem',hEsc(en.h)+' <span class="'+(en._kz.tl>=0?'pos':'neg')+'" style="font-size:13px">'+tlf(en._kz.tl)+'</span>',pyz(en._kz.y)+(L.length>1?' · en kötü: '+hEsc(ek.h)+' '+tlf(ek._kz.tl):''));
}
function dfKisaTL(x){var a=Math.abs(x),t=a>=1e6?(a/1e6).toLocaleString('tr-TR',{maximumFractionDigits:1})+' mn':a>=1e4?Math.round(a/1e3)+' bin':a>=1e3?(a/1e3).toLocaleString('tr-TR',{maximumFractionDigits:1})+' bin':Math.round(a).toString();return (x>=0?'+':'−')+t;}
function dfEgri(L){
 if(!L.length)return '';
 var s=L.slice().sort(dfSirala),W=640,H=190,pl=58,pr=12,pt=14,pb=26,top=0,y=[0];
 s.forEach(function(r){top+=r._kz.tl;y.push(top);});
 var mn=Math.min.apply(null,y),mx=Math.max.apply(null,y);if(mx===mn){mx+=1;mn-=1;}
 var X=function(i){return pl+(W-pl-pr)*i/(y.length-1||1);},Y=function(v){return pt+(H-pt-pb)*(mx-v)/(mx-mn);};
 var d=y.map(function(v,i){return (i?'L':'M')+X(i).toFixed(1)+' '+Y(v).toFixed(1);}).join(' ');
 var son=y[y.length-1],renk=son>=0?'#1B7F4B':'#B4362E';
 var nok=s.map(function(r,i){return '<circle cx="'+X(i+1).toFixed(1)+'" cy="'+Y(y[i+1]).toFixed(1)+'" r="3.2" fill="'+(r._kz.tl>=0?'#1B7F4B':'#B4362E')+'"><title>'+dfTr(r.s)+' '+hEsc(r.h)+': '+tlf(r._kz.tl)+' · toplam '+tlf(y[i+1])+'</title></circle>';}).join('');
 return '<div class="dfpanel"><h3>📈 Gerçekleşen kâr eğrisi <span class="sgun" style="font-weight:400">(kümülatif, satış sırasıyla)</span></h3>'+
  '<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Kümülatif gerçekleşen kâr">'+
  '<line x1="'+pl+'" x2="'+(W-pr)+'" y1="'+Y(0).toFixed(1)+'" y2="'+Y(0).toFixed(1)+'" stroke="#9AA0A6" stroke-dasharray="4 3"/>'+
  '<text x="'+(pl-6)+'" y="'+(Y(mx)+4).toFixed(1)+'" text-anchor="end" font-size="13" fill="#6B7079">'+dfKisaTL(mx)+'</text>'+
  '<text x="'+(pl-6)+'" y="'+(Y(mn)+4).toFixed(1)+'" text-anchor="end" font-size="13" fill="#6B7079">'+dfKisaTL(mn)+'</text>'+
  (mx>0&&mn<0&&Y(0)-Y(mx)>14&&Y(mn)-Y(0)>14?'<text x="'+(pl-6)+'" y="'+(Y(0)+4).toFixed(1)+'" text-anchor="end" font-size="13" fill="#6B7079">0</text>':'')+
  '<path d="'+d+'" fill="none" stroke="'+renk+'" stroke-width="2.2" stroke-linejoin="round"/>'+nok+
  '<text x="'+pl+'" y="'+(H-6)+'" font-size="13" fill="#6B7079">'+dfTr(s[0].s)+'</text>'+
  '<text x="'+(W-pr)+'" y="'+(H-6)+'" text-anchor="end" font-size="13" fill="#6B7079">'+dfTr(s[s.length-1].s)+' · toplam '+tlf(son)+'</text>'+
  '</svg></div>';
}
function dfAyDegis(n){var p=(dfAy||dfBugun().slice(0,7)).split('-'),d=new Date(+p[0],+p[1]-1+n,1);dfAy=d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2);dfRender();}
function dfTakvim(L){
 if(!dfAy){var son=L.slice().sort(dfSirala).pop();dfAy=(son&&son.s.slice(0,7)!==dfBugun().slice(0,7)&&!L.some(function(r){return r.s.slice(0,7)===dfBugun().slice(0,7);}))?son.s.slice(0,7):dfBugun().slice(0,7);}
 var y=+dfAy.slice(0,4),m=+dfAy.slice(5,7),gun={},top=0,adet=0,bug=dfBugun();
 L.forEach(function(r){if(r.s.slice(0,7)!==dfAy)return;var g=gun[r.s]||(gun[r.s]={tl:0,n:0});g.tl+=r._kz.tl;g.n++;top+=r._kz.tl;adet++;});
 var bas=(new Date(y,m-1,1).getDay()+6)%7,son_=new Date(y,m,0).getDate();
 var h='<div class="dfpanel"><h3>📅 Takvim</h3><div class="dftakbas"><button class="dfbtn kucuk" onclick="dfAyDegis(-1)" aria-label="Önceki ay">‹</button><b>'+DF_AYLAR[m-1]+' '+y+'</b>'+
  '<span class="'+(top>=0?'pos':'neg')+'" style="font-size:12px">'+(adet?tlf(top)+' · '+adet+' işlem':'<span class="sgun">işlem yok</span>')+'</span><button class="dfbtn kucuk" onclick="dfAyDegis(1)" aria-label="Sonraki ay">›</button></div><div class="dftak">';
 ['Pzt','Sal','Çar','Per','Cum','Cmt','Paz'].forEach(function(g){h+='<div class="dgb">'+g+'</div>';});
 for(var i=0;i<bas;i++)h+='<div class="dgk bos"></div>';
 for(var g=1;g<=son_;g++){var t=dfAy+'-'+('0'+g).slice(-2),v=gun[t],c=v?(Math.abs(v.tl)<0.005?'be':v.tl>0?'kaz':'zar'):'';
  h+='<div class="dgk '+c+(t===bug?' bugun':'')+'"'+(v?' title="'+dfTr(t)+': '+v.n+' işlem, '+tlf(v.tl)+'"':'')+'><div class="dgn">'+g+'</div>'+(v?'<div class="dgt">'+dfKisaTL(v.tl)+'</div><div>'+v.n+' işl.</div>':'')+'</div>';}
 return h+'</div><div class="sgun" style="font-size:11px;margin-top:5px">Kutuda o gün kapanan (satılan) işlemlerin toplam kâr/zararı ve sayısı.</div></div>';
}
function dfTablo(L){
 var s=L.slice().sort(dfSirala).reverse();
 var h='<div class="sar" style="margin-top:0"><table class="df"><thead><tr><th>Satış</th><th>Hisse</th><th class="num">Alış → Satış</th><th class="num">Adet</th><th class="num">Kâr/zarar</th><th class="num">%</th><th class="num">Gün</th><th>Sistem (🚀)</th><th>Duygu</th><th>Plan</th><th></th></tr></thead><tbody>';
 s.forEach(function(r){
  var z=r._kz,c=z.s==='be'?'':(z.tl>=0?'pos':'neg'),dg=DF_DUYGU[r.d];
  var bt=dfSilId===r.i?'<span class="dfonay">Silinsin mi? <button class="dfbtn kucuk tehlike" onclick="event.stopPropagation();dfSil(\''+r.i+'\')">Evet, sil</button><button class="dfbtn kucuk" onclick="event.stopPropagation();dfSilSor(null)">Vazgeç</button></span>':
   '<button class="pfsil pfduz" title="Düzenle" aria-label="Düzenle" onclick="event.stopPropagation();dfFormAc(\'duz\',\''+r.i+'\')">✎</button> <button class="pfsil" title="Sil" aria-label="Sil" onclick="event.stopPropagation();dfSilSor(\''+r.i+'\')">🗑</button>';
  h+='<tr onclick="dfAc(\''+r.i+'\')" title="Ayrıntı için tıkla"><td>'+dfTr(r.s)+'</td><td class="kod">'+hEsc(r.h)+((r.pl||r.no)?' <span title="Not var">📝</span>':'')+'</td>'+
   '<td class="num">'+dfSayi(r.m)+' → '+dfSayi(r.f)+'</td><td class="num">'+dfSayi(r.n)+'</td>'+
   '<td class="num '+c+'"><b>'+tlf(z.tl)+'</b></td><td class="num '+c+'">'+pyz(z.y)+'</td><td class="num">'+(r._g!=null?r._g:'—')+'</td>'+
   '<td>'+dfRoz(r)+'</td><td>'+(dg?'<span title="'+hEsc(dg[2])+'">'+dg[0]+' '+dg[1]+'</span>':'<span class="sgun">—</span>')+'</td>'+
   '<td>'+(r.u?DF_PLAN[r.u]:'<span class="sgun">—</span>')+(r.q?' <span class="dfroz" title="'+hEsc(DF_KALITE[r.q]||'')+'">'+r.q+'</span>':'')+'</td><td class="num">'+bt+'</td></tr>';
  if(dfAcikId===r.i){
   var xb=r.x!=null?'<div>📊 Aynı günlerde BIST 100: <b>'+pyz(r.x)+'</b> → '+(z.y>r.x?'<span class="pos">endeksi '+(z.y-r.x).toFixed(1).replace('.',',')+' puan geçtin</span>':'<span class="neg">endeksin '+(r.x-z.y).toFixed(1).replace('.',',')+' puan gerisinde kaldın</span>')+'</div>':'<div class="sgun">📊 BIST 100 kıyası için alış tarihi gerekli.</div>';
   var sa=DF_SA[r.sa||'?']||DF_SA['?'],ss=DF_SS[r.ss||'?']||DF_SS['?'];
   h+='<tr class="dfdetay"><td colspan="11"><div class="dfdk">'+
    '<div>🗓 Alış '+dfTr(r.a)+' · satış '+dfTr(r.s)+(r._g!=null?' · '+r._g+' gün':'')+'</div>'+xb+
    '<div>🚀 Alışta: '+sa[3]+(r.sg?' (sinyal günü '+dfTr(r.sg)+')':'')+'</div>'+
    '<div>🚪 Satışta: '+ss[3]+(r.cg?' (sistem çıkışı '+dfTr(r.cg)+((r.cb&2)?', 🔐 kâr kilidi':'')+((r.cb&1)?', kilitli taban':'')+')':'')+(r.st?' · satış günü stop '+dfSayi(r.st,2)+' TL':'')+(r.gs?' · gösterge SAT '+dfTr(r.gs)+'\'den beri':'')+'</div>'+
    '<div>💸 Komisyon: '+(r.k?dfSayi(r.k,2)+' TL':'girilmedi (0)')+(r.q?' · Kalite '+hEsc(DF_KALITE[r.q]||r.q):'')+'</div>'+
    '<div>📝 Plan: '+(r.pl?'<span class="dfmetin">'+hEsc(r.pl)+'</span>':'<span class="sgun">'+(r.kn?'bu cihazda değil (GitHub sınırı)':'—')+'</span>')+'</div>'+
    '<div>💡 Not: '+(r.no?'<span class="dfmetin">'+hEsc(r.no)+'</span>':'<span class="sgun">—</span>')+'</div>'+
    '</div></td></tr>';
  }
 });
 return h+'</tbody></table></div>';
}
// --- Analiz: gruplara göre sonuç + kısa çıkarımlar (grup başına en az DF_MIN işlem; az işlemde şans uyarısı)
function dfGrup(L,fn,sira,ad){
 var g={};L.forEach(function(r){var k=fn(r);if(k==null)return;var x=g[k]||(g[k]={n:0,kaz:0,zar:0,tl:0,y:0});x.n++;x.tl+=r._kz.tl;x.y+=r._kz.y;if(r._kz.s==='kaz')x.kaz++;else if(r._kz.s==='zar')x.zar++;});
 return sira.filter(function(k){return g[k];}).map(function(k){var x=g[k];return {k:k,ad:ad(k),n:x.n,tl:x.tl,oy:x.y/x.n,is:(x.kaz+x.zar)?x.kaz/(x.kaz+x.zar)*100:null};});
}
function dfGrupHtml(baslik,G,alt){
 if(!G.length)return '<div class="dfpanel dfat"><h3>'+baslik+'</h3><div class="dfaz">Bu bilgi henüz girilmemiş.</div></div>';
 var h='<div class="dfpanel dfat"><h3>'+baslik+'</h3><div class="sar" style="margin-top:0;border:none;background:none"><table><thead><tr><th>Grup</th><th class="num">İşlem</th><th class="num">İsabet</th><th class="num">Net</th><th class="num">Ort.</th></tr></thead><tbody>';
 G.forEach(function(x){var az=x.n<DF_MIN;h+='<tr'+(az?' class="dfaz" title="Daha fazla veri gerekli (en az '+DF_MIN+' işlem)"':'')+'><td>'+x.ad+(az?' <span class="sgun">· az veri</span>':'')+'</td><td class="num">'+x.n+'</td><td class="num">'+(x.is==null?'—':'%'+Math.round(x.is))+'</td><td class="num '+(az?'':(x.tl>=0?'pos':'neg'))+'">'+dfKisaTL(x.tl)+'</td><td class="num">'+pyz(x.oy)+'</td></tr>';});
 h+='</tbody></table></div>';
 if(G.every(function(x){return x.n<DF_MIN;}))h+='<div class="sgun" style="font-size:11.5px">Daha fazla veri gerekli: bir grubu yorumlamak için en az '+DF_MIN+' işlem.</div>';
 return h+(alt?'<div class="sgun" style="font-size:11.5px;margin-top:4px">'+alt+'</div>':'')+'</div>';
}
function dfAnaliz(L){
 if(!L.length)return '';
 var dg=dfGrup(L,function(r){return r.d||null;},Object.keys(DF_DUYGU),function(k){return DF_DUYGU[k][0]+' '+DF_DUYGU[k][1];});
 var pl=dfGrup(L,function(r){return r.u||null;},['e','k','h'],function(k){return DF_PLAN[k];});
 var ka=dfGrup(L,function(r){return r.q||null;},['A','B','C'],function(k){return k;});
 var sa=dfGrup(L,function(r){return r.sa||'?';},['al','tr','yok','?'],function(k){return DF_SA[k][0];});
 var ss=dfGrup(L,function(r){return r.ss||'?';},['ayni','stopalti','erken','cikti','yok','?'],function(k){return DF_SS[k][0];});
 var su=dfGrup(L,function(r){return r._g==null?null:r._g<=5?'a':r._g<=30?'b':'c';},['a','b','c'],function(k){return {a:'≤ 5 gün',b:'6-30 gün',c:'30+ gün'}[k];});
 var xl=L.filter(function(r){return r.x!=null;}),xy=xl.filter(function(r){return r._kz.y>r.x;}).length,xf=0;xl.forEach(function(r){xf+=r._kz.y-r.x;});
 var xh='<div class="dfpanel dfat"><h3>📊 BIST 100\'ü yendiğin işlemler</h3>'+(xl.length?'<div style="font-size:13px"><b>'+xl.length+'</b> işlemin <b>'+xy+'</b>\''+dfEk(xy)+' (<b>%'+Math.round(xy/xl.length*100)+'</b>) aynı günlerde BIST 100 almaktan iyi sonuç aldın; ortalama fark <b class="'+(xf>=0?'pos':'neg')+'">'+(xf>=0?'+':'−')+Math.abs(xf/xl.length).toFixed(1).replace('.',',')+' puan</b>.</div>'+(xl.length<DF_MIN?'<div class="sgun" style="font-size:11.5px">Daha fazla veri gerekli.</div>':''):'<div class="dfaz">Kıyas için işlemlerde alış tarihi gerekli.</div>')+
  '<div class="sgun" style="font-size:11.5px;margin-top:4px">Temettü iki tarafta da yok; komisyon sadece girdiysen düşülür.</div></div>';
 // çıkarımlar
 var c=[],tam=function(G,k){return G.filter(function(x){return x.k===k&&x.n>=DF_MIN;})[0];};
 var dgs=dg.filter(function(x){return x.n>=DF_MIN;}).sort(function(a,b){return Math.abs(b.tl)-Math.abs(a.tl);}).slice(0,2);
 dgs.forEach(function(x){c.push(x.ad+' duygusuyla girdiğin '+x.n+' işlem toplam <b class="'+(x.tl>=0?'pos':'neg')+'">'+tlf(x.tl)+'</b> (ortalama '+pyz(x.oy)+').');});
 var pe=tam(pl,'e'),ph=tam(pl,'h');if(pe&&ph)c.push('Planına uyduğun işlemlerde ortalama <b>'+pyz(pe.oy)+'</b>, uymadığında <b>'+pyz(ph.oy)+'</b>.');
 else if(ph&&ph.tl<0)c.push('Planına uymadığın '+ph.n+' işlem toplam <b class="neg">'+tlf(ph.tl)+'</b>.');
 var qa=tam(ka,'A'),qc=tam(ka,'C');if(qa&&qc)c.push('A kalite işlemlerin ortalama <b>'+pyz(qa.oy)+'</b>, C kalite (dürtüsel) olanlar <b>'+pyz(qc.oy)+'</b>.');
 var al=tam(sa,'al'),yk=tam(sa,'yok');if(al&&yk)c.push('Sistemin 🚀 AL verdiği günlerde aldıkların ortalama <b>'+pyz(al.oy)+'</b>; sistem dışı aldıkların <b>'+pyz(yk.oy)+'</b>.');
 else if(yk)c.push('Sistem dışı (🚀 AL yokken) aldığın '+yk.n+' işlem: toplam <b class="'+(yk.tl>=0?'pos':'neg')+'">'+tlf(yk.tl)+'</b>, isabet %'+Math.round(yk.is||0)+'.');
 var er=tam(ss,'erken');if(er)c.push('Sistem hâlâ AL\'deyken erken çıktığın '+er.n+' işlemin ortalaması <b>'+pyz(er.oy)+'</b>. (Testlerde erken çıkış büyük yükselişleri sık kesti; bu işlemlerden sonra hisse ne yaptı, ara ara bak.)');
 var gc=tam(ss,'cikti');if(gc)c.push('Sistem çıktıktan sonra hâlâ tuttuğun '+gc.n+' işlemin ortalaması <b>'+pyz(gc.oy)+'</b>.');
 var sx=su.filter(function(x){return x.n>=DF_MIN;});if(sx.length>=2){sx.sort(function(a,b){return b.oy-a.oy;});c.push('En iyi sonuç <b>'+sx[0].ad+'</b> tuttuklarında (ort. '+pyz(sx[0].oy)+'), en zayıf <b>'+sx[sx.length-1].ad+'</b> tuttuklarında (ort. '+pyz(sx[sx.length-1].oy)+').');}
 if(xl.length>=DF_MIN)c.push('İşlemlerinin %'+Math.round(xy/xl.length*100)+'\''+dfEk(Math.round(xy/xl.length*100))+' aynı günlerde BIST 100\'den iyi sonuç aldın.');
 var n=L.length;
 var h='<div class="dfcik"><b>🧠 Ne görüyorum?</b>'+(c.length?'<ul>'+c.map(function(x){return '<li>'+x+'</li>';}).join('')+'</ul>':'<div class="dfaz">Henüz yorum için yeterli veri yok: bir grubun yorumlanması için en az '+DF_MIN+' işlem gerekiyor. Satışlarda duygu / plan / kalite alanlarını doldurdukça burası dolar.</div>')+
  '<div class="dfsans">⚠️ <b>Şansa dikkat:</b> '+(n<20?'Şu an '+n+' işlem var. Bu kadar az işlemde iyi ya da kötü sonuç büyük ölçüde şans olabilir; bir desene güvenmek için en az 20-30 işlem bekle.':n+' işlem var; yine de bir grubun iyi görünmesi o koşulun her zaman iyi olduğunu kanıtlamaz — birkaç büyük işlem ortalamayı tek başına çekebilir.')+' Geçmiş sonuç geleceği garanti etmez.</div></div>';
 return h+'<div class="dfgrid">'+dfGrupHtml('🙂 Duyguya göre',dg,'Duygu seçmediğin işlemler bu tabloda yok.')+dfGrupHtml('📋 Planına uyma',pl)+dfGrupHtml('🏅 Kaliteye göre',ka,'Kalite karara göre: A planlı, C dürtüsel.')+
  dfGrupHtml('🚀 Alışta sistem',sa,'Sisteme uyduğun (🚀 AL\'de) ve uymadığın işlemler. "Geç giriş": AL 5 işlem gününden eskiydi.')+dfGrupHtml('🚪 Satışta sistem',ss,'"Erken çıkış": sattığın gün sistem hâlâ AL\'deydi. "Geç çıkış": sistem senden önce çıkmıştı.')+
  dfGrupHtml('⏱️ Tutma süresine göre',su,'Alış tarihi olmayan işlemler bu tabloda yok.')+xh+'</div>';
}
function dfRender(){
 var o=dfOku(),oz=document.getElementById('dfozet'),gv=document.getElementById('dfgovde');if(!gv)return;
 var net=0;o.k.forEach(function(r){net+=dfKZ(r).tl;});
 oz.innerHTML=o.k.length?o.k.length+' işlem · net <b class="'+(net>=0?'pos':'neg')+'">'+tlf(net)+'</b>':'henüz kayıt yok';
 if(!o.k.length){document.getElementById('dfkartlar').innerHTML='';gv.innerHTML='<div class="pfy bos">Henüz kapanmış işlem yok. Portföyünde bir hisseyi sattığında satırdaki <b>Sattım</b>\'a bas (kısmi satış da olur) ya da <b>+ Geçmiş işlem</b> ile eski bir işlemi ekle.</div>';return;}
 var L=dfSuz(o);dfKartlar(L,o.k.length);
 if(!L.length){gv.innerHTML='<div class="pfy bos">Süzgece uyan işlem yok.</div>';return;}
 gv.innerHTML='<div class="dfgrid" style="margin-top:0">'+dfEgri(L)+dfTakvim(L)+'</div>'+dfTablo(L)+dfAnaliz(L);
}
function dfBaslat(){
 var b=document.getElementById('dfbox');if(!b)return;
 var ac=null;try{ac=localStorage.getItem(DF_ACIK_KEY);}catch(e){}
 if(ac==='1')b.open=true;
 dfIsaretle(dfOku(),dfBulutHazirla(dfOku()));dfRender();dfBulutOku();
}

// --- CSV yedeği (Excel Türkçe: UTF-8 BOM, ';' ayırıcı, ondalık virgül) ve içe aktarma (virgül ya da nokta; mevcut kayıtlar silinmez, aynı id atlanır)
var DF_CSV=[['id','i'],['hisse','h'],['alis_tarihi','a'],['satis_tarihi','s'],['adet','n','#'],['alis_fiyati','m','#'],['satis_fiyati','f','#'],['komisyon_tl','k','#'],
 ['kar_zarar_tl',null],['yuzde',null],['gun',null],['bist100_yuzde','x','#'],['alis_sistem','sa','sa'],['satis_sistem','ss','ss'],['sinyal_gunu','sg'],['sistem_cikis_gunu','cg'],
 ['cikis_bit','cb','#'],['satis_gunu_stop','st','#'],['gosterge_sat_tarihi','gs'],['duygu','d','d'],['plana_uydu','u','u'],['kalite','q'],['plan','pl','m'],['not','no','m'],['kayit_zamani','t','#']];
function dfCsvHucre(v){v=v==null?'':String(v);return /[;"\r\n]/.test(v)||/^\s|\s$/.test(v)?'"'+v.replace(/"/g,'""')+'"':v;}
function dfCsvSayi(x){return x==null||x===''?'':(Number.isInteger(+x)?String(+x):String(Math.round(x*1e6)/1e6).replace('.',','));}
function dfCsvMetin(v){return v&&/^[=+\-@\t\r]/.test(v)?'\''+v:v;}  // Excel formül sanmasın
function dfCsvIndir(){
 var o=dfOku();if(!o.k.length){dfNot('İndirilecek kayıt yok.');return;}
 var sat=[DF_CSV.map(function(c){return c[0];}).join(';')];
 o.k.slice().sort(dfSirala).forEach(function(r){var z=dfKZ(r);
  sat.push(DF_CSV.map(function(c){var k=c[1],t=c[2],v;
   if(c[0]==='kar_zarar_tl')v=dfCsvSayi(Math.round(z.tl*100)/100);else if(c[0]==='yuzde')v=dfCsvSayi(Math.round(z.y*100)/100);else if(c[0]==='gun'){var g=dfGun(r.a,r.s);v=g==null?'':g;}
   else if(t==='#')v=dfCsvSayi(r[k]);else if(t==='sa')v=r.sa?(DF_SA[r.sa]||DF_SA['?'])[1]:'';else if(t==='ss')v=r.ss?(DF_SS[r.ss]||DF_SS['?'])[1]:'';else if(t==='d')v=r.d&&DF_DUYGU[r.d]?DF_DUYGU[r.d][1]:'';
   else if(t==='u')v=r.u?DF_PLAN[r.u]:'';else if(t==='m')v=dfCsvMetin(r[k]||'');else v=r[k]==null?'':r[k];
   return dfCsvHucre(v);}).join(';'));});
 var blob=new Blob(['﻿'+sat.join('\r\n')+'\r\n'],{type:'text/csv;charset=utf-8'}),a=document.createElement('a');
 a.href=URL.createObjectURL(blob);a.download='islem-defteri-'+dfBugun()+'.csv';document.body.appendChild(a);a.click();
 setTimeout(function(){URL.revokeObjectURL(a.href);a.remove();},1000);
 dfNot('⬇ CSV yedeği indirildi ('+o.k.length+' işlem). Excel\'de açılır; notlar dahil, bu dosyayı kimseyle paylaşma.');
}
function dfCsvAyristir(t,ay){
 var sat=[],h=[],v='',q=false,i=0,c;
 for(;i<t.length;i++){c=t[i];
  if(q){if(c==='"'){if(t[i+1]==='"'){v+='"';i++;}else q=false;}else v+=c;}
  else if(c==='"')q=true;else if(c===ay){h.push(v);v='';}
  else if(c==='\n'||c==='\r'){if(c==='\r'&&t[i+1]==='\n')i++;h.push(v);v='';if(h.length>1||h[0]!=='')sat.push(h);h=[];}
  else v+=c;}
 if(v!==''||h.length){h.push(v);sat.push(h);}
 return sat;
}
function dfCsvSayiOku(s){s=String(s||'').replace(/\s|TL|%/g,'');if(!s)return null;
 if(s.indexOf(',')>=0&&s.indexOf('.')>=0){if(s.lastIndexOf(',')>s.lastIndexOf('.'))s=s.replace(/\./g,'').replace(',','.');else s=s.replace(/,/g,'');}
 else s=s.replace(',','.');
 var x=parseFloat(s);return isFinite(x)?x:null;}
function dfCsvTarih(s){s=String(s||'').trim();if(!s)return '';var m;
 if(/^\d{4}-\d{2}-\d{2}/.test(s))return s.slice(0,10);
 if((m=s.match(/^(\d{1,2})[.\/](\d{1,2})[.\/](\d{4})/)))return m[3]+'-'+('0'+m[2]).slice(-2)+'-'+('0'+m[1]).slice(-2);
 return null;}
function dfKodBul(obj,v,ix){v=String(v||'').trim();if(!v)return '';var lv=v.toLocaleLowerCase('tr');
 for(var k in obj){var o=obj[k],e=Array.isArray(o)?o[ix]:o;if(k.toLocaleLowerCase('tr')===lv||(e&&String(e).toLocaleLowerCase('tr')===lv))return k;}return null;}
function dfCsvOku(inp){
 var dosya=inp.files&&inp.files[0];if(!dosya)return;
 var fr=new FileReader();
 fr.onload=function(){
  try{dfCsvIceAl(String(fr.result||''));}catch(e){dfNot('⚠ Dosya okunamadı: '+hEsc(e.message||e));}
  inp.value='';
 };
 fr.onerror=function(){dfNot('⚠ Dosya okunamadı.');inp.value='';};
 fr.readAsText(dosya,'utf-8');
}
function dfCsvIceAl(t){
 t=t.replace(/^﻿/,'');
 var ilk=t.split(/\r?\n/)[0]||'';if(/^sep=/i.test(ilk)){t=t.slice(ilk.length).replace(/^\r?\n/,'');ilk=t.split(/\r?\n/)[0]||'';}
 var ay=ilk.indexOf(';')>=0?';':(ilk.indexOf('\t')>=0?'\t':',');
 var S=dfCsvAyristir(t,ay);if(S.length<2){dfNot('⚠ Dosyada kayıt bulunamadı.');return 0;}
 var bas=S[0].map(function(x){return x.trim().toLocaleLowerCase('tr');}),ix={};DF_CSV.forEach(function(c){ix[c[0]]=bas.indexOf(c[0]);});
 if(ix.hisse<0||ix.satis_tarihi<0||ix.adet<0||ix.alis_fiyati<0||ix.satis_fiyati<0){dfNot('⚠ Sütun başlıkları tanınmadı. Bu panonun <b>⬇ CSV yedeği</b> ile indirdiğin dosyayı kullan (hisse; satis_tarihi; adet; alis_fiyati; satis_fiyati gerekli).');return 0;}
 var o=dfOku(),var_={},ekle=0,atla=0,hata=0;o.k.forEach(function(r){var_[r.i]=1;});
 S.slice(1).forEach(function(sat){
  var al=function(ad){var j=ix[ad];return j>=0&&j<sat.length?sat[j]:'';};
  var r={},tamam=true;
  DF_CSV.forEach(function(c){var k=c[1],tp=c[2];if(!k)return;var v=al(c[0]);if(v==null||String(v).trim()===''){return;}
   if(tp==='#'){var x=dfCsvSayiOku(v);if(x!=null)r[k]=x;}
   else if(tp==='sa'){var a=dfKodBul(DF_SA,v,1);if(a)r.sa=a;}
   else if(tp==='ss'){var b=dfKodBul(DF_SS,v,1);if(b)r.ss=b;}
   else if(tp==='d'){var d=dfKodBul(DF_DUYGU,v,1);if(d)r.d=d;}
   else if(tp==='u'){var u=dfKodBul(DF_PLAN,v);if(u)r.u=u;}
   else if(tp==='m'){v=String(v);if(/^'[=+\-@\t\r]/.test(v))v=v.slice(1);r[k]=v.slice(0,1000);}
   else if(k==='a'||k==='s'||k==='sg'||k==='cg'||k==='gs'){var tt=dfCsvTarih(v);if(tt===null){if(k==='s'||k==='a')tamam=false;}else if(tt)r[k]=tt;}
   else if(k==='q'){v=String(v).trim().toUpperCase();if(DF_KALITE[v])r.q=v;}
   else r[k]=String(v).trim();});
  if(r.h)r.h=r.h.toLocaleUpperCase('tr').replace(/[^A-Z0-9ÇĞİÖŞÜ]/g,'').slice(0,12);
  if(!tamam||!r.h||!r.s||!(r.n>0)||!(r.m>0)||!(r.f>0)){hata++;return;}
  if(r.i&&var_[r.i]){atla++;return;}
  if(!r.i||!/^[A-Za-z0-9]{4,40}$/.test(r.i))r.i=dfId(o);
  if(r.cb!=null)r.cb=Math.round(r.cb)&3;if(!r.cb)delete r.cb;if(!r.k)delete r.k;
  if(!r.t)r.t=Date.now();
  if(!r.sa||!r.ss)dfOtoKoy(r,dfSinyal(r.h,r.a,r.s,r.f,null));
  o.k.push(r);var_[r.i]=1;ekle++;});
 if(ekle)dfYaz(o);
 dfRender();
 dfNot('⬆ İçe aktarma: <b>'+ekle+'</b> işlem eklendi'+(atla?', '+atla+' işlem zaten defterde vardı (atlandı)':'')+(hata?', '+hata+' satır eksik/hatalı olduğu için alınmadı':'')+'.');
 return ekle;
}
(function(){var dl=document.getElementById('pfkodlar');if(dl){dl.innerHTML=Object.keys(DATA).sort().map(function(k){return '<option value="'+k+'"></option>';}).join('');}pfRender();pfBulutOku();alBulutOku();tabloDuzen();favBulutOku();bugunRender();dfBaslat();})();
</script></body></html>"""


_GECMIS = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Sinyal Geçmişi</title>
<style>
:root{--bg:#FAFAF8;--ink:#16181D;--muted:#6B7079;--line:#E6E7E4;--accent:#0E4D45;--pos:#1B7F4B;--neg:#B4362E;--panel:#FFF}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;font-feature-settings:"tnum" 1}
.wrap{max-width:1000px;margin:0 auto;padding:26px 18px 60px}
a.geri{color:var(--accent);text-decoration:none;font-weight:600;font-size:13px}
h1{font-size:19px;margin:10px 0 2px}.tarih{color:var(--muted);font-size:12.5px}
.kartlar{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:20px 0}
.k{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.k .b{font-size:26px;font-weight:680}.k .l{color:var(--muted);font-size:12px;margin-top:3px}
h2{font-size:15px;margin:22px 0 8px}
.sar{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--panel)}
table{width:100%;border-collapse:collapse;font-size:13px;min-width:560px}
th,td{padding:9px 11px;text-align:left;white-space:nowrap}th{color:var(--muted);font-weight:600;font-size:11.5px;border-bottom:1px solid var(--line)}
tbody tr{border-bottom:1px solid var(--line)}tbody tr:last-child{border-bottom:none}
.kod{font-weight:650}.num{text-align:right;font-variant-numeric:tabular-nums}.stop{color:var(--neg)}.pos{color:var(--pos)}.neg{color:var(--neg)}
.not{margin-top:22px;padding:13px 15px;border:1px solid var(--line);border-radius:10px;background:#fff;color:var(--muted);font-size:12px;line-height:1.6}
.eskib{font-size:9.5px;font-weight:700;padding:2px 6px;border-radius:5px;margin-left:5px;background:#F1F1EE;color:#6B7079}
</style></head><body><div class="wrap">
<a class="geri" href="index.html">← Panoya dön</a>
<h1>Sinyal Geçmişi (canlı karne)</h1><div class="tarih">Güncelleme: __TARIH__</div>
<div class="kartlar">
<div class="k"><div class="b">%__ISABET__</div><div class="l">kapanan 🚀 v3 sinyallerinde isabet</div></div>
<div class="k"><div class="b">__KAPANAN__</div><div class="l">kapanan sinyal sayısı</div></div>
<div class="k"><div class="b">%__ORT__</div><div class="l">kapananların ortalama sonucu</div></div>
<div class="k"><div class="b">__ACIK__</div><div class="l">şu an açık takip</div></div>
</div>
__ESKI__
<h2>Açık pozisyonlar (takipte)</h2>
<div class="sar"><table><thead><tr><th>Hisse</th><th>Sinyal tarihi</th><th class="num">Giriş</th><th class="num">Güncel</th><th class="num">Anlık %</th><th class="num">Stop</th></tr></thead><tbody>__ACIKROWS__</tbody></table></div>
<h2>Kapanmış sinyaller</h2>
<div class="sar"><table><thead><tr><th>Hisse</th><th>Giriş tarihi</th><th class="num">Giriş</th><th>Çıkış tarihi</th><th class="num">Çıkış</th><th class="num">Sonuç %</th><th>Sebep</th></tr></thead><tbody>__KAPALIROWS__</tbody></table></div>
<div class="not">Bu sayfa <b>ileriye dönük gerçek</b> karnedir ve canlıdaki (v3) kuralların aynısını uygular: 🚀 trend kırılımı günü kapanış fiyatını kaydeder (trend şablonunda 20 günlük zirve kırılımı; aşırı oynak ya da taban serisinde olmayan hisseler; piyasa zayıfken kayıt açılmaz); fiyat, kayıttan beri görülen en yüksek kapanışın %20 altına inerse (iz stop) kapatıp sonucu yazar. SAT sinyali tek başına kapatmaz. Aynı AL dalgası bir kez sayılır.__KKKARNE__ (Eylül 2026 öncesi kayıtlar eski, daha gevşek kurallarla açılmıştı.) Backtest geçmişi simüle eder; bu sayfa ise sistemin <b>bugünden itibaren</b> gerçek performansını biriktirir. Yatırım tavsiyesi değildir.</div>
</div></body></html>"""
