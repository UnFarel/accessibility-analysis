import streamlit as st
from streamlit_folium import st_folium
import folium
import geopandas as gpd
import pandas as pd
import requests
import os
from shapely.geometry import Point
from dotenv import load_dotenv

st.set_page_config(layout="wide")


@st.cache_data
def load_data():
    sports = gpd.read_file("data/processed/sport_all.geojson")
    sports = sports[pd.notnull(sports["global_id"])].copy()
    sports["global_id"] = sports["global_id"].astype(int)
    return sports.to_crs("EPSG:4326")


sports = load_data()
load_dotenv()


def draw_map():
    m = folium.Map(location=[55.75, 37.6], zoom_start=11, control_scale=True)
    for _, row in sports.iterrows():
        gid = row["global_id"]
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=6,
            color="gray",
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(f"ID: {gid}", max_width=200),
            tooltip=f"ID: {gid}"
        ).add_to(m)
    return m


st.title("🧭 Проверка транспортной доступности спортобъектов Москвы")
st.markdown("Кликните на серую точку на карте, чтобы узнать, насколько хорошо этот спортобъект обеспечен медицинской инфраструктурой.")

with st.container():
    map_output = st_folium(draw_map(), width=1000, height=600)

if map_output and map_output.get("last_clicked"):
    clicked = map_output["last_clicked"]
    click_point = Point(clicked["lng"], clicked["lat"])

    st.markdown("---")
    st.subheader("📍 Результаты анализа")
    st.info("🔄 Определяем ближайший спортобъект и отправляем запрос...")

    sports_proj = sports.to_crs("EPSG:3857")
    click_proj = gpd.GeoSeries(
        [click_point], crs="EPSG:4326").to_crs("EPSG:3857")
    sports_proj["dist"] = sports_proj.geometry.distance(click_proj.iloc[0])
    nearest_id = sports_proj.loc[sports_proj["dist"].idxmin(), "global_id"]
    gid = int(nearest_id)

    st.write(f"**ID ближайшего объекта:** `{gid}`")

    try:
        response = requests.get(
            f"https://app-back-bk00.onrender.com/predict?sport_id={gid}")
        result = response.json()

        if not isinstance(result, dict):
            st.error("❌ API вернул неожиданный формат.")
        elif "status" not in result:
            st.error("⚠️ В ответе отсутствует ключ 'status'.")
        else:
            col1, col2 = st.columns([1, 2])

            with col1:
                status_color = {
                    "green": "🟢 Зелёный — рядом есть медучреждение",
                    "yellow": "🟡 Желтый — есть путь через остановку",
                    "red": "🔴 Красный — доступ ограничен"
                }
                st.markdown("### 🏁 Статус доступности:")
                st.markdown(
                    f"**{status_color.get(result['status'], result['status'])}**")

            with col2:
                distances = result.get("distances", {})
                st.markdown("### 📏 Расстояния:")
                st.markdown(f"""
                - До медучреждения напрямую: `{distances.get('direct', '–')} м`  
                - До ближайшей остановки: `{distances.get('to_stop', '–')} м`  
                - От остановки до медучреждения: `{distances.get('via_stop', '–')} м`
                """)

            if "paths" in result and result["paths"]:
                st.markdown("### 🧩 Детали маршрутов:")
                for path in result["paths"]:
                    st.markdown(
                        f"- `{path['type']}` — `{path['distance_m']} м`")

    except Exception as e:
        st.error(f"💥 Ошибка при обращении к API: {e}")
