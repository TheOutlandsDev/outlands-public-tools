"""Create a fictional game installation for the checker walkthrough."""

from __future__ import annotations

import argparse
from pathlib import Path


PROFILE = """\
name = "demo"
game = "Demo Server"
engine = "standalone"
enabled = true
platform = "any"
install_dir = "servers/demo"
executable = "server.bin"
required_files = ["required.txt"]
save_paths = ["saves"]
ports = [27015]
expect_running = false
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="New directory under an existing parent.")
    root = parser.parse_args().root
    try:
        root.mkdir()
        profiles = root / "config" / "game-profiles"
        profiles.mkdir(parents=True)
        install = root / "servers" / "demo"
        (install / "saves").mkdir(parents=True)
        (profiles / "demo.toml").write_text(PROFILE, encoding="utf-8", newline="\n")
        for path, content in (
            (install / "server.bin", "Fictional executable marker.\n"),
            (install / "required.txt", "Fictional required file.\n"),
            (install / "saves" / "fixture.marker", "Fictional save directory marker.\n"),
        ):
            path.write_text(content, encoding="utf-8", newline="\n")
    except OSError:
        parser.exit(2, "Could not create the sample in a new directory.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
