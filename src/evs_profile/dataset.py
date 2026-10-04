"""Build and validate the reproducible EVS Parquet dataset."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.parquet as pq


EXPECTED_SOURCE_ROWS = 156_658
EXPECTED_SOURCE_COLUMNS = 231
EXPECTED_EVS_ROWS = 59_438
EXPECTED_EVS_COLUMNS = 226


@dataclass(frozen=True)
class BuildResult:
    source_file: str
    output_file: str
    source_sha256: str
    source_rows: int
    source_columns: int
    rows: int
    columns: int
    dropped_columns: list[str]
    parquet_bytes: int
    compression: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_evs_parquet(
    source_path: Path,
    output_path: Path,
    *,
    expected_source_rows: int = EXPECTED_SOURCE_ROWS,
    expected_source_columns: int = EXPECTED_SOURCE_COLUMNS,
    expected_rows: int = EXPECTED_EVS_ROWS,
    expected_columns: int = EXPECTED_EVS_COLUMNS,
) -> BuildResult:
    """Filter EVS rows, remove WVS-only columns, and write validated Parquet."""

    source_path = source_path.resolve()
    output_path = output_path.resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Source CSV not found: {source_path}")

    source = pacsv.read_csv(source_path)
    _require_shape(
        "source CSV",
        source.num_rows,
        source.num_columns,
        expected_source_rows,
        expected_source_columns,
    )
    if "study" not in source.column_names or "uniqid" not in source.column_names:
        raise ValueError("Source CSV must contain study and uniqid columns.")

    evs = source.filter(pc.equal(source["study"], 1))
    dropped_columns = sorted(
        column for column in evs.column_names if column.endswith("_WVS7")
    )
    evs = evs.drop(dropped_columns)
    _require_shape(
        "EVS subset",
        evs.num_rows,
        evs.num_columns,
        expected_rows,
        expected_columns,
    )

    studies = set(evs["study"].unique().to_pylist())
    if studies != {1}:
        raise ValueError(f"EVS subset contains unexpected study values: {sorted(studies)}")
    if pc.count_distinct(evs["uniqid"]).as_py() != evs.num_rows:
        raise ValueError("EVS subset contains duplicate uniqid values.")

    source_hash = sha256_file(source_path)
    metadata = dict(evs.schema.metadata or {})
    metadata.update(
        {
            b"dataset": b"EVS 2017 analytical subset",
            b"source_dataset": b"Joint EVS/WVS 2017-2022 Version 5.0.0",
            b"source_file": source_path.name.encode("utf-8"),
            b"source_sha256": source_hash.encode("ascii"),
            b"filter": b"study == 1",
            b"dropped_columns": ",".join(dropped_columns).encode("utf-8"),
            b"missing_codes": b"-1,-2,-3,-4,-5 preserved as documented values",
            b"builder": b"scripts/build_evs_parquet.py",
        }
    )
    evs = evs.replace_schema_metadata(metadata)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent, delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)
        pq.write_table(
            evs,
            temp_path,
            compression="zstd",
            use_dictionary=True,
            write_statistics=True,
        )
        _validate_parquet(temp_path, expected_rows, expected_columns, source_hash)
        os.replace(temp_path, output_path)
        os.chmod(output_path, 0o644)
        temp_path = None
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    result = BuildResult(
        source_file=source_path.name,
        output_file=output_path.name,
        source_sha256=source_hash,
        source_rows=source.num_rows,
        source_columns=source.num_columns,
        rows=evs.num_rows,
        columns=evs.num_columns,
        dropped_columns=dropped_columns,
        parquet_bytes=output_path.stat().st_size,
        compression="zstd",
    )
    _write_manifest(output_path.with_suffix(".metadata.json"), result)
    return result


def _require_shape(
    label: str,
    rows: int,
    columns: int,
    expected_rows: int,
    expected_columns: int,
) -> None:
    if rows != expected_rows or columns != expected_columns:
        raise ValueError(
            f"Unexpected {label} shape: {rows:,} x {columns:,}; "
            f"expected {expected_rows:,} x {expected_columns:,}."
        )


def _validate_parquet(
    path: Path, expected_rows: int, expected_columns: int, source_hash: str
) -> None:
    metadata = pq.read_metadata(path)
    _require_shape(
        "written Parquet",
        metadata.num_rows,
        metadata.num_columns,
        expected_rows,
        expected_columns,
    )
    schema_metadata = metadata.metadata or {}
    if schema_metadata.get(b"source_sha256") != source_hash.encode("ascii"):
        raise ValueError("Written Parquet provenance hash does not match the source CSV.")


def _write_manifest(path: Path, result: BuildResult) -> None:
    payload = json.dumps(asdict(result), indent=2, sort_keys=True) + "\n"
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as temp_file:
            temp_file.write(payload)
            temp_path = Path(temp_file.name)
        os.replace(temp_path, path)
        os.chmod(path, 0o644)
        temp_path = None
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
