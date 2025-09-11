import json

# Load the JSON file with only text snippets
with open("W3Results_Codes_only.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Open a .txt file for writing all codes
with open("W3School_codes_only.txt", "w", encoding="utf-8") as f:
    for section, snippets in data.items():
        for code in snippets:
            f.write(code.strip())  
            # separator between snippets for clarity

print("✅ Saved all pure code snippets to W3School_codes_only.txt")
