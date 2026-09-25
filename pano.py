# -*- coding: utf-8 -*-
"""Etkileşimli pano: satıra tıkla -> grafik + o hisseye özel yorum + TradingView linki."""
import json
import pandas as pd

RENK = {"AL": "al", "NÖTR": "notr", "SAT": "sat"}


def _simdi():
    """Türkiye saati (Actions sunucusu UTC'de çalışır)."""
    return pd.Timestamp.now(tz="Europe/Istanbul").strftime("%d.%m.%Y %H:%M")


def _med(xs):
    xs = sorted(x for x in xs if x)
    return xs[len(xs) // 2] if xs else None


def pano_uret(sonuclar, ornek=False, uyari=None, piyasa=None, yeni_arzlar=None, endeks=None):
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
        yildiz = ' <span class="yildiz">★</span>' if s.get("guclu") else ""
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
        if s.get("arz"):
            sdrz += ' <span class="arzb" title="Son 12 ayın halka arzı">ARZ</span>'
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
            f'<tr onclick="ac(\'{k}\')">'
            f'<td class="kod">{k}</td>'
            f'<td class="num">{s.get("fiyat","—")}</td>'
            f'<td class="num {dcls}">{dtxt}</td>'
            f'<td><span class="pill {RENK[s["sinyal"]]}{ncls}"{ntit}>{s["sinyal"]}</span>{yildiz}{yenirz}{sdrz}</td>'
            f'<td class="num sgun">{sgunt}</td>'
            f'<td class="num uyum">{s.get("uyum","—")}</td>'
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
            "oynak": bool(s.get("oynak")), "vol60": s.get("vol60"), "trend": bool(s.get("trend")), "v2_uygun": bool(s.get("v2_uygun")),
            "hedef": s.get("hedef"), "sinyal_gun": s.get("sinyal_gun"), "notr_kaynak": s.get("notr_kaynak"),
            "sinyal_tarih": s.get("sinyal_tarih"), "sinyal_degisim": s.get("sinyal_degisim"),
            "uyum": s.get("uyum"), "detay": s.get("detay", []), "ek": s.get("ek", []),
            "gerekce": s.get("gerekce", []), "yorum": s.get("yorum", ""),
            "spark": s.get("spark", {}),
            "al_stop": s.get("al_stop"), "al_tarih": s.get("al_tarih"), "hacim_kat": s.get("hacim_kat"),
            "hacim_teyit": bool(s.get("hacim_teyit")), "taban15": s.get("taban15"), "patlak": bool(s.get("patlak")),
            "arz": s.get("arz"), "sektor": s.get("sektor"), "endustri": s.get("endustri"), "mom20": s.get("mom20"), "uv": s.get("uv"), "bayrak": s.get("bayrak"), "bilanco": s.get("bilanco"), "temettu": s.get("temettu"),
        }

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
    for a, b in [("__TARIH__", tarih), ("__AL__", str(al)), ("__GUCLU__", str(guclu)),
                 ("__TOPLAM__", str(len(sonuclar))), ("__BANNER__", banner),
                 ("__ROWS__", "".join(rows)), ("__ARZ__", arzblok),
                 ("__XU__", json.dumps(endeks)),
                 ("__DATA__", json.dumps(veri, ensure_ascii=False))]:
        html = html.replace(a, b)
    return html


def gecmis_uret(acik, kapali, ozet):
    """Sinyal geçmişi sayfası: açık pozisyonlar + kapanmış sinyaller + karne."""
    def satirlar(kayitlar, acikmi):
        out = []
        for r in sorted(kayitlar, key=lambda x: x.get("giris_tarih", ""), reverse=True):
            if acikmi:
                s = r.get("anlik")
                scls = "pos" if (s or 0) >= 0 else "neg"
                stxt = f"{'+' if (s or 0) >= 0 else ''}{s}%" if s is not None else "—"
                out.append(f'<tr><td class="kod">{r["kod"]}</td><td>{r["giris_tarih"]}</td>'
                           f'<td class="num">{r["giris_fiyat"]}</td><td class="num">{r.get("guncel","—")}</td>'
                           f'<td class="num {scls}">{stxt}</td><td class="num stop">{r["stop"]}</td></tr>')
            else:
                s = r.get("sonuc")
                scls = "pos" if (s or 0) >= 0 else "neg"
                stxt = f"{'+' if (s or 0) >= 0 else ''}{s}%" if s is not None else "—"
                out.append(f'<tr><td class="kod">{r["kod"]}</td><td>{r["giris_tarih"]}</td>'
                           f'<td class="num">{r["giris_fiyat"]}</td><td>{r.get("cikis_tarih","—")}</td>'
                           f'<td class="num">{r.get("cikis_fiyat","—")}</td>'
                           f'<td class="num {scls}">{stxt}</td><td>{r.get("sebep","—")}</td></tr>')
        return "".join(out) or '<tr><td colspan="7" style="color:#6B7079">Kayıt yok.</td></tr>'

    html = _GECMIS
    reps = {
        "__ISABET__": str(ozet.get("isabet", "—")), "__KAPANAN__": str(ozet.get("kapanan", 0)),
        "__ORT__": str(ozet.get("ort", "—")), "__ACIK__": str(ozet.get("acik", 0)),
        "__ACIKROWS__": satirlar(acik, True), "__KAPALIROWS__": satirlar(kapali, False),
        "__TARIH__": _simdi(),
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
th,td{padding:11px 12px;text-align:left;white-space:nowrap}
th{position:sticky;top:0;background:var(--panel);color:var(--muted);font-weight:600;font-size:12px;
border-bottom:1px solid var(--line);cursor:pointer;user-select:none}th:hover{color:var(--ink)}
tbody tr{border-bottom:1px solid var(--line);cursor:pointer}tbody tr:last-child{border-bottom:none}
tbody tr:hover{background:#F2F5F3}
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
.alsat{font-size:13px;margin:3px 0;display:flex;align-items:center;gap:8px}
.bilb{background:#EEF1F8;color:#2F4A7A;font-size:9.5px;font-weight:700;padding:2px 6px;border-radius:5px;margin-left:5px;white-space:nowrap}
.bilkutu{margin:0 0 14px;border:1px solid var(--line);border-radius:10px;padding:10px 14px;font-size:13px;line-height:1.55}
.bilkutu svg{display:block;width:100%;max-width:420px;height:auto;margin-top:6px}
.uvsb{background:#E4F2E9;color:#14633A;font-size:9.5px;font-weight:700;padding:2px 6px;border-radius:5px;margin-left:5px;white-space:nowrap}
.bayrakb{font-size:11px;margin-left:4px}
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
.uyari{margin-top:28px;padding:13px 16px;border:1px solid var(--line);border-radius:10px;background:#fff;color:var(--muted);font-size:12.2px;line-height:1.6}
.glink{color:var(--accent);font-weight:600;text-decoration:none}.glink:hover{text-decoration:underline}
.pfbox{margin-top:18px}
.pfbas{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:8px}
.pfbas h2{margin:0;font-size:16px}.pftop{font-weight:650;font-size:14px}.pftop.pos{color:var(--pos)}.pftop.neg{color:var(--neg)}
table.pf{min-width:820px}
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
.leg .c5::before{background:#3A6EA5}.leg .c6::before{background:#B7791F}
.leg{flex-wrap:wrap}
.uyum{font-weight:650;color:var(--accent)}
.uyroz{background:#EEF4F1;color:var(--accent);font-size:11.5px;font-weight:650;padding:2px 8px;border-radius:999px}
.gbas{font-size:13px;font-weight:650;margin:4px 0 8px}
.gliste{display:grid;grid-template-columns:1fr;gap:7px;margin-bottom:12px}
.gi{display:flex;align-items:flex-start;gap:10px;background:#F7F7F4;border-radius:9px;padding:8px 11px}
.gi .pill{flex:none}.gt{display:flex;flex-direction:column;line-height:1.3}.gt b{font-size:12.5px}.gt span{font-size:11.5px;color:var(--muted)}
.ekler{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.ekb{background:#FBF7EE;border:1px solid #EADFC7;border-radius:8px;padding:5px 9px;font-size:11.5px;color:#7A5B10}
@media(max-width:560px){.ozet .b{font-size:30px}}
</style>
</head><body><div class="wrap">
<header><div><h1>BIST Sinyal Panosu</h1><div class="tarih">Son güncelleme: __TARIH__ · <a href="#" onclick="yenile();return false" title="Sayfanın en son halini getirir (önbelleği atlar)">↻ Yenile</a> · <a href="https://github.com/BoranZZ/Bist-signal/actions/workflows/tarama.yml" target="_blank" rel="noopener" title="GitHub'da 'Run workflow' ile taramayı hemen başlat; 3-5 dk sonra Yenile'ye bas">Taramayı şimdi başlat ↗</a></div></div>
<div class="ozet">
<div><div class="b">__AL__</div><div class="l">/ __TOPLAM__ hissede AL</div></div>
<div><div class="b g">__GUCLU__</div><div class="l">★ AL+ (teknik+temel)</div></div>
</div></header>
<div class="ipucu">İncelemek için bir satıra tıkla → grafik, oranlar ve o hisseye özel yorum açılır. Sütun başlığına tıklayınca sıralanır. · <a class="glink" href="gecmis.html">Sinyal Geçmişi →</a></div>
__BANNER__
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
    <label class="pfuv" title="Uzun vadeli tuttuğun hisse: kısa vadeli SAT sinyalleri bilgi olarak gelir, çıkış yerine karar çizgisi (ana destek) gösterilir"><input id="pfuzun" type="checkbox"> Uzun vade</label>
    <button id="pfkaydetbtn" class="pfkaydet" onclick="pfKaydet()">Ekle</button>
    <button class="pfipt" onclick="pfFormKapat()">İptal</button>
  </div>
  <div id="pflist"></div>
</div>
<div class="sar"><table id="t"><thead><tr>
<th data-t="s">Hisse</th><th class="num" data-t="n">Fiyat</th><th class="num" data-t="n">Değişim</th><th data-t="s">Sinyal</th>
<th class="num" data-t="n">Sinyalde</th><th class="num" data-t="n">Uyum</th><th class="num" data-t="n">RSI</th><th class="num" data-t="n">F/K</th><th class="num" data-t="n">PD/DD</th><th class="num" data-t="n">Stop</th><th class="num" data-t="n">Öneri lot</th>
</tr></thead><tbody>__ROWS__</tbody></table></div>
__ARZ__
<div class="aciklama">
<div class="kart"><h3>AL / AL+ / NÖTR / SAT</h3><p>Trend, ortalama dizilimi, MACD kesişimi ve RSI momentumundan bir puan. <b>★ AL+</b>: teknik AL ile birlikte F/K ve PD/DD de grup medyanının altında.</p></div>
<div class="kart"><h3>📈 hacim · ⚡ oynak · ⚠ taban serisi</h3><p><b>📈 hacim</b>: AL günü işlem hacmi son 20 günün 1,5 katından fazla — ilgi arttığını gösterir; ama backtest'te tek başına belirgin bir üstünlük sağlamadı, bilgi amaçlıdır. <b>⚡ oynak</b>: son 60 günde günlük oynaklık %5'ten fazla (spekülatif) — AL mesajı gönderilmez. <b>⚠ taban serisi</b>: son 15 günde 4+ kez ~%10 düştü (fon krizi tipi çöküş) — bu hisselerden AL mesajı gönderilmez.</p></div>
<div class="kart"><h3>🌱 Uzun vade sinyali · 🚩 Bayrak</h3><p><b>🌱 UV AL</b>: yükselen trendde (fiyat 200 günlük ortalamanın üstünde ve o yükseliyor) 50 günlük ortalamaya geri çekilip dönen hisse. 2 gün üst üste 200 günlük ortalamanın altında kapanırsa SAT. Günlük sinyalden yavaş, 3-4 ay tutuş; backtest'te düşük faiz döneminde isabet %65. <b>🚩</b>: boğa bayrağı kırılımı (bilgi amaçlı).</p></div>
<div class="kart"><h3>Piyasa filtresi</h3><p>BIST 100, 50 günlük ortalamasının altındaysa üstte "Piyasa zayıf" uyarısı çıkar. 5 yıllık backtest'te bu dönemlerde gelen AL'ler belirgin şekilde daha kötü sonuç verdi.</p></div>
<div class="kart"><h3>Çıkış (v2) ve hedef</h3><p><b>📍 İz stop</b>: AL'den beri görülen en yüksek kapanışın %20 altı; fiyat yükseldikçe yukarı taşınır, kapanış altına inerse "çık". SAT sinyali tek başına çıkış değildir (gece testleri: SAT'ta çıkmak yükseliş piyasasında kazancı eritiyordu; iz stop 2023'te −%6 yerine +%45). <b>🎯 1. hedef</b>: en yakın direnç — geçmişte satış gelen tepe. <b>🎯 2. hedef</b>: risk/ödül 2:1 (maliyetinden stop'a olan mesafenin 2 katı yukarısı). Hedefler satış emri değil, izleme noktasıdır: 5 yıllık backtest'te hedefte kısmi satış, SAT/stop'a kadar tutmaktan belirgin şekilde kötü sonuç verdi.</p></div>
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
</div>

<div class="ust" id="ust" onclick="if(event.target===this)kapat()"><div class="modal" id="modal"></div></div>
<script>
const DATA=__DATA__;
const XU=__XU__;  // BIST 100: son 2 yıl günlük, öncesi haftalık — portföy-endeks kıyası
const t=document.getElementById('t');
t.querySelectorAll('th').forEach((th,i)=>{th.addEventListener('click',()=>{
const tb=t.tBodies[0],rows=[...tb.rows],num=th.dataset.t==='n',asc=th._asc=!th._asc;
rows.sort((a,b)=>{let x=a.cells[i].innerText.replace('%','').replace('+',''),y=b.cells[i].innerText.replace('%','').replace('+','');
if(num){x=parseFloat(x)||-1e9;y=parseFloat(y)||-1e9;return asc?x-y:y-x;}return asc?x.localeCompare(y,'tr'):y.localeCompare(x,'tr');});
rows.forEach(r=>tb.appendChild(r));});});

function sinyalCls(d){if(d.sinyal==='AL')return 'al';if(d.sinyal==='SAT')return 'sat';
 return 'notr'+(d.notr_kaynak==='AL'?' notr-al':d.notr_kaynak==='SAT'?' notr-sat':'');}
// Büyük grafik: fiyat/tarih eksenleri, AL/SAT dönüş işaretleri, destek/direnç çizgileri, fare/dokunma ile değer
var GR={W:600,H:260,L:6,R:54,T:10,B:24},_gr=null;
var AYLAR=['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara'];
function trTarih(s){var p=s.split('-');return (+p[2])+' '+AYLAR[+p[1]-1];}
function grX(i,n){return GR.L+(n>1?i/(n-1):0)*(GR.W-GR.L-GR.R);}
function grY(v,mn,mx){return GR.T+(1-(v-mn)/(mx-mn||1))*(GR.H-GR.T-GR.B);}
function cizgi(vals,color,mn,mx,w){
 var pts=[],n=vals.length;
 for(var i=0;i<n;i++){if(vals[i]==null)continue;pts.push(grX(i,n).toFixed(1)+','+grY(vals[i],mn,mx).toFixed(1));}
 return '<polyline fill="none" stroke="'+color+'" stroke-width="'+w+'" points="'+pts.join(' ')+'"/>';
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
function grafik(sp,sd){
 if(!sp||!sp.c) return '<div style="color:#6B7079;font-size:13px">Grafik verisi yok.</div>';
 var ds=sd&&sd.destek?sd.destek.fiyat:null,dr=sd&&sd.direnc?sd.direnc.fiyat:null,n=sp.c.length;
 var hepsi=sp.c.concat(sp.s20||[],sp.s50||[],[ds,dr]).filter(function(x){return x!=null;});
 var mn=Math.min.apply(null,hepsi),mx=Math.max.apply(null,hepsi),pay=(mx-mn)*0.04;mn-=pay;mx+=pay;
 _gr={sp:sp,mn:mn,mx:mx,n:n};
 var g='<svg id="grsvg" viewBox="0 0 '+GR.W+' '+GR.H+'" width="100%" style="display:block;touch-action:pan-y" onmousemove="grHover(event)" ontouchstart="grHover(event)" ontouchmove="grHover(event)" onmouseleave="grCik()">';
 adimlar(mn,mx).forEach(function(v){var y=grY(v,mn,mx).toFixed(1);
  g+='<line x1="'+GR.L+'" x2="'+(GR.W-GR.R)+'" y1="'+y+'" y2="'+y+'" stroke="#ECEDEA" stroke-width="1"/>'+
     '<text x="'+(GR.W-GR.R+4)+'" y="'+(+y+3.5)+'" font-size="10" fill="#8A8F98">'+v+'</text>';});
 for(var k=0;k<5;k++){var i=Math.round(k*(n-1)/4),x=grX(i,n);
  g+='<text x="'+x.toFixed(1)+'" y="'+(GR.H-6)+'" font-size="10" fill="#8A8F98" text-anchor="'+(k===0?'start':k===4?'end':'middle')+'">'+trTarih(sp.t[i])+'</text>';}
 if(ds!=null)g+=yatay(ds,'#3A6EA5',mn,mx);
 if(dr!=null)g+=yatay(dr,'#B7791F',mn,mx);
 if(sp.s50)g+=cizgi(sp.s50,'#C7962B',mn,mx,1.2);
 if(sp.s20)g+=cizgi(sp.s20,'#0E4D45',mn,mx,1.2);
 if(sp.st)g+=cizgi(sp.st,'#B4362E',mn,mx,1.3);
 g+=cizgi(sp.c,'#16181D',mn,mx,1.8);
 if(sp.sg){var sonK='';for(var j=0;j<n;j++){var a=sp.sg[j];if(a==='N'||a===sonK){continue;}var ilk=sonK==='';sonK=a;if(ilk||sp.c[j]==null)continue;  // Telegram gibi: NÖTR ara geçişleri sayılmaz
  var xx=grX(j,n),yy=grY(sp.c[j],mn,mx);
  g+=a==='A'?'<path d="M'+xx.toFixed(1)+' '+(yy+6).toFixed(1)+' l-5 9 h10 z" fill="#1B7F4B"><title>AL: '+trTarih(sp.t[j])+'</title></path>'
            :'<path d="M'+xx.toFixed(1)+' '+(yy-6).toFixed(1)+' l-5 -9 h10 z" fill="#B4362E"><title>SAT: '+trTarih(sp.t[j])+'</title></path>';}}
 g+='<line id="grcizgi" x1="0" x2="0" y1="'+GR.T+'" y2="'+(GR.H-GR.B)+'" stroke="#16181D" stroke-width="0.8" stroke-dasharray="3 3" visibility="hidden"/>'+
    '<circle id="grnokta" r="3.5" fill="#16181D" visibility="hidden"/></svg><div id="grbilgi" class="grbilgi" hidden></div>';
 return g;
}
function grHover(e){
 if(!_gr)return;var svg=document.getElementById('grsvg');if(!svg)return;
 var p=e.touches?e.touches[0]:e,r=svg.getBoundingClientRect(),x=(p.clientX-r.left)/r.width*GR.W;
 var n=_gr.n,i=Math.max(0,Math.min(n-1,Math.round((x-GR.L)/(GR.W-GR.L-GR.R)*(n-1)))),sp=_gr.sp;if(sp.c[i]==null)return;
 var xx=grX(i,n),yy=grY(sp.c[i],_gr.mn,_gr.mx),cz=document.getElementById('grcizgi'),nk=document.getElementById('grnokta'),b=document.getElementById('grbilgi');
 cz.setAttribute('x1',xx);cz.setAttribute('x2',xx);cz.setAttribute('visibility','visible');
 nk.setAttribute('cx',xx);nk.setAttribute('cy',yy);nk.setAttribute('visibility','visible');
 var sg={A:'AL',S:'SAT',N:'NÖTR'}[(sp.sg||'')[i]]||'';
 b.innerHTML='<b>'+trTarih(sp.t[i])+' '+sp.t[i].slice(0,4)+'</b> · '+sp.c[i]+' TL'+(sg?' · '+sg:'')+
  (sp.s20&&sp.s20[i]!=null?'<br><span style="color:#0E4D45">SMA20 '+sp.s20[i]+'</span>':'')+(sp.s50&&sp.s50[i]!=null?' · <span style="color:#C7962B">SMA50 '+sp.s50[i]+'</span>':'');
 b.hidden=false;b.style.left=Math.min(Math.max(xx/GR.W*100,2),70)+'%';
}
function grCik(){['grcizgi','grnokta'].forEach(function(id){var el=document.getElementById(id);if(el)el.setAttribute('visibility','hidden');});var b=document.getElementById('grbilgi');if(b)b.hidden=true;}
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
 if(iz&&iz.cikti){pl.izCikti=iz.cikis_tarih;stop=null;}
 else if(iz){stop=iz.stop;pl.iz=true;pl.tepe=iz.tepe;}
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
 if(pl.sat)h+='<div class="pk">ℹ️ Kısa vadeli SAT sinyali — v2\'de çıkış kuralı iz stop; SAT tek başına "çık" demek değil.</div>';
 if(pl.izCikti)h+='<div class="pk neg">📍 <b>İz stop '+pl.izCikti+' tarihinde kırıldı</b> — v2 kuralına göre çıkış zamanı geçti.</div>';
 else if(pl.stop&&pl.iz)h+='<div class="pk">📍 <b>İz stop: '+pl.stop+' TL</b> (AL\'den beri tepe '+pl.tepe+' TL\'nin %20 altı) — '+yzd(pl.stopUzak)+' aşağıda. Buraya inerse sonuç: <b class="'+(pl.stopKz>=0?'pos':'neg')+'">'+tlf(pl.stopKz)+'</b>'+(pl.stopKz>=0?' (yine kârda)':'')+'</div>';
 else if(pl.stop){
  h+=pl.asildi?'<div class="pk neg">📍 <b>Fiyat çıkış seviyesinin ('+pl.stop+' TL) altında</b> — sistemin kuralına göre çıkış zamanı.</div>'
   :'<div class="pk">📍 <b>Çıkış (stop): '+pl.stop+' TL</b> — '+yzd(pl.stopUzak)+' aşağıda. Buraya inerse sonuç: <b class="'+(pl.stopKz>=0?'pos':'neg')+'">'+tlf(pl.stopKz)+'</b>'+(pl.stopKz>=0?' (yine kârda)':'')+'</div>';
 }
 pl.hedefler.forEach(function(x,i){h+='<div class="pk">🎯 <b>'+(i+1)+'. hedef: '+x[0]+' TL</b> — '+x[1]+', '+yzd((x[0]/pl.f-1)*100)+' yukarıda.'+
   (x[1].indexOf('direnç')>=0?' Burada satış baskısı gelebilir; aşarsa yükseliş hızlanabilir.':' (Tahmin değil, izleme noktası.)')+'</div>';});
 if(pl.hedefler.length)h+='<div class="pk sgun">ℹ️ Hedefler satış emri değil, izleme noktası. 5 yıllık backtest\'te hedefte kısmi satış yapmak, pozisyonu SAT/stop gelene kadar tutmaktan belirgin şekilde kötü sonuç verdi — büyük kazançlar erken kesildi.</div>';
 var kural='Kural (v2): kapanış iz stop\'un altına inerse çık. İz stop, fiyat yükseldikçe yukarı taşınır; SAT sinyali tek başına çıkış değildir.';
 return h+'<div class="pk">'+kural+'</div></div>';
}
function uvHtml(d){
 var u=d.uv;if(!u)return '';
 var h='<div class="uvkutu">🌱 <b>Uzun vade sinyali: ';
 if(u.durum==='AL')h+='AL</b> — '+u.tarih+' tarihinden beri ('+u.gun+' işlem günü, '+(u.degisim>=0?'+':'')+u.degisim+'%). Yükselen trendde 50 günlük ortalamaya geri çekilip dönmüştü. Çıkış: 2 gün üst üste 200 günlük ortalamanın ('+u.sma200+' TL) altında kapanış.';
 else if(u.durum==='SAT')h+='SAT</b> — '+u.tarih+' tarihinde fiyat 200 günlük ortalamanın altına indi; uzun vadeli trend bozuk (200 günlük ort. '+u.sma200+' TL).';
 else h+='yok</b>.';
 if(u.durum!=='AL'&&u.trend)h+=' Trend yükselişte; uzun vade AL için 50 günlük ortalamaya ('+u.sma50+' TL) geri çekilme bekleniyor.';
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
function arzHtml(d){
 var z=d.arz;if(!z)return '';
 var g=z.getiri==null?'':' · arzdan beri <b class="'+(z.getiri>=0?'pos':'neg')+'">'+(z.getiri>=0?'+':'')+z.getiri+'%</b>';
 return '<div class="arzkutu">🆕 <b>Halka arz:</b> '+z.tarih+' tarihinde işlem görmeye başladı'+(z.arz_fiyat?' · arz fiyatı <b>'+z.arz_fiyat+' TL</b>':' (bölünmeyle geldi, arz fiyatı yok)')+g+'</div>';
}
function ac(k){
 const d=DATA[k];if(!d)return;
 const dcls=(d.degisim||0)>=0?'pos':'neg';const dtxt=d.degisim==null?'—':((d.degisim>=0?'+':'')+d.degisim+'%');
 const pill='<span class="pill '+sinyalCls(d)+'">'+d.sinyal+'</span>'+(d.guclu?' <span class="yildiz">★</span>':'');
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
   if(d.sinyal==='SAT')zaman+='<div class="cikis">ℹ️ Kısa vadeli SAT. v2\'de çıkış kuralı iz stop'+(d.iz&&!d.iz.cikti?' (<b>'+d.iz.stop+' TL</b>)':'')+'; elindeyse SAT tek başına "çık" demek değil.</div>';
   if(d.sinyal==='AL'){
     const gs=(d.giris_stop!=null?d.giris_stop:d.stop);
     const izs=(d.iz&&!d.iz.cikti)?d.iz.stop:Math.round(d.fiyat*0.8*100)/100;
     zaman+='<div class="cikis">Çıkış kuralı (v2): kapanış <b>iz stop '+izs+' TL</b>\'nin altına inerse (AL\'den beri tepe kapanışın %20 altı; fiyat yükseldikçe yukarı taşınır).'+
       (d.v2_uygun?'':' <i>Not: trend dışı ya da aşırı oynak — v2 filtresine takılıyor.</i>')+
       ((d.hedef&&!pfOku().some(function(x){return x.kod===k;}))?' · Örnek hedef (2R, mekanik referans): <b>'+d.hedef+' TL</b>':'')+'</div>';
   }
   zaman+='</div>';
 }
 document.getElementById('modal').innerHTML=
 '<div class="mh"><div class="sol"><h2>'+k+'</h2>'+pill+uyum+'</div><button class="kapa" onclick="kapat()">✕</button></div>'+
 '<div class="mfiyat">'+(d.fiyat!=null?d.fiyat+' TL':'')+' <span class="'+dcls+'">'+dtxt+'</span>'+
   (d.sektor?' <span class="sektorb">'+d.sektor+(d.endustri&&d.endustri!==d.sektor?' · '+d.endustri:'')+'</span>':'')+'</div>'+
 zaman+
 (d.patlak?'<div class="patlakkutu">⚠ <b>Taban serisi:</b> son 15 günde '+d.taban15+' kez ~%10 düştü. Fon krizi tipi çöküş olabilir; bu hisseden AL mesajı gönderilmez.</div>':'')+
 pozHtml(k,d)+arzHtml(d)+uvHtml(d)+bilHtml(d)+
 '<div class="grafik">'+grafik(d.spark,d.sd)+'<div class="leg"><span class="c1">Fiyat</span><span class="c2">SMA20</span><span class="c3">SMA50</span><span class="c4">SuperTrend</span>'+
   (d.sd&&d.sd.destek?'<span class="c5">Destek</span>':'')+(d.sd&&d.sd.direnc?'<span class="c6">Direnç</span>':'')+
   '<span style="color:#1B7F4B">▲ AL</span><span style="color:#B4362E">▼ SAT</span></div></div>'+
 sdHtml(d)+
 '<div class="metr">'+m('RSI',d.rsi)+m('F/K',d.fk)+m('PD/DD',d.pddd)+m('FD/FAVÖK',d.favok)+m('İz stop',d.iz&&!d.iz.cikti?d.iz.stop:'—')+m('Öneri lot',lot)+'</div>'+
 '<div class="gbas">Göstergeler</div><div class="gliste">'+gost+'</div>'+
 (ekh?'<div class="ekler">'+ekh+'</div>':'')+
 '<div class="yorum">'+(d.yorum||d.gerekce.join(' · '))+'</div>'+
 alarmHtml(k,d)+
 '<div class="btnler"><a class="btn p" href="'+tv+'" target="_blank" rel="noopener">TradingView\'de tam ekran ↗</a></div>';
 document.getElementById('ust').classList.add('acik');
}
function kapat(){document.getElementById('ust').classList.remove('acik');_gr=null;}
document.addEventListener('keydown',e=>{if(e.key==='Escape')kapat();});

var PF_KEY='portfoyum_v1',GH_KEY='gh_anahtar_v1',GH_REPO='BoranZZ/Bist-signal',pfDuzenlenen=-1;
function pfOku(){try{return JSON.parse(localStorage.getItem(PF_KEY))||[]}catch(e){return[]}}
function pfYazYerel(a){try{localStorage.setItem(PF_KEY,JSON.stringify(a))}catch(e){}}
function pfYaz(a){pfYazYerel(a);pfBulutYaz(a);}
function pfNot(t){var n=document.getElementById('pfnot');n.innerHTML=t||'';n.hidden=!t;}
function pfFormAc(i){
 pfDuzenlenen=(typeof i==='number')?i:-1;var p=pfDuzenlenen>=0?pfOku()[i]:null;
 document.getElementById('pfkod').value=p?p.kod:'';document.getElementById('pfkod').disabled=!!p;
 document.getElementById('pfadet').value=p?p.adet:'';document.getElementById('pfmal').value=p?p.maliyet:'';document.getElementById('pfuzun').checked=!!(p&&p.uzun);document.getElementById('pfalis').value=(p&&p.tarih)||'';
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
 pfYaz(a);pfFormKapat();pfRender();pfNot(not);
}
function pfSil(i){var a=pfOku();a.splice(i,1);pfYaz(a);pfRender();pfNot('');}

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
  liste+='<div class="alsat">🔔 '+(x.yon==='ust'?'<b>'+x.fiyat+' TL</b> üstüne çıkınca':'<b>'+x.fiyat+' TL</b> altına inince')+
   ' <button class="pfsil" title="Sil" onclick="alSil('+i+',\''+k+'\')">✕</button></div>';});
 return '<div class="alkutu"><div class="gbas">🔔 Fiyat alarmı</div>'+liste+
  '<div class="pfform" style="display:flex;margin:6px 0 0"><input id="alfiyat" type="number" step="any" min="0" placeholder="Fiyat (TL)" style="width:120px">'+
  '<button class="pfipt" onclick="alEkle(\''+k+'\',\'ust\')">Üstüne çıkınca</button><button class="pfipt" onclick="alEkle(\''+k+'\',\'alt\')">Altına inince</button></div>'+
  '<div class="cikis" id="alnot">'+(ghAnahtar()?'Alarm tetiklenince Telegram\'a bir kez mesaj gelir (her 15 dakikalık taramada kontrol edilir).'
   :'Bu cihaz Telegram\'a bağlı değil: alarm sadece burada kayıtlı, bildirim gelmez. Portföyüm → <b>Telegram\'a bağla</b>.')+'</div></div>';
}
function alEkle(k,yon){
 var f=parseFloat(document.getElementById('alfiyat').value);
 if(!(f>0)){document.getElementById('alnot').textContent='Geçerli bir fiyat gir.';return;}
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
  if(ok){alBulutOku().then(function(v){if(!v)alYaz(alOku());});document.getElementById('pfkur').hidden=true;pfNot('✓ Bağlandı. Portföyündeki değişiklikler artık otomatik olarak Telegram mesajlarına yansıyacak.');}
  else{try{localStorage.removeItem(GH_KEY);}catch(e){}s.textContent='Olmadı: anahtar yanlış ya da "Variables: Read and write" yetkisi yok. Adımları kontrol edip tekrar dene.';pfBulutDurum('yerel');}
 });
}
function ghKaldir(){try{localStorage.removeItem(GH_KEY);}catch(e){}document.getElementById('pfkur').hidden=true;pfBulutDurum('yerel');}

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
 var r='<div class="sar"><table class="pf"><thead><tr><th>Hisse</th><th class="num">Adet</th><th class="num">Maliyet</th><th class="num">Güncel</th><th class="num">K/Z %</th><th class="num">K/Z TL</th><th>Sinyal</th><th class="num">Çıkış (stop)</th><th class="num">Hedef</th><th></th></tr></thead><tbody>';
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
     (function(){if(f==null)return '<td class="num">—</td><td class="num">—</td>';var pl=pozPlan(d,p),h=pl.hedefler.length?pl.hedefler[0][0]:null;
       if(pl.uzun)return '<td class="num stop">'+(pl.karar?(pl.kararAsildi?'<b>🧭 '+pl.karar+' ⚠</b>':'🧭 '+pl.karar+' <span class="sgun">'+yzd(pl.kararUzak)+'</span>'):'—')+'</td>'+
              '<td class="num pos">'+(h?h+' <span class="sgun">'+yzd((h/f-1)*100)+'</span>':'—')+'</td>';
       if(pl.izCikti)return '<td class="num stop"><b>kırıldı ⚠</b></td><td class="num">—</td>';
       return '<td class="num stop">'+(pl.stop?(pl.asildi?'<b>'+pl.stop+' ⚠</b>':pl.stop+' <span class="sgun">'+yzd(pl.stopUzak)+'</span>'):'—')+'</td>'+
              '<td class="num pos">'+(h?h+' <span class="sgun">'+yzd((h/f-1)*100)+'</span>':'—')+'</td>';})()+
     '<td class="num"><button class="pfsil pfduz" title="Düzenle" onclick="event.stopPropagation();pfFormAc('+i+')">✎</button> '+
     '<button class="pfsil" title="Sil" onclick="event.stopPropagation();pfSil('+i+')">✕</button></td></tr>';
 });
 r+='</tbody></table></div>';
 var dag=pfDagilim(a);
 if(dag.length){
  var ust=a.length>=2&&dag[0][1]>40;
  r+='<div class="pfdag'+(ust?' uyar':'')+'">'+(ust?'⚠️ Portföyünün <b>%'+dag[0][1].toFixed(0)+'</b>\'i tek sektörde (<b>'+dag[0][0]+'</b>) — o sektördeki bir haber hepsini birlikte etkiler. ':'')+
     'Dağılım: '+dag.slice(0,5).map(function(x){return x[0]+' %'+x[1].toFixed(0);}).join(' · ')+'</div>';
 }
 var ky=pfKiyas(a);
 if(ky){
  r+='<div class="pfkiyas">📈 <b>Endeksle kıyas</b>'+(ky.n<a.length?' (alış tarihi girilen '+ky.n+'/'+a.length+' hisse)':'')+': portföy <b class="'+(ky.pf>=0?'pos':'neg')+'">'+(ky.pf>=0?'+':'')+ky.pf.toFixed(1)+'%</b> · aynı parayla aynı günlerde BIST 100 alsaydın <b>'+(ky.xu>=0?'+':'')+ky.xu.toFixed(1)+'%</b> → endeksin <b class="'+(ky.fark>=0?'pos':'neg')+'">'+Math.abs(ky.fark).toFixed(1)+' puan '+(ky.fark>=0?'önünde':'gerisinde')+'</b>.'+
     '<span class="pfxu">Temettüler iki tarafta da dahil değil. Kıyas için hisse eklerken/düzenlerken alış tarihini gir.</span></div>';
 }else if(XU)r+='<div class="pfkiyas sgun">📈 Portföyünü BIST 100 ile kıyaslamak için hisseyi düzenle (✎) ve <b>alış tarihini</b> gir.</div>';
 liste.innerHTML=r;
 top.innerHTML='Toplam K/Z: <b class="'+(toplam>=0?'pos':'neg')+'">'+(toplam>=0?'+':'')+Math.round(toplam).toLocaleString('tr-TR')+' TL</b>';
}
(function(){var dl=document.getElementById('pfkodlar');if(dl){dl.innerHTML=Object.keys(DATA).sort().map(function(k){return '<option value="'+k+'"></option>';}).join('');}pfRender();pfBulutOku();alBulutOku();})();
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
</style></head><body><div class="wrap">
<a class="geri" href="index.html">← Panoya dön</a>
<h1>Sinyal Geçmişi (canlı karne)</h1><div class="tarih">Güncelleme: __TARIH__</div>
<div class="kartlar">
<div class="k"><div class="b">%__ISABET__</div><div class="l">kapanan sinyallerde isabet</div></div>
<div class="k"><div class="b">__KAPANAN__</div><div class="l">kapanan sinyal sayısı</div></div>
<div class="k"><div class="b">%__ORT__</div><div class="l">kapananların ortalama sonucu</div></div>
<div class="k"><div class="b">__ACIK__</div><div class="l">şu an açık takip</div></div>
</div>
<h2>Açık pozisyonlar (takipte)</h2>
<div class="sar"><table><thead><tr><th>Hisse</th><th>Sinyal tarihi</th><th class="num">Giriş</th><th class="num">Güncel</th><th class="num">Anlık %</th><th class="num">Stop</th></tr></thead><tbody>__ACIKROWS__</tbody></table></div>
<h2>Kapanmış sinyaller</h2>
<div class="sar"><table><thead><tr><th>Hisse</th><th>Giriş tarihi</th><th class="num">Giriş</th><th>Çıkış tarihi</th><th class="num">Çıkış</th><th class="num">Sonuç %</th><th>Sebep</th></tr></thead><tbody>__KAPALIROWS__</tbody></table></div>
<div class="not">Bu sayfa <b>ileriye dönük gerçek</b> karnedir ve canlıdaki (v2) kuralların aynısını uygular: sinyal AL'e döndüğü gün fiyatı kaydeder (trend içinde, aşırı oynak ya da taban serisinde olmayan hisseler; piyasa zayıfken kayıt açılmaz); fiyat, kayıttan beri görülen en yüksek kapanışın %20 altına inerse (iz stop) kapatıp sonucu yazar. SAT sinyali tek başına kapatmaz. Aynı AL dalgası bir kez sayılır. (Eylül 2026 öncesi kayıtlar eski, daha gevşek kurallarla açılmıştı.) Backtest geçmişi simüle eder; bu sayfa ise sistemin <b>bugünden itibaren</b> gerçek performansını biriktirir. Yatırım tavsiyesi değildir.</div>
</div></body></html>"""
