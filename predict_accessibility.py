from flask import Flask, request, jsonify
from shapely.geometry import mapping
from utils import load_data, find_nearest_objects
import joblib
import pandas as pd
import numpy as np

app = Flask(__name__)

# === ЗАГРУЗКА ДАННЫХ И МОДЕЛИ ===
print("[INFO] Загружаем данные и модель...")
gdf_sport, gdf_med, gdf_stops = load_data()

model_data = joblib.load("models/accessibility_classifier.pkl")
model = model_data["model"]
label_encoder = model_data["label_encoder"]

print(
    f"[INFO] Загружено: {len(gdf_sport)} спортобъектов, {len(gdf_med)} медучреждений, {len(gdf_stops)} остановок")


@app.route("/predict", methods=["GET"])
def predict_access():
    sport_id = request.args.get("sport_id")
    if not sport_id:
        return jsonify({"error": "sport_id обязателен"}), 400

    try:
        sport_id = int(sport_id)
    except ValueError:
        return jsonify({"error": "Некорректный sport_id"}), 400

    match = gdf_sport[gdf_sport["global_id"] == sport_id]
    if match.empty:
        return jsonify({"error": f"Спортобъект с id={sport_id} не найден"}), 404

    point = match.geometry.values[0]

    # === Находим расстояния и объекты
    direct_dist, via_stop_dist, to_stop_dist, nearest_med, nearest_stop = find_nearest_objects(
        point, gdf_med, gdf_stops
    )

    # === Модель предсказывает цвет
    X_input = pd.DataFrame([[direct_dist, via_stop_dist, to_stop_dist]],
                           columns=["direct_med_dist", "via_stop_dist", "nearest_stop_dist"])
    label_encoded = model.predict(X_input)[0]
    color = label_encoder.inverse_transform([label_encoded])[0]

    # === Сбор ответа
    response = {
        "status": color,
        "distances": {
            "direct": direct_dist,
            "via_stop": via_stop_dist,
            "to_stop": to_stop_dist
        },
        "paths": []
    }

    if color == "green" and nearest_med is not None:
        response["paths"].append({
            "from": mapping(point),
            "to": mapping(nearest_med.geometry),
            "type": "direct",
            "distance_m": direct_dist
        })
    elif color in {"yellow", "red"}:
        if nearest_stop is not None:
            response["paths"].append({
                "from": mapping(point),
                "to": mapping(nearest_stop.geometry),
                "type": "to_stop",
                "distance_m": to_stop_dist
            })
        if nearest_med is not None:
            response["paths"].append({
                "from": mapping(nearest_stop.geometry),
                "to": mapping(nearest_med.geometry),
                "type": "stop_to_med",
                "distance_m": via_stop_dist
            })

    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True)
