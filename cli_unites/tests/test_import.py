#!/usr/bin/env python3
import sys
import os

print('Working directory:', os.getcwd())
print('sys.executable:', sys.executable)
print('sys.path:')
for p in sys.path:
    print(f'  {p}')

print('\nTrying to import cli_unites...')
try:
    from cli_unites.cli import cli
    print('Import successful!')
    print('CLI object:', cli)
except Exception as e:
    print(f'Import failed: {e}')
    import traceback
    traceback.print_exc()
