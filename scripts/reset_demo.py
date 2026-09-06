"""Restore the synthetic data to its pre-demo state.

Cadence writes to disk on purpose: captured meetings, captured tasks and
learning items extracted from transcripts all persist. Run this between
rehearsals so every demo starts from the same known state.

    python scripts/reset_demo.py
"""

import pathlib
import shutil

DATA = pathlib.Path(__file__).resolve().parent.parent / "cadence_tools" / "cadence" / "data"
STORES = ("learning", "calendar", "tasks")


def main() -> int:
    restored, missing = [], []
    for name in STORES:
        seed = DATA / f"{name}.seed.json"
        live = DATA / f"{name}.json"
        if seed.exists():
            shutil.copyfile(seed, live)
            restored.append(f"{name}.json")
        else:
            missing.append(f"{name}.seed.json")

    for name in restored:
        print(f"  restored {name}")
    for name in missing:
        print(f"  WARNING: no seed for {name}")
    print("Demo state is clean." if restored else "Nothing restored.")
    return 0 if restored else 1


if __name__ == "__main__":
    raise SystemExit(main())
