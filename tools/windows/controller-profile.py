"""Compatibility entry point for the shared MH controller profile validator."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from controller_profile import main, validate


if __name__ == '__main__':
    main()
