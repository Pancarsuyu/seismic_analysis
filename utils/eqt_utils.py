import pandas as pd
import plotly.graph_objects as go
import datetime
import pytz
import numpy as np

def plot_eqtransformer_picks(csv_file_path, eqt_start_hour, eqt_end_hour, eqt_date):
    """
    EQTransformer summary.csv dosyasından pick verilerini okur ve Plotly ile zaman-istasyon grafiği oluşturur.

    Args:
        csv_file_path (str): summary.csv dosyasının yolu.
        eqt_start_hour (int): EQTransformer için başlangıç saat filtresi (UTC).
        eqt_end_hour (int): EQTransformer için bitiş saat filtresi (UTC).
        eqt_date (str): EQTransformer için tarih filtresi (YYYY-MM-DD).

    Returns:
        plotly.graph_objects.Figure or None: Oluşturulan Plotly figürü veya hata durumunda None.
    """
    try:
        df = pd.read_csv(csv_file_path)
    except FileNotFoundError:
        print(f"Hata: EQTransformer CSV dosyası bulunamadı: {csv_file_path}")
        return None
    except Exception as e:
        print(f"Hata: EQTransformer CSV dosyası okunurken hata: {e}")
        return None

    # Gerekli sütunları kontrol et
    required_cols = ['pick_time', 'station_id', 'phase_type', 'pick_probability', 'snr']
    if not all(col in df.columns for col in required_cols):
        print(f"Hata: CSV dosyasında gerekli sütunlar eksik ({required_cols}). Mevcut sütunlar: {df.columns.tolist()}")
        return None

    # Veri tiplerini düzelt ve zamanı UTC'ye ayarla
    try:
        # SNR NaN değerlerini 0 ile doldur (veya başka bir strateji)
        df['snr'] = pd.to_numeric(df['snr'], errors='coerce').fillna(0)
        df['pick_probability'] = pd.to_numeric(df['pick_probability'], errors='coerce').fillna(0)

        # Pick zamanını datetime objesine çevir ve UTC yap
        df['pick_time'] = pd.to_datetime(df['pick_time'], errors='coerce')
        df.dropna(subset=['pick_time'], inplace=True) # Geçersiz zamanları kaldır
        # Eğer zaman zaten UTC değilse (offset bilgisi yoksa), UTC olduğunu varsay
        if df['pick_time'].dt.tz is None:
            df['pick_time'] = df['pick_time'].dt.tz_localize('UTC')
        else:
            df['pick_time'] = df['pick_time'].dt.tz_convert('UTC')

    except Exception as e:
        print(f"EQT CSV verisi işlenirken hata (tip dönüşümü): {e}")
        return None


    # Zaman aralığına göre filtrele
    try:
        start_dt_str = f"{eqt_date} {eqt_start_hour:02d}:00:00"
        end_dt_str = f"{eqt_date} {eqt_end_hour:02d}:00:00"
        start_time = datetime.datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
        # Bitiş saati dahil değil (<), bu yüzden bir sonraki saate kadar alıyoruz
        end_time = datetime.datetime.strptime(end_dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
        # Eğer end_hour 23 ise, bir sonraki günün 00:00'ı olur. Veya aynı gün 23:59:59 alınabilir.
        # Şimdilik tam saat sınırı kullanıyoruz.

        mask = (df['pick_time'] >= start_time) & (df['pick_time'] < end_time)
        df_filtered = df.loc[mask].copy() # Filtrelenmiş veri üzerinde çalışacağız
    except ValueError:
         print(f"Hata: Geçersiz tarih/saat formatı. Tarih: {eqt_date}, Saat: {eqt_start_hour}-{eqt_end_hour}")
         return None

    if df_filtered.empty:
        print(f"Uyarı: Belirtilen zaman aralığında ({start_dt_str} - {end_dt_str} UTC) EQTransformer pick verisi bulunamadı.")
        # İsteğe bağlı: Boş grafik döndürmek yerine None döndür
        # return None
        # Veya boş bir grafik oluştur
        fig = go.Figure() # Boş figür
    else:
        print(f"{len(df_filtered)} adet pick bulundu.")

        # Marker boyutunu SNR'a göre ayarla (abs kullanarak negatif SNR'ları da dikkate al)
        # Boyutu belirli bir aralıkta sınırla (min 5, max 20)
        df_filtered['marker_size'] = df_filtered['snr'].abs().fillna(0).clip(0) * 1.0 + 5 # SNR'a göre boyut, min 5
        df_filtered['marker_size'] = df_filtered['marker_size'].clip(5, 20) # Boyutu 5-20 arasında sınırla

        # Renk haritası
        color_map = {'P': 'blue', 'S': 'red'}

        # ---- Grafik Oluşturma ----
        fig = go.Figure()

        # İstasyonları Y ekseninde sıralamak için (alfabetik veya başka bir kritere göre)
        all_stations = sorted(df_filtered['station_id'].unique())

        for phase, group in df_filtered.groupby('phase_type'):
            phase_upper = phase.upper() # 'p'/'s' gelme ihtimaline karşı
            if phase_upper in color_map:
                hover_texts = [
                    f"İstasyon: {row.station_id}<br>"
                    f"Zaman: {row.pick_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}<br>"
                    f"Faz: {phase_upper}<br>"
                    f"Olasılık: {row.pick_probability:.2f}<br>"
                    f"SNR: {row.snr:.1f}"
                    for _, row in group.iterrows()
                ]
                fig.add_trace(go.Scatter(
                    x=group['pick_time'],
                    y=group['station_id'],
                    mode='markers',
                    marker=dict(
                        color=color_map[phase_upper],
                        size=group['marker_size'],
                        opacity=0.8,
                        line=dict(width=1, color='DarkSlateGrey')
                    ),
                    name=f'{phase_upper} Picks',
                    hovertext=hover_texts,
                    hoverinfo='text' # Sadece özel hover text'i göster
                ))

        # Y eksenini istasyonlara göre ayarla
        fig.update_yaxes(categoryorder='array', categoryarray=all_stations)


    # Genel Grafik Düzeni
    fig.update_layout(
        title=f'EQTransformer Pick Dağılımı ({eqt_start_hour:02d}:00 - {eqt_end_hour:02d}:00 UTC)<br><sup>Tarih: {eqt_date}</sup>',
        xaxis_title='Zaman (UTC)',
        yaxis_title='İstasyon ID',
        template='plotly_white',
        height=300, # Alt grafik için standart yükseklik
        hovermode='closest',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
         margin=dict(l=60, r=40, t=80, b=40) # Y ekseni etiketleri için sol boşluğu artır
    )
    # X ekseni formatını ve aralığını ayarla
    fig.update_xaxes(
        tickformat='%H:%M:%S', # Sadece saat:dakika:saniye göster
        range=[start_time, end_time] # X ekseni sınırlarını belirle
    )

    return fig