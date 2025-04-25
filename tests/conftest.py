# tests/conftest.py
import sys, os

# Calculates: <project_root> = parent of this conftest.py
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# Prepend it so `import trendstory` works
sys.path.insert(0, PROJECT_ROOT)
