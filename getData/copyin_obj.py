import os
import json
from pathlib import Path

# Folders
SRC_FOLDER = Path("W3_Tutorials_All")
DST_FOLDER = Path("W3_Tutorials_All copy")

# Ensure target folder exists
if not DST_FOLDER.exists():
    raise FileNotFoundError(f"Target folder {DST_FOLDER} not found.")

# Loop through all JSON files in source folder
for src_file in SRC_FOLDER.glob("*.json"):
    dst_file = DST_FOLDER / src_file.name

    if not dst_file.exists():
        print(f"⚠️ Skipping {src_file.name}, not found in target folder.")
        continue

    # Read source and destination JSONs
    with open(src_file, "r", encoding="utf-8") as f:
        src_data = json.load(f)

    with open(dst_file, "r", encoding="utf-8") as f:
        dst_data = json.load(f)

    # Extract objectives (last element in source JSON)
    if isinstance(src_data, dict) and "objectives" in src_data:
        objectives = src_data["objectives"]
    elif isinstance(src_data, list) and isinstance(src_data[-1], dict) and "objectives" in src_data[-1]:
        objectives = src_data[-1]["objectives"]
    else:
        print(f"❌ No objectives found in {src_file.name}")
        continue

    # Append objectives to target
    if isinstance(dst_data, dict):
        dst_data["objectives"] = objectives
    elif isinstance(dst_data, list):
        dst_data.append({"objectives": objectives})
    else:
        print(f"❌ Unexpected JSON format in {dst_file.name}")
        continue

    # Save back updated JSON
    with open(dst_file, "w", encoding="utf-8") as f:
        json.dump(dst_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated {dst_file.name} with objectives.")
