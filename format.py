import json

# Input and output file paths
input_file = "results/compiled_last10.json"
output_file = "predictions_dev_current.txt"

# Read the JSON data
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# Open the output file for writing
with open(output_file, "w", encoding="utf-8") as out:
    for idx, item in enumerate(data, 1):
        out.write(f"Entry {idx}:\n")
        out.write(f"Instance ID: {item.get('instance_id', 'N/A')}\n")
        out.write(f"Model Name/Path: {item.get('model_name_or_path', 'N/A')}\n")
        out.write("Model Patch:\n")
        # Remove code block markers if present
        patch = item.get("model_patch", "").strip("`")
        out.write(patch + "\n")
        out.write("-" * 40 + "\n\n")
        out.write("Expected Patch:\n")
        patch = item.get("expected_patch", "").strip("`")
        out.write(patch + "\n")
        out.write("-" * 40 + "\n\n")

print(f"Formatted output written to {output_file}")
