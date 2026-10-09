# BIST Sinyal Sistemi — Proje Notları (Claude Code için)

Bu depo, Borsa İstanbul (BIST) hisseleri için günlük teknik/temel sinyal panosu üretir.
Amaç: karar-destek aracı. **Yatırım tavsiyesi değildir**; kullanıcı kararı kendi verir.
Arayüz ve tüm metinler **Türkçe**. Kullanıcı kod bilmiyor — ona sade anlat, terminal
komutlarını tek tek ver.

## Nasıl çalışır
- GitHub Actions (`.github/workflows/tarama.yml`) hafta içi piyasa saatinde ~15 dk'da bir
  `python tarama.py` çalıştırır → `index.html` (pano), `gecmis.html` (canlı karne) üretir,
  yeni AL sinyallerini Telegram'a yollar, dosyaları repoya geri commit'ler.
- GitHub Pages `index.html`'i yayınlar: https://boranzz.github.io/Bist-signal/
- `backtest.yml` elle çalışır → gerçek 2 yıl veriyle `backtest.html`.
- Veri kaynağı: yfinance (`KOD.IS`), ~15 dk gecikmeli, ücretsiz.
- GitHub'ın cron'u saatlerce gecikiyor/atlıyor; asıl tetik cron-job.org → workflow_dispatch (README).
- Telegram: tüm hisselerde yeni AL; SAT sadece portföyde. NÖTR ara geçişleri sayılmaz
  (`durum.json` → `son`). Portföy repo'nun `PORTFOY` **variable**'ından gelir (kullanıcı onayıyla
  secret yerine variable: cihazlar arası eşitleme için). Pano, kullanıcının cihazındaki
  fine-grained anahtarla (Variables: R/W) her değişiklikte yazar. Anahtar localStorage'da
  olduğu için sayfaya üçüncü taraf script ekleme (TradingView tv.js bu yüzden kaldırıldı).
  **Actions logları herkese açık: portföy içeriğini/kodlarını asla print etme.**
  **durum.json da herkese açık:** portföyü ele verebilecek her anahtar `_gizli()` (TELEGRAM_TOKEN ile HMAC) ile
  saklanır (`sat_teyit_g`, `karar_kirilim_g`, alarm özetleri); portföy hissesine ait FİYAT da yazılmaz (fiyat
  hisseyi ele verir — karar çizgisi dünkü veriden yeniden hesaplanır). 2026-09-25/26'da `sat_teyit` düz kodla
  yazılmıştı (5 portföy kodu herkese açık göründü) — düzeltildi; git geçmişinde duruyor.

## Arkadaş kopyaları (fork)
Başkası kendi portföyü/Telegram'ı için repo'yu fork'lar (adımlar `KENDI-KOPYAN.md`). Bu yüzden depo adı sabit yazılmaz:
`pano.REPO` / `tarama.PANO_URL` Actions'ın `GITHUB_REPOSITORY`'sinden, panodaki `GH_REPO` adres çubuğundan (`<kullanıcı>.github.io/<repo>`)
türetilir; yerelde `BoranZZ/Bist-signal`. Fork'ta `tarama.yml` her taramada ana projeden `*.py`, `requirements.txt`, `*.md`'yi
alır (`KOD_GUNCELLE=hayir` variable'ı kapatır); veri dosyaları (durum/gecmis/index) fork'un kendisinin. Workflow dosyaları
GITHUB_TOKEN ile güncellenemez → workflow değişirse arkadaşa elle güncellemesini söyle. Yeni veri dosyası eklerken
`*.py`/`*.md` dışında bırak (aksi halde ana projeninki fork'unkini ezer).

## Dosyalar
- `sinyal.py` — gösterge + sinyal çekirdeği. **Tek kural seti** (canlı tarama + backtest ortak).
  SuperTrend, MACD, EMA20/50, RSI, Stochastic oy verir; ADX/Bollinger bağlam. `analiz_et(df)`
  son gün özetini döndürür (sinyal, uyum, detay, sinyal_gun, giris_stop, hedef, spark...).
- `tarama.py` — evren (BIST100 + EK_HISSELER + izleme listesi), oran önbelleği (F/K, PD/DD, FD-FAVÖK günde 1),
  yorum üretimi, sinyal geçmişi (gecmis.json), Telegram. Ayarlar dosyanın başında.
- `pano.py` — `index.html` ve `gecmis.html` üretir. Portföy istemci tarafında (localStorage),
  modalda kendi SVG grafiğimiz + TradingView butonu.
- `backtest.py` — ertesi-gün girişli, komisyonlu, al-tut kıyaslı simülasyon.
- `gunici.py` — ⏱️ gün içi görünüm (15 dk / 1 s / 4 s durum bilgisi; aşağıda 'Vadeler').

## Önemli ilkeler
- Sinyal kuralları tek yerde (`sinyal.py`); backtest ve canlı aynı motoru kullanmalı.
- Backtest'te look-ahead yasak; işleme ertesi gün girilir; maliyet `backtest.KOMISYON = 0.002` alışta VE satışta ayrı ayrı
  düşülür (`net = (1−K)·çıkış/giriş·(1−K) − 1` → gidiş-dönüş ≈ %0,4; eskiden burada yanlışlıkla 'çift yön %0,2' yazıyordu, kod hep
  böyleydi — 2026-10 kontrolü). Tüm geçmiş kararlar bu düzenekle alındı; değiştirme. Bazı scratchpad araştırmaları %0,1/yön kullandı.
- Dürüstlük: "daha çok gösterge = daha isabetli" değil; pusula backtest + canlı karne.
- Finansal tavsiye verme; stop/pozisyon büyüklüğü/risk vurgusu koru.

## TradingView notu (bilinen kısıt)
Ücretsiz TradingView gömülü widget'ı BIST sembollerini gösteremiyor ("sadece TradingView'de
bulunabilir" deyip Apple'a düşüyor). Bu yüzden modaldaki gömülü TradingView güvenilir değil.
Plan: kendi SVG grafiğimizi asıl grafik yap (eksen değerleri, daha uzun geçmiş, hover ile
tarih/fiyat), TradingView'i sadece "tam ekran aç" butonu olarak bırak.

## BEKLEYEN İŞLER (öncelik sırası)
1. **Grafik:** YAPILDI (eksenler, 6 ay, AL/SAT dönüş işaretleri, fare/dokunma ile değer). Eski not: kendi SVG grafiğini büyüt, fiyat/tarih
   eksen değerleri ekle, daha uzun geçmiş + hover tooltip. "Tam ekran aç" butonu kalsın.
2. **Hacim/likidite filtresi:** TEST EDİLDİ, GEREKMİYOR (2026-09-28, bt/likidite1.py: 586 hisse, 2022-26, ~2.000 v3
   işlemi; 60g medyan TL hacmine göre borsa içi sıra ya da nominal eşikte düşük likiditeli AL'ler kötü değil, farklar
   birkaç uç işlemden; en iyi 10 hariç gruplar benzer). Liste zaten <50 mn TL küçükleri almıyor.
3. **Destek/direnç + DİP mantığı:** YAPILDI (`sinyal.destek_direnc`): son 120 günün
   dip/tepelerinden "Destekten tepki" ve "Dirence yaklaşıyor" etiketleri, modalda seviye +
   tarih açıklaması. Eski RSI/Bollinger DİP etiketi kaldırıldı. Eksik kalan: düşen trend
   çizgisi kırılımı ile "olası dip".
3b. Modalda **DİP açıklaması**: YAPILDI (destek/direnç kutusu).
4. **FAVÖK açıklaması:** YAPILDI (açıklama kartı eklendi).
5. **KAP/haber akışı:** hisse başına son bildirim/haber (ücretsiz kaynak); yorumlamayı
   abartma (haber çoğu zaman fiyata yansımıştır).
6. Sektör dağılımı + yoğunlaşma uyarısı, haftalık Telegram özeti ve fiyat alarmı YAPILDI.

## Kullanıcının okumayı bilmediği şeyler (öğretilecek)
RSI, MACD ve hacim panellerinin nasıl okunacağını sade anlat (grafik dersi).

## Periyodik bakım
`tarama.py`'deki `BIST100` listesi 1 Ekim – 31 Aralık 2026 dönemine göre. Borsa İstanbul bileşimi
3 ayda bir değiştirir (sonraki: Ocak 2027). Endeksten çıkanları silme, `EK_HISSELER`'e taşı
(portföy ve sinyal geçmişi kopmasın). Yeni kodları yfinance'ta şirket adıyla doğrula.
`HALKA_ARZ` (son 12 ayın arzları: işlem başlangıcı + arz fiyatı, kaynak halkarz.com) ayda bir
güncellenmeli (güncelleyince `BIST100_GECERLI` / `HALKA_ARZ_GUNCEL` tarihlerini de değiştir: haftalık özet bunlara göre
🔧 bakım hatırlatması yapar); yfinance BIST bedelsiz/bölünme kaydı tutmuyor, arzdan beri getiri bölünmede yanılır.
Fon krizinde çöken şişirilmiş hisseler (TERA, SMRTG, GENIL, MIATK) listeden çıkarıldı; kullanıcı
isteğiyle faiz yüzünden düşen eski büyükler (KONTR vb.) KALDI — tüm çökenleri çıkarma.

## Tahtacı (şişir-çak) uyarısı — `sinyal.tahta_riski`
Olay çalışması (2022-26, tüm hisseler, bölünme düzeltmeli): 20 günde ≥%25 çakılma taban oranı %2,3. 🎈 şişme
(10g ≥5 tavan %19 / 20g ≥%100 %15 / 50g ort +%70 ve 20g std ≥%6 %16 / ≥3 tavan + hacim 5g/60g ≥3x %19) ve ⚠️ dağıtım
(hacim 5g/60g >2x iken 10g zirvenin %8+ altı, %9,5). Küçük tahta (düşük TL hacim) tek başına risk artırmıyor.
v3 girişlerinin sadece 1/417'si uyarılı günde (şablon + oynaklık filtresi zaten eliyor) → 🎈'de AL mesajı gitmez.
'Dipten kaldırma' tahmin edilemedi: tepeden %50+ çöken 75 olayda 60 gün sonrası −%65…+%189, hacim artışı ayırmıyor.
Pano rozeti + modal kutusu, portföy özetinde not. (scratchpad bt/tahta1.py)

## 🪤 Düşen trend kırılımı tuzağı — `sinyal.trend_tuzagi` (kullanıcının 'tahtacı' tarifi)
Düşük seviyedeki hisse (120g zirvesinin ≥%25 altı, < SMA50) iki tepeden çizilen düşen trendi ≥%4 yükselişle kırınca
küçük yatırımcı 'AL' okur. Tüm borsa (KAP'tan 586 hisse, 2022-26, 1.209 olay; bt/tahta2-3.py): %56'sı 15 günde kırılım
kapanışının %5+ altına döndü, %29'u +%20'ye ulaştı. Kırılımda alıp 60 gün tutmak aynı hisselerde rastgele günden kötü
(ort +%12,9 / medyan +%2 vs +%16 / +%3,7). Hacim, fitil, piyasa, hisse büyüklüğü tuzağı ayırmıyor (%55-68). Tuzak
sonrası 'dipten topla' sadece geriye bakınca iyi; gerçekçi limit emirle (kırılımın %5-15 altı) avantaj yok. → Sadece
uyarı rozeti (son 5 gün), sinyal değil. Canlı fonksiyon olayları birebir buluyor (150/150).

## Güç puanı, ayın güçlüleri, küçük hisseler, işaret sözlüğü (2026-09-26)
- 💪 Güç (`sinyal.guc_puani`, 0-7): şablon, Ichimoku (bulut üstü + tenkan>kijun), 55g zirveye ≤%3, CMF>0.05, ADX>25 & +DI>-DI,
  EMA10>EMA30, RSI>50. Test (bt/guc1.py; 125 ve 586 hisse): sonraki 20 günde endekse göre getiri puanla artıyor (iki faiz
  döneminde); 60 günde düşük faizde ters; v3 girişlerini seçmiyor → tablo sütunu + modal, Telegram'a GİRMEZ.
- 📈 Ayın güçlüleri (`tarama.momentum_listesi`): 6 ay getiri (son ay hariç) ilk %20, fiyat > SMA200, SADECE BIST100+EK
  (küçük hisseler dahil edilince tepeye +%1000-2000 şişirilmiş hisseler çıkıyordu). `durum.json` → `mom_ay`;
  ayın ilk kesin kapanış taramasında Telegram listesi (ilk çalışma sessiz). Bilgi; gece testi: v3 ile yarı yarıya iyi.
- `KUCUK_HISSELER`: BIST100/EK dışı, 60g medyan işlem ≥ 50 mn TL (163 hisse, KAP kod listesi) — tahtacı uyarıları görünsün diye.
- Pano altında 'İşaretler ne demek?' sözlüğü (tüm rozetler tek yerde); eski tekrar eden 3 açıklama kartı kaldırıldı.

## Veri kalitesi: Yahoo günlük kapanışı yanlış / boş
Yahoo'nun BIST günlük barlarında kapanış çoğu zaman resmi kapanıştan farklı (Eylül 2026: günlerin ~%30'unda >%0,3; THYAO
24.09 günlük 288,5, resmi 289,5) ve son günün kapanışı NaN geliyor (dropna ile önceki gün gösteriliyordu: THYAO 288,5 vs
gerçek 290,75). Saatlik verinin gün sonu = resmi kapanış (fast_info.previous_close ile 16/16). `veri_cek`: son 3 günün
kapanışı gün içi veriden (2026-10'dan beri 15 dk'lık: 326 hissede 1.956 gün sonu kapanışı saatlikle birebir aynı; 15 dk alınamazsa
eski saatlik indirmeye düşer); kesin kapanış (18:30+/hafta sonu) sonrası son gün `fast_info.last_price` (kapanış seansı, 12 iş
parçacığı, ~10 sn). Günlük–saatlik farkı >%2 ise (temettü düzeltmesi) dokunulmaz. Eski backtest verisindeki bu küçük
rastgele hatalar (~%0,3) sonuçları yönlü etkilemez.

## Veri kalitesi: kaydedilmemiş bedelsiz/bölünme
yfinance BIST bölünmelerini çoğu zaman kaydetmiyor (5 yılda 125 hissede 12 olay: KONTR, FENER×3, CCOLA, HEKTS, TUKAS,
BSOKE, EUREN, CVKMD...). BIST günlük sınırı ±%10 olduğundan tek gün ≤−%25 / ≥+%35 kapanış değişimi bölünme sayılır:
`sinyal.bolunme_duzelt` önceki fiyatları düzeltir (analiz_et, backtest, karar çizgisi). Aksi halde göstergeler, iz stop
ve 'çöken hisse' sınıflaması bozulur, bedelsiz günü yanlış 'iz stop kırıldı' gelir. Düzeltilmiş veriyle v3/v2 kıyası
değişmedi. Son 30 günde bölünme olan portföy hissesinde 'maliyetini güncelle' notu (kullanıcının maliyeti eski fiyatla).

## Klasik grafik formasyonları — TEST EDİLDİ, EKLENMEDİ (2026-09-29)
3 paralel araştırma (125 + 586 hisse, 2022-09 → 2026-09, iki faiz dönemi, çökenler hariç; pivotlar `_pivotlar` ile, look-ahead
yok; aynı hisse/dönem/SMA200 trendindeki rastgele günlerle kıyas; sepet/portföy simülasyonu; parametre komşuları). Scriptler:
scratchpad `bt/formasyon/` (dip_ortak + dip1-5, tepe_ortak + tepe1-5, devam_ortak + devam1-4). Sonuç: **11 formasyonun hiçbiri
sinyal, filtre, etiket ya da çıkış olarak eklenmeye değmez.** Kullanıcı formasyon sorarsa bu sonucu anlat, baştan araştırma.
- **Dip (W, TOBO, üçlü dip) — yeni AL olarak:** rastgele günden ayrılmıyor (20g ±2 puan); hedef tutma taban oranıyla aynı
  (~%50). TOBO sadece 586'da zayıf + (60g rastgeleye göre +6/+4), 125'te yok; 60 gün tut sepeti rastgele günlerin aralığında
  (yüksek faiz +%195 vs rastgele 165..195), düşüşü daha derin. %45-67'si 15 günde tetik kapanışının %5+ altına indi (🪤 ile aynı tablo).
- **Tepe (OBO, ikili, üçlü tepe) — v3 çıkışı olarak:** %20 iz stop'u tutarlı yenmiyor. OBO çıkışı işlemlerin %67-86'sında iz
  stop'tan iyi ama büyük kazananları kesiyor (yüksek faizde ort. −5…−11 puan); sepet farkı komşu ayarlarda işaret değiştiriyor
  (586 yüksek faiz −25…0). Uyarı olarak: OBO/ikili sonrası 20g ~−1 puan göreli zayıflık, 60g kayboluyor; iz stop'a inme
  olasılığını artırmıyor, sadece biraz öne çekiyor. ("Erken çıkış yükselişte kazancı eritir" bulgusunun tekrarı.)
- **Devam (fincan-kulp, yükselen/simetrik üçgen, VCP, yatay kanal) — v3'e katkı:** olayların çoğu zaten v3 kırılımıyla aynı gün;
  formasyon etiketli v3 işlemleri etiketsizlerden 4 kıyasın 4'ünde KÖTÜ (586: +3,7 vs +8,0 / +1,2 vs +4,4) → etiket bile yanıltıcı.
  VCP'nin tek iyi sonucu (586, yüksek faiz sepet +311 vs v3 +239) en iyi 10 işlem çıkınca kayboluyor (197 vs 206), 125'te ve düşük
  faizde geride; komşu ayarlar dağınık. Bayrak (`bayrak_kirilimi`) ile aynı tablo: bilgiyi v3 şablonu zaten taşıyor.

## v3 — 🚀 trend kırılımı (2026-09 gece araştırması, canlı AL kuralı)
- AL mesajı artık gösterge oylamasından (SINYAL) DEĞİL: `sinyal.trend_kirilimi` — Minervini trend şablonu (fiyat > SMA50 >
  SMA150 > SMA200, SMA200 20 günde yükselmiş, 52h zirvesinin ≥%75'i, 52h dibinin ≥%30 üstü) iken önceki 20 günün en yüksek
  kapanışının ilk kez aşılması + XU100 > SMA50 + 60g oynaklık ≤ %5. Çıkış: girişten beri tepe kapanışın %20 altı (iz stop).
  Pozisyon açıkken yeni kırılım sayılmaz. Canlı fonksiyon backtest işlemlerini birebir üretir (124 hisse, 467 işlem, 0 fark).
- Neden: 13 gösterge/strateji aynı düzenekle (sınırsız sepet, 3 evren × 2 faiz dönemi, 2022-09-26'dan) kıyaslandı
  (scratchpad bt/gece12-14). Minervini 6 hücrenin 6'sında v2'den iyi (çökenler hariç düşük/yüksek faiz +%83/+%263 vs
  +%73/+%215); komşu ayarlar (0.70-0.80, 1.2-1.5, 10-40g kırılım) neredeyse aynı; 200 rastgele yarım listede v2'yi
  %77-97, XU100'ü %88-100 yeniyor. Düşük faizde işlem isabeti %74 (v2 %47). backtest.py'de "düşük faiz" satırında v2
  işlem başı önde görünür: v3 250 günlük ısınma yüzünden Tem-Eyl 2022 rallisini kaçırıyor (adil değil).
- Örneklem dışı (2016-2021, 85 bugünkü hisse — hayatta kalan yanlılığı ikisine de eşit): sınırsız sepette v3 ≈ v2
  (+%46/+%50, +%232/+%232), 10 yuvalı portföyde v3 4 kıyasın 3'ünde önde (+%80 vs +%32, +%232 vs +%205); ikisi de
  BIST100'ü (+%29/+%109) yeniyor, eski canlı kurallar en kötü. v3 üstünlüğü son 4 yılda belirgin, eski dönemde küçük.
- Pratik: sınırsız sepette aynı anda ~35-45 pozisyon; 10 eşit yuva (dolunca atla) sonuçları çok bozmuyor.
- Aylık momentum rotasyonu (6 ay, üst %20): yüksek faizde çok güçlü, düşük faizde XU100 gerisinde; v3 ile yarı
  yarıya 4 yılda +%717 / maks düşüş −%21 (v3 +%562 / −%25) — uygulanmadı, kullanıcıya seçenek.
- Denenip v3'ten zayıf kalanlar: 55/100/250g zirve kırılımı, ADX/DI, Bollinger sıkışma, OBV, CMF, RSI 50, EMA10/30
  (yüksek faizde iyi, düşükte zayıf), Ichimoku (iyi ama Minervini'den geride), v2 VEYA Minervini birleşimi.
- Telegram: 17:30+ kırılımlar (`tk_gonderilen`, günde bir kez), 18:30 sonrası kapanışta tutmayan için "↩️ iptal".
  SINYAL AL'i artık mesaj değil (panoda gösterge bilgisi); SAT portföy bilgisi. Karne (gecmis.json, "kural": "v3")
  sadece kesin kapanışta kayıt açar. Portföy iz stop'u: en son giriş v3 kırılımıysa ondan (`analiz_et` iz override).
- Geç giriş (çökenler hariç, 2022-26): sinyalden 0/5/10/20/40 gün sonra (pozisyon hâlâ açıksa) girince ort +%20/+%19/
  +%18/+%15/+%8, isabet %52/51/50/47/35 → panoda ≤5 gün '🚀 AL Ng önce', sonrası 'trendde · Ng' (yeni alım değil).
- Pano: 🚀 KIRILIM (bugün) / 🚀 Ng (pozisyon) / 👀 kırılıma %x (şablonda, ≤%3) rozetleri; modalda tkHtml kutusu.
- **Veri penceresi uyarısı (2026-10-08 kontrolü):** tarama 2 yıllık veri indirir, kural 250 gün ısınma ister → canlı işlem listesi
  en fazla son ~1 yıl. Aynı veride `tk_gecmis` = backtest.py v3 (313 hisse, 5y 1.083 + 2y 316 işlem, 0 fark), ama 2y pencere 5y
  veriye göre: son ~8 ayın işlemleri birebir (son 90 gün 0 fark), daha eskilerde 284 hisseden 41'inde ≥1 işlem farklı (5y'de daha
  önceden açık kalan pozisyon); açık pozisyonlarda 4 hissede giriş tarihi farklı, iz stop aynı. Düzeltmek için `veri_cek` period'u
  uzatılabilir (yapılmadı: tüm göstergeleri/uv durumunu ve çalışma süresini etkiler).

## 🚀 Sinyal geçmişi · son AL/SAT grafikte · Son roketler filtresi (2026-10, hepsi BİLGİ)
- `sinyal.tk_gecmis` → `tkg`: son 6 v3 işlemi `[sinyal günü, giriş (ertesi açılış), çıkış günü|null, çıkış kapanışı|null(, 1 = çıkış günü kilitli taban)]`
  (canlı `trend_kirilimi(ham=True)`; komisyonsuz). Portföyden bağımsız. `tk.kisa` = veri <250 gün (yeni arz: sinyal çıkamaz).
- Modal grafik: ▲ AL (yeşil, 🚀 girişi) / ▼ SAT (kırmızı, iz stop çıkışı), mor kesikli iz stop; üstte `tkSonHtml` özet satırı;
  '6 ay / 1 yıl' düğmesi — 1 yılda grafik penceresinden önceki ~6 ay HAFTALIK kapanış (`spark.w0` pazartesi + `spark.w`, x ekseni
  tarihe göre), eski işlemlerin işaretleri `tkg`'den. Kullanılmayan `spark.sg` (eski oylama dizisi) kaldırıldı. Altta `tkGecmisHtml`
  tablosu (getiri, aynı günlerde BIST 100'e göre fark — XU sinyal günü kapanışından; 6 aydan eski işlemler ≈ işaretli).
- Tablo filtresi '🚀 Son roketler' (5/20/60 işlem günü, `roketListe/roketOzet/roketHtml`): kapananlar DAHİL (seçim yanlılığı),
  sinyal gününe göre yeniden eskiye, üstte özet (sayı, artıda, ort/medyan, endekse göre), 20+ gün geç giriş notu. 'Bugün ne var?'
  kartında kısayol. `tkGun` = rozetlerdeki `tk.gun` (spark.t sırası). Python aynası testte (scratchpad sg/py_roket.py): 0 fark.
- Araştırma (2026-10-08, 5y veri): son 60 işlem gününün 50 sinyalinin 5'i artıda (ort −%11,8, medyan −%14,9; BIST 100'e göre
  medyan −8,8 puan; 37'si iz stop'la kapandı) — Ağustos kümesi piyasa düşüşüne denk geldi; AHGAZ (+%36) en iyisiydi, genel değil.
  Tarihsel 30 gün ufku (1.033 işlem): ort +%13, medyan +%6, %59 artıda; 34 aylık kohortun 6'sında artıda oranı ≤%20 (2023-04,
  2023-09/10/11, 2024-07, 2025-01) → kötü kohortlar olağan dışı değil.

## 🔒 Kilitli taban · gerçekçi iz stop çıkışı · aşırı uzama notu (2026-10, scratchpad bt/korn: 587 hisse, 2021-10…2026-10)
- **🔒 `sinyal.kilitli_taban`** (olay serisi `kilitli_taban_seri`): dün ve bugün taban (kapanış ≤ −%9, `TABAN_GETIRI`), bugün **kilitli**
  (`kilitli_gun`: Yüksek−Düşük ≤ %0,15 × kapanış = gün boyu işlem neredeyse yok), ilk tabandan önceki 10 günde taban yok, XU100 iki
  gün de > −%4. Sonuç: 15 günde 4+ tabana uzama ~%60 (n=218; canlı liste %66; tüm ilk tabanlarda ~%9), yıllara göre %49-71, iki faiz
  döneminde tutarlı; bugünkü 'taban serisi' uyarısından ~2 gün önce. Canlı fonksiyon araştırma olaylarıyla birebir (228/228, 0 fark;
  araştırma ilk 130 günü almıyordu) ve son-gün fonksiyonu olay serisiyle 3.710 hisse-günde 0 fark (scratchpad kilit/t1, t4).
  **Bilinen kör nokta:** piyasa çöküş gününde (XU100 ≤ −%4) başlayan serileri kaçırır — 16.09.2026'da (XU −%5,5) başlayan OZATD, ALKLC,
  IEYHO, MANAS, TRHOL'de 🔒 hiç yanmadı. Çöküş günündeki kilitli olaylar tutarsız: Eylül 2026 öncesi 80 olayda kesinlik %5 (78'i 2023'te),
  2026'da 16/16 → koşul gevşetilmedi.
  Rozet 1-2 gün görünür (olay günü + ertesi gün hâlâ tabansa); 15 günde 4+ taban olunca `analiz_et` `kt`'yi boşaltır, 'taban serisi'
  öncelikli (çift gösterim yok). Eşik ±%9,5 gün içi 'taban' mesajıyla değil, araştırma ve taban serisiyle aynı −%9 (BIST taban fiyatı
  önceki kapanış × 0,90'ın fiyat adımına yuvarlanmışı ≈ −%9,5…−%10; −%9 hepsini yakalar, adım hesabı gerekmiyor).
  **Zamanlama:** seans içinde Yahoo'nun gün içi Yüksek/Düşük'ü o ana kadarki işlemler → tarama `kt.kesin` ekler (18:30+ ya da son bar
  bugünün değilse kesin); kesin değilse metinde 'gün içi veri, kapanışta kesinleşir'. Telegram: portföy hissesinde gün içi olay
  `kilitli` (olay günü, fiyat hâlâ günün dibinde / tabanda ve aralık ≤ %0,15; 'taban'/'sert'i bastırır, gizli anahtarla günde bir kez)
  + akşam portföy özetinde en başta not. 🔒 olan hisseden 🚀 AL mesajı gitmez (`_riskli`, taban serisi/🎈 gibi). durum.json'a yeni
  anahtar yok. Pano: tablo rozeti, modal kutusu (taban serisi kutusuyla birlikte en üstte), sade anlat uyarısı en üstte (🔒 > taban
  serisi > 🎈), 'Bugün ne var?' (`bugunUyari` ilk sırada), sözlük. Metin Python `tarama.kilit_metni` = JS `ktMetin` (810/810 eşleşme).
- **Gerçekçi iz stop çıkışı (`sinyal.gercekci_cikis`, backtest.py v3 varsayılanı):** iz stop kilitli taban gününde tetiklenirse o gün
  satılamaz; ilk kilitsiz günün açılışında çıkılır, veri biterken hâlâ kilitliyse son kapanışla değerlenir. Canlı liste (1.208 işlem):
  endekse göre +%18,4 → +%16,7 (en iyi 10 hariç +13,3 → +11,7), en kötü işlem −%27 → −%81 (TRHOL/IEYHO 18.09.2026). Katı varyant
  ('her taban günü satılamaz', `v3_taban`) +%13,6 / en kötü −%82; backtest.html'de duyarlılık tablosu (kapanış / kilitli / katı).
  backtest.py korn verisiyle s4_kart.txt'yi birebir tekrarladı. v2/eski kurallarda bu düzeltme yok (kıyas v3 aleyhine hafif eğik).
  `tk_gecmis` 5. eleman `1` = çıkış günü kilitli tabandı → Sinyal geçmişi / grafik üstü satır / Son roketler'de '🔒 tabanda alıcı
  yoktu, bu fiyattan satılamamış olabilir' (OZATD 18 Eyl 3.632,5).
- **Aşırı uzamış 🚀 girişi (`sinyal.asiri_uzama` → `tk.uzama`, BİLGİ notu, AL engellenmez):** sinyal günü fiyat 52h (250g) dibinin ≥5
  katı ya da 126 gün öncesinin ≥3 katı. s1_kuyruk (OR birleşimi, canlı liste, 'her taban satılamaz' çıkışıyla): bu grubun %13,3'ü
  %30+ kayıpla kapandı, diğerleri %1,3 (sadece kilitli taban satılamazsa %5,7 / %0,2; kapanış varsayımıyla ikisi de %0); en büyük
  %5 kazananın 6/60'ı bu grupta. Düşük faizde çok az olay. Portföyde filtre (hariç/yarım) hücreden hücreye işaret değiştiriyor →
  sadece not: modal tkHtml kutusu (pozisyon açıkken) + Telegram 🚀 AL satırı. Python `uzama_metni` = JS `uzamaMetin` (173/173).
- **Test edilip GEREKMİYOR çıkanlar (tekrar araştırma):** aşırı uzama FİLTRESİ (hariç/yarım pozisyon; sepet farkı −160…+24 puan,
  tutarsız); 🔻 hacim kuruması (taban + hacim <0,5x: düşük faizde endeksi yenme %51 — ayırmıyor; 1. gün hacim <0,25x kesinlik %18,5,
  taban oranı %7,3, olay az); 1. gün taban/1. gün kilitli uyarısı (kesinlik %22-30, yanlış alarm çok); KAP VBTS tedbiri (kesinlik
  %13 vs %9 taban oranı) ve pay bazında devre kesici bildirimi (%8,4 vs %9 — hiç ayırmıyor).
- Not (değiştirilmedi): canlı karne kaydı (`gecmis_guncelle`) sadece taban serisini dışlar; Telegram AL ise 🎈 şişme ve 🔒'yi de
  dışlar → karne, mesajı gitmeyen birkaç 🎈 girişini de sayabilir (v3 girişlerinin ~1/417'si 🎈'li günde).

## 📏 Sıkı çizgi · uyarlamalı çıkış araştırması (2026-10-09, scratchpad `cikis/`; kullanıcı onayıyla sadece BİLGİ notu)
- Soru: paralı bir indikatör OZATD'den (27.08 🚀, 16.09'dan taban serisi, iz stop çıkışı kilitli tabanda −%81) erken çıkardı mı? **Tek örnekten
  kural çıkarılmaz** — 587 hisse 2022-09…2026-10, sepet + 10 yuva, iki faiz dönemi, çökenler dahil/hariç, 200 rastgele yarım liste ile test edildi.
- Düz çıkış araçları (c13, ~60 araç: SuperTrend, PSAR, chandelier, kijun, EMA/SMA, Donchian, Heikin-Ashi, RSI uyumsuzluğu, sıkı iz %8-15, zaman...):
  **30'u OZATD'yi kurtarıyor ama bu 30'un hiçbiri genel testte v3'ü (iz %20) sepet hücrelerinin 3/4'ünde bile geçmiyor** (erken çıkış büyük
  kazananları kesiyor; genelde iyi olan keltner_alt OZATD'yi kurtarmıyor).
- Uyarlamalı (sadece aşırı uzamış pozisyonda sıkı araç, c5/c6): en sağlamı uzama/hic/kijun sepette çoğu hücrede biraz önde, ama canlı listenin
  10 yuvasında yüksek faiz/çökenler hariç geride (+%178 vs +%213), 2026 çökenler hariç −%11 vs −%8; en büyük kazananları kesiyor
  (RAYSG +%2.132 → +%122, KTLEV +%1.734 → +%324); kijun-altı ilk kapanıştan sonra (c12, 306 olay) 20 günde %5'inde 4+ taban, %11'inde %25+ düşüş ama %20'sinde %25+ yükseliş, 60 gün sonra %41'i satış fiyatının üstünde.
  → **Canlı kural YAPILMADI** (v3 AL/SAT, iz stop, backtest değişmedi); kullanıcı onayıyla bilgi notu.
- **`sinyal.siki_cizgi` → `tk.sc`** (sadece açık 🚀 pozisyonda, `trend_kirilimi` içinde; backtest/islemler/ham yolları etkilenmez): sinyal gününden
  bugüne herhangi bir gün `asiri_uzama` (52h dibinin ≥5 katı ya da 6 ayda ≥3 kat; araştırmanın en sağlam ailesi 'uzama/hic' = girişten beri)
  ise bugünkü **kijun** (26 günün en yüksek + en düşük ortası, bugün dahil) = `s`; `alt` = son 5 işlem gününde kijun altı kapanışlar, `ilk` =
  pozisyondaki ilk kijun-altı kapanış (araştırmanın çıkış günü), `u` = uzama sinyal gününden sonra başladıysa ilk günü, `bugun`; tarama `kesin`
  ekler (seans içinde bugünkü 'altında' kesin sayılmaz: 'şu an altında, kapanışta kesinleşir'). Grafik için `spark.sc` = [başlangıç sırası, değerler].
- **Neden kijun (chandelier 3 ATR değil):** 200 rastgele yarım listede uzama/hic/kijun v3'ü 100/86/95/82 (düşük dahil/hariç, yüksek dahil/hariç),
  chand3 100/94/87/62 — yüksek faiz çökenler hariç hücrede kijun daha sağlam; c12'de daha az yanlış alarm (306 vs 399 tetik; %25+ yükselişi
  kaçırma %20 vs %25). İkisinden yüksek olanı seçmek (karışık tanım) test edilmedi ve c12 oranlarını geçersiz kılar. OZATD'de ikisi de 10.09.
- Doğrulama: canlı `ilk` ↔ araştırma motoru (`cikis/ortak_c.cikis_bul`, uzama/hic/kijun) 2.031 v3 işleminde 0 fark (421'inde çizgi gösterilir,
  369'unda iz stop'tan önce altında kapanış). OZATD 10.09 kapanış 4.450 < kijun 4.542,5 → 'altında kapandı (10.09)'. KTLEV: iz stop'tan (02.09) önce
  altına inmedi (araştırmayla aynı). Bilinen küçük fark: araştırma 52h dibini ≥120 günle de alıyordu, canlı `asiri_uzama` 250 gün ister.
- Pano: 🚀 kutusunda aşırı uzama notunun yanında (`scMetin`), grafikte ince pembe kesikli çizgi (#D6336C; iz stop mor), fare bilgisinde 'Sıkı çizgi',
  sözlük + 'Grafik nasıl okunur?'. Portföyde: 'Bugün ne var?' (`bugunUyari`, son 5 günde altında kapanış) ve akşam portföy özeti notu (özet zaten günde
  bir kez, kesin kapanıştan sonra; durum.json'a anahtar YOK). AL mesajına eklenmedi. Metin Python `tarama.siki_metni`/`siki_alt`/`_sayi_tr` =
  JS `scMetin`/`scAlt`/`sayiTr` (3.094/3.094). Sayılar c12'den (`SIKI_NOT`); değişirse ikisini birlikte güncelle.

## 📅 Vadeler · ⏱️ gün içi görünüm · 🚀 gün içi kırılım notu (2026-10, hepsi BİLGİ — scratchpad vade_uzun, vade_gunici, vade_impl)
- **Vadeler (`sinyal.vade_durum` → `vd` = [günlük, haftalık, aylık], +1/0/−1/None):** Günlük ↑ = kapanış > SMA50 ve SMA50 10 gün
  öncesinden yüksek, ↓ = altında ve yükselmiyor; Haftalık (Weinstein) = son TAMAMLANMIŞ haftanın (W-FRI) kapanışı > 30 haftalık ort.
  ve ort. 4 hafta öncesinden yüksek; Aylık = son tamamlanmış ay > 10 aylık ort. ve ort. bir önceki aydan yüksek; aksi →. Mumlar 2 yıllık
  günlükten türetilir; hafta/ay 'tamam' = son gün kesin (18:30+ ya da geçmiş gün) ve sonraki iş günü ya da bugün yeni dönemde
  (`analiz_et(bar_kesin, bugun)`). 11 aydan kısa geçmişte aylık —. Doğrulama (vade_impl/t_vade.py, 258 hisse × son 120 gün = 30.960
  hisse-gün): 2y pencere = 5y veri 0 fark; araştırma `durum.py` ile günlük/aylık 0, haftalık 33 fark (hepsi 30.04.2026: 1 Mayıs tatili,
  araştırma perşembe kapanışında haftayı tamam sayıyor, canlı ertesi günü bekliyor). Pano: tablo 'Vade' sütunu (G↑ H↑ A↓, istemcide
  `DATA.vd`'den çizilir, sıralanabilir), modal `vadeHtml` satırı, sözlük. Üçü ↓: 2016-2026'da sonraki 60/120 günde endeksi yenme
  ~%35-45 (tüm hisselerde ~%41-56; düşük faiz/çökenler hariç n=53 hücrede %49-53) → 'fark küçük, kesin değil'. Üçü ↑: 'tek başına
  alım sinyali değil'.
- **⏱️ Gün içi görünüm (`gunici.py` → panoda `const GI={g,t,tam,v:{kod:[15dk trend,RSI,kırılım, 1s…, 4s…]}}`):** trend ↑ = EMA20 >
  EMA50 ve fiyat > EMA50 (↓ tersi), RSI(14), son 3 mumda önceki 20 mumun zirve/dip kırılımı. 15 dk verisi `veri_cek`'in tek toplu
  indirmesinden (`start=` son 59 gün, threads=True; kapanış düzeltmesi de bundan); 1 s 10:00 hizalı, 4 s 10:00-14:00 / 14:00-18:00;
  bitişi 'şimdi − 15 dk'dan sonra olan yarım mum atılır; `bolunme_duzelt` uygulanır; <60 mum → o vade boş. 59 gün yeterliliği: 45
  güne kısaltınca 4 s trendi 325 hissenin 7'sinde değişiyor (EMA50 tam oturmuyor, Yahoo 15 dk en fazla 60 gün veriyor). Seans
  dışında (18:30+, hafta sonu, 10:00 öncesi) önceki index.html'deki `GI` son seansın tamamlanmış hâliyse (`tam`) yeniden kullanılır
  ve sadece 7 günlük 15 dk iner. İndirme/hesap hatasında `GI=null`, tarama bozulmaz (test: 15 dk yok → saatlik yedek; hepsi yok;
  hesap hatası). Süre: 15 dk 59 gün ≈ 15 sn (eski saatlik 7 gün ≈ 12-15 sn, yerine geçti) + hesap ~10 sn → Actions'a ~+10 sn.
  Araştırma (323 hisse 2023-11→2026-10): BIST100+EK'te 1 s trend/RSI/oylama sonraki 1-5 günde maliyetten küçük fark (±3-12 baz
  puan); RSI<30 sonraki 5 günde ort. hisseden −36 bp (tümü −100 bp) → modal notu.
- **🚀 gün içi kırılım:** kesin kapanış öncesi `tk.bugun` ise `tk.gk` = verinin saatine (şimdi − 15 dk) göre o saatte görünen
  kırılımların kapanışta tutma oranı (`tarama.GK_ORAN`: 10:30 %67, 11:30 %71, 12:30 %74, 13:30 %77, 14:30 %76, 15:30 %79, 16:30 %85,
  17:30 %88; v3_yanlis.py, 611 aday gün). Kutuda + Telegram 🚀 başlığında `GK_NOT` (kapanış seansında almak ertesi açılışa göre
  ort. +0,8 puan; ertesi gün VWAP geri çekilmesi −1,0, limit −%1/−%2 −6,8/−10,2 puan — en güçlüler dolmadan kaçıyor). Backtest'in
  ertesi açılış varsayımı DEĞİŞMEDİ. 17:30-18:30 mesajındaki eski '25/25 tuttu' cümlesi `gk_metni` ile değişti. Python `gk_metni` /
  `GK_NOT` = JS `gkMetin` / `GK_NOT` (9/9).
- **🚀 'seviyenin üstünde ama AL yok' (ENERY 2026-10-08):** kutu 'Kapanış 14 TL üstüne çıkarsa AL (%-1.1 yukarıda)' diyordu; fiyat
  zaten üstteydi ama (a) kırılım ilk gün değildi (dünkü kapanış da 20g zirvesinin üstünde, kural sadece ilk günü sayar) ve (b) BIST 100
  < SMA50 (piyasa filtresi). `trend_kirilimi` artık şablonda/pozisyonsuzken `eksik` = ['ilk','oynak','piyasa','cikis'] verir; kutu ve
  sade anlat eksik koşulu yazar. Aynı durumda HRKET (−%1,5) vardı.
- **Test edilip GEREKMİYOR çıkanlar (tekrar araştırma):** 1/5/15 dk sistemleri (oylama, SuperTrend, EMA kesişimi, kırılım; maliyet
  sonrası işlem başı −0,6…+0,4 puan, aynı tutuşlu rastgele girişe göre fark küçük; 1 dk'da hepsi eksi); 1 s / 4 s trend sistemleri (aynı tutuşlu rastgele girişten fark tutarsız, 4 s kırılım
  tümünde −2,7 puan); açılış aralığı kırılımı (ORB 30/60 dk), VWAP kesişimi, RSI<30 dip dönüşü (rastgeleden ayrılmıyor ya da kötü);
  haftalık/aylık v3 değişikliği (haftalık+aylık ↑ filtresi, cuma kapanışında iz stop, haftalık SAT'ta çık, haftalık v3: 200 yarım
  listede v3'ü yenme %16-90, düşük faizde fark yok → tutarsız); 'zayıf kapanış' etiketi (kapanış gün aralığının alt yarısı / tipik
  fiyat altı: yüksek faizde kötü, düşük faizde iyi; 10 yuvada atlamak 4 yılda +%478 → +%424).

## Canlı kurallar (5 yıllık backtest'e dayanarak, 2026-09)
- Piyasa filtresi: XU100 < SMA50 → "piyasa zayıf" bandı + Telegram notu (AL'ler engellenmez).
- Hacim: AL'e dönüş günü hacmi ≥ 1.5× önceki 20 gün → "📈 hacim" etiketi. Aynı işlemler etiketlenince (çökenler hariç) hacimli/hacimsiz farkı YOK; önceki "filtre" testindeki fark seçim yan etkisiydi → bilgi amaçlı tut, filtreye çevirme.
- Piyasa filtresi etiket testinde de sağlam (her iki faiz dönemi, çökenler dahil/hariç).
- Dirence <%3 yakınken gelen AL'ler backtest'te en iyi grup (kırılım) → "Dirence yaklaşıyor" yeni AL için "uzak dur" değil.
- AL eşiği (4/5) ve stop (%8+20g dip) zaten en dengeli; %10-15 stop farkı gürültü düzeyinde.
- Kısmi kâr alma (dirençte ya da 2R'de yarısını sat) backtest'te belirgin şekilde KÖTÜ (düşük faiz +9.3 → −1.3; yüksek +2.5 → +0.2-0.4 endekse göre). Hedefleri "satış emri" diye sunma; izleme noktası.
- Zamanlama: AL/SAT geçişleri 17:30'dan (`SINYAL_DAKIKA`) sonra değerlendirilir; gün içi daha erken taramada
  `durum.json` → `son` DEĞİŞMEZ. Saatlik veriyle: 17:00 civarı yeni AL'lerin ~%88'i kapanışta tutuyor (erken saatte
  ~%75); 17:00 fiyatıyla ertesi açılış arasında belirgin fark yok. 17:30–18:30 arası verilen sinyaller `on_sinyal`'de
  tutulur; 18:30 (`KAPANIS_DAKIKA`, kesin kapanış) sonrası tutmayanlar için "iptal" mesajı ve `son` geri alınır.
  Günlük/haftalık özet ve uzun vade kırılım kontrolü 18:30 sonrası.
- Uzun vade (`uzun: true` portföy kaydı): stop yerine karar çizgisi = fiyatın altındaki en yakın destek × (1−tol).
  Karar çizgisi hep fiyatın altından hesaplandığı için kırılım, bir önceki kapanışta kaydedilen çizgiyle
  (`karar_cizgisi`) kıyaslanır; aynı seviye için bir kez (`karar_kirilim`). Backtest: güçlü yükselişte büyük
  hisselerde al-tut, sinyale göre girip çıkmaktan belirgin iyi (19 hisseden 15'i).
- SAT + destekten tepki: SAT sürerken destek tepkilerinin ~%68'i 20 günde kırıldı → çelişki notu + karar çizgisi.
- **v2 (gece testleri 2026-09-26, `oneri/v2-iz-stop`):** sınırsız sepet simülasyonunda asıl sorun ÇIKIŞ: stop+SAT2
  yükseliş piyasasında kazancı eritiyor (düşük faiz +%9; 2023 −%6). %20 iz stop (AL'den beri tepe kapanışın %20 altı,
  SAT'ı yok say) + giriş filtresi (trend: fiyat>SMA200 ve SMA200 20 günde yükselmiş; 60g oynaklık ≤%5): düşük faiz
  +%67/+%70/+%52 (tüm/çökenler hariç/büyük), yüksek faiz +%224/+%215/+%174; hiçbir yıl eksi değil; %18/%22 komşu
  tutarlı; ort. tutuş ~4 ay. İşlem başı (backtest.py v2): düşük faiz isabet %71, endekse göre +%19.4 (top10 hariç +%8.5).
  İz stop manipülatif hisse etkisini de nötrlüyor (tüm ≈ çökenler hariç). Önceki per-trade testte iz stop kötü
  görünmüştü: ölçüt farkı (per-trade vs portföy) — kararları sepet simülasyonuyla ver.
- Kısa vade gerçeği: BIST'te <1 ay tutuşlu çıkışlar (SMA20 altı, SuperTrend dönüşü) her evrende en kötü.
- 🌱 Uzun vade sinyali (`sinyal.uzun_vade`): yükselen trendde (fiyat>SMA200, SMA200 20 günde yükselmiş) SMA50'ye
  %2 yakın geri çekilip yükselişle kapanış → AL; 2 gün SMA200 altı → SAT. Backtest (çökenler hariç): düşük faiz
  endekse göre +%10.7/isabet %65, yüksek faiz +%3.4 — günlük sinyalden iyi ama en iyi 10 işlem hariç hafif eksi.
  Alternatifler (altın kesişim: kırılgan; haftalık MACD: +8.5/+2.2) daha zayıf. SMA200 için tarama 2 yıl veri çeker.
  Telegram: kapanış sonrası (18:30+) `uv_son` ile geçişler; AL herkese, SAT portföye.
- 🚩 Bayrak kırılımı (`sinyal.bayrak_kirilimi`): isabet %46 (günlük %34) ama endekse göre fark günlükten düşük
  ve kırılımların %70-85'i zaten AL ile aynı gün → sadece bilgi etiketi, ayrı sinyal değil.
- **AL önceliği:** portföy simülasyonunda aynı gün birden çok AL varken son 20 (10/40) günde AZ yükselmiş olanı
  önce seçmek, çökenler hariç her iki faiz döneminde en iyi (yüksek faiz +%208 → +%290). Telegram AL listesi
  buna göre sıralı (`mom20`). Çökenler dahil edilince uç sonuç (+%1128) — güvenilmez, o yüzden sadece sıralama.
- **Portföy düzeyi gerçekçilik (2026-09):** 10 eşit parçalı portföy simülasyonunda canlı kurallar 4 yılda
  (Eyl 2022–Eyl 2026) XU100 al-tut'u YENEMEDİ: endeks +%295 (maks düşüş −%23); sistem nakit faizli +%277
  (−%28), faizsiz +%179 (−%33). Sadece yüksek faiz döneminde, nakit faizli ve çökenler hariç endeksin
  önünde (+%208 vs +%160). İşlem başı "endekse göre fark" pozitif olsa da nakitte bekleme + yoğunlaşma
  portföyü geri bırakıyor. Kullanıcıya "endeksi yener" deme; sistemin değeri risk uyarılarında. Yeni
  kural önerirken portföy simülasyonuyla da ölç (scratchpad bt/portfoy_sim.py mantığı).
- Sektör: Yahoo sector/industry günlük oran önbelleğinde (5 elemanlı liste); `ENDUSTRI_TR` Türkçe karşılıklar.
- Bilanço (`bilanco.py`, bilgi amaçlı): yfinance çeyreklik net kâr/satış (son ~6 çeyrek), geçen yılın aynı çeyreğine
  göre değişim, sonraki bilanço tarihi (Yahoo takvimi varsa, yoksa SPK konsolide son teslim: 3/9 ay 40, 6 ay 60, yıllık 70 gün).
  `bilanco.json` önbelleği 3 günde bir, seans dışında (18:30+) yenilenir. Veri geçmişi kısa → backtest edilemedi, sinyale
  GİRMEZ. Portföy özetinde 7 gün içindeki bilanço uyarısı; panoda 📅 rozet + modal çeyreklik grafik. THY gibi USD raporlayanlar var.
- Endeksle kıyas: portföy kaydında isteğe bağlı `tarih` (alış) ve `xu_birim` = adet×maliyet / o günkü BIST 100 (pano
  hesaplar; aynı hisseye eklemede birimler toplanır, tarihsiz alım kıyası o hisse için kapatır). Kıyas = Σ adet×fiyat vs
  Σ xu_birim×XU_son. `tarama.endeks_serisi` (son 2 yıl günlük + 10 yıla kadar haftalık) panoya `XU` olarak gömülür;
  `endeks_kiyas` (Python) ve `pfKiyas` (JS) aynı mantık. Portföy özetinde de satır. Temettü iki tarafta da yok.
- Temettü (`bilanco.temettu_ozet`, aynı önbellek): son 12 ay nakit temettü/hisse + verim (>%25 'şüpheli': yfinance
  bedelsizi bilmez), Yahoo'da varsa ileri hak kullanım günü (az hissede var, tahmini olabilir). 7 gün içindeyse 💰 rozet +
  portföy özeti notu (o sabah fiyat temettü kadar düşük açılır). Bilgi amaçlı.
- KAP (`kap.py`): kap.org.tr'nin kendi sitesinin kullandığı POST `api/disclosure/members/byCriteria` (ODA + FR,
  son 7 gün, tek istekte tüm şirketler; en çok 2000 kayıt). Gürültü konular ayıklanır; `kap.json` 45 gün hisse başı.
  Modalda son 5 bildirim. Telegram: portföy hisselerinin yeni bildirimleri (geri alım hariç), `durum.json` → `kap_son`
  (genel bildirim sayacı, portföy bilgisi içermez); ilk çalışmada sessiz başlangıç. KAP'a ulaşılamazsa önbellekle devam.
- 📋 'Bugün ne var?' kartı (`bugunRender`, istemci): PIYASA (piyasa_durumu JSON), 🚀 AL son 5 gün, portföy uyarıları
  (`bugunUyari`: 🔒/taban serisi ilk sırada; iz stop kırıldı/%3'ten yakın sadece portföyde; 🎈/⚠️/🪤/bilanço/temettü ≤7 gün/bölünme ≤30 gün),
  favoriler (🚀, 👀 ≤%3, uyarılar). Üst sayılar artık v3: bugün 🚀 AL / son 5 günde 🚀 AL.
- Karne (gecmis.html): kartlar sadece `kural: v3` kayıtları; eski kayıtlar 'eski kural' etiketi + ayrı özet satırı (`ozet['eski']`).
- ⭐ Favoriler: istemci tarafı (`favoriler_v1` localStorage + `FAVORILER` variable, portföyle aynı anahtar). `tabloDuzen()`
  favorileri üste alır (sunucu sırası AL→NÖTR→SAT korunur), sütun sıralamasında da üstte tutar; arama kutusu + 'sadece
  favoriler'. Satırlarda `data-kod`; ilk sütun ⭐. AL+ işareti ★ yerine 'AL+' yazısı (favori yıldızıyla karışmasın).
- 📍 Portföy gün içi (`tarama.gunici_olaylar`, 10:15-18:10 hafta içi): destek/direnç DÜNKÜ kapanışa kadarki veriyle
  (`sd_dun`; bugün yeniden hesaplanan destek kırılınca alttaki dibe kayar),
  destek dün üstünde kapanılıp bugün karar çizgisi üstünde (hafif altında) kapanınca ertesi gün de korunur (`destek_direnc`,
  2026-09-29; eskiden %97'sinde kayboluyordu, 'yarın izle' izlenmiyordu; gün içi 'desteği kırdı' mesajı hisse-günlerin %4,9 → %8,1'i), olaylar d_yakin/d_sarkti/d_kirildi (karar
  çizgisi = S·(1−tol)), r_kirdi/r_dondu, iz_yakin (%2)/iz_alti, taban/tavan (±%9,5)/sert (−%5). Olay+seviye günde bir kez
  (`durum.gunici`, gizli anahtar); ağır olay hafifleri bastırır. Veri teyidi: olay `_son_fiyat` (fast_info) ile de tutmalı,
  iki fiyat >%1 farklıysa atlanır (THYAO 24.09 Yahoo günlük 288,5 / resmi 289,5, destek 289,25 → yanlış 'kırıldı' görünmüştü).
  Son bar bugünün değilse (hisse henüz işlem görmedi) olay yok. Kesin kapanışta `kapanis_sd` sonucu günlük portföy özetinin
  başında (ayrı mesaj değil; uzun vadede kırılım karar çizgisi mesajına bırakılır). `GUNICI_OLAYLAR`: d_sarkti/d_yakin
  kapalı (gürültü); r_dondu gün içi tepe dirence DEĞMELİ (bölge kenarı değil). bt/mesajsay*.py: 5 hisselik portföyde
  mesaj gelen gün %82 → %41. ☀️ Sabah (`seviye_satiri`, günün ilk taraması <12:00, `sabah_tarih`).
  Olay çalışması (bt/sd1-2.py, 125 hisse 2022-26): sarkmaların %41'i kapanışta geri alındı, %40 tolerans içi, %19 kırıldı;
  kırılım/dönüş/aşım sonrası 20g getiri, aynı trenddeki rastgele günden ±1-2 puan ve dönemden döneme yön değiştiriyor
  (düşük faizde kırılanlar daha İYİ gitti) → mesajlar bilgi, sinyal değil (`SD_NOT`).
  Ek gün içi olaylar: 🎈/⚠️ `tahta_riski` bugün yeni oluştuysa (dünkü veriyle aynıysa sadece günlük özette), BIST 100
  ±%2,5 (`PIYASA_SERT`) günde portföyün günlük K/Z satırı. iz_alti metni: v3 pozisyonlarında gün içi iz stop altına ilk
  sarkmaların %44'ü kapanışta geri alındı; kapanışa bakmak gün içi stop'ta satmaktan ort. +%3 (bt/izgunici.py).
- Portföy özeti: 🛡️ risk satırı (her pozisyon iz stop / karar çizgisine inerse kayıp, % portföy değeri); 📉 `trend_asagi`
  (fiyat < SMA200 ve SMA200 20 günde düşmüş) notu. bt/trend1.py (125 hisse + tüm borsa, 5 günde bir örnek): düşük faizde
  ASAGI'daki hisselerin 60g'de endeksi yenme oranı %24-38 (YUKARI %41-50), medyan −%9…−12; yüksek faizde fark küçük/karışık
  (tüm borsada ters). Pano portföy tablosunda Destek sütunu (`d.sd.destek`, bugünkü veriyle en yakın destek).
- Fiyat alarmı: panoda hisse penceresinden kurulur, `ALARMLAR` variable'ına (portföyle aynı anahtar) yazılır;
  her taramada (gün içi de) kontrol, her alarm bir kez çalar. durum.json herkese açık olduğundan sadece
  alarmın sha1 özeti (`alarm_tetik`) saklanır; silinen alarmın kaydı temizlenir. **Önerilen alarmlar** (`alOneriler`, JS):
  en yakın destek (fiyat desteğin hafif altındaysa karar çizgisi), direnç, 🚀 kırılım seviyesi (şablonda), portföydeyse iz stop /
  karar çizgisi (aşılmış seviye önerilmez); tek tek ya da 'Hepsini kur', aynı kod+yön+fiyata ikinci alarm kurulmaz (elle de).
  Kayıtta isteğe bağlı `not` ('destek', 'iz stop'...; ≤40 karakter, Telegram'da escape'li gösterilir). Anahtar hâlâ
  kod|yön|fiyat → eski alarmlar aynen çalışır.
- Taban serisi: son 15 günde ≥4 kez ≤ −%9 → "⚠ taban serisi"; bu hisselerden AL mesajı gitmez. Erken aşaması 🔒 kilitli taban (yukarıda).
- SAT: 1. gün "⏳" işaretiyle gösterilir/bildirilir, 2. gün "✅ teyit" mesajı (portföy).
- Portföy: çıkış = son AL başındaki sabit stop (`al_stop`), SAT'ta çıkış sebebi sinyal; hedefler
  küçükten büyüğe (en yakın direnç, 2R). Günlük portföy özeti 18:00 sonrası ilk taramada.
- Python (`tarama.pozisyon_plani`) ve JS (`pano.pozPlan`) aynı mantık — birini değiştirirsen ikisini de.
- Şablon (pano.py `_SABLON`) raw string içinde JS: tek tırnaklı JS dizelerinde kesme işareti `\'` olmalı;
  değişiklikten sonra şablon JS'ini `node --check` ile doğrula (bir kez sayfayı tamamen bozuyordu).

## 💬 Sade anlat · 🔎 Neden yükseldi/düştü? (2026-10, hisse penceresi, hepsi istemci JS — yapay zekâ yok)
- `sadeHtml`: (a) genel yön — `trend`/`trend_asagi` + SMA50 (📉 trend aşağı uyarısıyla aynı kural), ikisi de değilse 60g
  getiri ±%10; (b) kısa vade alıcı/satıcı — 💪 güç ≥5 (sinyal SAT değilse) / ≤2 (AL değilse), yoksa 'dengede' (oylama ile
  çelişmesin) + 5g hacim ≥1,5x notu; (c) tek seviye — portföydeyse iz stop / karar çizgisi (JS, localStorage), değilse 👀 kırılım
  seviyesi (≤%3) ya da en yakın destek/direnç (±%15'ten uzaksa 'yakında seviye yok'); (d) en önemli tek uyarı (🔒 > taban serisi >
  🎈 > ⚠️ > 🪤 > 🔻 > bilanço/temettü ≤7g > bölünme > ⚡). Sunucu tarafına portföy cümlesi YAZILMAZ.
- Metin düzeltmeleri (2026-10-08 vaka testi): (a) taban serisinde ya da 60 günde ≤ −%50'de genel yön '💥 çöküş' (DMRGD 7 tabanla
  'yükseliş' diyordu); (b) 🎈 tetiklendi ama 20g getiri eksiyse (çöküş sonrası tepki tavanları: HEDEF, PASEU, KLRHO, CRDFA, LYDHO)
  rozet/kutu/Telegram metni '🎈 sert dalgalanma / sert tavan-taban dalgalanması' (`thDalga` = `tarama._sisme_ad`; `tahta_riski` tetiği
  aynı); (c) 🌱 SAT kalmışken fiyat SMA200 üstüne döndüyse 'hâlâ SAT …, fiyat o zamandan beri üstüne döndü' (eskiden hem 'trend
  bozuk' hem 'trend yükselişte'); (d) neden kutusundaki iz stop satırı: portföy dışında sadece 🚀 v3 çıkışı (`tk.cikis_tarih`,
  Sinyal geçmişiyle aynı), portföyde portföyün kullandığı `d.iz` (eskiden gösterge iz stop'u: 313 hissenin 175'inde çelişki).
- `nedenHtml`/`hareket`: 1/5/20 gün hisse getirisi (grafik verisi `spark`), aynı tarihlerde BIST 100 (`XU`), kıyas grubundaki
  diğer hisselerin ortalaması, hacim oranı (`sinyal.hacim_oranlari` → `hv`: 1g/önceki 20g, 5g/önceki
  60g, 20g/önceki 60g), pencere içi tavan/taban, KAP (son 5 bildirimden pencere içindekiler, geri alım ayrı sayılır), bölünme,
  6 ay/20 gün zirve-dip, destek tepkisi/direnç, iz stop kırılımı. 'Aynı dönemde' der, sebep iddia etmez.
- Eşikler (scratchpad bt/hareket/dagilim.py, 299 hisse, Eki 2021–Eki 2026): endeksten ayrışma ≥ 4 / 10 / 20 puan (1/5/20 gün)
  → günlerin %12,9 / %11,6 / %12,8'i; hacim ≥1,5x → %12,5-12,7 (≥2,5x 'çok yüksek', <%5). Ayrışanların sadece %7-8'inde
  sektör de aynı yönde gitmiş ('sektörel': sektörden fark < T/2 ve sektör endeksten ≥ T/2 aynı yönde); gerisi 'hisseye özel'.
- Olay çalışması (bt/hareket/olay.py; aynı hissede 20 günde bir olay; sonraki 20g endekse göre, aynı hisselerin tüm günleri
  ort +%1,4 / medyan −%1,2 / endeksi yenme %46): hisseye özel + hacimli YÜKSELİŞ (5g) ort +%2,3 / medyan −%2,4 / %44 (2.421
  olay; 1g ve 20g benzer, hacimsizler biraz daha iyi) → belirgin değil, kutuda sadece 'farklı gitmedi' notu. Hisseye özel +
  hacimli DÜŞÜŞ ise her yıl endeksin gerisinde: 5g ort −%3,8 / medyan −%5,2 / yenme %36 (839 olay), 20g −%7,4 / %33 (284) —
  bugünkü hisselerle (hayatta kalan yanlılığı tersine çalışır).
- 🔻 **Hisseye özel hacimli düşüş** (`tarama.ozel_dusus`, kullanıcı onayıyla BİLGİ uyarısı — AL/SAT kuralı değil): 5 ya da 20 günde
  getiri ve endeksten fark ≤ −10 / −20 puan, tür 'hisseye özel' (benzer hisseler açıklamıyor), hacim ≥1,5x. Canlı tanımla
  sağlamlık (bt/hareket/olay2.py, 299 hisse, aynı hissede 20 günde bir olay, sonraki 20g endekse göre; parantezde tüm günler):
  tümü 1.052 olay medyan −%4,8 / endeksi yenme %38 (−%1,1 / %46); 2021-10/2022-09 %33 (%45), **düşük faiz 2022-09/2023-06 %46
  (%47) → fark YOK**, yüksek faiz 2023-07 sonrası %38 (%46); çökenler hariç (örneklemde taban serisi yaşamış 144 hisse çıkarılınca)
  345 olay %39 (%45), düşük faizde yine fark yok. Metinler buna göre yumuşak: "~%38'i endeksi geçti (normalde ~%46); 2022-23 düşük
  faizde fark yoktu; kesin değil". Canlı fonksiyon geçmiş olaylarla birebir: 25 rastgele gün × tüm hisse 6.152 hisse-gün, 5 fark
  (4'ü 15 Temmuz tatil günü karşılaştırma artefaktı, 1 yuvarlama). Pano: tablo rozeti '🔻 özel düşüş', sözlük, sade anlat uyarı
  önceliği (🪤'dan sonra), `bugunUyari` (sadece portföyde), neden kutusu notu; Telegram akşam portföy özetinde hisse notu.
- Python aynası: `tarama.hareket_hepsi` = JS `hareket` (aynı girdi: spark + XU + hv + kg, aynı eşikler `HR_ESIK`/`HR_HACIM`).
  Kontrol: 313 hissede 939 ufuk, 0 fark. Akşam portföy özetinde '🔎 Bugün hisseye özel hareket' satırı (`hareket_satiri`: 1 günde
  tür 'hisseye özel' ve dikkat çekici olanlar; yoksa satır yok).
- Sektör kıyas grubu (`tarama.kiyas_gruplari` → panoda `kg`): Yahoo endüstrileri çoğu hissede 2-3 hisse, ana sektör ise çok
  geniş ('Sanayi' 77: holding+havayolu+savunma). `KIYAS_GRUP` benzer küçük endüstrileri birleştirir (Elektrik/doğalgaz,
  Ulaştırma, Makine/metal, Gıda/içecek, Yazılım/BT, GYO, Sağlık...); grupta (kendisi dahil) <4 hisse varsa kıyas yok
  ("karşılaştırılacak yeterli benzer hisse yok", 313 hisseden 10'u). Ana sektöre düşülmez.
- Eskiyen önerilen alarm (`alEski`/`alGuncelle`, JS): notlu (önerilenden kurulmuş) alarmın aynı aile+yöndeki güncel önerisi
  farklı seviyedeyse ya da yoksa '⚠ bu seviye artık güncel değil' + 'Güncelle' (güncel seviye zaten kuruluysa eskisi silinir).
  Notsuz (elle) alarmlara dokunulmaz. Seviye değişince alarm anahtarı da değişir → yeni seviye için yeniden kurulmuş sayılır.
