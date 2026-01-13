#!/usr/bin/env python3
"""
Quick test script to verify retrieval integration works.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_FOLDER = PROJECT_ROOT / "src"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_FOLDER))

def test_imports():
    """Test that all retrieval imports work."""
    print("Testing imports...")
    
    try:
        from src.retrieval import get_retriever, build_retrieval_query, combine_retrieved_chunks
        print("✅ Retrieval module imports successful")
    except ImportError as e:
        print(f"❌ Retrieval import failed: {e}")
        return False
    
    try:
        from src.fill_table.fill_table import fill_table_with_retrieval
        print("✅ fill_table_with_retrieval import successful")
    except ImportError as e:
        print(f"❌ fill_table import failed: {e}")
        return False
    
    try:
        from src.config.config import (
            USE_RETRIEVAL, 
            RETRIEVAL_STRATEGY, 
            RETRIEVAL_TOP_N
        )
        print("✅ Config imports successful")
        print(f"   USE_RETRIEVAL: {USE_RETRIEVAL}")
        print(f"   RETRIEVAL_STRATEGY: {RETRIEVAL_STRATEGY}")
        print(f"   RETRIEVAL_TOP_N: {RETRIEVAL_TOP_N}")
    except ImportError as e:
        print(f"❌ Config import failed: {e}")
        return False
    
    return True


def test_query_building():
    """Test query building."""
    print("\nTesting query building...")
    
    from src.retrieval import build_retrieval_query
    
    # Sample group
    group = [
        {"Column Name": "Age", "Definition": "Patient age at enrollment"},
        {"Column Name": "Sex", "Definition": "Biological sex of patient"}
    ]
    
    query = build_retrieval_query(group)
    print(f"✅ Generated query:\n   {query}")
    
    expected_substring = "What is the value of Age:"
    if expected_substring in query:
        print("✅ Query format is correct")
        return True
    else:
        print("❌ Query format is incorrect")
        return False


def test_chunk_combining():
    """Test chunk combining."""
    print("\nTesting chunk combining...")
    
    from src.retrieval import combine_retrieved_chunks
    
    # Sample chunks
    chunks = [
        {"content": "Sample text 1", "type": "text", "page": 1},
        {"content": "Sample text 2", "type": "text", "page": 2},
        {"content": "Sample text 3", "type": "text", "page": 3}
    ]
    
    combined = combine_retrieved_chunks(chunks)
    
    print(f"✅ Combined {combined['source_chunks']} chunks")
    print(f"   Type: {combined['type']}")
    print(f"   Pages: {combined['pages']}")
    
    if "CHUNK 1" in combined["content"] and "CHUNK 2" in combined["content"]:
        print("✅ Chunk structure is correct")
        return True
    else:
        print("❌ Chunk structure is incorrect")
        return False


def test_retriever_basic():
    """Test basic retriever functionality (requires rank_bm25)."""
    print("\nTesting retriever initialization...")
    
    try:
        from src.retrieval import get_retriever
        
        # Sample chunks
        chunks = [
            {"content": "The patient was 65 years old at enrollment", "type": "text", "page": 1},
            {"content": "Treatment arm A received chemotherapy", "type": "text", "page": 2},
            {"content": "Median survival was 18 months", "type": "text", "page": 3},
            {"content": "Age range was 45-82 years", "type": "text", "page": 4},
        ]
        
        # Test BM25 retriever
        retriever = get_retriever(chunks, strategy="bm25")
        print("✅ BM25 retriever initialized")
        
        # Test retrieval
        query = "What is the patient age?"
        top_chunks = retriever.retrieve(query, top_n=2)
        print(f"✅ Retrieved {len(top_chunks)} chunks")
        print(f"   Top chunk: {top_chunks[0]['content'][:50]}...")
        
        return True
    
    except ImportError as e:
        print(f"⚠️  Retriever test skipped (missing dependencies): {e}")
        print("   Run: pip install rank-bm25 sentence-transformers scikit-learn")
        return None
    except Exception as e:
        print(f"❌ Retriever test failed: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("RETRIEVAL INTEGRATION TEST")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("Query Building", test_query_building),
        ("Chunk Combining", test_chunk_combining),
        ("Retriever", test_retriever_basic)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{'='*60}")
        result = test_func()
        results.append((name, result))
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)
    
    for name, result in results:
        status = "✅ PASS" if result is True else "❌ FAIL" if result is False else "⚠️  SKIP"
        print(f"{status:10s} {name}")
    
    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("\n✅ All tests passed! Retrieval integration is ready to use.")
        sys.exit(0)
