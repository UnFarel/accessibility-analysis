import pandas as pd
import os
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import LabelEncoder

# === Пути ===
INPUT_CSV = "data/processed/training_dataset.csv"
MODEL_PATH = "models/accessibility_classifier.pkl"

# === Шаг 1: Загрузка данных ===
print("[INFO] Загружаем датасет...")
df = pd.read_csv(INPUT_CSV)

# Заполняем пропуски большими числами — считаем, что далеко
df = df.fillna({
    "direct_med_dist": 9999,
    "via_stop_dist": 9999,
    "nearest_stop_dist": 9999
})

# === Шаг 2: Разделение на признаки и целевую переменную ===
X = df[["direct_med_dist", "via_stop_dist", "nearest_stop_dist"]]
y = df["label"]

# Кодируем целевую переменную
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# === Шаг 3: Делим на обучающую и тестовую выборки ===
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
)

# === Шаг 4: Обучение модели ===
print("[INFO] Обучаем RandomForest...")
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# === Шаг 5: Оценка на тестовой выборке ===
y_pred = model.predict(X_test)
print("\n[INFO] Accuracy на тестовой выборке:", accuracy_score(y_test, y_pred))
print("[INFO] Classification report:")
print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))

# === Шаг 6: Кросс-валидация ===
cv_scores = cross_val_score(model, X, y_encoded, cv=5)
print("\n[INFO] Cross-validation accuracy scores:", cv_scores)
print("[INFO] Mean CV accuracy:", cv_scores.mean())

# === Шаг 7: Сохраняем модель и энкодер ===
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
joblib.dump({"model": model, "label_encoder": label_encoder}, MODEL_PATH)
print(f"[DONE] Модель и энкодер сохранены: {MODEL_PATH}")
