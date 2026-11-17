"""Append-only SQLite migrations.

Once a migration has been applied, add a new numbered file instead of editing
the existing file. The runtime verifies each applied migration's SHA-256.
"""
