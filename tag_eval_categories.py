import pandas as pd
import re

def assign_eval_category(column_name, definition):
    """
    Assign evaluation category based on column name and definition.
    
    Categories:
    - exact_match: IDs, categorical, binary, discrete counts
    - numeric_tolerance: Continuous numbers, percentages, ages, durations, rates
    - structured_text: Descriptions, regimens, treatments, endpoints
    """
    col_lower = column_name.lower()
    def_lower = definition.lower()
    
    # exact_match: IDs, categorical, binary, discrete counts
    exact_match_keywords = [
        'nct', 'pubmed', 'trial name', 'author', 'year', 
        'full pub or abstract', 'phase', 'original/follow up',
        'number of arms included',  # Discrete count - must be exact
        'quality of life reported', 'reporting by prognostic',
        'coe_rct_ind'
    ]
    
    for keyword in exact_match_keywords:
        if keyword in col_lower:
            return 'exact_match'
    
    # Check definition for Yes/No patterns
    if 'yes or no' in def_lower or 'answer yes or no' in def_lower:
        return 'exact_match'
    
    # numeric_tolerance: Any column with N, %, ages, durations, survival, rates
    # Use more specific patterns to avoid false matches
    numeric_patterns = [
        r'\s-\s+n\b',  # " - N" (participant count)
        r'n\s*\(%\)',  # "N (%)"
        r'\(mo\)',     # "(mo)" - months
        r'\byears?\b', # "year" or "years"
        r'\bmedian\b', # "median"
        r'\bduration\b', # "duration"
        r'\bsurvival\b', # "survival"
        r'\brate\b',   # "rate"
        r'\bdeaths?\b', # "death" or "deaths"
        r'\bttpsa\b',  # "TTPSA"
        r'\borr\b',    # "ORR"
        r'\badverse\b', # "adverse events"
        r'\bpfs\b',    # "PFS"
        r'\bos\b',     # "OS"
    ]
    
    for pattern in numeric_patterns:
        if re.search(pattern, col_lower):
            return 'numeric_tolerance'
    
    # structured_text: Everything else (regimens, treatments, endpoints, etc.)
    return 'structured_text'


def main():
    # Load original definitions
    input_path = "/mnt/data1/nahuja11/Mayo/CoRal-Map-Make/src/table_definitions/Definitions_open_ended.csv"
    df = pd.read_csv(input_path)
    
    print(f"Loaded {len(df)} columns from definitions file")
    
    # Assign eval categories
    df['eval_category'] = df.apply(
        lambda row: assign_eval_category(row['Column Name'], row['Definition']),
        axis=1
    )
    
    # Count by category
    category_counts = df['eval_category'].value_counts()
    print(f"\n{'='*60}")
    print("CATEGORY DISTRIBUTION")
    print(f"{'='*60}")
    for cat, count in category_counts.items():
        print(f"{cat:20s}: {count:3d} columns")
    
    # Show examples from each category
    print(f"\n{'='*60}")
    print("EXAMPLES FROM EACH CATEGORY")
    print(f"{'='*60}")
    
    for category in ['exact_match', 'numeric_tolerance', 'structured_text']:
        print(f"\n{category.upper()}:")
        examples = df[df['eval_category'] == category]['Column Name'].head(5).tolist()
        for ex in examples:
            print(f"  - {ex}")
    
    # Save with eval_category column
    output_path = "/mnt/data1/nahuja11/Mayo/CoRal-Map-Make/src/table_definitions/Definitions_with_eval_category.csv"
    df.to_csv(output_path, index=False)
    print(f"\n✅ Saved tagged definitions to: {output_path}")
    
    return df


if __name__ == "__main__":
    df = main()
