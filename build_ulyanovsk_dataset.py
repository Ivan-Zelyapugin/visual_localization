import os
import csv
import math
import time
import requests

# 1. ИСПРАВЛЕНО: Формулы СФЕРИЧЕСКОГО Меркатора строго для Google Карт
def lat_lon_to_tile(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x_tile = int((lon + 180.0) / 360.0 * n)
    y_tile = int((1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return x_tile, y_tile

def tile_to_lat_lon(x, y, zoom):
    n = 2.0 ** zoom
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

# 2. Настраиваем точные координаты воинской части связи в Ульяновске
TOP_LEFT_LAT, TOP_LEFT_LON = 54.340735, 48.400038
BOTTOM_RIGHT_LAT, BOTTOM_RIGHT_LON = 54.335231, 48.403521
ZOOM = 18  
OUTPUT_DIR = os.path.join("data", "map")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 3. Рассчитываем диапазон тайлов по формулам Google
x_start, y_start = lat_lon_to_tile(TOP_LEFT_LAT, TOP_LEFT_LON, ZOOM)
x_end, y_end = lat_lon_to_tile(BOTTOM_RIGHT_LAT, BOTTOM_RIGHT_LON, ZOOM)

x_min, x_max = min(x_start, x_end), max(x_start, x_end)
y_min, y_max = min(y_start, y_end), max(y_start, y_end)

# 4. ИСПРАВЛЕНО: Настройка сессии для прямой и безопасной загрузки с Google
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

# 5. Скачиваем тайлы и формируем базу данных для проекта
csv_path = os.path.join(OUTPUT_DIR, "map.csv")
print(f"Начинаем скачивание тайлов Google Карт для Ульяновска в {OUTPUT_DIR}...")

total_tiles = (x_max - x_min + 1) * (y_max - y_min + 1)
print(f"Всего к скачиванию: {total_tiles} изображений.")

# Используем разделитель-запятую для pandas.read_csv в вашем ридере
with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f, delimiter=',')
    writer.writerow(["Filename", "Top_left_lat", "Top_left_lon", "Bottom_right_lat", "Bottom_right_long"])
    
    count = 0
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            target_file_name = f"sat_map_{count:02d}.png"
            file_path = os.path.join(OUTPUT_DIR, target_file_name)
            
            # Ссылка на тайловый сервер Google Спутника
            url = f"https://mt.google.com/vt/lyrs=s&x={x}&y={y}&z={ZOOM}"
            
            try:
                # Скачиваем тайл напрямую, минуя TileDownloader
                response = session.get(url, timeout=10)
                
                if response.status_code != 200:
                    print(f"Ошибка сервера для тайла {x}_{y}: Статус {response.status_code}")
                    continue
                
                with open(file_path, "wb") as img_f:
                    img_f.write(response.content)
                
                # ИСПРАВЛЕНО: Расчет точных географических координат углов по сетке Google
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
                if count % 5 == 0 or count == total_tiles:
                    print(f"Прогресс: {count}/{total_tiles} файлов успешно скачано и размечено.")
                
                time.sleep(0.05)  # Легкая задержка для стабильности соединения
                
            except Exception as e:
                print(f"Ошибка при скачивании тайла {x}_{y}: {e}")

print("✅ Карта воинской части от Google успешно создана! Индексный файл map.csv полностью готов.")
