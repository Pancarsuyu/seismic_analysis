# seismic_analysis/utils/catalog_utils.py

import io
import datetime
import plotly.graph_objects as go
import os
import re
import pytz # Zaman dilimi için

# --- Yardımcı Fonksiyonlar (parse_station_data, _read_file_content - Aynı kalır) ---
def _read_file_content(file_path):
    if not os.path.exists(file_path): print(f"Hata: Dosya bulunamadı: {file_path}"); return None
    try:
        with open(file_path, "r", encoding='utf-8') as file: return file.read()
    except UnicodeDecodeError:
        print(f"Uyarı: '{file_path}' dosyası utf-8 ile okunamadı, latin-1 deneniyor.")
        try:
             with open(file_path, "r", encoding='latin-1') as file: return file.read()
        except Exception as e: print(f"Hata: Dosya okunurken hata ({file_path}) (latin-1 denendi): {e}"); return None
    except Exception as e: print(f"Hata: Dosya okunurken hata ({file_path}): {e}"); return None

def parse_station_data(station_data_str):
    station_locations = {}
    if not station_data_str: print("Uyarı: İstasyon veri string'i boş."); return station_locations
    try:
        for line in io.StringIO(station_data_str):
            line = line.strip();
            if not line or line.startswith("#"): continue
            parts = line.split('|')
            if len(parts) >= 4:
                network = parts[0].strip(); station_name = parts[1].strip()
                try: latitude = float(parts[2].strip()); longitude = float(parts[3].strip()); station_locations[station_name] = {'lon': longitude, 'lat': latitude, 'network': network}
                except ValueError: print(f"Uyarı: İstasyon formatı hatalı (lat/lon sayısal değil): {line}")
            else: print(f"Uyarı: İstasyon formatı eksik (en az 4 sütun bekleniyor): {line}")
    except Exception as e: print(f"İstasyon verisi ayrıştırılırken hata: {e}")
    return station_locations
# --- ---

def plot_catalog_data(catalog_file_path, station_data_path):
    """
    Deprem kataloğu verisini (belirtilen formata göre) okur ve grafikler.
    Event merkezlerini pembe yıldız ile işaretler.
    """
    print("  Katalog verisi okunuyor...")
    station_data_str = _read_file_content(station_data_path)
    if station_data_str is None: return None
    station_locations = parse_station_data(station_data_str)
    print(f"  {len(station_locations)} adet istasyon lokasyonu yüklendi.")
    if not station_locations: print("  [ÖNEMLİ UYARI] İstasyon lokasyonları yüklenemedi!")

    event_data_str = _read_file_content(catalog_file_path)
    if event_data_str is None: return None
    print("  Katalog dosyası içeriği okundu.")

    print("  Katalog verisi ayrıştırılıyor (Format: EVENT/Origin/Picks)...")
    pick_lons_p = []; pick_times_p = []; pick_stations_p = []
    pick_lons_s = []; pick_times_s = []; pick_stations_s = []
    events = {}
    current_event_id = None
    line_count = 0; event_block_count = 0; origin_line_count = 0; pick_count_parsed = 0
    known_station_prefixes = list(station_locations.keys())

    # Regex desenleri
    datetime_pattern = re.compile(r'(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}(\.\d{1,})?)')
    phase_pattern = re.compile(r'\b(P[gn]?|S[gn]?)\b', re.IGNORECASE)
    # <<< DÜZELTME: Lat/Lon pattern daha esnek boşluklar ve N/E sonrası kontrol >>>
    origin_latlon_pattern = re.compile(r'(\d+\.\d+)\s*N\s+(\d+\.\d+)\s*E') # Örn: 40.5880N  29.1142E

    for line in io.StringIO(event_data_str):
        line_count += 1
        line = line.strip()
        if not line: continue

        # EVENT Satırı
        if line.startswith("EVENT "):
            parts = line.split(); current_event_id = parts[1] if len(parts) > 1 else None
            if current_event_id:
                 if current_event_id not in events: events[current_event_id] = {'picks': []}; event_block_count += 1
            else: print(f"    Satır {line_count}: Hatalı EVENT satırı: {line}"); current_event_id = None
            continue

        if current_event_id is None or current_event_id not in events: continue

        # Event Detay Satırı (Origin)
        dt_match_origin = datetime_pattern.search(line) # Satırın herhangi bir yerinde zaman ara
        latlon_match = origin_latlon_pattern.search(line) # Satırın herhangi bir yerinde Lat/Lon ara

        # <<< DÜZELTME: Koşulu sadece eşleşmelerin varlığına bağla >>>
        if dt_match_origin and latlon_match:
             # Muhtemelen origin satırı
             origin_line_count_before = origin_line_count # Başarıyı kontrol için
             try:
                 event_time_str = dt_match_origin.group(1)
                 try: event_datetime = datetime.datetime.strptime(event_time_str, "%Y/%m/%d %H:%M:%S.%f")
                 except ValueError: event_datetime = datetime.datetime.strptime(event_time_str, "%Y/%m/%d %H:%M:%S")
                 event_datetime = event_datetime.replace(tzinfo=pytz.UTC)

                 # latitude = float(latlon_match.group(1))
                 event_lon = float(latlon_match.group(2)) # Boylam

                 # Event kaydını güncelle
                 events[current_event_id]['event_time'] = event_datetime
                 events[current_event_id]['event_lon'] = event_lon
                 origin_line_count += 1 # Başarıyla işlendi, sayacı artır
                 # print(f"      Origin bilgisi {current_event_id} için kaydedildi: Time={event_datetime}, Lon={event_lon}")

             except (ValueError, IndexError, AttributeError) as e:
                 # Eğer zaman veya konum ayrıştırılamazsa sayaç artmaz
                 print(f"    Satır {line_count}: Event Origin satırı (eşleşme bulundu ama) ayrıştırılamadı: {line} - Hata: {e}")

             # Bu satır origin ise pick olamaz, sonraki satıra geç
             if origin_line_count > origin_line_count_before: # Eğer origin başarıyla işlendiyse atla
                 continue
             # else: # Tarihle başlıyor, Lat/Lon var ama zaman formatı uymuyor? Nadir olmalı.
             #    print(f"    Satır {line_count}: Origin gibi ama zaman formatı ({datetime_pattern}) eşleşmedi: {line}")


        # Pick Satırı (Kod aynı kalır)
        found_station = None; station_name = ""
        for station_code in known_station_prefixes:
            if line.startswith(station_code) and (len(line) == len(station_code) or line[len(station_code)].isspace()):
                found_station = True; station_name = station_code; break
        if found_station:
            phase_str = None; pick_datetime = None; pick_lon = None
            phase_match = phase_pattern.search(line); datetime_match = datetime_pattern.search(line)
            if phase_match and datetime_match:
                phase_full = phase_match.group(1).upper(); phase_str = 'P' if phase_full.startswith('P') else 'S'
                time_str = datetime_match.group(1)
                try:
                    pick_datetime = datetime.datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S.%f")
                except ValueError:
                     try: pick_datetime = datetime.datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S")
                     except ValueError as time_err: print(f"      Satır {line_count}: Pick zamanı ayrıştırma hatası ({phase_str}): {time_err}..."); pick_datetime = None
                if pick_datetime: pick_datetime = pick_datetime.replace(tzinfo=pytz.UTC)

            if phase_str and pick_datetime:
                if station_name in station_locations: pick_lon = station_locations[station_name]['lon']
                else: pick_lon = None
                if pick_lon is not None:
                    pick_count_parsed += 1
                    pick_info = {'phase': phase_str,'time': pick_datetime,'lon': pick_lon,'station': station_name}
                    if phase_str == 'P': pick_lons_p.append(pick_lon); pick_times_p.append(pick_datetime); pick_stations_p.append(station_name)
                    else: pick_lons_s.append(pick_lon); pick_times_s.append(pick_datetime); pick_stations_s.append(station_name)
                    if current_event_id in events: events[current_event_id]['picks'].append(pick_info)


    # Ayrıştırma Özeti
    print(f"  Ayrıştırma tamamlandı. Satır: {line_count}, EventBlok: {event_block_count}, OriginSatır: {origin_line_count}") # Origin sayacını yazdır
    print(f"  Başarıyla Ayrıştırılan Pick Sayısı: {pick_count_parsed} (P: {len(pick_times_p)}, S: {len(pick_times_s)})")
    valid_event_count = len([e for e in events.values() if e.get('event_time') and e.get('event_lon') is not None])
    print(f"  Grafiklenecek Event Merkezi Sayısı: {valid_event_count}") # Bu sayının artık > 0 olması beklenir

    # ---- Grafik Oluşturma ----
    fig = go.Figure()
    has_data_to_plot = False # Grafiklenecek anlamlı veri var mı?

    # P Fazları
    if pick_times_p:
        has_data_to_plot = True
        hover_texts_p = [f"Faz: P<br>İstasyon: {st}<br>Zaman: {dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}<br>Boylam: {lon:.4f}" for st, dt, lon in zip(pick_stations_p, pick_times_p, pick_lons_p)]
        fig.add_trace(go.Scatter(x=pick_times_p, y=pick_lons_p, mode='markers', marker=dict(color='blue', size=8, symbol='circle', line=dict(color='black', width=1)), name='P Fazı', hoverinfo='text', text=hover_texts_p, legendgroup="picks"))

    # S Fazları
    if pick_times_s:
        has_data_to_plot = True
        hover_texts_s = [f"Faz: S<br>İstasyon: {st}<br>Zaman: {dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}<br>Boylam: {lon:.4f}" for st, dt, lon in zip(pick_stations_s, pick_times_s, pick_lons_s)]
        fig.add_trace(go.Scatter(x=pick_times_s, y=pick_lons_s, mode='markers', marker=dict(color='red', size=8, symbol='x', line=dict(color='black', width=1)), name='S Fazı', hoverinfo='text', text=hover_texts_s, legendgroup="picks"))

    # Event Merkezleri (Pembe Yıldız)
    event_times = []; event_lons = []; event_texts = []; processed_events_for_lines = {}
    for eid, edata in events.items():
        if edata.get('event_time') and edata.get('event_lon') is not None:
            has_data_to_plot = True
            event_times.append(edata['event_time']); event_lons.append(edata['event_lon'])
            event_texts.append(f"Katalog Event ID: {eid}<br>Zaman: {edata['event_time'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}<br>Boylam: {edata['event_lon']:.4f}")
            processed_events_for_lines[eid] = edata
    if event_times:
        fig.add_trace(go.Scatter(
            x=event_times, y=event_lons, mode='markers',
            marker=dict(color='magenta', size=12, symbol='star', line=dict(color='black', width=1)),
            name='Katalog Event Merkezleri', hoverinfo='text', text=event_texts,
            legendgroup="events"
        ))

    # Pickleri Event Bazında Birleştiren Çizgiler
    # ... (Çizgi kodu aynı kalır) ...
    for eid, edata in processed_events_for_lines.items(): #...
        if 'picks' in edata and len(edata['picks']) > 1: #...
            picks = sorted(edata['picks'], key=lambda x: x['time']); #...
            pick_times_line = [p['time'] for p in picks]; pick_lons_line = [p['lon'] for p in picks]; #...
            fig.add_trace(go.Scatter(x=pick_times_line, y=pick_lons_line, mode='lines', line=dict(color='rgba(128,128,128,0.5)', width=1, dash='dot'), showlegend=False, hoverinfo='none')) #...

    # Veri yoksa uyarı
    if not has_data_to_plot:
        print("  Uyarı: Katalogdan grafiklenecek veri bulunamadı.")
        fig.add_annotation(text="Katalogdan Çizilecek Veri Bulunamadı", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="red"))

    # Grafik Düzeni
    # ... (Layout kodu aynı kalır) ...
    fig.update_layout(title="Deprem Katalog Verisi: Zaman-Boylam Dağılımı", xaxis_title="Zaman (UTC)", yaxis_title="Boylam (°)", hovermode="closest", legend=dict(title="Veri Türü", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), height=300, template="plotly_white", margin=dict(l=50, r=40, t=80, b=40))
    fig.update_xaxes(tickformat='%Y-%m-%d\n%H:%M:%S')

    return fig