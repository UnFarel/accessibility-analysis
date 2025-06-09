import pandas as pd
import ast

df = pd.read_csv("data/raw/sport_629.csv")

print("→ Первое значение:")
print(df.loc[0, "geoData"])
print("→ Тип:", type(df.loc[0, "geoData"]))

try:
    parsed = ast.literal_eval(df.loc[0, "geoData"])
    print("→ После ast.literal_eval:", parsed)
    print("→ Тип:", type(parsed))
except Exception as e:
    print("→ Ошибка парсинга:", e)
