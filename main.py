from plotly.subplots import make_subplots
import plotly.graph_objects as go
import os # Eklendi
import sys # exit() için

# Yardımcı fonksiyonları ilgili modüllerden import et
from utils import seismic_utils
from utils import catalog_utils
from utils import hdf5_utils
from utils import eqt_utils
from utils import download_utils # Yeni eklenen indirme modülü

# Yapılandırma ve veri dosyalarını import et
# config.py içindeki yollar artık otomatik olarak input_data klasörünü gösteriyor
try:
    from config.config import CONFIG
except ImportError:
     print("Hata: config/config.py dosyası bulunamadı veya içe aktarılamadı.")
     print("Lütfen dosyanın doğru yerde olduğundan ve Python hatası içermediğinden emin olun.")
     exit()
try:
    from data.station_names import STATION_NAMES # HDF5 için istasyon listesi
except ImportError:
     print("Hata: data/station_names.py dosyası bulunamadı veya içe aktarılamadı.")
     exit()


def main():
    """
    Ana fonksiyon. Gerekirse waveform indirir, verileri işler ve grafiği oluşturur.
    """
    print("="*50)
    print(" Seismic Analysis Pipeline Başlatılıyor ".center(50, "="))
    print("="*50)
    print(f"Proje Kök Dizini: {CONFIG.get('PROJECT_ROOT', 'Bilinmiyor')}")
    print(f"Girdi Veri Dizini: {CONFIG.get('INPUT_DATA_DIR', 'Bilinmiyor')}")

    # === 1. Adım: Waveform İndirme (Opsiyonel) ===
    try:
        # İndirme ayarları varsa ve enable_download True ise indirmeyi çalıştır
        if 'download_settings' in CONFIG and CONFIG['download_settings'].get('enable_download', False):
            download_utils.run_download(CONFIG)
        else:
            print("\nWaveform indirme adımı atlandı (config dosyasında etkin değil).")
            # İndirme yapılmadıysa mseed klasörünün varlığını kontrol etmek iyi olabilir
            mseed_folder = CONFIG.get('seismic_data', {}).get('mseed_folder')
            if not os.path.isdir(mseed_folder):
                 print(f"[UYARI] Mseed klasörü bulunamadı: {mseed_folder}")
                 print("        Grafikleme işlemi başarısız olabilir.")
            else:
                 print(f"Mevcut mseed klasörü kullanılacak: {mseed_folder}")

    except Exception as download_err:
        print(f"\n[HATA] Waveform indirme sırasında beklenmedik bir hata oluştu: {download_err}")
        print("İşlem devam ediyor, ancak waveform verileri eksik olabilir.")

    # === 2. Adım: Dosya Yolu Kontrolleri (Grafikleme Öncesi) ===
    print("\nGrafikleme için dosya ve klasör yolları kontrol ediliyor...")
    paths_ok = True
    # seismic_data.mseed_folder kontrolü indirme yapılmadıysa yukarıda yapıldı.
    # İndirme yapıldıysa zaten oluşturulmuş olmalı. Yine de kontrol edelim.
    mseed_folder = CONFIG.get('seismic_data', {}).get('mseed_folder')
    if not os.path.isdir(mseed_folder):
        print(f"  [HATA] Mseed klasörü bulunamadı/oluşturulamadı: {mseed_folder}")
        paths_ok = False

    required_files = [
        CONFIG.get('catalog_data', {}).get('catalog_file_path'),
        CONFIG.get('catalog_data', {}).get('station_data_path'),
        CONFIG.get('hdf5_data', {}).get('hdf5_file_path'),
        CONFIG.get('eqt_data', {}).get('summary_csv_path'),
    ]
    # None değerlerini filtrele (config'de eksik olabilir)
    required_files = [f for f in required_files if f is not None]

    for f in required_files:
         if not os.path.isfile(f):
            print(f"  [HATA] Gerekli dosya bulunamadı: {f}")
            paths_ok = False

    if not paths_ok:
         print("\nEksik girdi dosyaları veya klasörleri var!")
         print("Lütfen 'input_data' klasörünü ve içindekileri kontrol edin.")
         print("config.py dosyasındaki ayarların doğru olduğundan emin olun.")
         # sys.exit(1) # Durdurmak yerine devam edip grafiklerin eksik olmasına izin verilebilir.
         print("Grafikleme işlemi eksik verilerle devam edecek...")
    else:
         print("  Grafikleme için gerekli tüm girdi yolları mevcut görünüyor.")


    # === 3. Adım: Alt Grafikleri Oluştur ===
    print("\n--- Grafik Oluşturma İşlemi Başlatılıyor ---")
    fig = make_subplots(
        rows=4, cols=1,
        subplot_titles=(
            "Sismik Veri (Filtreli ve Ham)",
            "Deprem Katalog Verisi (Zaman-Boylam)",
            "HDF5 Deprem Pick Verisi (Zaman-Boylam)",
            "EQTransformer Pick Dağılımı (Zaman-İstasyon)"
        ),
        vertical_spacing=0.08
    )

    # 3.1 Sismik Veri Grafiği
    print("1. Sismik veri grafiği oluşturuluyor...")
    seismic_cfg = CONFIG['seismic_data']
    # seismic_utils.plot_seismic_data'nın indirilen dosya adını bulması önemli.
    # İndirilen format: {station}_{channel}_{network}_{date_YYYY-MM-DD}_{hour}00.mseed
    # Aranan glob: {mseed_folder}/{selected_station}_{phase_component}_*_{date}_*{start_hour:02d}00*.mseed
    # Bu glob deseninin çalışması gerekir.
    fig1 = seismic_utils.plot_seismic_data(
        output_folder=seismic_cfg['mseed_folder'], # Doğru parametre adı
        selected_station=seismic_cfg['selected_station'],
        date=seismic_cfg['date'],
        start_hour=seismic_cfg['start_hour'],
        filter_type=seismic_cfg['filter_type'],
        freqmin=seismic_cfg['freqmin'],
        freqmax=seismic_cfg['freqmax'],
        corners=seismic_cfg['corners'],
        zerophase=seismic_cfg['zerophase'],
        phase_component=seismic_cfg['phase_component']
    )
    if fig1:
        for trace in fig1.data: fig.add_trace(trace, row=1, col=1)
        fig.update_xaxes(title_text=fig1.layout.xaxis.title.text, row=1, col=1, rangeselector=fig1.layout.xaxis.rangeselector, rangeslider=fig1.layout.xaxis.rangeslider)
        fig.update_yaxes(title_text=fig1.layout.yaxis.title.text, row=1, col=1)
        print("   Sismik veri grafiği eklendi.")
    else:
        print("   Uyarı: Sismik veri grafiği oluşturulamadı (Muhtemelen ilgili mseed dosyası bulunamadı).")
        fig.add_annotation(text="Sismik Veri Yüklenemedi/Bulunamadı", row=1, col=1, showarrow=False)

    # 3.2 Katalog Grafiği
    print("2. Deprem katalog grafiği oluşturuluyor...")
    catalog_cfg = CONFIG['catalog_data']
    fig2 = catalog_utils.plot_catalog_data(
        catalog_file_path=catalog_cfg['catalog_file_path'],
        station_data_path=catalog_cfg['station_data_path']
    )
    if fig2:
        # ... (öncekiyle aynı grafik ekleme kodu) ...
        for trace in fig2.data: trace.showlegend = True; fig.add_trace(trace, row=2, col=1)
        fig.update_xaxes(title_text=fig2.layout.xaxis.title.text, row=2, col=1, tickformat='%H:%M:%S')
        fig.update_yaxes(title_text=fig2.layout.yaxis.title.text, row=2, col=1)
        print("   Katalog grafiği eklendi.")
    else:
        print("   Uyarı: Deprem katalog grafiği oluşturulamadı.")
        fig.add_annotation(text="Katalog Verisi Yüklenemedi", row=2, col=1, showarrow=False)

    # 3.3 HDF5 Grafiği
    print("3. HDF5 pick grafiği oluşturuluyor...")
    hdf5_cfg = CONFIG['hdf5_data']
    fig3 = hdf5_utils.plot_hdf5_picks(
        hdf5_file_path=hdf5_cfg['hdf5_file_path'],
        station_names=STATION_NAMES
    )
    if fig3:
        # ... (öncekiyle aynı grafik ekleme kodu) ...
        for trace in fig3.data: trace.showlegend = False; fig.add_trace(trace, row=3, col=1)
        fig.update_xaxes(title_text=fig3.layout.xaxis.title.text, row=3, col=1, tickformat='%H:%M:%S')
        fig.update_yaxes(title_text=fig3.layout.yaxis.title.text, row=3, col=1)
        print("   HDF5 pick grafiği eklendi.")
    else:
        print("   Uyarı: HDF5 pick grafiği oluşturulamadı.")
        fig.add_annotation(text="HDF5 Verisi Yüklenemedi", row=3, col=1, showarrow=False)

    # 3.4 EQT Grafiği
    print("4. EQTransformer pick grafiği oluşturuluyor...")
    eqt_cfg = CONFIG['eqt_data']
    fig4 = eqt_utils.plot_eqtransformer_picks(
        csv_file_path=eqt_cfg['summary_csv_path'],
        eqt_start_hour=eqt_cfg['start_hour'],
        eqt_end_hour=eqt_cfg['end_hour'],
        eqt_date=eqt_cfg['date']
    )
    if fig4:
        # ... (öncekiyle aynı grafik ekleme kodu) ...
        for trace in fig4.data: trace.showlegend = True; fig.add_trace(trace, row=4, col=1)
        fig.update_xaxes(title_text=fig4.layout.xaxis.title.text, row=4, col=1, tickformat='%H:%M:%S')
        fig.update_yaxes(title_text=fig4.layout.yaxis.title.text, row=4, col=1, categoryorder='array', categoryarray=fig4.layout.yaxis.categoryarray)
        print("   EQTransformer pick grafiği eklendi.")
    else:
        print("   Uyarı: EQTransformer pick grafiği oluşturulamadı.")
        fig.add_annotation(text="EQTransformer Verisi Yüklenemedi", row=4, col=1, showarrow=False)


    # --- 4. Adım: Genel Figür Ayarları ve Gösterim ---
    plot_cfg = CONFIG['plot_settings']
    fig.update_layout(
        height=plot_cfg['figure_height'],
        title_text=plot_cfg['figure_title'],
        title_x=0.5,
        showlegend=False,
        template="plotly_white"
    )

    print("\n--- Grafik Gösteriliyor ---")
    fig.show()
    print("\nProgram tamamlandı.")
    print("="*50)

if __name__ == "__main__":
    main()