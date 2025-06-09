import json
import os
import requests
import pandas as pd
from tqdm import tqdm


# Загрузка API-ключа из .secrets.json
def get_api_key():
    secrets_path = ".secrets.json"
    if not os.path.exists(secrets_path):
        raise FileNotFoundError(f"Файл {secrets_path} не найден.")
    
    with open(secrets_path, "r", encoding="utf-8") as f:
        secrets = json.load(f)
    
    if "mos_api_key" not in secrets:
        raise KeyError("Ключ 'mos_api_key' отсутствует в .secrets.json")
    
    return secrets["mos_api_key"]


def get_dataset_info(dataset_id, api_key):
    url = f"https://apidata.mos.ru/v1/datasets/{dataset_id}"
    params = {"api_key": api_key}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    raise Exception(f"Ошибка запроса dataset info {dataset_id}: {response.status_code}")


def get_dataset_version(dataset_id, api_key):
    url = f"https://apidata.mos.ru/v1/datasets/{dataset_id}/version"
    params = {"api_key": api_key}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    raise Exception(f"Ошибка запроса dataset version {dataset_id}: {response.status_code}")


def get_dataset_rows(dataset_id, version_number, release_number, api_key, skip=0):
    url = f"https://apidata.mos.ru/v1/datasets/{dataset_id}/rows"
    params = {
        "versionNumber": version_number,
        "releaseNumber": release_number,
        "$top": 500,
        "$skip": skip,
        "api_key": api_key,
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    raise Exception(f"Ошибка запроса dataset rows {dataset_id}: {response.status_code}")


def download_dataset(dataset_id, save_path=None):
    api_key = get_api_key()
    
    print(f"[INFO] Получаем метаинформацию по датасету {dataset_id}")
    info = get_dataset_info(dataset_id, api_key)
    
    print(f"[INFO] Получаем версию датасета")
    version = get_dataset_version(dataset_id, api_key)

    row_count = info.get("ItemsCount", 0)
    if row_count == 0:
        print(f"[WARN] Датасет {dataset_id} пуст или не удалось получить ItemsCount")
    
    v_num = version.get("VersionNumber")
    r_num = version.get("ReleaseNumber")

    all_rows = []
    for offset in tqdm(range(0, row_count, 500), desc=f"Загрузка {dataset_id}"):
        raw = get_dataset_rows(dataset_id, v_num, r_num, api_key, skip=offset)
        rows = [x["Cells"] for x in raw]
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    print(f"[INFO] Загружено {len(df)} строк из датасета {dataset_id}")
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        df.to_csv(save_path, index=False)
        print(f"[INFO] Сохранено в файл: {save_path}")
    
    return df
