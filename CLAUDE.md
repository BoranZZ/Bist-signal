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

## Canlı kurallar (5 yıllık backtest'e dayanarak, 2026-09)
- Piyasa filtresi: XU100 < SMA50 → "piyasa zayıf" bandı + Telegram notu (AL'ler engellenmez).
- Hacim: AL'e dönüş günü hacmi ≥ 1.5× önceki 20 gün → "📈 hacim" etiketi. Aynı işlemler etiketlenince (çökenler hariç) hacimli/hacimsiz farkı YOK; önceki "filtre" testindeki fark seçim yan etkisiydi → bilgi amaçlı tut, filtreye çevirme.
- Piyasa filtresi etiket testinde de sağlam (her iki faiz dönemi, çökenler dahil/hariç).
- Dirence <%3 yakınken gelen AL'ler backtest'te en iyi grup (kırılım) → "Dirence yaklaşıyor" yeni AL için "uzak dur" değil.
- AL eşiği (4/5) ve stop (%8+20g dip) zaten en dengeli; %10-15 stop farkı gürültü düzeyinde.
- Kısmi kâr alma (dirençte ya da 2R'de yarısını sat) backtest'te belirgin şekilde KÖTÜ (düşük faiz +9.3 → −1.3; yüksek +2.5 → +0.2-0.4 endekse göre). Hedefleri "satış emri" diye sunma; izleme noktası.
- Gün içi yeni AL/SAT'ların ~%22'si kapanışta geçersiz (saatlik veriyle ölçüldü): AL/SAT mesajları, SAT teyidi,
  günlük/haftalık özet ve uzun vade kırılım kontrolü sadece `KAPANIS_DAKIKA` (18:30, Yahoo ~15 dk gecikmeli) sonrası.
  Gün içi taramada `durum.json` → `son` DEĞİŞMEZ (yoksa kapanışta geçiş kaçar).
- Uzun vade (`uzun: true` portföy kaydı): stop yerine karar çizgisi = fiyatın altındaki en yakın destek × (1−tol).
  Karar çizgisi hep fiyatın altından hesaplandığı için kırılım, bir önceki kapanışta kaydedilen çizgiyle
  (`karar_cizgisi`) kıyaslanır; aynı seviye için bir kez (`karar_kirilim`). Backtest: güçlü yükselişte büyük
  hisselerde al-tut, sinyale göre girip çıkmaktan belirgin iyi (19 hisseden 15'i).
- SAT + destekten tepki: SAT sürerken destek tepkilerinin ~%68'i 20 günde kırıldı → çelişki notu + karar çizgisi.
- Stop yönetimi (başabaş, iz stop, zayıf piyasada hızlı çıkış) mevcut sabit stop'tan iyi değil — değiştirme.
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
