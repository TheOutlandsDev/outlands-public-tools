"""Document cataloging, text extraction, chunking, and FTS ingestion."""

from __future__ import annotations

from pathlib import Path

from program_data.ingest.common import (
    IngestResult,
    file_metadata,
    ingestion_session,
)

TEXT_SUFFIXES = {
    ".cfg",
    ".csv",
    ".ini",
    ".json",
    ".log",
    ".md",
    ".rst",
    ".sql",
    ".text",
    ".toml",
    ".tsv",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


def _extract_text(path: Path) -> tuple[str | None, str]:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return None, "not_supported"
    try:
        return path.read_text(encoding="utf-8-sig"), "extracted"
    except UnicodeDecodeError:
        return None, "not_supported"


def _chunks(
    text: str,
    *,
    chunk_size: int = 2000,
    overlap: int = 200,
) -> list[tuple[int, int, int, str]]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    chunks: list[tuple[int, int, int, str]] = []
    start = 0
    index = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append((index, start, end, text[start:end]))
        if end == len(text):
            break
        start = end - overlap
        index += 1
    return chunks


def ingest_document(
    path: str | Path,
    database_path: str | Path | None = None,
    *,
    source_key: str = "local_documents",
    source_name: str = "Local documents",
    title: str | None = None,
    chunk_size: int = 2000,
    overlap: int = 200,
    trigger_type: str = "manual",
) -> IngestResult:
    """Catalog a document and index UTF-8 text-like content."""

    source_path = Path(path).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Document does not exist: {source_path}")

    metadata = file_metadata(source_path)
    extracted_text, extraction_status = _extract_text(source_path)
    chunks = (
        _chunks(extracted_text, chunk_size=chunk_size, overlap=overlap)
        if extracted_text is not None
        else []
    )

    with ingestion_session(
        database_path,
        source_key=source_key,
        source_name=source_name,
        source_type="document",
        authority_note="The source document repository remains authoritative.",
        location_hint=str(source_path.parent),
        input_reference=str(source_path),
        input_sha256=metadata["content_sha256"],
        trigger_type=trigger_type,
    ) as context:
        context.records_read = 1
        existing_asset = context.existing_asset(
            asset_type="document",
            content_sha256=metadata["content_sha256"],
        )
        if existing_asset is not None:
            document = context.connection.execute(
                "SELECT document_id FROM documents WHERE asset_id = ?",
                (int(existing_asset["asset_id"]),),
            ).fetchone()
            context.metadata["deduplicated_asset_id"] = int(
                existing_asset["asset_id"]
            )
            return IngestResult(
                run_id=context.run_id,
                source_id=context.source_id,
                entity_type="document",
                entity_id=(
                    int(document["document_id"]) if document is not None else None
                ),
                asset_id=int(existing_asset["asset_id"]),
                records_read=1,
                records_written=0,
                deduplicated=True,
                metadata={"extraction_status": extraction_status},
            )

        asset_id = context.create_asset(
            asset_type="document",
            logical_name=metadata["logical_name"],
            source_uri=metadata["source_uri"],
            media_type=metadata["media_type"],
            byte_size=metadata["byte_size"],
            content_sha256=metadata["content_sha256"],
            source_modified_at=metadata["source_modified_at"],
            metadata={"suffix": source_path.suffix.lower()},
        )
        cursor = context.connection.execute(
            """
            INSERT INTO documents(
                asset_id,
                title,
                extraction_status,
                extracted_text,
                metadata_json
            )
            VALUES (?, ?, ?, ?, '{}')
            """,
            (
                asset_id,
                title or source_path.stem,
                extraction_status,
                extracted_text,
            ),
        )
        document_id = int(cursor.lastrowid)
        context.connection.executemany(
            """
            INSERT INTO document_chunks(
                document_id,
                chunk_index,
                char_start,
                char_end,
                content,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, '{}')
            """,
            [
                (document_id, index, start, end, content)
                for index, start, end, content in chunks
            ],
        )
        context.records_written = 1
        context.metadata.update(
            {
                "document_id": document_id,
                "chunk_count": len(chunks),
                "extraction_status": extraction_status,
            }
        )
        return IngestResult(
            run_id=context.run_id,
            source_id=context.source_id,
            entity_type="document",
            entity_id=document_id,
            asset_id=asset_id,
            records_read=1,
            records_written=1,
            deduplicated=False,
            metadata={
                "chunk_count": len(chunks),
                "extraction_status": extraction_status,
            },
        )
