# BIST Sinyal Sistemi — Kurulum Kılavuzu

Her hafta içi günü, borsa kapandıktan sonra otomatik çalışır:

1. Seçtiğin hisseleri tarar, **AL / AL+ / NÖTR / SAT** puanı üretir.
2. Bir **web panosu** günceller (telefondan da açılır).
3. **İzleme listendeki yeni AL sinyallerini Telegram'a** yollar — her gün değil, yalnızca yeni bir hisse AL'a geçtiğinde.

Hepsi ücretsiz; sunucu gerekmez, GitHub'ın ücretsiz altyapısında çalışır.

## İçindeki dosyalar
- `sinyal.py` — gösterge + sinyal kuralları (tek kaynak)
- `tarama.py` — canlı tarama + pano + Telegram (ayarlar en üstte)
- `pano.py` — web panosunu üretir
- `backtest.py` — kuralların geçmiş performansını ölçer
- `requirements.txt`, `.github/workflows/tarama.yml`

---

## Ne lazım?
- Ücretsiz **GitHub** hesabı · telefonunda **Telegram**. Kurulum ~15 dk. Takılırsan yaz, birlikte yaparız.

## Adım 1 — Telegram botu (token + chat id)
1. Telegram'da **@BotFather** → `/newbot` → sana bir **token** verir, kopyala.
2. **@userinfobot**'a mesaj at → sana **chat id** (bir numara) yazar.
3. Kendi botuna bir kez `/start` yaz (yoksa sana mesaj atamaz).

## Adım 2 — Repo oluştur, dosyaları yükle
GitHub → **New repository** (örn. `bist-sinyal`, Private olabilir) → tüm dosyaları `Add file → Upload files` ile yükle (`.github/workflows/tarama.yml` klasör yapısıyla).

## Adım 3 — Secrets ekle
**Settings → Secrets and variables → Actions → New repository secret**:
- `TELEGRAM_TOKEN` → BotFather token'ı
- `TELEGRAM_CHAT_ID` → userinfobot numarası

## Adım 4 — Web panosu (GitHub Pages)
**Settings → Pages → Source: Deploy from a branch → `main` / `root` → Save.**
Panon: `https://KULLANICIADIN.github.io/bist-sinyal/`

## Adım 5 — İlk taramayı elle çalıştır
**Actions → BIST Sinyal Taraması → Run workflow.** Sonra her hafta içi 18:30'da (İstanbul) kendi çalışır.

---

## Ayarlar (`tarama.py` en üstü)
| Ayar | Ne işe yarar |
|---|---|
| `IZLEME_LISTEM` | Senin hisselerin. **Telegram sadece bunlar için** çalar (pano yine tümünü gösterir). |
| `BIST30` | Panoda görünen geniş liste. Bileşim değişebilir, ara ara güncelle. |
| `PORTFOY_TL` | Toplam portföyün — **öneri lot** hesabı için. Kendi rakamını yaz. |
| `RISK_YUZDESI` | Bir işlemde riske atacağın portföy yüzdesi (öneri: %1). |
| `ASIRI_ISLEM_ESIGI` | Bir günde bundan çok yeni AL çıkarsa "seçici ol" uyarısı verir. |
| `SADECE_IZLEME_ALARM` | `True`: Telegram yalnızca izleme listen için. `False`: tüm evren. |

## Eklediğimiz özellikler
- **Risk yönetimi / öneri lot:** Her AL sinyalinde, stop yerse portföyünün sadece `RISK_YUZDESI` kadarını kaybedeceğin lot sayısını hesaplar: (portföy × risk%) ÷ (fiyat − stop). Panoda "Öneri lot" sütunu, Telegram'da mesaj içinde.
- **AL+ (teknik + temel birlikte):** Bir hisse hem teknik AL verip hem F/K ve PD/DD'si grup medyanının altındaysa **★ AL+** olur. Panoda yıldızlı, Telegram'da öncelikli.
- **Aşırı işlem uyarısı:** Bir günde eşikten çok yeni AL çıkarsa panoda ve Telegram'da "hepsini alma, seçici ol" uyarısı — çünkü fazla işlem komisyonda eritir.
- **İzleme listesi alarmı:** Telegram sadece senin listendeki hisseler için çalar; gürültü olmaz.

## Backtest — "bu kurallar geçmişte işe yaramış mı?"
Bilgisayarında (Python kurulu) çalıştır:
```
pip install -r requirements.txt
python backtest.py
```
`backtest.html` oluşur. Gerçekçi olması için: sinyal kapanışta oluşur, işleme **ertesi gün** girilir, her işlemde **çift yön %0.2 komisyon+kayma** düşülür, strateji **al-tut** ile kıyaslanır.
> Not: `backtest.py` şu an örnek/sentetik veriyle çalışır. Gerçek hisselerle çalıştırmak için içindeki veri üretimini `yfinance` ile değiştirmeni birlikte yapabiliriz — bir sonraki adım bu.
Okurken tek bir sayıya değil **isabet oranı + işlem başı ortalama + maksimum düşüşe birlikte** bak. Düşük isabetle bile ortalama pozitifse strateji kazananları büyütüp kaybı erken kesiyordur.

## Önemli — dürüst notlar
- Bu bir **karar destek** aracıdır, yatırım tavsiyesi değil. Senin yerine işlem yapmaz; sinyali sen değerlendirir, alım-satımı sen yaparsın.
- Göstergeler geçmişe bakar, geleceği garanti etmez. **Stop-loss'u ciddiye al** — uzun vadede seni ayakta tutan şey budur.
- Temel oranlar (F/K, PD/DD) veri sağlayıcıdan gelir; bazı hisselerde boş/gecikmeli olabilir.
