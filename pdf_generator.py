# export_generator.py
import os
import csv
import json
from typing import Dict

os.makedirs("uploads", exist_ok=True)

def save_application_csv(app_data: Dict, output_dir: str = "uploads") -> str:
    filename = f"{app_data.get('app_id','app')}.csv"
    path = os.path.join(output_dir, filename)
    # Write CSV (key,value per row)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Field", "Value"])
        for k, v in app_data.items():
            writer.writerow([k, json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v])
    return path

def save_application_json(app_data: Dict, output_dir: str = "uploads") -> str:
    filename = f"{app_data.get('app_id','app')}.json"
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(app_data, f, ensure_ascii=False, indent=2)
    return path


