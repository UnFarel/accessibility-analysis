import streamlit as st
from streamlit_folium import st_folium
import folium
import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Point

st.set_page_config(layout="wide")


@st.cache_data
def load_data():
    sports = gpd.read_file("data/processed/sport_all.geojson")
    meds = gpd.read_file("data/processed/med_all.geojson")
    stops = gpd.read_file("data/processed/transport_stops.geojson")

    sports = sports[pd.notnull(sports["global_id"])].copy()
    meds = meds[pd.notnull(meds["global_id"])].copy()
    stops = stops[pd.notnull(stops["global_id"])].copy()

    sports["global_id"] = sports["global_id"].astype(int)
    meds["global_id"] = meds["global_id"].astype(int)
    stops["global_id"] = stops["global_id"].astype(int)

    sports = sports.sample(10, random_state=42).reset_index(drop=True)

    return sports.to_crs("EPSG:4326"), meds.to_crs("EPSG:4326"), stops.to_crs("EPSG:4326")


sports, meds, stops = load_data()


def draw_map(clicked_gid=None, result=None, visible_sports=None):
    m = folium.Map(location=[55.75, 37.6], zoom_start=11, control_scale=True)
    sport_layer = folium.FeatureGroup(name="Спортобъекты").add_to(m)
    med_layer = folium.FeatureGroup(name="Медучреждения").add_to(m)
    stop_layer = folium.FeatureGroup(name="Остановки").add_to(m)

    color_map = {"green": "green", "yellow": "orange", "red": "red"}

    if visible_sports is None:
        visible_sports = sports

    for _, row in visible_sports.iterrows():
        gid = row["global_id"]
        color = "gray"
        radius = 6
        if result and gid == clicked_gid:
            color = color_map.get(result["status"], "gray")
            radius = 8

        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            tooltip=f"ID: {gid}",
            popup=folium.Popup(f"ID: {gid}")  # ❗️ Это нужно для click_data
        ).add_to(sport_layer)

    if result and clicked_gid:
        clicked = sports[sports["global_id"] == clicked_gid].iloc[0]
        lat, lon = clicked.geometry.y, clicked.geometry.x
        status = result.get("status", "unknown")
        color = color_map.get(status, "gray")

        folium.Circle(
            location=[lat, lon],
            radius=250,
            color=color,
            fill=True,
            fill_opacity=0.2,
            weight=2,
            tooltip="Буфер 250 м"
        ).add_to(m)

        if status in {"green", "yellow"}:
            for path in result.get("paths", []):
                to_point = path.get("to", {}).get("coordinates", [])
                if len(to_point) != 2:
                    continue
                lat2, lon2 = to_point[1], to_point[0]

                if path["type"].startswith("stop"):
                    icon = folium.CustomIcon(
                        "assets/icons/bus.png", icon_size=(24, 24))
                    folium.Marker(
                        location=[lat2, lon2],
                        icon=icon,
                        tooltip="Остановка поблизости"
                    ).add_to(stop_layer)
                elif path["type"].startswith("direct") or path["type"].startswith("stop_to_med"):
                    icon = folium.CustomIcon(
                        "assets/icons/medicine.png", icon_size=(24, 24))
                    folium.Marker(
                        location=[lat2, lon2],
                        icon=icon,
                        tooltip="Медучреждение поблизости"
                    ).add_to(med_layer)

    return m


# === ОТРИСОВКА ПЕРВОЙ КАРТЫ ===
click_data = st_folium(
    draw_map(),
    width=1400,
    height=800,
    returned_objects=["last_clicked"],  # обязательно
)

# === ОТЛАДКА ===
st.write("📍 DEBUG click_data:", click_data)

# === ОБРАБОТКА КЛИКА ===
if click_data and click_data.get("last_clicked"):
    clicked_point = click_data["last_clicked"]
    click_geom = Point(clicked_point["lng"], clicked_point["lat"])
    st.info("🟡 Обнаружен клик. Определяем ближайший спортобъект...")

    sports_proj = sports.to_crs("EPSG:3857")
    click_proj = gpd.GeoSeries(
        [click_geom], crs="EPSG:4326").to_crs("EPSG:3857")
    sports_proj["dist"] = sports_proj.geometry.distance(click_proj.iloc[0])
    nearest_id = sports_proj.loc[sports_proj["dist"].idxmin()]["global_id"]
    gid = int(nearest_id)

    st.write(f"📍 Ближайший sport_id: {gid}")

    try:
        response = requests.get(
            f"http://localhost:5000/predict?sport_id={gid}")
        result = response.json()

        st.write("🔎 Ответ от API:", result)

        if not isinstance(result, dict):
            st.error("❌ API вернул неожиданный формат (не словарь).")
        elif "status" not in result:
            st.error(
                "⚠️ API не вернул ключ 'status'. Проверь predict_accessibility.py")
        else:
            st.success(f"✅ Статус доступности: **{result['status'].upper()}**")

            if "distances" in result:
                st.markdown(f"""
                **Расстояния**:
                - Прямо до медучреждения: {result['distances'].get('direct', '–')} м  
                - До остановки: {result['distances'].get('to_stop', '–')} м  
                - От остановки до медучреждения: {result['distances'].get('via_stop', '–')} м
                """)

            st_folium(draw_map(clicked_gid=gid, result=result,
                      visible_sports=sports), width=1400, height=800)

    except Exception as e:
        st.error(f"💥 Ошибка при обращении к API: {e}")
