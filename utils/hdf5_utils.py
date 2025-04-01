import h5py
import numpy as np
import datetime
import plotly.graph_objects as go

def plot_hdf5_picks(hdf5_file_path, station_names):
    """
    HDF5 dosyasından deprem picklerini okur ve Plotly ile zaman-boylam grafiği oluşturur.

    Args:
        hdf5_file_path (str): HDF5 dosyasının yolu.
        station_names (list): İstasyon isimleri listesi (data/station_names.py'den gelir).

    Returns:
        plotly.graph_objects.Figure or None: Oluşturulan Plotly figürü veya hata durumunda None.
    """
    try:
        with h5py.File(hdf5_file_path, 'r') as hf:
            # Lokasyon verisini al (genellikle 'locs' veya benzeri bir isimle saklanır)
            if 'locs' not in hf:
                print(f"Hata: HDF5 dosyasında 'locs' datasetyi bulunamadı: {hdf5_file_path}")
                return None
            locs = np.array(hf['locs']) # [longitude, latitude, elevation] şeklinde varsayılıyor

            # Pick verisini al (genellikle 'Picks' grubu altında)
            if 'Picks' not in hf:
                print(f"Hata: HDF5 dosyasında 'Picks' grubu bulunamadı: {hdf5_file_path}")
                return None

            pick_groups = {} # earthquake_id: {'P': [], 'S': []}

            # 'Picks' grubundaki tüm datasetleri (her biri bir event'e ait olabilir) işle
            for dataset_name in hf['Picks'].keys():
                # Dataset adından event ID ve pick tipini çıkarmaya çalış
                # Örnek: 'Event123_P', 'SomeID_S' gibi olabilir. Bu kısmı dosya yapınıza göre ayarlayın.
                parts = dataset_name.split('_')
                if len(parts) < 2: continue # Beklenen formatta değilse atla

                earthquake_id = "_".join(parts[:-1]) # Son kısım hariç hepsi ID
                pick_type = parts[-1].upper() # Son kısım P veya S olmalı

                if pick_type not in ['P', 'S']:
                    continue # Sadece P ve S fazlarıyla ilgileniyoruz

                if earthquake_id not in pick_groups:
                    pick_groups[earthquake_id] = {'P': [], 'S': []}

                pick_data = np.array(hf['Picks'][dataset_name])
                # Pick datasının formatını kontrol et (genellikle [time_seconds, station_index, probability])
                if pick_data.shape[1] < 2:
                     print(f"Uyarı: {dataset_name} içinde yetersiz sütun (en az 2 bekleniyor: zaman, istasyon index).")
                     continue

                for pick_row in pick_data:
                    time_seconds = pick_row[0] # Epoch saniyesi olarak varsayılıyor
                    station_index = int(pick_row[1])
                    # probability = pick_row[2] # İleride kullanılabilir

                    # Geçerli index mi kontrol et
                    if station_index >= len(locs) or station_index >= len(station_names):
                        print(f"Uyarı: Geçersiz istasyon index ({station_index}) bulundu. Atlanıyor.")
                        continue

                    # Zamanı datetime objesine çevir
                    try:
                        # Bazen zaman UTC yerine başka bir referansa göre olabilir,
                        # HDF5 dosyasının nasıl oluşturulduğuna bakın. Genelde 1970-01-01 UTC'dir.
                        datetime_obj = datetime.datetime.utcfromtimestamp(time_seconds)
                    except ValueError:
                         print(f"Uyarı: Geçersiz zaman değeri ({time_seconds}) bulundu. Atlanıyor.")
                         continue

                    station_name = station_names[station_index]
                    longitude = locs[station_index][0] # locs'un [lon, lat, elev] olduğunu varsayıyoruz

                    pick_groups[earthquake_id][pick_type].append({
                        'time': datetime_obj,
                        'longitude': longitude,
                        'station': station_name
                        # 'probability': probability # İhtiyaç olursa eklenebilir
                    })

            # ---- Grafik Oluşturma ----
            fig = go.Figure()
            p_marker = dict(color='blue', symbol='circle', size=8, line=dict(color='black', width=1))
            s_marker = dict(color='red', symbol='x', size=8, line=dict(color='black', width=1))
            line_style = dict(color='rgba(0,0,0,0.5)', width=1, dash='dot')

            has_data = False # Grafiklenecek veri var mı?

            for earthquake_id, pick_types in pick_groups.items():
                p_picks = pick_types.get('P', [])
                s_picks = pick_types.get('S', [])

                if p_picks:
                    has_data = True
                    hover_texts_p = [f"Faz: P<br>İstasyon: {p['station']}<br>Zaman: {p['time'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}<br>Boylam: {p['longitude']:.4f}" for p in p_picks]
                    fig.add_trace(go.Scatter(
                        x=[p['time'] for p in p_picks], y=[p['longitude'] for p in p_picks],
                        mode='markers', marker=p_marker, name=f'P Picks ({earthquake_id})', # Lejantta event ID'si görünsün
                        text=hover_texts_p, hoverinfo='text', showlegend=False # Lejantı basit tutmak için gizleyelim
                        ))

                if s_picks:
                    has_data = True
                    hover_texts_s = [f"Faz: S<br>İstasyon: {s['station']}<br>Zaman: {s['time'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}<br>Boylam: {s['longitude']:.4f}" for s in s_picks]
                    fig.add_trace(go.Scatter(
                        x=[s['time'] for s in s_picks], y=[s['longitude'] for s in s_picks],
                        mode='markers', marker=s_marker, name=f'S Picks ({earthquake_id})',
                        text=hover_texts_s, hoverinfo='text', showlegend=False
                        ))

                # Aynı event'e ait pickleri birleştiren çizgi
                all_picks = sorted(p_picks + s_picks, key=lambda x: x['time'])
                if len(all_picks) > 1:
                    has_data = True
                    fig.add_trace(go.Scatter(
                        x=[p['time'] for p in all_picks], y=[p['longitude'] for p in all_picks],
                        mode='lines', line=line_style, hoverinfo='none', showlegend=False
                        ))

            if not has_data:
                 print("Uyarı: HDF5 dosyasında grafiklenecek P/S pick verisi bulunamadı.")
                 # Boş bir figür döndürebilir veya None
                 # return None

            fig.update_layout(
                title='HDF5 Deprem Pickleri: Zaman-Boylam Dağılımı',
                xaxis_title='Zaman (UTC)',
                yaxis_title='Boylam (°)',
                showlegend=False, # Ana lejant kapalı
                height=300, # Alt grafik için standart yükseklik
                template="plotly_white",
                hovermode='closest',
                margin=dict(l=40, r=40, t=60, b=40) # Kenar boşlukları
            )
            # X ekseni formatını daha okunabilir yapalım
            fig.update_xaxes(tickformat='%Y-%m-%d\n%H:%M:%S')

            return fig

    except FileNotFoundError:
        print(f"Hata: HDF5 dosyası bulunamadı: {hdf5_file_path}")
        return None
    except Exception as e:
        print(f'HDF5 verisi işlenirken beklenmedik bir hata oluştu: {str(e)}')
        return None