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

## Dosyalar
- `sinyal.py` — gösterge + sinyal çekirdeği. **Tek kural seti** (canlı tarama + backtest ortak).
  SuperTrend, MACD, EMA20/50, RSI, Stochastic oy verir; ADX/Bollinger bağlam. `analiz_et(df)`
  son gün özetini döndürür (sinyal, uyum, detay, sinyal_gun, giris_stop, hedef, spark...).
- `tarama.py` — evren (BIST100 + EK_HISSELER + izleme listesi), oran önbelleği (F/K, PD/DD, FD-FAVÖK günde 1),
  yorum üretimi, sinyal geçmişi (gecmis.json), Telegram. Ayarlar dosyanın başında.
- `pano.py` — `index.html` ve `gecmis.html` üretir. Portföy istemci tarafında (localStorage),
  modalda kendi SVG grafiğimiz + TradingView butonu.
- `backtest.py` — ertesi-gün girişli, komisyonlu, al-tut kıyaslı simülasyon.

## Önemli ilkeler
- Sinyal kuralları tek yerde (`sinyal.py`); backtest ve canlı aynı motoru kullanmalı.
- Backtest'te look-ahead yasak; işleme ertesi gün girilir; çift yön %0.2 maliyet düşülür.
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
2. **Hacim/likidite filtresi:** düşük hacimli/az işlem gören hisseleri ele veya işaretle
   (yanıltıcı sinyalleri azaltır).
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
güncellenmeli; yfinance BIST bedelsiz/bölünme kaydı tutmuyor, arzdan beri getiri bölünmede yanılır.
Fon krizinde çöken şişirilmiş hisseler (TERA, SMRTG, GENIL, MIATK) listeden çıkarıldı; kullanıcı
isteğiyle faiz yüzünden düşen eski büyükler (KONTR vb.) KALDI — tüm çökenleri çıkarma.

## Tahtacı (şişir-çak) uyarısı — `sinyal.tahta_riski`
Olay çalışması (2022-26, tüm hisseler, bölünme düzeltmeli): 20 günde ≥%25 çakılma taban oranı %2,3. 🔥 şişme
(10g ≥5 tavan %19 / 20g ≥%100 %15 / 50g ort +%70 ve 20g std ≥%6 %16 / ≥3 tavan + hacim 5g/60g ≥3x %19) ve ⚠️ dağıtım
(hacim 5g/60g >2x iken 10g zirvenin %8+ altı, %9,5). Küçük tahta (düşük TL hacim) tek başına risk artırmıyor.
v3 girişlerinin sadece 1/417'si uyarılı günde (şablon + oynaklık filtresi zaten eliyor) → 🔥'de AL mesajı gitmez.
'Dipten kaldırma' tahmin edilemedi: tepeden %50+ çöken 75 olayda 60 gün sonrası −%65…+%189, hacim artışı ayırmıyor.
Pano rozeti + modal kutusu, portföy özetinde not. (scratchpad bt/tahta1.py)

## Veri kalitesi: kaydedilmemiş bedelsiz/bölünme
yfinance BIST bölünmelerini çoğu zaman kaydetmiyor (5 yılda 125 hissede 12 olay: KONTR, FENER×3, CCOLA, HEKTS, TUKAS,
BSOKE, EUREN, CVKMD...). BIST günlük sınırı ±%10 olduğundan tek gün ≤−%25 / ≥+%35 kapanış değişimi bölünme sayılır:
`sinyal.bolunme_duzelt` önceki fiyatları düzeltir (analiz_et, backtest, karar çizgisi). Aksi halde göstergeler, iz stop
ve 'çöken hisse' sınıflaması bozulur, bedelsiz günü yanlış 'iz stop kırıldı' gelir. Düzeltilmiş veriyle v3/v2 kıyası
değişmedi. Son 30 günde bölünme olan portföy hissesinde 'maliyetini güncelle' notu (kullanıcının maliyeti eski fiyatla).

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
- Pano: 🚀 KIRILIM (bugün) / 🚀 Ng (pozisyon) / 👀 kırılıma %x (şablonda, ≤%3) rozetleri; modalda tkHtml kutusu.

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
- Fiyat alarmı: panoda hisse penceresinden kurulur, `ALARMLAR` variable'ına (portföyle aynı anahtar) yazılır;
  her taramada (gün içi de) kontrol, her alarm bir kez çalar. durum.json herkese açık olduğundan sadece
  alarmın sha1 özeti (`alarm_tetik`) saklanır; silinen alarmın kaydı temizlenir.
- Taban serisi: son 15 günde ≥4 kez ≤ −%9 → "⚠ taban serisi"; bu hisselerden AL mesajı gitmez.
- SAT: 1. gün "⏳" işaretiyle gösterilir/bildirilir, 2. gün "✅ teyit" mesajı (portföy).
- Portföy: çıkış = son AL başındaki sabit stop (`al_stop`), SAT'ta çıkış sebebi sinyal; hedefler
  küçükten büyüğe (en yakın direnç, 2R). Günlük portföy özeti 18:00 sonrası ilk taramada.
- Python (`tarama.pozisyon_plani`) ve JS (`pano.pozPlan`) aynı mantık — birini değiştirirsen ikisini de.
- Şablon (pano.py `_SABLON`) raw string içinde JS: tek tırnaklı JS dizelerinde kesme işareti `\'` olmalı;
  değişiklikten sonra şablon JS'ini `node --check` ile doğrula (bir kez sayfayı tamamen bozuyordu).
