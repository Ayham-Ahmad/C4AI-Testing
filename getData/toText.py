import json
import os

source_folder_path = "data/W3_Tutorials_All"
dist_folder_path = "data/W3_Tutorials_All_txt"

# Make sure destination folder exists
os.makedirs(dist_folder_path, exist_ok=True)

for filename in os.listdir(source_folder_path):
    source_file_path = os.path.join(source_folder_path, filename)
    base_name, _ = os.path.splitext(filename)  # remove .json
    dist_file_path = os.path.join(dist_folder_path, f"{base_name}.txt")

    if os.path.isfile(source_file_path):
        with open(source_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        with open(dist_file_path, "w", encoding="utf-8") as out_f:
            for section, snippets in data.items():
                if isinstance(snippets, list):
                    for item in snippets:
                        if isinstance(item, str):
                            out_f.write(item.strip() + "\n\n")
                        elif isinstance(item, dict):
                            # flatten dict values into text
                            for k, v in item.items():
                                if isinstance(v, str):
                                    out_f.write(f"{k}: {v.strip()}\n")
                                elif isinstance(v, list):
                                    for sub in v:
                                        if isinstance(sub, str):
                                            out_f.write(sub.strip() + "\n")
                            out_f.write("\n") 

        print(f"Converted -> {base_name} to .txt")

print("✅ Saved all JSON files as TXT")
