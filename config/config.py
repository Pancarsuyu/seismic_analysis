import os

# --- Otomatik Yol Tanımlama ---
# Bu script'in bulunduğu dizin (config/)
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
# Proje kök dizini (seismic_analysis/)
PROJECT_ROOT = os.path.dirname(_CONFIG_DIR)
# Girdi verilerinin ana klasörü (seismic_analysis/input_data/)
INPUT_DATA_DIR = os.path.join(PROJECT_ROOT, 'input_data')
# --- Otomatik Yol Tanımlama Sonu ---

# === DOSYA ADLARI (input_data içindeki) ===
# Eğer bu dosya adları değişirse, sadece burayı güncelleyin.
_MSEED_SUBDIR = 'mseed'
_CATALOG_SUBDIR = 'catalog'
_HDF5_SUBDIR = 'hdf5'
_EQT_SUBDIR = 'eqt'

_PHASE_CATALOG_FILENAME = "2023_12_04_fazcalismasi.txt" # Katalog dosyanızın adı
_STATION_DATA_FILENAME = "station_data.txt"           # İstasyon veri dosyanızın adı
_HDF5_FILENAME = "Marmara_Faz_results_continuous_days_2023_12_4_ver_1.hdf5"      # HDF5 dosyanızın adı
_EQT_SUMMARY_FILENAME = "summary.csv"                 # EQT summary dosyasının adı (genellikle sabit)
# ========================================


# Ana yapılandırma sözlüğü
CONFIG = {
    # === Yeni: Waveform İndirme Ayarları ===
    'download_settings': {
        'enable_download': False,                # İndirmeyi etkinleştirmek için True yapın
        'client_name': "KOERI",                 # Veri alınacak FDSN istemcisi (örn: "IRIS", "GFZ", "KOERI")
        'date': "2023-12-04",                   # İndirilecek tarih (YYYY-MM-DD)
        'start_hour': 6,                        # İndirilecek başlangıç saati (UTC)
        'end_hour': 8,                          # İndirilecek bitiş saati (UTC) - Bu saate KADAR indirir (8:00 dahil değil)
        'channel': "HHZ",                       # İndirilecek kanal (örn: "HHZ", "EHZ", "BHN")
        'stations_to_download': [               # İndirilecek istasyonların listesi
            "KCTX", "DOGC", "KAVV", "TKR", "KOUK", "KRBG", "GELI", "GOKC", "OSMT", "RKY",
            "CRLU", "MDNY", "KLYT", "HRTX", "CTKS", "ADVT", "TUZL", "EDC", "UKOP", "BUYA",
            "YKBL", "BGKT", "AVCI", "SILT", "BOTS", "CANM", "KUMB", "SINB", "GONE", "LAFA",
            "ASYA", "MRMT", "IZI", "TEKI", "SLVT", "ESKY", "LAP", "CTYL", "KRTL", "EDRB",
            "GAZK", "BRGA", "HVHR", "CRLT", "MAEG", "TZLA", "ENZZ", "YENI", "ARMT", "PHSR",
            "ERIK", "YLVH", "BUYK", "GEML", "SUSR", "HYBA", "YLV", "CAVI", "LAPK", "BIGA",
            "ORLT", "ISK", "ENEZ", "SILV"
            # Not: Bu liste data/station_names.py'deki ile aynı veya farklı olabilir.
        ],
    },
    # === Kod1: Sismik Veri İşleme Parametreleri ===
    'seismic_data': {
        # Mseed dosyalarının bulunduğu klasör (otomatik olarak input_data/mseed belirlendi)
        'mseed_folder': os.path.join(INPUT_DATA_DIR, _MSEED_SUBDIR),
        'selected_station': "GELI",              # Analiz edilecek istasyon
        'date': "2023-12-04",                    # Analiz tarihi (YYYY-MM-DD)
        'start_hour': 6,                         # İlgilenilen zaman diliminin başlangıç saati (UTC)
        'filter_type': "highpass",               # "highpass", "lowpass", "bandpass", "bandstop" veya None
        'freqmin': 0.1,                          # Minimum frekans (Hz)
        'freqmax': None,                         # Maksimum frekans (Hz) - highpass için None
        'corners': 4,                            # Filtre derecesi
        'zerophase': True,                       # Faz kaymasını önle (True/False)
        'phase_component': "HHZ",                # Kullanılacak faz bileşeni (örn. "HHZ", "EHZ")
    },

    # === Kod2: Deprem Katalog Verisi Parametreleri ===
    'catalog_data': {
        # Katalog dosyasının tam yolu (otomatik olarak input_data/catalog/dosya_adı belirlendi)
        'catalog_file_path': os.path.join(INPUT_DATA_DIR, _CATALOG_SUBDIR, _PHASE_CATALOG_FILENAME),
        # İstasyon bilgilerini içeren dosya yolu (otomatik olarak input_data/catalog/dosya_adı belirlendi)
        'station_data_path': os.path.join(INPUT_DATA_DIR, _CATALOG_SUBDIR, _STATION_DATA_FILENAME),
    },

    # === Kod3: HDF5 Deprem Pick Verisi Parametreleri ===
    'hdf5_data': {
        # HDF5 dosyasının tam yolu (otomatik olarak input_data/hdf5/dosya_adı belirlendi)
        'hdf5_file_path': os.path.join(INPUT_DATA_DIR, _HDF5_SUBDIR, _HDF5_FILENAME),
        # İstasyon isimleri data/station_names.py dosyasından alınacak (bu değişmedi)
    },

    # === Kod4: EQTransformer Pick Verisi Parametreleri ===
    'eqt_data': {
        # summary.csv dosyasının tam yolu (otomatik olarak input_data/eqt/summary.csv belirlendi)
        'summary_csv_path': os.path.join(INPUT_DATA_DIR, _EQT_SUBDIR, _EQT_SUMMARY_FILENAME),
        'start_hour': 7,                         # Grafiklenecek başlangıç saati (UTC)
        'end_hour': 8,                           # Grafiklenecek bitiş saati (UTC)
        'date': "2023-12-04",                    # Grafiklenecek tarih (YYYY-MM-DD)
    },

    # === Genel Grafik Ayarları ===
    'plot_settings': {
        'figure_height': 1500,                   # Toplam figür yüksekliği (piksel)
        'figure_title': "Veri Karşılaştırma Grafikleri", # Ana başlık
    }
}

# Yolların var olup olmadığını kontrol etmek için basit bir doğrulama (isteğe bağlı)
def check_paths():
    print("Yapılandırma dosyası yolları kontrol ediliyor...")
    paths_to_check = [
        CONFIG['seismic_data']['mseed_folder'],
        CONFIG['catalog_data']['catalog_file_path'],
        CONFIG['catalog_data']['station_data_path'],
        CONFIG['hdf5_data']['hdf5_file_path'],
        CONFIG['eqt_data']['summary_csv_path'],
    ]
    all_exist = True
    for p in paths_to_check:
        # Mseed bir klasör olduğu için farklı kontrol edilebilir, şimdilik dosya gibi kontrol edelim
        # Veya sadece klasörün varlığını kontrol edelim
        if os.path.isdir(p) if 'mseed_folder' in p else os.path.isfile(p):
             # print(f"  [OK] {p}") # Çok fazla çıktı olabilir
             pass
        else:
            # Sadece dosya yollarını kontrol et, klasör için os.path.isdir kullanılabilir
            if not os.path.exists(p):
                 print(f"  [UYARI] Yol bulunamadı veya dosya/klasör değil: {p}")
                 print(f"          Lütfen dosyanın doğru yerde olduğundan ve config.py'deki dosya adının doğru olduğundan emin olun.")
                 all_exist = False
            # else: print(f"  [OK] {p}")
    if all_exist:
        print("  Tüm temel yollar mevcut görünüyor.")
    else:
         print("  Bazı yollar bulunamadı. Lütfen yukarıdaki uyarıları kontrol edin.")

# Bu script import edildiğinde yolları kontrol et (main.py çalışmadan önce)
# check_paths() # İsterseniz bu kontrolü aktif edebilirsiniz.