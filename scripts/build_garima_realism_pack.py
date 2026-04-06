"""Build Garima's realism rerank, shortlist, and approval pack."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.garima_realism import build_realism_package


def main() -> None:
    outputs = build_realism_package()
    print("Garima realism package generated:")
    for label, path in outputs.items():
        print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
