import json

# Load your JSON file
with open("W3Results2.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Extract only the "text" fields
only_text = {}

for section, tutorials in data.items():
    only_text[section] = []
    for tutorial in tutorials:
        for snippet in tutorial.get("code_snippets", []):
            if "text" in snippet:
                only_text[section].append(snippet["text"])

# Save to a new file
with open("W3Results_Codes_only.json", "w", encoding="utf-8") as f:
    json.dump(only_text, f, indent=2, ensure_ascii=False)

print("✅ Extracted text-only snippets into W3Results_text_only.json")
