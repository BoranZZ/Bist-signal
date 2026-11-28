# -*- coding: utf-8 -*-
"""🎯 Tahtacı Haritası sayfa şablonu (harita.html). harita.py `html_yaz` ile yazılır; veri `fetch('harita.json')`.
Düzenlerken: JS dizelerinde Türkçe kesme işareti olan metinler ÇİFT tırnakta; sonra `node --check` (BENIOKU)."""

SAYFA = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Tahtacı Haritası</title>
<style>
:root{--bg:#F4F1FB;--panel:#FFFFFF;--ink:#1D1530;--muted:#6E6488;--line:#E3DCF2;--accent:#6D3FD8;--pos:#1B8A52;--neg:#C2412F;
--chip:#EFE9FB;--kel:#1B8A52;--kutu:#2F6FD8;--mal:#D9822B;--kilit:#8B3FD8;--gri:#8C84A3;--eg:#B4530A;--tb:#A8740A}
@media (prefers-color-scheme:dark){:root{--bg:#0F0A1E;--panel:#19122E;--ink:#ECE7FA;--muted:#A79BC8;--line:#2E2450;--accent:#B596FF;
--pos:#5BD69A;--neg:#FF7A6B;--chip:#241A40;--kel:#5BD69A;--kutu:#7FA8FF;--mal:#F2A65A;--kilit:#C59BFF;--gri:#8E86A8;--eg:#F5A524;--tb:#E8C15A}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
font-feature-settings:"tnum" 1;-webkit-font-smoothing:antialiased;line-height:1.45}
a{color:var(--accent)}
.ust{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;padding:14px 18px;border-bottom:1px solid var(--line);background:var(--panel)}
.ust h1{font-size:19px;margin:0;font-weight:700}.ust .alt{color:var(--muted);font-size:12.5px}
.ust .sag{margin-left:auto;font-size:13px}
.ana{max-width:1100px;margin:0 auto;padding:14px 18px 40px}
.kart{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin-bottom:14px;min-width:0}
.kart h2{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 8px;font-weight:700}
.uyari{background:var(--chip);border-radius:12px;padding:10px 14px;font-size:13.5px}
details.ne summary{cursor:pointer;font-weight:650}
details.ne p,details.ne li{font-size:13.5px}
.listeler{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;margin-bottom:14px}
.listeler .kart{margin:0}
.cips{display:flex;flex-wrap:wrap;gap:6px}
.cip{border:1px solid var(--line);background:var(--chip);color:var(--ink);border-radius:999px;padding:4px 10px;font:inherit;font-size:12.5px;cursor:pointer}
.cip small{color:var(--muted)}
.bos{color:var(--muted);font-size:13px}
.suz{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px}
.suz input,.suz select{font:inherit;font-size:14px;padding:7px 10px;border:1px solid var(--line);border-radius:10px;background:var(--panel);color:var(--ink)}
.suz input{flex:1;min-width:150px}
.suz .say{color:var(--muted);font-size:12.5px}
.hk{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px 14px;margin-bottom:14px;min-width:0}
.hk .bas{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px}
.hk .bas b.kod{font-size:18px}.hk .bas .fy{font-size:17px;font-weight:700}
.hk .bas .m{color:var(--muted);font-size:12px}
.etk{display:inline-block;font-size:11.5px;border-radius:6px;padding:1px 7px;background:var(--chip);color:var(--muted)}
.etk.dk{background:#D9A11B22;color:#B7860B}
.izg{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:12px;margin-top:8px}
@media(max-width:760px){.izg{grid-template-columns:minmax(0,1fr)}}
.dur{font-size:13.5px}
.dur p{margin:0 0 7px}
.dur .not{color:var(--muted);font-size:12.5px}
.oky{color:var(--pos);font-weight:700}.okk{color:var(--neg);font-weight:700}.okn{color:var(--gri)}
table.sv{width:100%;border-collapse:collapse;font-size:12.5px}
table.sv td{padding:4px 5px;border-bottom:1px solid var(--line);vertical-align:top}
table.sv td.r{text-align:right;white-space:nowrap}
table.sv td .a{color:var(--muted);font-size:11.5px}
table.sv tr.fy td{font-weight:700;background:var(--chip)}
.nokta{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px;vertical-align:0}
.graf{width:100%;height:auto;display:block}
.graf text{font-size:11px;fill:var(--muted)}
.dahafazla{display:block;margin:6px auto 0;border:1px solid var(--line);background:var(--chip);color:var(--ink);border-radius:10px;padding:8px 16px;font:inherit;cursor:pointer}
.eg{margin-top:10px;border-top:1px dashed var(--line);padding-top:8px;font-size:13px;min-width:0}
.eg .egb{font-weight:700;margin-bottom:6px;color:var(--eg)}.eg .egb span{font-weight:400;color:var(--muted);font-size:12px}
.eg ul{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:4px 16px}
.eg li{margin:0 0 6px;overflow-wrap:anywhere;min-width:0}
.eg .egn{color:var(--muted)}
.rz{color:var(--muted);font-size:12px;margin-top:2px}
.rz b{display:inline-block;background:var(--chip);border-radius:6px;padding:0 6px;color:var(--ink);font-weight:600;margin-right:3px}
.eg details{font-size:12px;color:var(--muted)}.eg details summary{cursor:pointer}
.egu{margin-bottom:14px;border-left:4px solid var(--eg)}
.egbtn[aria-pressed="false"]{opacity:.65}
.emk{border-left:4px solid var(--tb)}
.emk .cips{margin:8px 0 4px}
.cip.sec{background:var(--tb);border-color:var(--tb);color:var(--bg)}.cip.sec small{color:var(--bg);opacity:.9}
.tbp{background:var(--chip);border-radius:10px;padding:8px 10px;margin:0 0 8px;border-left:3px solid var(--tb)}
.tbp p{margin:0 0 6px}
.durust{font-size:13.5px}
.durust li{margin-bottom:5px}
@media(max-width:560px){.ana{padding:12px 10px 30px}.ust{padding:12px}.hk{padding:10px}.listeler{grid-template-columns:minmax(0,1fr)}.eg ul{grid-template-columns:minmax(0,1fr)}}
</style></head><body>
<div class="ust"><div><h1>🎯 Tahtacı Haritası</h1>
<div class="alt">Haftalık grafikte seviyeler ve durum bilgisi · <b>AL/SAT vermez</b> · <span id="tarih">yükleniyor…</span></div></div>
<div class="sag"><a href="index.html">← Panoya dön</a> · <a href="oda.html">🏢 İşlem Odası</a></div></div>
<div class="ana">
<div class="uyari egu">📚 <b>Eğitim katmanı:</b> her kartın altında eğitmenin gözüyle bakış (trend çizgisi, bariz destek/direnç, iki durak, ana tepe, kutu, kâr/zarar oranı, kilit, dip süpürmesi, dip arası takip bölgesi, ekmek kırıntısı). Bazı kavramlar BIST'te <b>tutmadı</b>, yanlarındaki rozetlere bak. <b>AL/SAT değildir.</b></div>
<div class="kart"><details class="ne"><summary>📊 Bu sayfa ne? (önce bunu oku)</summary>
<p>Bir borsa eğitmeni (DC Akademi) hisselere "tahtacı / piyasa yapıcı" gözüyle bakıyor: büyük para malı <b>ucuzdan toplar</b>, fiyatı bir süre
<b>kutu içinde</b> tutar, sonra kaldırır. Ona göre önce <b>bölgeyi</b> bulmak gerekir; gösterge ve formasyon ancak o bölgede anlam taşır.
Hisselere çoğunlukla <b>haftalık</b> grafikte bakıyor.</p>
<p>Biz bu anlatımın <b>ölçülebilen</b> parçalarını aldık ve BIST'in 10-25 yıllık haftalık verisinde test ettik. Bu sayfa her hisse için
o parçaları gösterir: büyük tepe ve dip, kutu, değer alanı, kelepir bandı, büyük düşüşten sonraki evre.</p>
<ul><li>Seviyelerin adları <b>bizim</b> ("kutu üst kenarı", "maliyet vekili"). Eğitmenin gizli hesabı değil; onun sayılarını tutturduğumuzu iddia etmiyoruz.</li>
<li>Durumlar <b>haftalık kapanışla</b> kesinleşir. Hafta içinde anlık fiyat "hafta şimdi kapansa" diye kullanılır.</li>
<li>Her satırın yanında geçmişte ne bulunduğu yazar. Tutmayan parçalar (trend çizgisi tuzağı, kâr/zarar oranı, kilit seviye) dünyada çok kullanıldıkları için yalnız kartın altındaki <b>📚 Eğitim katmanında</b>, "BIST'te ölçüldü: 🔴 tutmadı" rozetiyle gösterilir. Oradaki ölçüler bizim şeffaf yaklaşık tanımlarımız.</li>
<li>Panodaki AL/SAT, Telegram ve İşlem Odası bu sayfadan <b>etkilenmez</b>.</li></ul>
</details></div>
<div id="emtia"></div>
<div class="listeler" id="listeler"></div>
<div class="suz"><input id="ara" type="search" placeholder="Hisse ara (ör. THYAO)" autocomplete="off" autocapitalize="characters">
<select id="suzgec">
<option value="one">Öne çıkanlar</option><option value="hepsi">Tüm hisseler</option>
<option value="kelepir">🟢 Kelepir bandı</option><option value="ucuz">Ucuz bandı</option><option value="kutu">📦 Kutu alt bölgesi</option>
<option value="dusus">Büyük düşüş sonrası</option><option value="ucuzyari">Tepe-dip aralığının alt yarısı</option>
<option value="pahaliyari">Tepe-dip aralığının üst yarısı</option><option value="tdestek">📚 Çok temaslı desteğe yakın</option><option value="supurme">📚 Son dip süpürmesi</option><option value="dipara">📚 Dip arası takip bölgesinde</option><option value="ana">Ana liste (BIST 100 + ek)</option><option value="kucuk">Küçük hisseler</option>
</select><button type="button" class="cip egbtn" id="egbtn" aria-pressed="true">📚 Eğitim çizgileri: açık</button><span class="say" id="say"></span></div>
<div id="kartlar"></div>
<div class="kart durust"><h2>📊 Dürüstlük notu</h2>
<p>Eğitmenin iddiaları 2000-2026 haftalık verisinde (MANIPULE listesindeki 32 hisse hariç, ~256 hisse) test edildi. Kısaca:</p>
<ul>
<li><span class="oky">▲</span> <b>Kelepir bandı:</b> gerçekten nadir (haftada ortalama 1-2 hisse) ve sonrası iyi: 25 yılda 101 olay, 12 ayda aynı hissenin sıradan haftasından
+35 puan, 36 ayda +55 puan iyi. <span class="okk">▼</span> Ama "8-10 kat" abartı: medyan en yüksek nokta 3,3 kat, 8 katı ancak 10 olaydan 1'i gördü; ilk yılda medyan −%22 ara düşüş. Ayrıca aynı hafta başka bir BIST hissesi almakla kıyaslanınca avantaj kalmıyor (12 ayda −2,5 puan): getirinin çoğu kriz haftalarında almaktan geliyor. ABD'de (S&P 500 / 600) kelepir yine iyi, ama orada da batan şirketler veride yok.</li>
<li><span class="oky">▲</span> <b>Ucuz bandı:</b> 12 ayda rastgeleden +15 puan; kelepirden zayıf.</li>
<li><b>Büyük düşüş sonrası evre:</b> ilk tepkide alanların %40'ı bir yıl içinde yeni dip gördü (doğru). Ama ana tepenin üstünde haftalık kapanışı beklemek getiriyi
<span class="okk">▼</span> düşürdü (52 haftada rastgeleden −9 puan). Risk bilgisidir, "bekle" tavsiyesi değil.</li>
<li><span class="oky">▲</span> <b>Kutu alt bölgesi:</b> kutunun alt üçte birinde almak, kutu kırılımını beklemekten iyiydi (rastgeleye göre ~+6 puan, iki dönemde de).</li>
<li><span class="okk">▼</span> <b>Seviyeler:</b> eğitmenin seviye hesabı çözülemedi. "Kutu üst kenarı" onun "kilit" seviyelerine en yakın basit tanım, ama
kilitlerin ancak 4'te 1'i ile yarısını tutturuyor; "üstünde haftalık kapanışta al" kuralı rastgele alımdan iyi değil. "Maliyet vekili" doğrulanmadı.
Tepe-dip aralığının ucuz/pahalı yarısı AL'lere filtre olarak değer katmadı. Uzun taban büyük ralli getirmedi.</li>
<li><span class="okk">▼</span> <b>Yalnız 📚 Eğitim katmanında (rozetli):</b> "trend çizgisine 3. temasta kırarlar" (yazı-tura çıktı), "kâr/zarar oranı 1:4" (sonucu ayırmadı), iki durak, kilit, dip süpürmesi, dip arası takip bölgesi (bölgede almak iyi ama yapıdan değil 3 yılın dibine yakınlıktan; "üstünde tutunursa" teyidini beklemek kazancı düşürdü), ekmek kırıntısı (rastgele seviyeden farksız); yukarıdaki durum metinlerine karışmaz.
Haftalık Wyckoff "spring" (aralığın dibini süpürüp geri dönme) da test edildi: portföyde rastgele eklemeden iyi değil. Yabancı payı değişimi de test edildi; sonrasını öngörmüyor.</li>
<li><b>Manipülasyon yüzünden mi tutmadı?</b> Hayır: tutmayan kurallar büyük ve likit hisselerde (hacimce ilk 30/50) ve şişirme hisseleri çıkarılmış listede de tutmadı; tutanlar (kelepir, ilk tepkide yeni dip riski) her alt kümede tuttu (20.11 araştırması).</li>
<li><b>Türkiye'ye mi özgü?</b> Hayır: aynı kurallar ABD'de (S&P 500 ve S&P 600, 2000-2026) de denendi; 12 iddianın hepsi iki piyasada aynı yöne çıktı. Kâr/zarar oranı ABD'de tersine bile çalışıyor (yüksek oran = daha kötü sonuç).</li>
<li><span class="okk">▼</span> <b>Hayatta kalan yanlılığı:</b> veride yalnız bugün borsada olan şirketler var. Tabanına dönüp batan ya da borsadan çıkan şirketler yok. Kelepir
tam da onların bulunacağı yer: gerçek sonuç tablodakinden <b>kötüdür</b>, ne kadar kötü olduğu ölçülemiyor. 2025-26'nın şişirme rallileri (20-30 kat) geçmişte bu kadar yoktu.</li>
<li><b>Bu bir al-sat önerisi değildir.</b> Geçmiş ortalamalar tek hissede ne olacağını söylemez. Kararı sen verirsin; stop ve pozisyon büyüklüğünü unutma.</li>
</ul><p class="bos" id="kaynak"></p></div>
</div>
<script>
var D=null,H={},KODLAR=[],GOSTER=20,EG_ACIK=true;
try{EG_ACIK=localStorage.getItem("harita_eg")!=="0";}catch(e){}
var RZ={y:["🟢","tuttu"],s:["🟡","kısmen"],r:["🔴","tutmadı"],o:["⚪","henüz ölçülmedi"],t:["🧪","test sürüyor"]};var EMS=null;
var ANA_URL="https://boranzz.github.io/Bist-signal/harita.json";
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
function sayi(v,n){if(v==null||!isFinite(v))return "—";if(n==null)n=v<1?3:2;return Number(v).toLocaleString("tr-TR",{minimumFractionDigits:n,maximumFractionDigits:n});}
function yz(v,n){if(v==null||!isFinite(v))return "—";var s=(v*100).toLocaleString("tr-TR",{maximumFractionDigits:n==null?0:n});return "%"+s;}
function fark(x,f){if(!x||!f)return "";var r=x/f-1;return (r>=0?"+":"−")+"%"+Math.abs(r*100).toLocaleString("tr-TR",{maximumFractionDigits:r>-0.1&&r<0.1?1:0});}
function tr(t){if(!t)return "—";var p=String(t).split("-");return p[2]+"."+p[1]+"."+p[0];}
function yil(t){return t?String(t).slice(0,4):"";}
function oky(){return '<span class="oky">▲</span>';}function okk(){return '<span class="okk">▼</span>';}
function kelMetin(k,kod){var e=k.kel,d=k.d||{},f=k.f,h="";if(!e)return "";
 if(d.kel==="kelepir"){
  h+="<p>📊 <b>Kelepir bandında</b> — "+yil(e.T_t)+"'de "+sayi(e.T)+" TL'den başlayan ralli "+yil(e.P_t)+"'de "+sayi(e.P)+" TL'ye çıkmıştı ("+sayi(e.kat,1)+" kat). Fiyat şimdi "+sayi(f)+" TL: rallinin başladığı tabana dönmüş (bant "+sayi(e.kel_alt)+" – "+sayi(e.kel_ust)+").</p>";
  h+="<p>"+oky()+" Geçmişte (2000-2026, 101 olay) bu durumdan sonra 12 ayda ortalama +%50 (medyan +%30): aynı hissenin sıradan haftasından +35 puan, BIST 100'den +15 puan iyi. 36 ayda medyan +%96. <span class=\"okk\">▼</span> Ama aynı hafta başka bir BIST hissesi almaktan iyi değil (12 ayda −2,5 puan): avantajın çoğu kriz haftalarında almaktan geliyor.</p>";
  h+="<p>"+okk()+" Yolu sert: ilk yılda medyan −%22 ara düşüş, her 4 olaydan biri −%40'tan kötü. \"8-10 kat\" sadece 10'da 1 olayda görüldü (medyan en yüksek 3,3 kat).</p>";
  h+='<p class="not">⚠️ Veride batan / borsadan çıkan şirketler yok: gerçek sonuç bundan kötüdür.</p>';
 }else if(d.kel==="ucuz"){
  h+="<p>📊 <b>Ucuz bandında</b> — "+yil(e.T_t)+" tabanı "+sayi(e.T)+" → "+yil(e.P_t)+" tepesi "+sayi(e.P)+" ("+sayi(e.kat,1)+" kat). Fiyat "+sayi(f)+": rallinin büyük kısmını geri vermiş, kelepir bandının üstünde (ucuz bandı "+sayi(e.kel_ust)+" – "+sayi(e.ucuz_ust)+").</p>";
  h+="<p>"+oky()+" Geçmişte (292 olay) 12 ayda ortalama +%29 (medyan +%13): sıradan haftadan +15 puan iyi, ama BIST 100'den farksız (−2). Kelepirden zayıf.</p>";
  h+='<p class="not">⚠️ Veride batan şirketler yok: gerçek sonuç bundan kötüdür.</p>';
 }else if(d.kel==="altinda"){
  h+="<p>📊 <b>Ralli tabanının da altında</b> — taban "+sayi(e.T)+" ("+yil(e.T_t)+"), fiyat "+sayi(f)+" (tabanın "+fark(f,e.T)+"). Kelepir tanımı tabanın %70'ine kadar; bunun altı araştırmada sayılmadı.</p>";
 }else{if(e.kat<4)return "";
  return '<p class="not">Kelepir / ucuz bandında değil: son 5 yılın büyük rallisi '+sayi(e.T)+" ("+yil(e.T_t)+") → "+sayi(e.P)+" ("+yil(e.P_t)+"), "+sayi(e.kat,1)+" kat. Ucuz bandı "+sayi(e.ucuz_ust)+" altında başlar (fiyatın "+fark(e.ucuz_ust,f)+"), kelepir bandı "+sayi(e.kel_ust)+" altında. Fiyatlar bölünme/bedelsiz düzeltmeli: eski grafikteki sayılardan farklı görünebilir.</p>";}
 if(e.hizli)h+='<p class="not">'+okk()+" Ralli hızlıydı ("+e.rh+" haftada "+sayi(e.kat,1)+" kat, 1 yıldan kısa): şişirme tipi rallilerin tabanında geçmişteki fark küçük ve anlamsızdı (+12 puan). Taban güvenilmez.</p>";
 if(k.dk)h+='<p class="not">⚠️ Bu hissede panoda manipülasyon / şişme uyarısı var: dikkat.</p>';
 return h;}
function yonMetin(k){var y=k.yon,f=k.f,h="";if(!y)return "";
 if(y.asildi!=null){return "<p>📊 <b>Yön durumu</b> — büyük düşüşten (zirve "+sayi(y.zirve)+", dip "+sayi(y.dip)+", −%"+Math.round(y.dusus*100)+") sonra ana tepe "+sayi(y.ana_tepe)+" "+(y.asildi===0?"bu hafta":y.asildi+" hafta önce")+" haftalık kapanışla aşıldı: bölüm bitti.</p><p class=\"not\">Geçmişte bu noktada fiyat dipten ortalama +%73 yukarıdaydı ve sonraki 52 haftada rastgele haftadan 9 puan geride kaldı. Yeni dip görme oranı ise %15'e indi.</p>";}
 h+="<p>📊 <b>Yön durumu</b> — 104 haftalık zirveden ("+sayi(y.zirve)+", "+tr(y.zirve_t)+") −%"+Math.round(y.dusus*100)+" düştü. Dip "+sayi(y.dip)+" (haftalık kapanışla, "+(y.dip_yas===0?"bu hafta":y.dip_yas+" hafta önce")+"), ana tepe "+sayi(y.ana_tepe)+(y.tepecik?", tepecik "+sayi(y.tepecik)+(y.tgec?" (geçildi ✓)":""):"")+".</p>";
 if(!y.ilk)h+="<p>Dip arayışı: dipten henüz +%20 haftalık tepki yok.</p>";
 else h+="<p>İlk tepki evresi: geçmişte bu evrede alanların %40'ı bir yıl içinde yeni dip gördü (ana tepe kırılımından sonra alanlarda %15). Ama ana tepeyi beklemek ortalamada kazancı düşürdü: o noktada fiyat dipten ortalama +%73 yukarıdaydı ve 52 haftada rastgele haftadan 9 puan geride kaldı.</p>";
 if(f&&y.dip_yas>=4&&f<=y.dip*1.10&&f>=y.dip)h+="<p>Dip yakını: dip 4+ haftadır korunuyor, fiyat dibin en çok %10 üstünde. Geçmişte buradan 52 hafta tutmak sıradan haftadan +21 puan iyiydi, ama %79'u bir yıl içinde dibin altını gördü.</p>";
 return h+'<p class="not">Risk bilgisi; "bekle" ya da "al" tavsiyesi değil. Son tamamlanan hafta: '+tr(y.son_hafta)+".</p>";}
function kutuMetin(k){var b=k.kutu,d=k.d||{};if(!b||!d.kutu)return "";
 return "<p>📦 <b>Kutunun alt bölgesinde</b> — tepeden ("+sayi(b.tepe)+") %"+Math.round((1-b.ust/b.tepe)*100)+"+ çekilip 8 haftadır "+sayi(b.alt)+" – "+sayi(b.ust)+" kutusunda; fiyat "+sayi(k.f)+" kutunun alt üçte birinde ("+sayi(b.ucte)+" altı).</p><p>"+oky()+" Geçmişte kutu içi alt bölge alımı, kutu kırılımını beklemekten iyi sonuç verdi (rastgeleye göre ~+6 puan, iki dönemde de). Kutu dibinin %3 altına inen hafta kutu bozulmuş sayılır ("+sayi(b.alt*0.97)+").</p>";}
function svMetin(k){var s=k.sv,d=k.d||{},h="";if(!s)return "";
 if(d.konum!=null){var u=d.konum<0.5;h+="<p>"+(u?oky()+" Tepe-dip aralığının <b>alt (ucuz) yarısında</b>":okk()+" Tepe-dip aralığının <b>üst (pahalı) yarısında</b>")+": fiyat aralığın %"+Math.round(Math.max(0,Math.min(1,d.konum))*100)+"'inde (orta "+sayi(s.orta)+"). <span class=\"not\">Filtre olarak değer katmadı.</span></p>";}
 if(k.f&&k.f<s.dip)h+="<p>"+okk()+" Fiyat büyük dibin ("+sayi(s.dip)+") altında: dip yenileniyor.</p>";
 if(s.dip_yas<12)h+='<p class="not">Taban henüz oluşmadı: dip '+(s.dip_yas===0?"bu hafta":s.dip_yas+" hafta önce")+" (en az 12 hafta gerekir); kutu üst kenarı ve maliyet vekili gösterilmez.</p>";
 else{if(s.kilit)h+='<p class="not">Kutu üst kenarı '+sayi(s.kilit)+(k.f>s.kilit?" — fiyat üstünde (tek başına AL sebebi değil: rastgeleden iyi çıkmadı).":" ("+fark(s.kilit,k.f)+" yukarıda).")+"</p>";
  if(s.mal)h+='<p class="not">Maliyet vekili '+sayi(s.mal)+": fiyat "+(k.f>=s.mal?"üstünde":"altında")+" (doğrulanmamış tahmin).</p>";}
 h+='<p class="not">Taban süresi: '+s.sure+" hafta (kapanışlar 1,5 kat aralıkta). Uzun taban büyük ralli getirmedi.</p>";
 return h;}
function yabMetin(k){if(!D.bayrak||!D.bayrak.yabanci||!k.yb)return "";return "<p>📊 Yabancı payı: %"+sayi(k.yb.oran,1)+"</p>";}
function seviyeListesi(k){var L=[],s=k.sv,e=k.kel,y=k.yon,b=k.kutu&&(k.d||{}).kutu?k.kutu:null;
 if(s){L.push(["Büyük tepe","son 3 yılın en yükseği · "+tr(s.tepe_t),s.tepe,"var(--gri)","",1]);
  L.push(["Orta nokta","tepe-dip ortası (ucuz/pahalı yarı sınırı)",s.orta,"var(--gri)","3 4",0,0,1]);
  if(s.kilit)L.push(["Kutu üst kenarı","son 26 haftanın en yüksek kapanışı",s.kilit,"var(--kilit)","",1.4]);
  L.push(["Değer alanı üstü","52 haftada işlemin %70'i bu aralıkta",s.vah,"var(--kutu)","2 3",0.8,0,1]);
  L.push(["En yoğun fiyat","52 haftada en çok işlem gören fiyat",s.poc,"var(--kutu)","1 2",1]);
  L.push(["Değer alanı altı","",s.val,"var(--kutu)","2 3",0.8,0,1]);
  if(s.mal)L.push(["Maliyet vekili","dipten bugüne hacim ağırlıklı ortalama",s.mal,"var(--mal)","",1.4]);
  L.push(["Büyük dip",tr(s.dip_t)+" · "+(s.dip_yas===0?"bu hafta":s.dip_yas+" hafta önce"),s.dip,"var(--gri)","",1]);}
 if(y&&y.asildi==null){L.push(["Ana tepe","büyük düşüşteki son düşen tepe",y.ana_tepe,"var(--neg)","5 3",1.2]);if(y.tepecik)L.push(["Tepecik","dipten sonraki ilk küçük tepe"+(y.tgec?" · geçildi":""),y.tepecik,"var(--neg)","1 3",1]);}
 if(b){L.push(["Kutu üstü (8 hafta)","",b.ust,"var(--kutu)","",1]);L.push(["Kutu altı (8 hafta)","",b.alt,"var(--kutu)","",1]);}
 var t=k.tb;if(t){L.push(["Kırılan tepe","🧱 tabanın tavanı = kırılan eski tepe (en yüksek fitil)",t.tv,"var(--tb)","6 3",1.3]);
  L.push(["Taban üstü","🧱 taban bölgesi · "+tr(t.bt)+" – "+tr(t.bs)+" · "+t.n+" hafta",t.u,"var(--tb)","",1.5]);
  L.push(["Taban altı","🧱 taban bölgesi · gövdelerin yoğunlaştığı bant",t.a,"var(--tb)","",1.5]);}
 if(e&&e.kat>=4){L.push(["Ralli tepesi",tr(e.P_t)+" · "+sayi(e.kat,1)+" kat",e.P,"var(--kel)","4 3",0.9,0,s&&Math.abs(e.P/s.tepe-1)<0.03?1:0]);
  L.push(["Ucuz bandı üstü","taban + rallinin %21,4'ü",e.ucuz_ust,"var(--kel)","4 3",1]);
  L.push(["Kelepir bandı üstü","taban +%30",e.kel_ust,"var(--kel)","",1.2,0,1]);
  L.push(["Ralli tabanı",tr(e.T_t),e.T,"var(--kel)","",1.6]);
  L.push(["Kelepir bandı altı","tabanın %70'i",e.kel_alt,"var(--kel)","",1.2,0,1]);}
 return L;}
function tablo(k){var L=seviyeListesi(k).slice(),f=k.f,h='<table class="sv">';L.push(["Fiyat (şimdi)","",f,"var(--ink)","",0,1]);
 L.sort(function(a,b){return (b[2]||0)-(a[2]||0);});
 L.forEach(function(r){if(r[2]==null)return;h+="<tr"+(r[6]?' class="fy"':"")+'><td><span class="nokta" style="background:'+r[3]+'"></span>'+esc(r[0])+(r[1]?'<br><span class="a">'+esc(r[1])+"</span>":"")+'</td><td class="r">'+sayi(r[2])+'</td><td class="r">'+(r[6]?"":'<span class="a">'+fark(r[2],f)+"</span>")+"</td></tr>";});
 if(k.kel&&k.kel.kat<4)h+='<tr><td colspan="3"><span class="a">Kelepir: son 5 yılda büyük ralli yok (tepe/taban '+sayi(k.kel.kat,1)+" kat; en az 4 kat gerekir).</span></td></tr>";
 return h+"</table>";}
function grafik(k){var s=k.s||[],n=s.length;if(n<10)return "";var W=Math.max(300,Math.min(640,(window.innerWidth||640)-50)),Hh=W<480?240:260,ml=4,mr=W<480?92:118,mt=10,mb=20,pw=W-ml-mr,ph=Hh-mt-mb;
 var v=s.filter(function(x){return x!=null&&x>0;});if(v.length<5)return "";var lo=Math.min.apply(null,v),hi=Math.max.apply(null,v);
 var L=seviyeListesi(k).concat(egSeviye(k)),ic=[],dis=[];L.forEach(function(r){if(r[7])return;if(r[2]>0&&r[2]>=lo/1.7&&r[2]<=hi*1.7)ic.push(r);else if(r[2]>0)dis.push(r);});
 ic.forEach(function(r){lo=Math.min(lo,r[2]);hi=Math.max(hi,r[2]);});
 var tc=EG_ACIK&&k.eg&&k.eg.tc&&k.eg.tc.a,ta=null;if(tc&&tc[1]>0&&tc[3]>0&&tc[1]>=lo/1.7&&tc[1]<=hi*1.7&&tc[3]>=lo/1.7&&tc[3]<=hi*1.7){ta=tc;lo=Math.min(lo,tc[1],tc[3]);hi=Math.max(hi,tc[1],tc[3]);}
 var a=Math.log(lo/1.03),b=Math.log(hi*1.03);function Y(p){return mt+ph*(1-(Math.log(p)-a)/(b-a));}function X(i){return ml+pw*i/(n-1);}
 var g='<svg class="graf" viewBox="0 0 '+W+" "+Hh+'" role="img" width="100%" aria-label="Haftalık kapanış grafiği ve seviyeler">';
 var e=k.kel;if(e&&e.kat>=4&&e.kel_ust>=lo&&e.kel_alt<=hi){var y1=Y(Math.min(e.kel_ust,hi*1.03)),y2=Y(Math.max(e.kel_alt,lo/1.03));g+='<rect x="'+ml+'" y="'+y1+'" width="'+pw+'" height="'+Math.max(1,y2-y1)+'" fill="var(--kel)" opacity=".12"/>';}
 var da=EG_ACIK&&k.eg&&k.eg.da;if(da&&da.y>0&&da.u>=lo&&da.a<=hi){var y5=Y(Math.min(da.u,hi*1.03)),y6=Y(Math.max(da.a,lo/1.03));g+='<rect x="'+ml+'" y="'+y5+'" width="'+pw+'" height="'+Math.max(1,y6-y5)+'" fill="var(--eg)" opacity=".14"/>';}
 var tb=k.tb;if(tb&&tb.u>=lo&&tb.a<=hi){var gx=new Date((k.g0||D.g0)+"T00:00:00").getTime(),i0=Math.max(0,Math.round((new Date(tb.bt+"T00:00:00").getTime()-gx)/(7*864e5))),y7=Y(Math.min(tb.u,hi*1.03)),y8=Y(Math.max(tb.a,lo/1.03));if(i0<n-1)g+='<rect x="'+X(i0)+'" y="'+y7+'" width="'+(X(n-1)-X(i0))+'" height="'+Math.max(1,y8-y7)+'" fill="var(--tb)" opacity=".2"/>';}
 var sv=k.sv;if(sv&&sv.vah&&sv.val){var y3=Y(Math.min(sv.vah,hi*1.03)),y4=Y(Math.max(sv.val,lo/1.03));g+='<rect x="'+ml+'" y="'+y3+'" width="'+pw+'" height="'+Math.max(1,y4-y3)+'" fill="var(--kutu)" opacity=".07"/>';}
 var g0=new Date((k.g0||D.g0)+"T00:00:00"),son=-1;for(var i=0;i<n;i++){var dt=new Date(g0.getTime()+i*7*864e5);var yl=dt.getFullYear();if(son>=0&&yl!==son){g+='<line x1="'+X(i)+'" x2="'+X(i)+'" y1="'+mt+'" y2="'+(mt+ph)+'" stroke="var(--line)"/><text x="'+(X(i)+3)+'" y="'+(Hh-6)+'">'+yl+"</text>";}son=yl;}
 var et=[];ic.forEach(function(r){var y=Y(r[2]);g+='<line x1="'+ml+'" x2="'+(ml+pw)+'" y1="'+y+'" y2="'+y+'" stroke="'+r[3]+'" stroke-width="'+(r[5]||1)+'"'+(r[4]?' stroke-dasharray="'+r[4]+'"':"")+(r[5]?"":' opacity=".7"')+"/>";et.push([y,r[0],r[3]]);});
 if(ta){g+='<line x1="'+X(ta[0])+'" x2="'+X(ta[2])+'" y1="'+Y(ta[1])+'" y2="'+Y(ta[3])+'" stroke="var(--eg)" stroke-width="1.4" stroke-dasharray="8 3"/>';et.push([Y(ta[3]),(k.eg.tc.y>0?"↗":"↘")+" Trend ×"+k.eg.tc.n,"var(--eg)"]);}
 var p="",acik=false;for(i=0;i<n;i++){if(s[i]==null||!(s[i]>0)){acik=false;continue;}p+=(acik?"L":"M")+X(i).toFixed(1)+" "+Y(s[i]).toFixed(1)+" ";acik=true;}
 g+='<path d="'+p+'" fill="none" stroke="var(--ink)" stroke-width="1.6"/>';
 if(k.f>0){g+='<circle cx="'+X(n-1)+'" cy="'+Y(k.f)+'" r="3" fill="var(--accent)"/>';et.push([Y(k.f),"Fiyat "+sayi(k.f),"var(--accent)"]);}
 et.sort(function(u,w){return u[0]-w[0];});var top=mt+4;et.forEach(function(q){q[3]=Math.max(q[0]+4,top);top=q[3]+13;});
 var asl=mt+ph+6;for(i=et.length-1;i>=0;i--){if(et[i][3]>asl)et[i][3]=asl;asl=et[i][3]-13;}
 et.forEach(function(q){g+='<text x="'+(ml+pw+4)+'" y="'+q[3]+'" style="fill:'+q[2]+'">'+esc(q[1].length>16?q[1].slice(0,15)+"…":q[1])+"</text>";});
 g+="</svg>";if(dis.length)g+='<div class="bos" style="font-size:11.5px">Grafiğin dışında kalan: '+dis.map(function(r){return esc(r[0])+" "+sayi(r[2]);}).join(" · ")+"</div>";
 return g+'<div class="bos" style="font-size:11.5px">Son 3 yıl, haftalık kapanış (log ölçek). '+(k.tb?'Sarı şerit = 🧱 taban bölgesi (tabanın başladığı haftadan bugüne). ':'')+'Yeşil şerit = kelepir bandı, mavi şerit = değer alanı. Son nokta = anlık fiyat. Tüm seviyeler tabloda.'+(EG_ACIK&&k.eg?' Turuncu = 📚 eğitim katmanı (yaklaşık; rozetlere bak), turuncu şerit = dip arası takip bölgesi.':'')+'</div>';}
function rozet(ad){var r=((D&&D.egr)||{})[ad];if(!r)return "";var z=RZ[r[0]]||RZ.o,h='<div class="rz"><b>'+(r[0]==="t"?"Ölçüm: ":"BIST'te ölçüldü: ")+z[0]+" "+z[1]+"</b> "+esc(r[1])+"</div>";
 if(r[2]&&r[2].length){var u=RZ[r[2][0]]||RZ.o;h+='<div class="rz"><b>'+"ABD'de ölçüldü: "+u[0]+" "+u[1]+"</b> "+esc(r[2][1])+"</div>";}return h;}
function rzKisa(ad){var r=((D&&D.egr)||{})[ad];if(!r)return "—";var z=RZ[r[0]]||RZ.o;return z[0]+" "+z[1];}
function egYakin(e,yon,cok){var a=e&&(yon<0?e.sd:e.sr);if(!a||!a.length)return null;if(!cok)return a[0];for(var i=0;i<a.length;i++)if(a[i][1]>=3)return a[i];return null;}
function egMetin(k,ek){var e=k.eg,f=k.f,L=[];if(!e||!f)return "";
 function li(b,m,rz){L.push("<li><b>"+b+"</b> "+m+rozet(rz)+"</li>");}
 var t=e.tc,m;
 if(t){m=(t.y>0?"📈 Yükselen":"📉 Düşen")+" çizgi (haftalık "+(t.y>0?"diplerden":"tepelerden")+", "+tr(t.qt)+" başlangıçlı): <b>"+t.n+" temas</b>, şu an "+sayi(t.v)+" (fiyata göre "+fark(t.v,f)+"), haftada "+(t.e>=0?"+":"−")+"%"+sayi(Math.abs(t.e*100),1)+".";
  m+=t.n>=3?" <span class=\"egn\">Çok temaslı: eğitmene göre tuzak / süpürme adayı (\"2 kez zıplatırlar, 3.'de kırarlar\").</span>":" <span class=\"egn\">2 temas: eğitmene göre henüz \"çok temaslı\" değil.</span>";}
 else m="Son 2 yılda kırılmamış belirgin trend çizgisi yok.";
 li("1 · Trend çizgisi",m,"trend");
 function sv(ad,yon){var a=egYakin(e,yon),c=egYakin(e,yon,1),h;if(!a)return (yon<0?"Kapanışın":"kapanışın")+" %15 içinde "+ad.toLowerCase()+" yok";
  h=ad+" <b>"+sayi(a[0])+"</b> ("+a[1]+" temas, "+fark(a[0],f)+")";if(c&&c!==a)h+=", çok temaslı "+ad.toLowerCase()+" <b>"+sayi(c[0])+"</b> ("+c[1]+" temas, "+fark(c[0],f)+")";return h;}
 m=sv("Destek",-1)+" · "+sv("Direnç",1)+".";
 m+=" <span class=\"egn\">Eğitmene göre bariz seviye (çok temas) tuzaktır: stoplar desteğin altında (direncin üstünde) birikir, oraya sarkıtılır; kırılırsa alttaki seviyeye gider.</span>";
 li("2 · Bariz destek / direnç",m,"yatay");
 var r=e.dr;if(r){m="Üst durak <b>"+sayi(r.u)+"</b> (son büyük dip, "+tr(r.ut)+")"+(r.a?" · alt durak <b>"+sayi(r.a)+"</b> (önceki daha derin dip, "+tr(r.at)+")":" · altında daha derin eski dip yok")+". ";
  if(f>r.u)m+="Fiyat üst durağın üstünde (durak "+fark(r.u,f)+").";
  else if(r.a&&f>r.a)m+="<b>İnanç evresinde:</b> üst durak kırıldı, fiyat iki durak arasında. Eğitmen burada \"alma; üstte dönmezse alttan\" der.";
  else if(r.a)m+="Fiyat alt durakta ya da altında.";
  else m+="Fiyat üst durağın altında.";
  li("3 · İki durak",m,"durak");}
 var p=e.tp;if(p){
  if(p.k==="yon")m="Büyük düşüş bölümü (araştırmanın tanımı): dip "+sayi(p.dp)+", ana tepe <b>"+sayi(p.at)+"</b> "+(p.g?"haftalık kapanışla geçildi ✓":"geçilmedi (fiyata göre "+fark(p.at,f)+")");
  else m="Son dip "+sayi(p.dp)+" ("+tr(p.dt)+"); ona ait ana tepe <b>"+sayi(p.at)+"</b> ("+tr(p.att)+"): "+(p.g?"haftalık kapanışla geçildi ✓ ("+tr(p.gt)+")":"geçilmedi (fiyata göre "+fark(p.at,f)+")");
  m+=". Tepecik: "+(p.tc?sayi(p.tc)+(p.tg?" — geçildi ✓":" — geçilmedi (fiyata göre "+fark(p.tc,f)+")"):"henüz oluşmadı")+".";
  if(!p.g)m+=" <span class=\"egn\">Eğitmene göre dönüş = ana tepenin üstünde haftalık kapanış (uzaksa tepecik).</span>";
  li("4 · Ana tepe / tepecik",m,"tepe");}
 var b=e.kt;if(b&&b.u>b.a){var gen=b.u/b.a-1;m="Son 8 hafta kutusu <b>"+sayi(b.a)+" – "+sayi(b.u)+"</b> (genişlik %"+Math.round(gen*100)+"). ";
  if(f>b.u)m+="Fiyat kutunun üstünde.";else if(f<b.a)m+="Fiyat kutunun altında.";
  else{var kp=(f-b.a)/(b.u-b.a);m+="Fiyat kutunun içinde, "+(kp<1/3?"<b>alt üçte birinde</b>":kp<2/3?"orta üçte birinde":"üst üçte birinde")+" (%"+Math.round(kp*100)+").";}
  if(k.kutu&&(k.d||{}).kutu)m+=" 📦 Araştırmanın kutu alt bölgesi şartları da sağlanıyor.";else if(gen>0.30)m+=" <span class=\"egn\">Genişlik %30'dan fazla: araştırmanın kutu tanımına girmiyor.</span>";
  li("5 · Kutu",m,"kutu");}
 var z=e.kz;if(z){m=(z.ad==="a"?"Alt duraktan":"Üst duraktan")+" ("+sayi(z.g)+") "+(z.hk==="t"?"ana tepeye":"3 yılın tepesine")+" ("+sayi(z.h)+") kâr %"+Math.round((z.h/z.g-1)*100)+", stop "+sayi(z.s)+" (durağın 1 haftalık ATR altı) zarar %"+sayi((1-z.s/z.g)*100,1)+" → <b>oran 1:"+sayi(z.o,1)+"</b>. Eğitmen 1:4'ü yeterli sayıyor.";
  if(z.h>f){var kal=z.h/f-1;m+=" Fiyattan hedefe kalan kâr %"+Math.round(kal*100)+(kal<0.30?" <span class=\"egn\">(eğitmen: \"%30 kalmıyorsa aşağıdan alırız\")</span>":"")+".";}
  li("6 · Kâr/zarar oranı",m,"kz");}
 var c=e.kl;if(c){m="Yaklaşık kilit <b>"+sayi(c.v)+"</b> = son 26 haftanın en yüksek haftalık kapanışı (<b>yaklaşık, eğitmenin hesabı bilinmiyor</b>). Son haftalık kapanış "+sayi(c.c)+": "+(c.u?"kilidin <b>üstünde</b> ✓":"kilidin altında (kilit "+fark(c.v,c.c)+" yukarıda)")+".";
  if(!c.u&&f>c.v)m+=" Anlık fiyat kilidin üstünde: hafta kapanışında kesinleşir.";
  li("7 · Kilit seviye (yaklaşık)",m,"kilit");}
 var s=e.sp;m=s?(sayi(s.s)+" desteğinin ("+s.n+" temas) altında "+tr(s.bt)+" kapanış, "+s.gun+" işlem günü sonra ("+tr(s.t)+") kapanışla geri alındı (en düşük "+sayi(s.d)+")"+(s.h===0?", son işlem günü":", "+s.h+" işlem günü önce")+". Fiyat şimdi seviyenin "+(f>=s.s?"üstünde.":"altında: süpürme bozuldu.")):"Son 40 işlem gününde 3+ temaslı desteğin altına sarkıp geri alma yok.";
 li("8 · Son dip süpürmesi",m,"supurme");
 var q=e.da;if(q){m="Önceki (ana) dip <b>"+sayi(q.a)+"</b> ("+tr(q.at)+", son 3 yılın en düşüğü)"+(q.u?" · yukarıdaki dip <b>"+sayi(q.u)+"</b> ("+tr(q.ut)+")":"")+". ";
  if(!q.u)m+=(q.yd<=12?"3 yılın dibi "+(q.yd===0?"bu hafta":q.yd+" hafta önce")+" yenilendi (önceki bölge kırıldıysa yapı sıfırlandı); yukarıda yeni dip henüz yok.":q.ik?"Ana dipten sonra aynı seviyede ikinci dip var (ikili dip); yukarıda yeni dip henüz oluşmadı.":"Ana dipten sonra yukarıda yeni bir dip henüz oluşmadı.");
  else if(f>q.u)m+="Fiyat bölgenin üstünde (yukarıdaki dip "+fark(q.u,f)+").";
  else if(f>=q.a)m+="<b>Fiyat takip bölgesinde</b> (bölgenin %"+Math.round((f-q.a)/(q.u-q.a)*100)+" yüksekliğinde).";
  else m+="Fiyat önceki dibin altında: eğitmene göre bölge kırıldı.";
  if(q.gt)m+=" Bölgeye ilk iniş "+tr(q.gt)+(q.ty?"; sonra "+tr(q.ty)+" haftasında yukarıdaki dibin %5 üstünde kapanış (teyit)":"")+".";
  m+=" <span class=\"egn\">Eğitmen: \"Bir önceki dip ile yukarıdaki dip arasındaki mesafe takip edilecek yer; üstünde tutunur, yukarı giderse trend döner.\"</span>";
  li("9 · Dip arası takip bölgesi",m,"dipara");}
 var r2=e.kr;if(r2&&r2.s&&r2.s.length){var ilk=null;r2.s.forEach(function(x){if(x[0]<f&&(ilk===null||x[0]>ilk))ilk=x[0];});
  m="Son 3 yılın en büyük tepesi "+sayi(r2.t)+" ("+tr(r2.tt)+(r2.g?", sonra aşıldı":"")+"); o tepeye çıkarken bırakılan ara dipler (yeniden eskiye): "+r2.s.map(function(x){return "<b>"+sayi(x[0])+"</b>";}).join(" · ")+". ";
  m+=ilk?"Fiyatın altındaki ilk kırıntı "+sayi(ilk)+" (fiyata göre "+fark(ilk,f)+").":"Fiyat bütün kırıntıların altında.";
  m+=" <span class=\"egn\">Eğitmen: \"Tahtacı yükseltirken bu diplere ekmek kırıntısı gibi pasif alış emri bırakır; düşürürken fiyat oralarda tutulur.\"</span>";
  li("10 · Ekmek kırıntısı",m,"kirinti");}
 return "<div class=\"eg\"><div class=\"egb\">📚 Eğitim katmanı <span>· eğitmenin gözüyle · ölçüler bizim yaklaşık tanımlarımız · AL/SAT değil</span></div>"+(ek?'<div class="bos" style="margin-bottom:6px">'+ek+"</div>":"")+"<ul>"+L.join("")+"</ul>"+
  "<details><summary>Tanımlar (nasıl ölçtük?)</summary><p>Destek/direnç ve süpürme dışındakiler tamamlanmış haftalık mumlarla. <b>Temas (trend çizgisi):</b> haftanın en düşüğü (en yükseği) çizgiye ya da seviyeye 0,5 haftalık ATR kadar yaklaşması; ardışık haftalar tek temas. <b>Trend çizgisi:</b> son 2 yılın iki haftalık dönüş noktası arasından çekilen, o günden beri haftalık kapanışla kırılmamış en çok temaslı çizgi (log fiyat). <b>Bariz destek/direnç</b> (20.11 temas araştırmasının tanımı, GÜNLÜK): iki yanındaki 5 günün en düşüğü olan dip seviye kurar (1. temas); fiyat seviyeye 0,5 ATR(14) yaklaşıp kapanışla 2 tolerans yukarı zıplarsa temas +1; son temastan 250 gün sonra seviye düşer; yalnız kapanışın %15 içindekiler gösterilir. Direnç aynı kuralın tersi. <b>Durak:</b> haftalık kapanışta %15 dönüş yapan son dip (üst) ve ondan en az %5 derin önceki dip (alt). <b>Ana tepe:</b> büyük düşüş (%40+) varsa araştırmanın tanımı, yoksa son dipten önceki son %15'lik tepe; tepecik = dipten sonra %8 geri çekilen ilk tepe. <b>Kutu:</b> son 8 haftanın en yüksek ve en düşüğü. <b>Kilit:</b> son tamamlanan hafta hariç son 26 haftanın en yüksek haftalık kapanışı. <b>Süpürme</b> (günlük, aynı araştırma): 3+ temaslı desteğin bir tolerans altında kapanış, en çok 5 işlem günü içinde yeniden seviyenin üstünde kapanış; son 40 işlem günü. <b>Dip arası takip bölgesi</b>: önceki dip = son 3 yılın en düşük haftalık dibi (ana dip), yukarıdaki dip = ondan sonraki ilk onaylı dip (haftalık en yüksek/en düşükle %15 zigzag), en az %3 yüksekse yükselen yapı; şerit ikisinin arası. Videodaki ENTRA kutusunu bu tanım veriyor. Ana dipten %3'ten az yüksek dipler tabanın parçası sayılır (ikili dip). Bölgeye inişten sonraki 12 haftada yukarıdaki dibin %5 üstünde kapanış = teyit; ana dibin altında kapanış = kırılım (yeni dip ana dip olur, yapı sıfırlanır). <b>Ekmek kırıntısı:</b> aynı zigzagda son 3 yılın en büyük tepesine çıkarken bırakılan, her biri bir öncekinden yüksek en çok 4 dip.</p></details></div>";}
function egSeviye(k){var e=k.eg,f=k.f,L=[];if(!e||!EG_ACIK)return L;var C="var(--eg)";
 [[-1,"Destek"],[1,"Direnç"]].forEach(function(q){var a=egYakin(e,q[0]),c=egYakin(e,q[0],1);if(a)L.push([q[1]+" ×"+a[1],"",a[0],C,"",1.1]);if(c&&c!==a)L.push([q[1]+" ×"+c[1],"",c[0],C,"",1.1]);});
 var da=e.da&&e.da.y>0?e.da:null;function yakin(v){return da&&(Math.abs(v/da.u-1)<0.01||Math.abs(v/da.a-1)<0.01);}
 if(e.dr){if(!yakin(e.dr.u))L.push(["Üst durak","",e.dr.u,C,"7 3",1]);if(e.dr.a&&!yakin(e.dr.a))L.push(["Alt durak","",e.dr.a,C,"7 3",1]);}
 if(da){L.push(["Yukarıdaki dip","",da.u,C,"",1]);L.push(["Önceki (ana) dip","",da.a,C,"",1]);}
 if(e.kr&&e.kr.s)e.kr.s.forEach(function(x){if(!yakin(x[0])&&!L.some(function(r){return Math.abs(r[2]/x[0]-1)<0.01;}))L.push(["Kırıntı","",x[0],C,"1 3",1]);});
 if(e.kl)L.push(["Kilit ≈","",e.kl.v,C,"2 2",1.2]);
 if(e.tp&&e.tp.k==="zz"&&!e.tp.g)L.push(["Ana tepe (son dip)","",e.tp.at,C,"5 3",1]);
 return L;}
function emF(k,v){return v==null?"—":sayi(v)+" "+k.br;}
function tbMetin(k){var t=k.tb,f=k.f,h;
 if(!t)return '<div class="tbp"><p>🧱 <b>Taban bölgesi:</b> son 10 yılda tanıma uyan taban yok (en az 8 hafta yatay, ardından bir yıl içinde %40+ yükseliş).</p>'+rozet("taban")+tbrMetin()+"</div>";
 h="<p>🧱 <b>Taban bölgesi</b> (son büyük yükselişin kalktığı yatay taban): "+tr(t.bt)+" – "+tr(t.bs)+" ("+t.n+" hafta). Bölge <b>"+emF(k,t.a)+" – "+emF(k,t.u)+"</b> (gövdelerin yoğunlaştığı bant; tüm gövdeler "+sayi(t.a0)+" – "+sayi(t.u0)+"). Tabanın tavanı = <b>kırılan eski tepe "+emF(k,t.tv)+"</b>. "+tr(t.kt)+" haftasında yukarı kırıldı, en yüksek "+emF(k,t.tp)+" ("+tr(t.tpt)+", bölge üstünden +%"+Math.round(t.it*100)+").</p>";
 if(f>t.tv)h+="<p>Fiyat "+emF(k,f)+": kırılan eski tepenin <b>"+fark(f,t.tv)+"</b> üstünde · bölge üst kenarı "+fark(t.u,f)+" · bölge alt kenarı "+fark(t.a,f)+".</p>";
 else if(f>t.u)h+="<p>Fiyat "+emF(k,f)+": <b>eski tepe ile bölge arasında</b> (eski tepe "+fark(t.tv,f)+", bölge üst kenarı "+fark(t.u,f)+").</p>";
 else if(f>=t.a)h+="<p><b>Fiyat "+emF(k,f)+": taban bölgesinin içinde</b> (bölgenin %"+Math.round((f-t.a)/(t.u-t.a)*100)+" yüksekliğinde; alt kenar "+fark(t.a,f)+").</p>";
 else h+="<p>Fiyat "+emF(k,f)+": <b>bölgenin altında</b> (alt kenar "+fark(t.a,f)+" yukarıda): taban bozulmuş.</p>";
 h+='<p class="not">'+(t.gr?"Zirveden sonra fiyat bölgenin üst kenarına ilk kez "+tr(t.gr)+" haftasında indi.":"Zirveden sonra fiyat bölgeye henüz dönmedi.")+" Eğitmenlerin anlatımında burası \"talep bölgesi\": büyük paranın topladığı, dönüşte yeniden alıcı beklenen yer. Bölge geriye dönük çizilir (taban ancak yükseliş görüldükten sonra bilinir); AL/SAT değil.</p>";
 if(/^(USD|EUR)TRY=X$/.test(k.yf||""))h+='<p class="not">'+okk()+" Kur yıllardır sürekli yükseldiği için taban/kelepir mantığı dövizde zayıf: eski tabana dönüş pek beklenmez.</p>";
 return '<div class="tbp">'+h+rozet("taban")+tbrMetin()+"</div>";}
function tbrMetin(){var r=D&&D.tbr;if(!r)return "";var z=RZ[r[0]]||RZ.o;return '<div class="rz"><b>'+"Emtia/dövizde ölçüldü: "+z[0]+" "+z[1]+"</b> "+esc(r[1])+"</div>";}
function emDurum(k){var e=k.kel,d=k.d||{},f=k.f,y=k.yon,s=k.sv,h="";
 if(e&&d.kel==="kelepir")h+="<p>🟢 <b>Kelepir bandında</b>: "+yil(e.T_t)+" tabanı "+emF(k,e.T)+" → "+yil(e.P_t)+" tepesi "+emF(k,e.P)+" ("+sayi(e.kat,1)+" kat); bant "+sayi(e.kel_alt)+" – "+sayi(e.kel_ust)+".</p>";
 else if(e&&d.kel==="ucuz")h+="<p><b>Ucuz bandında</b>: "+yil(e.T_t)+" tabanı "+emF(k,e.T)+" → "+yil(e.P_t)+" tepesi "+emF(k,e.P)+" ("+sayi(e.kat,1)+" kat); ucuz bandı "+sayi(e.kel_ust)+" – "+sayi(e.ucuz_ust)+".</p>";
 else if(e&&d.kel==="altinda")h+="<p>Ralli tabanının ("+emF(k,e.T)+", "+yil(e.T_t)+") da altında.</p>";
 else if(e&&e.kat>=4)h+='<p class="not">Kelepir / ucuz bandında değil: son 5 yılın büyük rallisi '+emF(k,e.T)+" ("+yil(e.T_t)+") → "+emF(k,e.P)+" ("+yil(e.P_t)+"), "+sayi(e.kat,1)+" kat. Ucuz bandı "+sayi(e.ucuz_ust)+" altında başlar ("+fark(e.ucuz_ust,f)+").</p>";
 else if(e)h+='<p class="not">Kelepir: son 5 yılda tabanının 4 katına çıkan ralli yok ('+sayi(e.kat,1)+" kat).</p>";
 if(k.kutu&&d.kutu)h+="<p>📦 <b>Kutunun alt bölgesinde</b>: 8 haftadır "+sayi(k.kutu.alt)+" – "+sayi(k.kutu.ust)+", fiyat alt üçte birde ("+sayi(k.kutu.ucte)+" altı).</p>";
 if(y){if(y.asildi!=null)h+="<p>📊 Büyük düşüş (zirve "+sayi(y.zirve)+", dip "+sayi(y.dip)+", −%"+Math.round(y.dusus*100)+") bitti: ana tepe "+sayi(y.ana_tepe)+" haftalık kapanışla aşıldı.</p>";
  else h+="<p>📊 <b>Büyük düşüş sonrası</b>: 104 haftalık zirveden ("+sayi(y.zirve)+") −%"+Math.round(y.dusus*100)+"; dip "+sayi(y.dip)+" ("+(y.dip_yas===0?"bu hafta":y.dip_yas+" hafta önce")+"), ana tepe "+sayi(y.ana_tepe)+(y.tepecik?", tepecik "+sayi(y.tepecik)+(y.tgec?" (geçildi)":""):"")+". "+(y.ilk?"İlk tepki (+%20) geldi.":"Dipten henüz +%20 tepki yok.")+"</p>";}
 if(d.konum!=null&&s)h+="<p>Son 3 yılın tepe-dip aralığının <b>%"+Math.round(Math.max(0,Math.min(1,d.konum))*100)+"</b>'inde (tepe "+sayi(s.tepe)+", dip "+sayi(s.dip)+", orta "+sayi(s.orta)+").</p>";
 return h+'<p class="not">Hisse kartlarındaki geçmiş oranlar (ör. "kelepirden sonra +35 puan") BIST hisselerinden ölçüldü; altın, gümüş, döviz ve Bitcoin için ölçülmedi, bu yüzden burada yazılmadı.</p>';}
function kartEm(kod){var E=D.em,k=E.h[kod];if(!k)return "";
 return '<div class="hk" id="h_'+esc(kod)+'"><div class="bas"><b class="kod">'+esc(k.ad)+'</b><span class="fy">'+emF(k,k.f)+'</span><span class="etk">'+esc(k.yf)+'</span><span class="m">son veri '+tr(k.son)+" · bilgi amaçlı, AL/SAT değil</span></div>"+
  '<div class="izg"><div class="dur">'+tbMetin(k)+emDurum(k)+"</div><div>"+grafik(k)+tablo(k)+"</div></div>"+egMetin(k,"Rozetler BIST (ve ABD) hisselerindeki ölçümdür; altın, döviz ve Bitcoin için ayrıca ölçülmedi.")+"</div>";}
function emCip(kod){var k=D.em.h[kod],t=k.tb,ek="";if(t&&k.f)ek=k.f>t.u?"tabana %"+sayi(Math.abs(t.u/k.f-1)*100,1):k.f>=t.a?"🧱 tabanda":"taban altında";
 return '<button class="cip'+(kod===EMS?" sec":"")+'" onclick="emSec(\''+esc(kod)+'\')">'+esc(k.ad)+" "+emF(k,k.f)+(ek?" <small>"+ek+"</small>":"")+"</button>";}
function emCiz(){var el=document.getElementById("emtia"),E=D&&D.em;if(!el)return;if(!E||!E.h||!Object.keys(E.h).length){el.innerHTML="";return;}
 var sira=(E.sira||Object.keys(E.h)).filter(function(x){return E.h[x];});if(!EMS||!E.h[EMS])EMS=sira[0];
 el.innerHTML='<div class="kart emk"><h2>🥇 Altın, gümüş ve döviz</h2><div class="bos">Hisse kartlarıyla aynı ölçüler (haftalık) + <b>🧱 taban bölgesi</b>: son büyük yükselişin kalktığı yatay taban ve fiyatın ona uzaklığı. Sadece bilgi, AL/SAT değil. Veri '+esc(E.t||"?")+(E.taze===false?" · ⚠️ son denemede veri alınamadı, eski veri":"")+'.</div><div class="cips">'+sira.map(emCip).join("")+"</div>"+kartEm(EMS)+"</div>";}
function emSec(kod){EMS=kod;emCiz();try{history.replaceState(null,"","#"+kod);}catch(e){}}
function kart(kod){var k=H[kod];if(!k)return "";var d=k.d||{};
 var dur=kelMetin(k,kod)+kutuMetin(k)+yonMetin(k)+svMetin(k)+yabMetin(k);
 if(!dur)dur='<p class="bos">Bu hisse için öne çıkan durum yok.</p>';
 return '<div class="hk" id="h_'+esc(kod)+'"><div class="bas"><b class="kod">'+esc(kod)+'</b><span class="fy">'+sayi(k.f)+' TL</span><span class="etk">'+(k.g==="ana"?"ana liste":"küçük hisse")+"</span>"+(k.dk?'<span class="etk dk">⚠️ panoda risk uyarısı</span>':"")+'<span class="m">bilgi amaçlı, AL/SAT değil</span></div>'+
  '<div class="izg"><div class="dur">'+dur+'</div><div>'+grafik(k)+tablo(k)+"</div></div>"+egMetin(k)+"</div>";}
function cip(kod,ek){return '<button class="cip" onclick="sec(\''+esc(kod)+'\')">'+esc(kod)+(ek?" <small>"+ek+"</small>":"")+"</button>";}
function listeler(){var L=D.liste||{},h="";
 function kutu(baslik,aciklama,dizi,ek){h+='<div class="kart"><h2>'+baslik+'</h2><div class="bos" style="margin-bottom:6px">'+aciklama+'</div><div class="cips">'+(dizi&&dizi.length?dizi.map(function(k){return cip(k,ek(k));}).join("")+'<span class="bos"> ('+dizi.length+' hisse)</span>':'<span class="bos">Şu an yok.</span>')+"</div></div>";}
 kutu("🟢 Şu an kelepir bandında","Büyük (≥4 kat) rallinin başladığı tabana dönenler. Yanındaki sayı: fiyat ÷ taban. ×1,2 civarı = banda yeni girmiş (üst uç) · ×1,0 civarı = taban test ediliyor · 1’in altı (ör. ×0,84) = taban kırılmış: daha ucuz ama taban tutmamış, daha riskli. Hangi değerin daha iyi olduğu 25 yıllık veride kesin ayrışmadı (taban civarı 3 yılda biraz iyi görünüyor, az olay).",L.kelepir,function(k){return "×"+sayi(H[k].f/H[k].kel.T,2);});
 kutu("📦 Kutu alt bölgesinde","Tepeden çekilip 8 haftalık dar kutuya giren, fiyatı kutunun alt üçte birinde olanlar.",L.kutu,function(k){return "";});
 kutu("Ucuz bandında","Rallinin büyük kısmını geri vermiş, kelepirin bir üstündeki bant.",L.ucuz,function(k){return "×"+sayi(H[k].f/H[k].kel.T,1);});
 kutu("📚 Çok temaslı desteğe yakın","Eğitim katmanı: fiyat 3+ temaslı yatay desteğin en çok %3 üstünde (eğitmene göre stoplar altında birikir). BIST ölçümü: "+rzKisa("yatay")+". AL/SAT değil.",L.tdestek,function(k){var z=egYakin(H[k].eg,-1,1);return z?"+%"+sayi((H[k].f/z[0]-1)*100,1):"";});
 kutu("📚 Dip arası takip bölgesinde","Eğitim katmanı: son 3 yılın ana dibinden sonra daha yüksek bir dip oluşmuş ve fiyat ikisinin arasında. Eğitmen: \"takip edilecek yer\". Yanındaki sayı: bölgedeki yeri (%0 = önceki dip, %100 = yukarıdaki dip). BIST ölçümü: "+rzKisa("dipara")+" (bölgeye özgü değil). AL/SAT değil.",L.dipara,function(k){var q=H[k].eg.da;return "%"+Math.round((H[k].f-q.a)/(q.u-q.a)*100);});
 kutu("📚 Son dip süpürmesi","Eğitim katmanı: son ~4 haftada (20 işlem günü) 3+ temaslı desteğin altında kapanıp 5 gün içinde geri alanlar. BIST ölçümü: "+rzKisa("supurme")+". AL/SAT değil.",L.supurme,function(k){var h=H[k].eg.sp.h;return h===0?"bugün":h+" gün önce";});
 document.getElementById("listeler").innerHTML=h;}
function suz(){var q=document.getElementById("ara").value.trim().toUpperCase(),s=document.getElementById("suzgec").value,L=D.liste||{};
 if(q)return KODLAR.filter(function(k){return k.indexOf(q)===0;}).concat(KODLAR.filter(function(k){return k.indexOf(q)>0;}));
 if(s==="one"){var g={},o=[];(L.kelepir||[]).concat(L.kutu||[],L.ucuz||[]).forEach(function(k){if(!g[k]){g[k]=1;o.push(k);}});return o;}
 if(s==="hepsi")return KODLAR;
 if(s==="kelepir"||s==="ucuz"||s==="kutu")return L[s]||[];
 if(s==="dusus")return L.dusus||[];
 if(s==="tdestek"||s==="supurme"||s==="dipara")return L[s]||[];
 if(s==="ana"||s==="kucuk")return KODLAR.filter(function(k){return H[k].g===s;});
 return KODLAR.filter(function(k){var c=(H[k].d||{}).konum;return c!=null&&(s==="ucuzyari"?c<0.5:c>=0.5);}).sort(function(a,b){return (H[a].d.konum-H[b].d.konum)*(s==="ucuzyari"?1:-1);});}
function ciz(){var L=suz(),h=L.slice(0,GOSTER).map(kart).join("");if(!L.length)h='<div class="kart bos">Eşleşen hisse yok.</div>';
 if(L.length>GOSTER)h+='<button class="dahafazla" onclick="GOSTER+=20;ciz()">Daha fazla göster ('+(L.length-GOSTER)+" kaldı)</button>";
 document.getElementById("kartlar").innerHTML=h;document.getElementById("say").textContent=L.length+" hisse";}
function sec(kod){document.getElementById("ara").value=kod;GOSTER=20;ciz();try{history.replaceState(null,"","#"+kod);}catch(e){}
 var el=document.getElementById("kartlar");if(el.scrollIntoView)el.scrollIntoView({behavior:"smooth",block:"start"});}
function basla(d){D=d;H=d.h||{};KODLAR=Object.keys(H).sort();
 var t="Seviyeler "+(d.uretim||"?")+" · fiyat "+(d.guncel||"?")+" · hafta "+tr(d.hafta)+(d.tamam?" (kapandı)":" (sürüyor; durumlar hafta kapanışında kesinleşir)");
 if(!d.taze)t+=" · ⚠️ uzun geçmiş alınamadı, seviyeler eski";
 document.getElementById("tarih").textContent=t;document.getElementById("kaynak").textContent=KODLAR.length+" hisse · ana liste + küçük hisseler, MANIPULE hariç · veri Yahoo (~15 dk gecikmeli).";
 var h=decodeURIComponent((location.hash||"").slice(1)).toUpperCase();if(d.em&&d.em.h&&d.em.h[h])EMS=h;
 try{emCiz();}catch(e){document.getElementById("emtia").innerHTML="";}
 listeler();if(h&&H[h])document.getElementById("ara").value=h;ciz();
 if(EMS&&EMS===h){var el=document.getElementById("emtia");if(el&&el.scrollIntoView)el.scrollIntoView({block:"start"});}}
function hata(){document.getElementById("tarih").textContent="harita verisi (harita.json) okunamadı";document.getElementById("kartlar").innerHTML='<div class="kart bos">Harita henüz üretilmedi ya da okunamadı. Bir sonraki taramadan sonra tekrar dene.</div>';}
function al(u){return fetch(u+"?v="+Date.now(),{cache:"no-store"}).then(function(r){if(!r.ok)throw 0;return r.json();}).then(function(d){if(!d||!d.h)throw 0;return d;});}
document.getElementById("ara").addEventListener("input",function(){GOSTER=20;ciz();});
function egDugme(){var b=document.getElementById("egbtn");b.textContent="📚 Eğitim çizgileri: "+(EG_ACIK?"açık":"kapalı");b.setAttribute("aria-pressed",EG_ACIK?"true":"false");}
egDugme();document.getElementById("egbtn").addEventListener("click",function(){EG_ACIK=!EG_ACIK;try{localStorage.setItem("harita_eg",EG_ACIK?"1":"0");}catch(e){}egDugme();if(D){ciz();try{emCiz();}catch(e){}}});
document.getElementById("suzgec").addEventListener("change",function(){document.getElementById("ara").value="";GOSTER=20;ciz();});
al("harita.json").then(basla).catch(function(){if(location.hostname.indexOf("boranzz.github.io")<0&&location.protocol!=="file:")al(ANA_URL).then(basla).catch(hata);else hata();});
</script></body></html>
"""
