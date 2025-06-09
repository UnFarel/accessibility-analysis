import pandas as pd
import geopandas as gpd
import joblib
import os

# === Пути ===
MODEL_PATH = "/models/random_forest_accessibility.pkl"
FEATURES_PATH = "/data/processed/features.csv"
OUTPUT_PATH = "/data/processed/accessible_predicted.geojson"

# === Загрузка модели ===
print("[INFO] Загружаем модель...")
model = joblib.load(MODEL_PATH)

# === Загрузка данных ===
print("[INFO] Загружаем признаки...")
df = pd.read_csv(FEATURES_PATH)

# === Подготовка признаков ===
features = df.select_dtypes(include=["int64", "float64"])
X = features.copy()

# === Предсказание ===
print("[INFO] Делаем предсказание...")
df["predicted_accessible"] = model.predict(X)

# === Геопривязка: загрузим sport_629 и sport_893 и объединим ===
gdf_629 = gpd.read_file("/data/processed/sport_629.geojson")
gdf_893 = gpd.read_file("/data/processed/sport_893.geojson")
gdf_all = pd.concat([gdf_629, gdf_893], ignore_index=True)

# Сопоставим по глобальному ID
gdf_all["global_id"] = gdf_all["global_id"].astype(str)
df["sport_global_id"] = df["sport_global_id"].astype(str)

gdf_merged = gdf_all.merge(df, left_on="global_id", right_on="sport_global_id")

# === Сохраняем результат ===
print(f"[INFO] Сохраняем в {OUTPUT_PATH}...")
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
gdf_merged.to_file(OUTPUT_PATH, driver="GeoJSON")
print(f"[DONE] Предсказания сохранены: {len(gdf_merged)} объектов.")
