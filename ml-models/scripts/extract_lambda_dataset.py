"""Command-line entry point for runtime_detector.extraction."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from runtime_detector.extraction import main

if __name__ == "__main__":
    main()
