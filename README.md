# BIST Sinyal Sistemi

Hafta içi, piyasa saatlerinde **~15 dk'da bir** çalışır: BIST 100'ü tarar, panoyu günceller, izleme listendeki yeni AL'leri Telegram'a yollar. Ücretsiz (public repo + Actions + Pages). Veri ~15 dk gecikmeli olabilir.

## Sayfalar
- **index.html** — ana pano: Portföyüm bölümü + tüm hisseler. Satıra tıkla → grafik + o hisseye özel yorum + TradingView.
- **gecmis.html** — Sinyal Geçmişi (canlı karne): açık takipler + kapanmış sinyaller + isabet oranı.
- **backtest.html** — geçmiş simülasyonu (elle çalıştırılır).

## Dosyalar
`sinyal.py` (kurallar) · `tarama.py` (tarama+pano+Telegram, ayarlar en üstte) · `pano.py` (pano+geçmiş sayfası) · `backtest.py` · `portoy.json` (portföyün) · `requirements.txt` · `.github/workflows/tarama.yml` (15 dk) · `.github/workflows/backtest.yml` (elle)

## Portföyün (artık butonla)
Panoda **Portföyüm → + Ekle** ile hisse/adet/maliyet girersin; **cihazında** saklanır (dosya düzenlemeye gerek yok). Her satırda kâr/zarar, güncel sinyal ve SAT uyarısı; ✕ ile silersin. Tüm hisseler yine taranır — bu sadece senin pozisyonların.


## Sinyal geçmişi (canlı karne)
Sistem AL dediği anki fiyatı `gecmis.json`'a kaydeder; stop yerse ya da sinyal SAT'a dönerse kapatıp sonucu yazar. `gecmis.html`'de birikir. Bu **ileriye dönük gerçek** performanstır (bugünden itibaren). `gecmis.json` otomatik oluşur, elleme.

## Backtest (geçmiş simülasyonu)
Actions → **Backtest (elle)** → **Run workflow**. Gerçek 2 yıllık veriyle çalışır, `backtest.html` üretir. Sinyal kapanışta oluşur, işleme ertesi gün girilir, çift yön %0.2 komisyon düşülür, al-tut ile kıyaslanır.

## Ayarlar (`tarama.py` en üstü)
`IZLEME_LISTEM` (Telegram sadece bunlara) · `BIST100` (panodaki liste, bileşim değişebilir) · `PORTFOY_TL`, `RISK_YUZDESI` (öneri lot) · `ASIRI_ISLEM_ESIGI` · `SADECE_IZLEME_ALARM`.

## Mevcut repo'yu güncelleme
1. **Add file → Upload files** → şunları sürükle (üzerine yazılır): `sinyal.py`, `tarama.py`, `pano.py`, `backtest.py`, `requirements.txt`, `README.md`, `portoy.json` → Commit.
2. `.github/workflows/tarama.yml`'i aç → ✏️ → içeriği yenisiyle değiştir → Commit.
3. **Add file → Create new file** → ad: `.github/workflows/backtest.yml` → paketteki içeriği yapıştır → Commit.
4. **Actions → BIST Sinyal Taraması → Run workflow** (bir kez elle).

## Göstergeler (çoklu, şeffaf)
Artık tek bir karar yerine **5 popüler gösterge ayrı ayrı** oy veriyor; genel sinyal bunların uyumundan çıkıyor. Tabloda "Uyum" sütunu (ör. 4/5), hisseye tıklayınca her göstergenin ayrı AL/SAT durumu:
- **SuperTrend** (ATR tabanlı trend) — fiyat çizginin üstünde mi? Grafikte kırmızı çizgi olarak da görünür.
- **MACD** — momentum yönü. **EMA 20/50** — kısa/uzun ortalama dizilimi. **RSI** — aşırı alım/satım. **Stochastic** — kısa vadeli zamanlama.
- Bağlam (oy vermez): **ADX** (trend gücü) ve **Bollinger** (banda göre konum).

Eşikleri `sinyal.py` başından ayarlarsın (`AL_ESIK`, `SAT_ESIK`). Uyarı: çoğu gösterge trendi ölçtüğü için birlikte hareket eder; "daha çok gösterge = daha isabetli" değildir. Hangi kurgunun işe yaradığını **backtest + canlı karne** söyler.

## Sinyal zamanlaması ve çıkış
Her sinyalin **ne zaman başladığı** artık belli:
- Tabloda **"Sinyalde"** sütunu: kaç gündür o sinyalde (ör. `1g`, `12g`). **YENİ** etiketi = bugün AL'a döndü. Taze AL'ler listenin en üstünde.
- Hisseye tıklayınca: sinyal başlangıç tarihi, **başlangıçtan beri % değişim** (hareketi kaçırdın mı görürsün) ve **çıkış kuralı**: "sinyal SAT'a dönerse ya da stop X TL altına inerse çık." Ayrıca mekanik bir **2R örnek hedef** (tahmin değil, referans).
- Telegram zaten sadece **yeni** AL'de (ilk döndüğü an) mesaj atar — yani "kaçırdığın eski AL" değil, tazesi gelir.

Ne kadar tutmalı? Bu sistem **hedefe göre değil kurala göre** çıkışlıdır: pozisyonu sinyal AL kaldıkça / stop üstünde durdukça tutar, SAT'a döndüğünde ya da stop yediğinde bırakırsın. "3 gün / 5 gün" gibi sabit bir süre yok; piyasa karar verir, sen kurala uyarsın.

## Dürüst notlar
Yatırım tavsiyesi değildir; senin yerine işlem yapmaz. Göstergeler geçmişe bakar, geleceği garanti etmez. Stop-loss'u ciddiye al. F/K'nın mutlak "iyi" eşiği yoktur; grup medyanına göre görecedir ve enflasyonda yanıltıcı olabilir.
