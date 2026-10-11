#!/usr/bin/env python3
"""
Universal NAND Flash Clone Tool - Desktop Application Launcher
Run via: python run.py
"""

import sys
import os

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import main

if __name__ == "__main__":
    main()

