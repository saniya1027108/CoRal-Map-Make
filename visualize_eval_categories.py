import pandas as pd

# Read the CSV
df = pd.read_csv("/mnt/data1/nahuja11/Mayo/CoRal-Map-Make/src/table_definitions/Definitions_with_eval_category.csv")

# Create HTML with styling
html = """
<!DOCTYPE html>
<html>
<head>
    <title>Evaluation Categories</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
        }
        .summary {
            background: white;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .summary span {
            display: inline-block;
            margin-right: 30px;
            font-weight: bold;
        }
        .exact_match { background-color: #e3f2fd; }
        .numeric_tolerance { background-color: #fff3e0; }
        .structured_text { background-color: #f3e5f5; }
        
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        th {
            background: #2196F3;
            color: white;
            padding: 12px;
            text-align: left;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .category-cell {
            font-weight: bold;
            padding: 5px 10px;
            border-radius: 3px;
            display: inline-block;
        }
        .filter-buttons {
            margin: 20px 0;
        }
        .filter-btn {
            padding: 8px 15px;
            margin-right: 10px;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-weight: bold;
        }
        .filter-btn.active {
            box-shadow: 0 0 0 2px #2196F3;
        }
    </style>
    <script>
        function filterByCategory(category) {
            const rows = document.querySelectorAll('tbody tr');
            const buttons = document.querySelectorAll('.filter-btn');
            
            // Update button states
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            // Filter rows
            rows.forEach(row => {
                if (category === 'all') {
                    row.style.display = '';
                } else {
                    const rowCategory = row.getAttribute('data-category');
                    row.style.display = rowCategory === category ? '' : 'none';
                }
            });
        }
    </script>
</head>
<body>
    <h1>📊 Evaluation Categories for All Columns</h1>
    
    <div class="summary">
        <span class="exact_match">exact_match: {exact_count}</span>
        <span class="numeric_tolerance">numeric_tolerance: {numeric_count}</span>
        <span class="structured_text">structured_text: {text_count}</span>
        <span>Total: {total_count}</span>
    </div>
    
    <div class="filter-buttons">
        <button class="filter-btn active" style="background: #2196F3; color: white;" onclick="filterByCategory('all')">All</button>
        <button class="filter-btn exact_match" onclick="filterByCategory('exact_match')">exact_match</button>
        <button class="filter-btn numeric_tolerance" onclick="filterByCategory('numeric_tolerance')">numeric_tolerance</button>
        <button class="filter-btn structured_text" onclick="filterByCategory('structured_text')">structured_text</button>
    </div>
    
    <table>
        <thead>
            <tr>
                <th style="width: 5%">#</th>
                <th style="width: 25%">Column Name</th>
                <th style="width: 15%">Label</th>
                <th style="width: 15%">Eval Category</th>
                <th style="width: 40%">Definition</th>
            </tr>
        </thead>
        <tbody>
"""

# Get counts
category_counts = df['eval_category'].value_counts()
html = html.replace('{exact_count}', str(category_counts.get('exact_match', 0)))
html = html.replace('{numeric_count}', str(category_counts.get('numeric_tolerance', 0)))
html = html.replace('{text_count}', str(category_counts.get('structured_text', 0)))
html = html.replace('{total_count}', str(len(df)))

# Add rows
for idx, row in df.iterrows():
    category = row['eval_category']
    html += f"""
            <tr data-category="{category}" class="{category}">
                <td>{idx + 1}</td>
                <td><strong>{row['Column Name']}</strong></td>
                <td>{row['Label']}</td>
                <td><span class="category-cell {category}">{category}</span></td>
                <td style="font-size: 0.9em;">{row['Definition'][:150]}...</td>
            </tr>
    """

html += """
        </tbody>
    </table>
</body>
</html>
"""

# Write to file
output_path = "/mnt/data1/nahuja11/Mayo/CoRal-Map-Make/eval_categories_visualization.html"
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ HTML visualization created: {output_path}")
print(f"\nOpen this file in your browser to view the interactive table.")
