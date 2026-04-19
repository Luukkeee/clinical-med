"""
MedRAG Demo Script
Run: python demo/demo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run import run_demo

if __name__ == "__main__":
    run_demo()
