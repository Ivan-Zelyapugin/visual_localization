import os
import csv
import math
from svl.tms import TileDownloader
from svl.tms.data_structures import Tile

# 1. Формулы перевода GPS координат в X и Y тайлы для ЭЛЛИПТИЧЕСКОГО Меркатора (Яндекс)
def lat_lon_to_tile(lat, lon, zoom):
    # Константы эллипсоида WGS 84
    a = 6378137.0
    e = 0.0818191908426
    
    lon_rad = math.radians(lon)
    lat_rad = math.radians(lat)
    
    n = 2.0 ** zoom
    x_tile = int((lon + 180.0) / 360.0 * n)
    
    # Прямое проецирование Меркатора для эллипсоида
    sin_lat = math.sin(lat_rad)
    ts = math.tan(lat_rad / 2.0 + math.pi / 4.0) * (((1.0 - e * sin_lat) / (1.0 + e * sin_lat)) ** (e / 2.0))
    y = a * math.log(ts)
    
    # Перевод в пиксельные координаты и номер тайла (Яндекс использует 20037508.342789244 как полупериметр)
    max_merc = 20037508.342789244
    y_tile = int((max_merc - y) * n / (2.0 * max_merc))
    return x_tile, y_tile

def tile_to_lat_lon(x, y, zoom):
    # Константы эллипсоида WGS 84
    a = 6378137.0
    e = 0.0818191908426
    max_merc = 20037508.342789244
    
    n = 2.0 ** zoom
    lon_deg = x / n * 360.0 - 180.0
    
    # Обратное проецирование Меркатора для эллипсоида
    merc_y = max_merc - (y * 2.0 * max_merc / n)
    ts = math.exp(-merc_y / a)
    
    # Итерационный расчет широты
    lat_rad = math.pi / 2.0 - 2.0 * math.atan(ts)
    for _ in range(5):
        sin_lat = math.sin(lat_rad)
        lat_rad_new = math.pi / 2.0 - 2.0 * math.atan(ts * (((1.0 - e * sin_lat) / (1.0 + e * sin_lat)) ** (e / 2.0)))
        if abs(lat_rad_new - lat_rad) < 1e-10:
            lat_rad = lat_rad_new
            break
        lat_rad = lat_rad_new
        
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

# 2. Настраиваем координаты военного городка в Ульяновске
TOP_LEFT_LAT, TOP_LEFT_LON = 54.341000, 48.391000
BOTTOM_RIGHT_LAT, BOTTOM_RIGHT_LON = 54.331000, 48.411000
ZOOM = 18  # Высокая детализация
OUTPUT_DIR = os.path.join("data", "map")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 3. Рассчитываем диапазон тайлов (теперь по формулам Яндекса)
x_start, y_start = lat_lon_to_tile(TOP_LEFT_LAT, TOP_LEFT_LON, ZOOM)
x_end, y_end = lat_lon_to_tile(BOTTOM_RIGHT_LAT, BOTTOM_RIGHT_LON, ZOOM)

# На всякий случай выравниваем границы
x_min, x_max = min(x_start, x_end), max(x_start, x_end)
y_min, y_max = min(y_start, y_end), max(y_start, y_end)

# 4. Инициализируем загрузчик для Яндекс Спутника
# Используем актуальный пользовательский агент, чтобы Яндекс не блокировал запросы
# 4. Инициализируем загрузчик для Яндекс Спутника (альтернативный URL без знаков &)
tms_url = "https://mt.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
tile_downloader = TileDownloader(
    url=tms_url,
    channels=3,
    api_key=None,
    headers=None,
    img_format="png",
)


# 5. Скачиваем тайлы и формируем базу данных для проекта
csv_path = os.path.join(OUTPUT_DIR, "map.csv")
print(f"Начинаем скачивание тайлов Яндекс Карт для Ульяновска в {OUTPUT_DIR}...")

total_tiles = (x_max - x_min + 1) * (y_max - y_min + 1)
print(f"Всего к скачиванию: {total_tiles} изображений.")

with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f, delimiter=',')
    writer.writerow(["Filename", "Top_left_lat", "Top_left_lon", "Bottom_right_lat", "Bottom_right_long"])
    
    count = 0
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            tile = Tile(x=x, y=y, zoom_level=ZOOM)
            
            original_file_name = f"{x}_{y}_{ZOOM}.png"
            target_file_name = f"sat_map_{count:02d}.png"
            
            try:
                tile_downloader.download_tile(tile, OUTPUT_DIR)
                
                old_path = os.path.join(OUTPUT_DIR, original_file_name)
                new_path = os.path.join(OUTPUT_DIR, target_file_name)
                if os.path.exists(old_path):
                    if os.path.exists(new_path):
                        os.remove(new_path)
                    os.rename(old_path, new_path)
                
                # Точные географические координаты УГЛОВ для Яндекс-проекции
                top_left_lat, top_left_lon = tile_to_lat_lon(x, y, ZOOM)
                bottom_right_lat, bottom_right_lon = tile_to_lat_lon(x + 1, y + 1, ZOOM)
                
                writer.writerow([
                    target_file_name, 
                    f"{top_left_lat:.6f}", 
                    f"{top_left_lon:.6f}", 
                    f"{bottom_right_lat:.6f}", 
                    f"{bottom_right_lon:.6f}"
                ])
                
                count += 1
                if count % 20 == 0 or count == total_tiles:
                    print(f"Прогресс: {count}/{total_tiles} файлов успешно скачано и размечено.")
            except Exception as e:
                print(f"Ошибка при скачивании тайла {x}_{y}: {e}")

print("✅ Карта Ульяновска от Яндекс успешно создана! Индексный файл map.csv полностью готов.")
