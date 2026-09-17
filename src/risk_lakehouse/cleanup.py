from __future__ import annotations

import argparse
from pathlib import Path


def clean_output(output: Path) -> None:
    output = output.resolve()
    if output.name != "processed":
        raise ValueError("Cleanup is restricted to a directory named 'processed'")
    if output.exists():
        for path in sorted(output.rglob("*"), reverse=True):
            if path.is_file() and path.name != ".gitkeep":
                path.unlink()
            elif path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    clean_output(args.output)


if __name__ == "__main__":
    main()

