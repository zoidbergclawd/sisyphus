#!/usr/bin/env python3
import sys
import os

"""
Mock Foreman (The Fake Factory)
Acts as a validator for testing Ralph's closed loop.
"""

def check_file_content(path, expected_content):
    if not os.path.exists(path):
        print(f"❌ Failure: File '{path}' does not exist.")
        return False
    
    with open(path, 'r') as f:
        content = f.read().strip()
    
    if content == expected_content:
        print(f"✅ Success: '{path}' contains '{expected_content}'")
        return True
    else:
        print(f"❌ Failure: '{path}' contains '{content}', expected '{expected_content}'")
        return False

if __name__ == "__main__":
    # Scenario 1: Check for magic_token.txt
    target_file = "magic_token.txt"
    expected_value = "42"
    
    print(f"🏭 Fake Factory running scenario: Check {target_file}")
    
    if check_file_content(target_file, expected_value):
        sys.exit(0)
    else:
        sys.exit(1)
