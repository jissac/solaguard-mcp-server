#!/usr/bin/env python3
"""
Cross-Reference Test Script

Quick test script to validate cross-reference JSON data format and 
test verse mapping before running full ingestion.
"""

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ingest_cross_references import VerseMapper


def test_json_format(json_file: Path) -> None:
    """Test the format of a single JSON file."""
    print(f"\n📁 Testing JSON file: {json_file}")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ JSON file loaded successfully")
        print(f"📊 Contains {len(data)} entries")
        
        # Test first few entries
        sample_count = min(3, len(data))
        print(f"\n🔍 Sample entries (first {sample_count}):")
        
        for i, (verse_id, verse_data) in enumerate(list(data.items())[:sample_count]):
            print(f"\nEntry {i+1}:")
            print(f"  Verse ID: {verse_id}")
            print(f"  Reference: {verse_data.get('v', 'MISSING')}")
            print(f"  Cross-refs: {len(verse_data.get('r', {}))}")
            
            # Show first few cross-references
            cross_refs = verse_data.get('r', {})
            if cross_refs:
                sample_refs = list(cross_refs.items())[:3]
                print(f"  Sample cross-refs:")
                for ref_id, ref_text in sample_refs:
                    print(f"    {ref_id}: {ref_text}")
    
    except Exception as e:
        print(f"❌ Error testing JSON file: {e}")


def test_verse_mapping(db_path: Path) -> None:
    """Test verse mapping functionality."""
    print(f"\n🗄️ Testing verse mapping with database: {db_path}")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        mapper = VerseMapper(db_path)
        print(f"✅ Verse mapper initialized")
        print(f"📚 Loaded {len(mapper.verse_cache):,} verses into cache")
        
        # Test some common verse references
        test_refs = [
            "GEN 1 1",
            "JHN 3 16", 
            "PSA 23 1",
            "ROM 8 28",
            "REV 22 21"
        ]
        
        print(f"\n🔍 Testing verse reference mapping:")
        for ref in test_refs:
            verse_id = mapper.get_verse_id(ref)
            status = "✅" if verse_id else "❌"
            print(f"  {status} {ref} → {verse_id}")
    
    except Exception as e:
        print(f"❌ Error testing verse mapping: {e}")


def main():
    """Main test function."""
    print("🧪 Cross-Reference Data Test")
    print("=" * 50)
    
    # Test JSON files
    json_dir = Path("data/cross_references")
    if json_dir.exists():
        json_files = list(json_dir.glob("*.json"))
        if json_files:
            print(f"📂 Found {len(json_files)} JSON files in {json_dir}")
            
            # Test first JSON file
            test_json_format(json_files[0])
        else:
            print(f"⚠️ No JSON files found in {json_dir}")
    else:
        print(f"⚠️ JSON directory not found: {json_dir}")
        print("💡 Create the directory and add your JSON files there")
    
    # Test database mapping
    db_path = Path("data/bible.db")
    test_verse_mapping(db_path)
    
    print(f"\n✨ Test complete!")
    print(f"💡 If everything looks good, run:")
    print(f"   python scripts/ingest_cross_references.py --dry-run")


if __name__ == "__main__":
    main()