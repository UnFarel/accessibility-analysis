import json
import os

def get_secret(key: str) -> str:
    with open('.secrets.json', 'r', encoding='utf-8') as f:
        secrets = json.load(f)
    return secrets.get(key)
