import os
import csv
import math
from svl.tms import TileDownloader
from svl.tms.data_structures import Tile

# 1. Формулы перевода GPS координат в X и Y тайлы Меркатора
def lat_lon_to_tile(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x_tile = int((lon + 180.0) / 360.0 * n)
    y_tile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return x_tile, y_tile

def tile_to_lat_lon(x, y, zoom):
    n = 2.0 ** zoom
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

# 2. Настраиваем координаты военного городка в Ульяновске
TOP_LEFT_LAT, TOP_LEFT_LON = 54.341000, 48.391000
BOTTOM_RIGHT_LAT, BOTTOM_RIGHT_LON = 54.331000, 48.411000
ZOOM = 18  # Высокая детализация
OUTPUT_DIR = os.path.join("data", "map")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 3. Рассчитываем диапазон тайлов
x_start, y_start = lat_lon_to_tile(TOP_LEFT_LAT, TOP_LEFT_LON, ZOOM)
x_end, y_end = lat_lon_to_tile(BOTTOM_RIGHT_LAT, BOTTOM_RIGHT_LON, ZOOM)

# На всякий случай выравниваем границы
x_min, x_max = min(x_start, x_end), max(x_start, x_end)
y_min, y_max = min(y_start, y_end), max(y_start, y_end)

# 4. Инициализируем загрузчик по документации (Google Спутник)
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
print(f"Начинаем скачивание тайлов для Ульяновска в {OUTPUT_DIR}...")

total_tiles = (x_max - x_min + 1) * (y_max - y_min + 1)
print(f"Всего к скачиванию: {total_tiles} изображений.")

with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    # Пишем заголовки, которые ожидает SatelliteMapReader
    writer.writerow(["image_name", "latitude", "longitude"])
    
    count = 0
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            tile = Tile(x=x, y=y, zoom_level=ZOOM)
            file_name = f"{x}_{y}_{ZOOM}.png"
            
            # Скачиваем отдельный тайл по документации
            try:
                tile_downloader.download_tile(tile, OUTPUT_DIR)
                
                # Считаем точные географические координаты центра этого фрагмента
                lat, lon = tile_to_lat_lon(x + 0.5, y + 0.5, ZOOM)
                
                # Записываем метаданные
                writer.writerow([file_name, lat, lon])
                count += 1
                if count % 20 == 0 or count == total_tiles:
                    print(f"Прогресс: {count}/{total_tiles} файлов скачано.")
            except Exception as e:
                print(f"Ошибка при скачивании тайла {x}_{y}: {e}")

print("✅ Карта Ульяновска успешно создана! Индексный файл map.csv заполнен.")
