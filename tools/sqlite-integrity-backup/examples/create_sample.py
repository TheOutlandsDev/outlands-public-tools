"""Create a fictional SQLite database at a new path."""

from __future__ import annotations

import argparse
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    destination = parser.parse_args().path.expanduser().absolute()
    try:
        with tempfile.TemporaryDirectory(dir=destination.parent) as directory:
            staging = Path(directory) / "sample.sqlite"
            with closing(sqlite3.connect(staging)) as connection:
                connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
                connection.execute("INSERT INTO sample(id, value) VALUES (1, 'fictional sample')")
                connection.commit()
            os.link(staging, destination)
    except (OSError, sqlite3.Error):
        parser.exit(2, "Could not create a sample database at the supplied new path.\n")


if __name__ == "__main__":
    main()
