import pandas as pd
import re
import json

def extract_location_and_value(cell_content):
    """
    Extract location citations from cell content.
    
    Location patterns: (pg X, description) or (pg X–Y, description) or (pg X)
    Returns: {"value": cleaned_value, "location": location_string}
    """
    if pd.isna(cell_content):
        return {"value": "", "location": ""}
    
    # Convert to string
    cell_str = str(cell_content).strip()
    
    if not cell_str:
        return {"value": "", "location": ""}
    
    # Pattern to match location citations like (pg3, text) or (pg3–4, Results; Table 2)
    # This matches: (pg + digits/ranges + optional comma and description + )
    location_pattern = r'\(pg[\d–\-]+(?:\s*,\s*[^)]+)?\)'
    
    # Find all locations
    locations = re.findall(location_pattern, cell_str)
    
    # Remove location citations from the value
    cleaned_value = cell_str
    for loc in locations:
        cleaned_value = cleaned_value.replace(loc, '')
    
    # Clean up whitespace
    cleaned_value = re.sub(r'\s+', ' ', cleaned_value).strip()
    
    # Join all locations with semicolon if multiple
    location_str = '; '.join(locations) if locations else ""
    
    return {
        "value": cleaned_value,
        "location": location_str
    }


def clean_excel_to_json(excel_path, output_path):
    """
    Read Excel file, extract locations from values, output readable JSON.
    """
    print(f"Reading Excel file: {excel_path}")
    df = pd.read_excel(excel_path)
    
    print(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    
    # Get column names
    columns = df.columns.tolist()
    
    # Process each row
    data = []
    for idx, row in df.iterrows():
        row_dict = {}
        for col in columns:
            cell_content = row[col]
            extracted = extract_location_and_value(cell_content)
            row_dict[col] = extracted
        data.append(row_dict)
    
    # Create output structure (just the data array)
    output = {
        "data": data
    }
    
    # Write to JSON
    print(f"\nWriting to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Statistics
    total_cells = df.shape[0] * df.shape[1]
    cells_with_locations = sum(
        1 for row in data for col, cell in row.items() if cell["location"]
    )
    
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total rows: {df.shape[0]}")
    print(f"Total columns: {df.shape[1]}")
    print(f"Total cells: {total_cells}")
    print(f"Cells with locations: {cells_with_locations} ({cells_with_locations/total_cells*100:.1f}%)")
    print(f"Cells without locations: {total_cells - cells_with_locations}")
    
    # Show a few examples
    print(f"\n{'='*60}")
    print(f"EXAMPLES (First study - row 1, showing cells with locations)")
    print(f"{'='*60}")
    # Row 1 (skip header row which is row 0)
    row_1 = data[1]
    count = 0
    for col in columns:
        if count >= 10:
            break
        cell = row_1[col]
        if cell["value"] or cell["location"]:
            print(f"\n{col}:")
            val_display = cell['value'][:100] if len(cell['value']) > 100 else cell['value']
            print(f"  Value: {val_display}")
            print(f"  Location: {cell['location']}")
            if cell["location"]:
                count += 1
    
    return output


if __name__ == "__main__":
    excel_path = "/mnt/data1/nahuja11/Mayo/CoRal-Map-Make/dataset/Manual_Benchmark_GoldTable.xlsx"
    output_path = "/mnt/data1/nahuja11/Mayo/CoRal-Map-Make/dataset/Manual_Benchmark_GoldTable_cleaned.json"
    
    clean_excel_to_json(excel_path, output_path)
