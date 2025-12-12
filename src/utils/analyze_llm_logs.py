# scripts/analyze_llm_logs.py
"""
Script to analyze LLM logs and provide insights into extraction quality.
Usage: python analyze_llm_logs.py <path_to_llm_logs_dir>
"""
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict


def analyze_logs(log_dir: Path):
    """Analyze LLM logs and generate insights."""
    
    log_file = log_dir / "llm_calls.jsonl"
    summary_file = log_dir / "llm_summary.json"
    
    if not log_file.exists():
        print(f"❌ Log file not found: {log_file}")
        return
    
    # Read summary
    if summary_file.exists():
        with open(summary_file, "r") as f:
            summary = json.load(f)
        print("\n" + "="*80)
        print("📊 SUMMARY STATISTICS")
        print("="*80)
        print(f"Total Calls: {summary['total_calls']}")
        print(f"Successful: {summary['successful_extractions']}")
        print(f"Failed: {summary['failed_extractions']}")
        print(f"Success Rate: {summary['successful_extractions']/summary['total_calls']*100:.1f}%")
        print(f"Total Input Tokens: {summary['total_input_tokens']:,}")
        print(f"Total Output Tokens: {summary['total_output_tokens']:,}")
        print(f"\nCalls by Group:")
        for group, count in sorted(summary['calls_by_group'].items(), key=lambda x: -x[1])[:10]:
            print(f"  {group}: {count}")
        print(f"\nCalls by Chunk Type:")
        for chunk_type, count in summary['calls_by_chunk_type'].items():
            print(f"  {chunk_type}: {count}")
    
    # Detailed analysis
    print("\n" + "="*80)
    print("🔍 DETAILED ANALYSIS")
    print("="*80)
    
    calls = []
    with open(log_file, "r") as f:
        for line in f:
            calls.append(json.loads(line))
    
    # Analysis 1: Columns that are never found
    columns_extracted = defaultdict(int)
    columns_total = defaultdict(int)
    
    for call in calls:
        for col_name, data in call.get("extracted_values", {}).items():
            columns_total[col_name] += 1
            if data.get("value") is not None:
                columns_extracted[col_name] += 1
    
    never_found = [col for col, count in columns_extracted.items() if count == 0]
    rarely_found = [(col, columns_extracted[col], columns_total[col]) 
                    for col in columns_total 
                    if 0 < columns_extracted[col] < columns_total[col] * 0.2]
    
    print(f"\n❌ Columns NEVER found ({len(never_found)}):")
    for col in never_found[:20]:  # Show first 20
        print(f"  - {col}")
    if len(never_found) > 20:
        print(f"  ... and {len(never_found) - 20} more")
    
    print(f"\n⚠️  Columns RARELY found (< 20% success rate, {len(rarely_found)}):")
    for col, found, total in sorted(rarely_found, key=lambda x: x[1]/x[2])[:20]:
        print(f"  - {col}: {found}/{total} ({found/total*100:.1f}%)")
    if len(rarely_found) > 20:
        print(f"  ... and {len(rarely_found) - 20} more")
    
    # Analysis 2: Most common errors
    print(f"\n🚨 ERRORS:")
    errors = [call for call in calls if call.get("error")]
    error_types = Counter([call["error"].split(":")[0] for call in errors])
    
    print(f"Total errors: {len(errors)}")
    for error_type, count in error_types.most_common(5):
        print(f"  - {error_type}: {count}")
    
    # Analysis 3: Reasoning patterns for nulls
    print(f"\n🤔 REASONING FOR NULLS (sample):")
    null_reasonings = []
    for call in calls[:50]:  # First 50 calls
        for col_name, data in call.get("extracted_values", {}).items():
            if data.get("value") is None and data.get("reasoning"):
                null_reasonings.append((col_name, data["reasoning"]))
    
    reasoning_counter = Counter([r[1] for r in null_reasonings])
    for reasoning, count in reasoning_counter.most_common(10):
        print(f"  - '{reasoning}': {count}")
    
    # Analysis 4: Token usage by chunk type
    print(f"\n📊 TOKEN USAGE BY CHUNK TYPE:")
    tokens_by_type = defaultdict(lambda: {"input": 0, "output": 0, "count": 0})
    for call in calls:
        chunk_type = call.get("chunk_type", "unknown")
        tokens_by_type[chunk_type]["input"] += call.get("input_tokens", 0)
        tokens_by_type[chunk_type]["output"] += call.get("output_tokens", 0)
        tokens_by_type[chunk_type]["count"] += 1
    
    for chunk_type, data in tokens_by_type.items():
        avg_input = data["input"] / data["count"]
        avg_output = data["output"] / data["count"]
        print(f"  {chunk_type}:")
        print(f"    Avg input: {avg_input:.0f} tokens")
        print(f"    Avg output: {avg_output:.0f} tokens")
        print(f"    Calls: {data['count']}")
    
    # Analysis 5: Groups with most failures
    print(f"\n⚠️  GROUPS WITH MOST NULL VALUES:")
    group_nulls = defaultdict(lambda: {"nulls": 0, "total": 0})
    for call in calls:
        group_label = call.get("group_label", "unknown")
        for col_name, data in call.get("extracted_values", {}).items():
            group_nulls[group_label]["total"] += 1
            if data.get("value") is None:
                group_nulls[group_label]["nulls"] += 1
    
    group_null_rates = [
        (group, data["nulls"], data["total"], data["nulls"]/data["total"])
        for group, data in group_nulls.items()
        if data["total"] > 0
    ]
    
    for group, nulls, total, rate in sorted(group_null_rates, key=lambda x: -x[3])[:10]:
        print(f"  {group}: {nulls}/{total} ({rate*100:.1f}% null)")
    
    print("\n" + "="*80)
    print(f"📝 Full human-readable logs available at:")
    print(f"   {log_dir / 'llm_calls_readable.txt'}")
    print("="*80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_llm_logs.py <path_to_llm_logs_dir>")
        sys.exit(1)
    
    log_dir = Path(sys.argv[1])
    if not log_dir.exists():
        print(f"❌ Directory not found: {log_dir}")
        sys.exit(1)
    
    analyze_logs(log_dir)