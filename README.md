# Sismik Veri Analizi ve Karşılaştırma Pipeline'ı

Bu proje, farklı kaynaklardan gelen sismik verileri (waveform, katalog, HDF5 pickler, EQTransformer çıktıları) görselleştirmek ve karşılaştırmak için geliştirilmiş bir Python tabanlı pipeline içerir.

**Amaç:** Belirli bir zaman aralığı için sismik waveform verilerini indirmek, farklı analiz yöntemlerinden elde edilen pick ve event bilgilerini tek bir arayüzde görselleştirerek karşılaştırma yapmayı kolaylaştırmaktır.

**Görselleştirilen Veriler:**

1.  **Sismik Veri:** Seçilen bir istasyona ait ham ve filtrelenmiş waveform (Zaman-Amplitüd).
2.  **Deprem Katalog Verisi:** Manuel veya otomatik sistemlerden elde edilen katalog dosyasındaki P/S pickleri ve event merkezleri (Zaman-Boylam).
3.  **HDF5 Verisi:** Genellikle makine öğrenmesi modelleri tarafından üretilen HDF5 dosyasındaki P/S pickleri ve event merkezleri (Zaman-Boylam, Konumlar HDF5'ten).
4.  **EQTransformer Pick Dağılımı:** EQTransformer modelinin ürettiği `summary.csv` dosyasındaki P/S pickleri (Zaman-İstasyon).

## Kurulum

1.  **Depoyu Klonlayın veya İndirin:**
    ```bash
    git clone https://github.com/Pancarsuyu/seismic_analysis.git 
    cd seismic_analysis
    ```
    Veya dosyaları manuel olarak `seismic_analysis` adında bir klasöre indirin.

2.  **Gerekli Kütüphaneleri Kurun:**
    Projenin çalışması için aşağıdaki Python kütüphaneleri gereklidir. `requirements.txt` dosyası mevcutsa, bu adımı kullanabilirsiniz:
    ```bash
    pip install -r requirements.txt
    ```
    Eğer `requirements.txt` yoksa veya manuel kurmak isterseniz:
    ```bash
    pip install pandas plotly obspy numpy pytz h5py
    ```
    *Not: Python 3.8 veya üzeri bir sürüm önerilir.*

## Klasör Yapısı

Proje aşağıdaki klasör yapısını kullanır:
📁 seismic_analysis/
│
├── 📄 README.md # Bu dosya
├── 📄 requirements.txt # Gerekli Python kütüphaneleri
│
├── 📁 config/ # Yapılandırma dosyaları
│ └── 📄 config.py # <<< ANA AYAR DOSYASI >>>
│
├── 📁 data/ # Kod içinde kullanılan veri listeleri
│ └── 📄 station_names.py # HDF5 için istasyon isimleri listesi
│
├── 📁 utils/ # Yardımcı fonksiyon modülleri
│ ├── 📄 init.py
│ ├── 📄 seismic_utils.py # Waveform işleme/grafikleme
│ ├── 📄 catalog_utils.py # Katalog işleme/grafikleme
│ ├── 📄 hdf5_utils.py # HDF5 işleme/grafikleme
│ ├── 📄 eqt_utils.py # EQT işleme/grafikleme
│ └── 📄 download_utils.py # Waveform indirme
│
├── 📄 main.py # <<< ANA ÇALIŞTIRMA DOSYASI >>>
│
└── 📁 input_data/ # <<< TÜM GİRDİ DOSYALARININ YERİ >>>
│
├── 📁 mseed/ # İndirilen/Mevcut MSeed dosyaları buraya gelir/konur
│ └── ...
├── 📁 catalog/ # Katalog ve ilgili dosyalar
│ ├── 📄 [katalog_dosya_adi.txt] # Katalog dosyanız
│ └── 📄 [istasyon_dosya_adi.txt] # İstasyon bilgileri dosyası
├── 📁 hdf5/ # HDF5 dosyaları
│ └── 📄 [hdf5_dosya_adi.hdf5] # HDF5 dosyanız
└── 📁 eqt/ # EQTransformer çıktıları
└── 📄 summary.csv # EQT summary dosyası



## Yapılandırma (`config/config.py`)

Analizi çalıştırmadan önce `config/config.py` dosyasını kendi verilerinize ve tercihlerinize göre düzenlemeniz **gereklidir**.

**Önemli Ayarlar:**

1.  **Dosya Adları:**
    *   `_PHASE_CATALOG_FILENAME`: `input_data/catalog/` içindeki katalog dosyanızın adı.
    *   `_STATION_DATA_FILENAME`: `input_data/catalog/` içindeki istasyon bilgi dosyanızın adı.
    *   `_HDF5_FILENAME`: `input_data/hdf5/` içindeki HDF5 dosyanızın adı.
    *   `_EQT_SUMMARY_FILENAME`: `input_data/eqt/` içindeki EQT summary dosyasının adı (genellikle `summary.csv`).

2.  **Waveform İndirme (`download_settings`):**
    *   `enable_download`: Waveform indirme özelliğini açmak için `True`, kapatmak için `False` yapın.
    *   `client_name`: Veri alınacak FDSN istemcisi (örn: `"KOERI"`, `"IRIS"`).
    *   `date`, `start_hour`, `end_hour`: İndirilecek UTC zaman aralığı.
    *   `channel`: İndirilecek kanal kodu (örn: `"HHZ"`, `"EHZ"`).
    *   `stations_to_download`: İndirilecek istasyon kodlarının listesi.

3.  **Sismik Veri İşleme (`seismic_data`):**
    *   `selected_station`: Grafiklenecek waveform için istasyon kodu.
    *   `date`, `start_hour`, `phase_component`: Grafiklenecek waveformun zaman ve kanal bilgileri (indirilen veya `input_data/mseed` klasöründe bulunan veriyle eşleşmeli).
    *   `filter_type`, `freqmin`, `freqmax`, `corners`, `zerophase`: Waveform filtreleme parametreleri (`filter_type=None` filtre uygulamamak için).

4.  **Diğer Veri Kaynakları (`catalog_data`, `hdf5_data`, `eqt_data`):**
    *   Bu bölümlerdeki dosya yolları genellikle otomatik olarak ayarlanır. Sadece `eqt_data` içindeki `start_hour`, `end_hour`, `date` gibi grafikleme aralığını belirleyen parametreleri ayarlamanız gerekebilir.

5.  **Genel Grafik Ayarları (`plot_settings`):**
    *   `figure_height`: Oluşturulacak toplam figürün yüksekliği (piksel).
    *   `figure_title`: Figürün ana başlığı.

## Kullanım

1.  **Girdi Dosyalarını Hazırlayın:**
    *   Analiz etmek istediğiniz Katalog, HDF5 ve EQTransformer (`summary.csv`) dosyalarını `input_data/` altındaki ilgili klasörlere (`catalog`, `hdf5`, `eqt`) yerleştirin.
    *   Katalog grafiği için gerekli olan istasyon bilgilerini içeren dosyayı (`station_data.txt` formatında) `input_data/catalog/` içine yerleştirin.
    *   Eğer waveformları indirmek istemiyorsanız (`enable_download=False`), kullanmak istediğiniz `.mseed` dosyalarını `input_data/mseed/` klasörüne manuel olarak koyun. Dosya adlarının `ISTASYON_KANAL_NETWORK_TARIH_SAAT.mseed` formatına benzer olması beklenir (`seismic_utils.py`'deki glob deseniyle eşleşmeli).

2.  **`config.py` Dosyasını Düzenleyin:** Yukarıda "Yapılandırma" bölümünde açıklanan ayarları yapın. Özellikle dosya adlarını ve analiz parametrelerini kontrol edin. Waveform indirme istiyorsanız `enable_download = True` yapmayı unutmayın.

3.  **Pipeline'ı Çalıştırın:**
    Terminali açın, `seismic_analysis` klasörüne gidin ve aşağıdaki komutu çalıştırın:
    ```bash
    python main.py
    ```

4.  **Sonucu Görüntüleyin:**
    *   Kod çalışırken terminalde ilerleme durumunu ve olası uyarı/hataları göreceksiniz.
    *   Eğer waveform indirme etkinse, indirme işlemi başlayacaktır.
    *   Başarıyla tamamlandığında, 4 alt grafikten oluşan interaktif bir Plotly figürü varsayılan web tarayıcınızda veya ayrı bir pencerede açılacaktır.

## Hata Ayıklama İpuçları

*   **Dosya Bulunamadı Hataları:** `config.py`'deki dosya adlarının (`_FILENAME` değişkenleri) `input_data` altındaki gerçek dosya adlarıyla eşleştiğinden emin olun. Yolların doğru oluşturulduğunu terminal çıktısından kontrol edin.
*   **Boş Grafikler:**
    *   **Sismik Veri:** İlgili `.mseed` dosyasının `input_data/mseed/` içinde bulunduğundan veya başarılı bir şekilde indirildiğinden emin olun. `config.py`'deki `selected_station`, `date`, `start_hour`, `phase_component` ayarlarının mevcut bir dosyayla eşleştiğini kontrol edin.
    *   **Katalog/HDF5:** Terminaldeki ayrıştırma özeti mesajlarına bakın (`Başarıyla Ayrıştırılan Pick Sayısı`, `Grafiklenecek Event Merkezi Sayısı`). Eğer sayılar sıfırsa, girdi dosyasının formatı kodun beklediği formatla uyuşmuyor olabilir. İlgili `_utils.py` dosyasındaki ayrıştırma mantığını veya regex desenlerini dosya formatına göre ayarlamanız gerekebilir.
    *   **EQT:** `summary.csv` dosyasının varlığından ve `config.py`'deki zaman aralığında veri içerdiğinden emin olun.
*   **Konum Hataları (HDF5):** HDF5 grafiği konumları doğrudan HDF5 `locs` verisinden alır. Eğer konumlar hatalı görünüyorsa, bu HDF5 dosyasının oluşturulması sırasındaki bir sorundur. Kod, `locs` verisindeki 0. sütunu Boylam, 1. sütunu Enlem olarak varsayar. Eğer HDF5 dosyanızda bu sıra farklıysa (`0=Lat, 1=Lon`), `hdf5_utils.py` içindeki `longitude = locs[...]` ve `latitude = locs[...]` satırlarındaki indeksleri (0 ve 1) değiştirmeniz gerekir.
*   **Zaman Hataları (HDF5):** Kod, HDF5 `Picks` zamanını Epoch saniyesi, HDF5 `srcs` zamanını ise `config.py`'de belirtilen günün başlangıcından itibaren geçen saniye olarak varsayar. Eğer HDF5 dosyanız farklı bir zaman formatı kullanıyorsa, `hdf5_utils.py` içindeki zaman hesaplama kısımlarını güncellemeniz gerekir.
*   **Python Hataları (`TypeError`, `IndexError` vb.):** Terminaldeki tam hata mesajını ve traceback'i inceleyin. Genellikle veri formatı uyumsuzluklarından veya beklenmeyen `None` değerlerinden kaynaklanır. İlgili `_utils.py` dosyasına ek `print()` ifadeleri ekleyerek sorunun kaynağını bulabilirsiniz.

