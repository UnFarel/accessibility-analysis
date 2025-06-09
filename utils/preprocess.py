import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import os
import ast


def extract_coordinates(row):
    geo = row.get("geoData")
    if not isinstance(geo, dict):
        return None

    coords = geo.get("coordinates")

    # Попытка распаковать: [[[lon, lat]]] → [lon, lat]
    if (
        isinstance(coords, list)
        and len(coords) > 0
        and isinstance(coords[0], list)
        and len(coords[0]) > 0
        and isinstance(coords[0][0], list)
        and len(coords[0][0]) == 2
    ):
        lon, lat = coords[0][0]
        return Point(lon, lat)

    print("[DEBUG] Неизвестный формат координат:", coords)
    return None


def safe_parse_geo(val):
    try:
        return ast.literal_eval(val)
    except Exception:
        return {}


def clean_and_convert(input_path, output_path):
    print(f"[INFO] Обработка: {input_path}")

    def safe_parse_geo(val):
        try:
            return ast.literal_eval(val)
        except Exception:
            return {}

    df = pd.read_csv(input_path)
    if "geoData" not in df.columns:
        print(f"[WARN] Нет поля geoData в {input_path}")
        return None

    df["geoData"] = df["geoData"].apply(safe_parse_geo)
    df["geometry"] = df.apply(extract_coordinates, axis=1)
    df = df[df["geometry"].notnull()]

    if df.empty:
        print(f"[WARN] Нет валидных координат в {input_path}")
        return None

    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    gdf.to_file(output_path, driver="GeoJSON")
    print(f"[INFO] Сохранено: {output_path} ({len(gdf)} объектов)")
    return gdf


def parse_geo(row):
    try:
        geo = ast.literal_eval(row["geoData"])
        if isinstance(geo, dict) and "coordinates" in geo:
            coords = geo["coordinates"]
            if isinstance(coords, list) and len(coords) == 2:
                return Point(coords[0], coords[1])
    except Exception as e:
        print(f"[DEBUG] Ошибка парсинга: {e}")
    return None


def clean_transport_stops(input_path, output_path):
    print(f"[INFO] Обработка: {input_path}")
    df = pd.read_csv(input_path)

    if "geoData" not in df.columns:
        print(f"[ERROR] Нет поля geoData в {input_path}")
        return None

    df["geometry"] = df.apply(parse_geo, axis=1)
    df = df[df["geometry"].notnull()]

    if df.empty:
        print(f"[WARN] Нет валидных координат в {input_path}")
        return None

    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    gdf.to_file(output_path, driver="GeoJSON")
    print(f"[INFO] Сохранено: {output_path} ({len(gdf)} объектов)")
    return gdf
