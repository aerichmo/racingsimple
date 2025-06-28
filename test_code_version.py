#!/usr/bin/env python3
"""Test which version of code is running"""

import rtn_runner_headless
import inspect

# Get the find_fair_meadows_stream method
method = rtn_runner_headless.RTNCaptureHeadless.find_fair_meadows_stream

# Get the source code
source = inspect.getsource(method)

# Check for key phrases
if "Page contains 'Live Simulcasts':" in source:
    print("✓ NEW CODE IS LOADED")
else:
    print("✗ OLD CODE IS LOADED")

if "Found Available Simulcasts link, clicking" in source:
    print("✗ OLD LOG MESSAGE FOUND")
    
if "Method 1: Try to find Live Simulcasts" in source:
    print("✓ New Method 1 code found")
    
if "LAST RESORT: Trying Available Simulcasts" in source:
    print("✓ New fallback code found")

# Show first few lines of the method
print("\nFirst lines of find_fair_meadows_stream method:")
lines = source.split('\n')
for i, line in enumerate(lines[:20]):
    print(f"{i}: {line}")