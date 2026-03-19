"""
Unit tests for jsonl_queue module.

Test: 100 concurrent threads appending produce 100 parseable JSON lines.
"""

import unittest
import tempfile
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from storage.jsonl_queue import append_jsonl, read_jsonl, clear_jsonl


class TestJSONLQueue(unittest.TestCase):
    """Test JSONL queue storage with file locking."""
    
    def setUp(self):
        """Create temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test.jsonl')
    
    def tearDown(self):
        """Clean up temporary files."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_single_append(self):
        """Test appending a single record."""
        record = {'id': 1, 'action': 'buy', 'price': 100.5}
        append_jsonl(self.test_file, record)
        
        records = read_jsonl(self.test_file)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0], record)
    
    def test_multiple_appends(self):
        """Test appending multiple records sequentially."""
        records_to_add = [
            {'id': 1, 'action': 'buy'},
            {'id': 2, 'action': 'sell'},
            {'id': 3, 'action': 'hold'},
        ]
        
        for record in records_to_add:
            append_jsonl(self.test_file, record)
        
        read_records = read_jsonl(self.test_file)
        self.assertEqual(len(read_records), 3)
        self.assertEqual(read_records, records_to_add)
    
    def test_read_nonexistent_file(self):
        """Test reading from non-existent file returns empty list."""
        nonexistent = os.path.join(self.temp_dir, 'nonexistent.jsonl')
        records = read_jsonl(nonexistent)
        self.assertEqual(records, [])
    
    def test_clear_jsonl(self):
        """Test clearing a JSONL file."""
        append_jsonl(self.test_file, {'id': 1})
        append_jsonl(self.test_file, {'id': 2})
        
        records = read_jsonl(self.test_file)
        self.assertEqual(len(records), 2)
        
        clear_jsonl(self.test_file)
        records = read_jsonl(self.test_file)
        self.assertEqual(len(records), 0)
    
    def test_json_serialization_types(self):
        """Test various JSON-serializable types."""
        records_to_add = [
            {'string': 'value', 'number': 42, 'float': 3.14},
            {'list': [1, 2, 3], 'dict': {'nested': 'value'}},
            {'bool': True, 'null': None},
        ]
        
        for record in records_to_add:
            append_jsonl(self.test_file, record)
        
        read_records = read_jsonl(self.test_file)
        self.assertEqual(read_records, records_to_add)
    
    def test_concurrent_appends_100_threads(self):
        """
        ACCEPTANCE TEST: 100 concurrent threads appending produce 100 
        parseable JSON lines.
        """
        num_threads = 100
        
        def append_record(thread_id):
            """Worker function to append a record."""
            record = {
                'thread_id': thread_id,
                'data': f'record_{thread_id}',
                'value': thread_id * 10,
            }
            append_jsonl(self.test_file, record)
            return thread_id
        
        # Submit all tasks concurrently
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(append_record, i) 
                for i in range(num_threads)
            ]
            
            # Wait for all to complete
            completed = [f.result() for f in as_completed(futures)]
        
        # Verify all threads completed
        self.assertEqual(len(completed), num_threads)
        
        # Read and verify records
        records = read_jsonl(self.test_file)
        
        # Acceptance: 100 parseable JSON lines
        self.assertEqual(len(records), num_threads, 
                        f"Expected {num_threads} records, got {len(records)}")
        
        # Verify each record is valid and parseable
        thread_ids = set()
        for record in records:
            self.assertIn('thread_id', record)
            self.assertIn('data', record)
            self.assertIn('value', record)
            thread_ids.add(record['thread_id'])
        
        # Verify all thread IDs are represented (no data loss)
        self.assertEqual(len(thread_ids), num_threads,
                        f"Expected {num_threads} unique thread IDs, got {len(thread_ids)}")
        
        # Verify no duplicates
        self.assertEqual(len(records), len(thread_ids),
                        "Duplicate records detected")
    
    def test_large_json_records(self):
        """Test appending large JSON records."""
        large_record = {
            'id': 1,
            'data': 'x' * 10000,  # 10KB of data
            'nested': {
                'level1': {
                    'level2': {
                        'level3': list(range(100))
                    }
                }
            }
        }
        
        append_jsonl(self.test_file, large_record)
        records = read_jsonl(self.test_file)
        
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['data'], large_record['data'])
        self.assertEqual(records[0]['nested'], large_record['nested'])
    
    def test_special_characters_in_json(self):
        """Test JSON with special characters."""
        record = {
            'text': 'Line\nBr"Quotes\'and\ttabs',
            'unicode': '🚀 Bitcoin 中文 العربية',
            'escaped': '\\backslash',
        }
        
        append_jsonl(self.test_file, record)
        records = read_jsonl(self.test_file)
        
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['text'], record['text'])
        self.assertEqual(records[0]['unicode'], record['unicode'])


if __name__ == '__main__':
    unittest.main()
