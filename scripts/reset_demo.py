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

    if _server_running():
        print()
        print("  !! A server is still running on port 8080 or 4173.")
        print("     It holds the old data in memory and will write it back over")
        print("     these files on its next save. Stop the server, run this again,")
        print("     then start it. Order matters.")
        return 1

    return 0 if restored else 1


def _server_running() -> bool:
    """Best-effort check for a live neuro-san on the default ports."""
    import socket

    for port in (8080, 4173):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.3)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
