import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import nearest_points


def load_data():
    """Загружает объединённые данные о спортобъектах, медучреждениях и остановках."""
    sport = gpd.read_file("data/processed/sport_all.geojson")
    med = gpd.read_file("data/processed/med_all.geojson")
    stops = gpd.read_file("data/processed/transport_stops.geojson")

    # Убедимся, что всё в одном CRS
    sport = sport.to_crs("EPSG:4326")
    med = med.to_crs("EPSG:4326")
    stops = stops.to_crs("EPSG:4326")

    return sport, med, stops


def find_nearest_objects(point: Point, gdf_med: gpd.GeoDataFrame, gdf_stops: gpd.GeoDataFrame):
    """
    Находит:
    - расстояние от sport до ближайшего мед. учреждения (direct_dist)
    - ближайшую остановку и расстояние до неё (to_stop_dist)
    - расстояние от этой остановки до ближайшего мед. учреждения (via_stop_dist)
    """
    # Преобразуем всё в метры
    crs = "EPSG:3857"
    gdf_med = gdf_med.to_crs(crs)
    gdf_stops = gdf_stops.to_crs(crs)
    gdf_point = gpd.GeoSeries([point], crs="EPSG:4326").to_crs(crs)
    point_m = gdf_point.iloc[0]

    # Расстояние напрямую до медучреждения
    gdf_med["dist"] = gdf_med.geometry.distance(point_m)
    nearest_med = gdf_med.loc[gdf_med["dist"].idxmin()]
    direct_dist = float(nearest_med["dist"])

    # Расстояние до ближайшей остановки
    gdf_stops["dist"] = gdf_stops.geometry.distance(point_m)
    nearest_stop = gdf_stops.loc[gdf_stops["dist"].idxmin()]
    to_stop_dist = float(nearest_stop["dist"])

    # Расстояние от остановки до ближайшего медучреждения
    gdf_med["stop_dist"] = gdf_med.geometry.distance(nearest_stop.geometry)
    nearest_med_via_stop = gdf_med.loc[gdf_med["stop_dist"].idxmin()]
    via_stop_dist = float(nearest_med_via_stop["stop_dist"])

    return direct_dist, via_stop_dist, to_stop_dist, nearest_med, nearest_stop


def find_access(point: Point, med_gdf: gpd.GeoDataFrame, stops_gdf: gpd.GeoDataFrame):
    """
    Оценивает доступность для заданной точки:
    - если медучреждение в пределах 250 м — зелёный
    - если ближайшая остановка в пределах 250 м и от неё до медучреждения < 1000 м — жёлтый
    - иначе — красный
    """
    # Прямо до медучреждения
    nearest_med, dist_to_med = get_nearest(med_gdf, point)
    if dist_to_med <= 250:
        return "green", nearest_med, None, None

    # Ищем ближайшую остановку
    nearest_stop, dist_to_stop = get_nearest(stops_gdf, point)
    if dist_to_stop > 250:
        return "red", None, nearest_stop, None

    # От остановки до медучреждения
    stop_point = nearest_stop.geometry
    med_from_stop, dist_med_from_stop = get_nearest(med_gdf, stop_point)

    if dist_med_from_stop <= 1000:
        return "yellow", med_from_stop, nearest_stop, dist_med_from_stop
    else:
        return "red", med_from_stop, nearest_stop, dist_med_from_stop
