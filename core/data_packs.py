"""Install named, publisher-verified local collections without touching notebooks."""
from __future__ import annotations

from contextlib import closing
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4
import zipfile

CATALOG = Path(__file__).resolve().parents[1] / "atlas/gui/data/data_pack_catalog.json"
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
VERSION = re.compile(r"\d{1,4}(?:\.\d{1,4}){1,3}\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")
FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\Z")
SQL_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,79}\Z")
DOWNLOAD_HOSTS = {"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}


def _no_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("The collection metadata contains duplicate keys.")
        value[key] = item
    return value


def _json(path):
    if path.stat().st_size > 2_000_000:
        raise ValueError("The collection metadata is too large.")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates)


def _download_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("The collection download address is invalid.")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.hostname not in DOWNLOAD_HOSTS or parsed.username
            or parsed.password or parsed.port not in (None, 443) or parsed.fragment
            or any(ord(char) < 33 for char in value)):
        raise ValueError("The collection download must use its approved HTTPS publisher.")
    return value


def _source_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or any(ord(char) < 33 for char in value)):
        raise ValueError("A collection source address is invalid.")


@lru_cache(maxsize=8)
def _catalog(path, modified, size):
    document = _json(Path(path))
    if (not isinstance(document, dict) or set(document) != {"format_version", "packs"}
            or type(document["format_version"]) is not int or document["format_version"] != 1
            or not isinstance(document["packs"], list) or len(document["packs"]) > 10_000):
        raise ValueError("The collection catalog has an unsupported format.")
    seen = set()
    for pack in document["packs"]:
        required = {"id", "version", "title", "description", "records", "record_type", "coverage",
                    "source_release", "license", "source_url", "citation_url", "download_url",
                    "archive_bytes", "archive_sha256", "installed_bytes", "files", "countries"}
        if not isinstance(pack, dict) or set(pack) != required:
            raise ValueError("The collection definition has unsupported fields.")
        text_fields = required - {"records", "archive_bytes", "installed_bytes", "files", "countries"}
        if any(not isinstance(pack[key], str) or len(pack[key]) > 4096 or any(ord(char) < 32 for char in pack[key]) for key in text_fields):
            raise ValueError("A collection description is invalid.")
        if any(type(pack[key]) is not int for key in ("records", "archive_bytes", "installed_bytes")) or pack["records"] < 0:
            raise ValueError("A collection count or size is invalid.")
        if not isinstance(pack["files"], list) or not isinstance(pack["countries"], list):
            raise ValueError("A collection file or coverage list is invalid.")
        if not ID.fullmatch(pack["id"]) or not VERSION.fullmatch(pack["version"]):
            raise ValueError("A collection identifier or version is invalid.")
        key = pack["id"], pack["version"]
        if key in seen or not SHA.fullmatch(pack["archive_sha256"]):
            raise ValueError("A collection version is duplicated or has an invalid checksum.")
        seen.add(key)
        _download_url(pack["download_url"])
        _source_url(pack["source_url"])
        _source_url(pack["citation_url"])
        countries = set()
        if len(pack["countries"]) > 1000:
            raise ValueError("The collection coverage list is too large.")
        for country in pack["countries"]:
            if (not isinstance(country, dict) or set(country) != {"label", "value", "records"}
                    or any(not isinstance(country[key], str) or not country[key]
                           or len(country[key]) > 100 or any(ord(char) < 32 for char in country[key])
                           for key in ("label", "value"))
                    or type(country["records"]) is not int or country["records"] < 0
                    or country["value"] in countries):
                raise ValueError("A collection country definition is invalid.")
            countries.add(country["value"])
        if not 1 <= pack["archive_bytes"] <= 2 * 1024**3 or not 1 <= pack["installed_bytes"] <= 16 * 1024**3:
            raise ValueError("A collection exceeds the supported storage bounds.")
        if not 1 <= len(pack["files"]) <= 1024:
            raise ValueError("A collection has an unsupported number of files.")
        names = set()
        for row in pack["files"]:
            common = {"name", "bytes", "sha256"}
            database_fields = {"schema", "record_table", "records", "user_version"}
            if (not isinstance(row, dict) or not common.issubset(row) or not isinstance(row["name"], str)
                    or set(row) != common | (database_fields if row["name"].endswith(".sqlite") else set())
                    or type(row["bytes"]) is not int or not isinstance(row["sha256"], str)):
                raise ValueError("A collection file definition is invalid.")
            if (not FILENAME.fullmatch(row["name"]) or row["name"] in names
                    or row["name"] in (".", "..") or not SHA.fullmatch(row["sha256"])
                    or not 1 <= row["bytes"] <= 2 * 1024**3):
                raise ValueError("A collection file is invalid.")
            names.add(row["name"])
            if row["name"].endswith(".sqlite"):
                if (not isinstance(row["schema"], dict) or not isinstance(row["record_table"], str)
                        or type(row["records"]) is not int or type(row["user_version"]) is not int
                        or not SQL_NAME.fullmatch(row["record_table"]) or row["records"] < 0
                        or not 0 <= row["user_version"] <= 2**31 - 1
                        or not row["schema"] or len(row["schema"]) > 100
                        or row["record_table"] not in row["schema"]
                        or any(not isinstance(name, str) or not SQL_NAME.fullmatch(name)
                               or not isinstance(columns, list) or not 1 <= len(columns) <= 200
                               or any(not isinstance(column, str) or not SQL_NAME.fullmatch(column) for column in columns)
                               or len(set(columns)) != len(columns)
                               for name, columns in row["schema"].items())):
                    raise ValueError("A collection database definition is invalid.")
        if sum(row["bytes"] for row in pack["files"]) != pack["installed_bytes"]:
            raise ValueError("The collection storage count is inconsistent.")
    return document["packs"]


def catalog_definitions(path=None):
    path = Path(CATALOG if path is None else path).resolve()
    attributes = path.stat()
    return json.loads(json.dumps(_catalog(str(path), attributes.st_mtime_ns, attributes.st_size)))


def _hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inside(root, path):
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError("A collection path leaves its local storage folder.")
    return path


@lru_cache(maxsize=2048)
def _verified_file(path, size, modified, changed, expected):
    return _hash(Path(path)) == expected


def _check_files(root, pack, *, database_checks=False):
    expected = {row["name"] for row in pack["files"]}
    if not root.is_dir() or root.is_symlink() or {path.name for path in root.iterdir()} != expected:
        raise ValueError("The installed collection is incomplete or contains unexpected files.")
    for row in pack["files"]:
        path = _inside(root, root / row["name"])
        details = path.stat()
        if (details.st_size != row["bytes"] or not _verified_file(
                str(path.resolve()), details.st_size, details.st_mtime_ns, details.st_ctime_ns, row["sha256"])):
            raise ValueError("A collection file does not match its published checksum.")
        if database_checks and path.suffix == ".sqlite":
            with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)) as connection:
                if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("The collection database failed its integrity check.")
                if connection.execute("PRAGMA user_version").fetchone()[0] != row["user_version"]:
                    raise ValueError("The collection database version is unsupported.")
                for table, columns in row["schema"].items():
                    found = [entry[1] for entry in connection.execute(f'PRAGMA table_info("{table}")')]  # nosec B608: checked identifier from the publisher catalog, never query text
                    if found != columns:
                        raise ValueError("The collection database columns changed.")
                count = connection.execute(f'SELECT count(*) FROM "{row["record_table"]}"').fetchone()[0]  # nosec B608: checked publisher identifier
                if count != row["records"] or connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                    raise ValueError("The collection record count or relationships are inconsistent.")


class _CheckedRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        _download_url(new_url)
        return super().redirect_request(request, response, code, message, headers, new_url)


def _open_download(request, timeout):
    _download_url(request.full_url)
    return build_opener(_CheckedRedirect()).open(request, timeout=timeout)  # nosec B310: fixed catalog HTTPS URLs and allowlisted redirects


class PackStore:
    def __init__(self, root=None, catalog_path=None):
        self.root = Path(root or os.environ.get("CLOVIS_PACKS_PATH") or Path.home() / "Clovis Local" / "packs").resolve()
        self.definitions = catalog_definitions(catalog_path)

    def definition(self, identifier):
        if not isinstance(identifier, str) or not ID.fullmatch(identifier):
            raise ValueError("Choose a collection in the catalog.")
        matches = [row for row in self.definitions if row["id"] == identifier]
        if not matches:
            raise ValueError("Choose a collection in the catalog.")
        return max(matches, key=lambda row: tuple(int(part) for part in row["version"].split(".")))

    def installed_definition(self, identifier):
        self.definition(identifier)
        pointer = _inside(self.root, self.root / identifier / "active.json")
        if not pointer.is_file():
            return None
        value = _json(pointer)
        if (not isinstance(value, dict) or set(value) != {"id", "version", "archive_sha256"} or value["id"] != identifier
                or not isinstance(value["archive_sha256"], str) or not SHA.fullmatch(value["archive_sha256"])):
            raise ValueError("The saved collection selection is invalid.")
        matches = [row for row in self.definitions if row["id"] == identifier
                   and row["version"] == value["version"] and row["archive_sha256"] == value["archive_sha256"]]
        if len(matches) != 1:
            raise ValueError("This installed snapshot is absent from the current collection catalog.")
        return matches[0]

    def resolve_file(self, identifier, filename):
        pack = self.installed_definition(identifier)
        if pack is None:
            return None
        if filename not in {row["name"] for row in pack["files"]}:
            raise ValueError("Choose a file in the installed collection.")
        directory = _inside(self.root, self.root / identifier / pack["archive_sha256"])
        _check_files(directory, pack)
        return _inside(self.root, directory / filename)

    def status(self, identifier):
        latest = self.definition(identifier)
        try:
            active = self.installed_definition(identifier)
            if active is None:
                return {"state": "available", "version": None, "message": "Not installed"}
            self.resolve_file(identifier, active["files"][0]["name"])
            return {"state": "installed" if active["archive_sha256"] == latest["archive_sha256"] else "update",
                    "version": active["version"], "message": "Installed" if active["archive_sha256"] == latest["archive_sha256"] else "Update available"}
        except (ValueError, OSError, sqlite3.Error):
            return {"state": "damaged", "version": None, "message": "The local collection needs verification. Existing files were preserved."}

    def install_archive(self, identifier, archive, progress=None):
        pack = self.definition(identifier)
        archive = Path(archive)
        if archive.stat().st_size != pack["archive_bytes"] or _hash(archive) != pack["archive_sha256"]:
            raise ValueError("The download does not match the published collection checksum.")
        self.root.mkdir(parents=True, exist_ok=True)
        parent = _inside(self.root, self.root / identifier)
        parent.mkdir(exist_ok=True)
        staging = _inside(self.root, parent / (".install-" + uuid4().hex))
        staging.mkdir()
        written = []
        try:
            with zipfile.ZipFile(archive) as zipped:
                entries = zipped.infolist()
                expected = {row["name"]: row for row in pack["files"]}
                if len(entries) != len(expected) or {entry.filename for entry in entries} != set(expected):
                    raise ValueError("The collection archive has missing or unexpected files.")
                completed = 0
                for entry in entries:
                    definition = expected[entry.filename]
                    kind = stat.S_IFMT(entry.external_attr >> 16)
                    if (entry.is_dir() or kind not in (0, stat.S_IFREG) or entry.flag_bits & 1
                            or entry.file_size != definition["bytes"]):
                        raise ValueError("The collection archive contains an unsupported file.")
                    target = _inside(staging, staging / entry.filename)
                    digest = hashlib.sha256()
                    written.append(target)
                    total = 0
                    with zipped.open(entry) as source, target.open("xb") as output:
                        for block in iter(lambda: source.read(1024 * 1024), b""):
                            total += len(block)
                            if total > definition["bytes"]:
                                raise ValueError("An expanded collection file is too large.")
                            digest.update(block)
                            output.write(block)
                            if progress:
                                progress("Checking collection", completed + total, pack["installed_bytes"])
                        output.flush()
                        os.fsync(output.fileno())
                    if total != definition["bytes"] or digest.hexdigest() != definition["sha256"]:
                        raise ValueError("An expanded collection file failed verification.")
                    completed += total
            _check_files(staging, pack, database_checks=True)
            destination = _inside(self.root, parent / pack["archive_sha256"])
            if destination.exists():
                try:
                    _check_files(destination, pack, database_checks=True)
                except (ValueError, sqlite3.Error):
                    preserved = _inside(self.root, parent / ("preserved-" + pack["archive_sha256"][:16] + "-" + uuid4().hex))
                    destination.rename(preserved)
                    staging.rename(destination)
                    written = []
            else:
                try:
                    staging.rename(destination)
                    written = []
                except FileExistsError:
                    _check_files(destination, pack, database_checks=True)
            pointer = _inside(self.root, parent / ("active-" + uuid4().hex + ".tmp"))
            try:
                with pointer.open("x", encoding="utf-8") as output:
                    json.dump({"id": identifier, "version": pack["version"], "archive_sha256": pack["archive_sha256"]}, output)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(pointer, _inside(self.root, parent / "active.json"))
            finally:
                if pointer.exists():
                    _inside(self.root, pointer).unlink()
            return {"id": identifier, "version": pack["version"], "records": pack["records"]}
        finally:
            # Only this operation's uniquely named, verified temporary files.
            for target in written:
                if target.exists():
                    _inside(self.root, target).unlink()
            if staging.exists():
                _inside(self.root, staging).rmdir()

    def download(self, identifier, progress=None, opener=None):
        pack = self.definition(identifier)
        opener = opener or _open_download
        directory = _inside(self.root, self.root / ".downloads")
        directory.mkdir(parents=True, exist_ok=True)
        partial = _inside(self.root, directory / (identifier + "-" + pack["archive_sha256"] + ".part"))
        if partial.exists() and partial.stat().st_size > pack["archive_bytes"]:
            raise ValueError("The retained partial download exceeds the published size.")
        for attempt in range(3):
            offset = partial.stat().st_size if partial.exists() else 0
            if offset == pack["archive_bytes"]:
                break
            request = Request(_download_url(pack["download_url"]), headers={"User-Agent": "Clovis-local-collections/1.0"})
            if offset:
                request.add_header("Range", f"bytes={offset}-")
            try:
                with opener(request, timeout=60) as response:
                    status = response.status
                    if status == 206:
                        content_range = response.headers.get("Content-Range", "")
                        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", content_range)
                        if (match is None or int(match[1]) != offset or int(match[3]) != pack["archive_bytes"]
                                or int(match[2]) >= pack["archive_bytes"] or int(match[2]) < offset):
                            raise ValueError("The publisher returned an inconsistent resumed download.")
                    elif status == 200:
                        offset = 0
                    else:
                        raise ValueError("The publisher returned an unsupported download response.")
                    with partial.open("ab" if offset else "wb") as output:
                        received = offset
                        for block in iter(lambda: response.read(1024 * 1024), b""):
                            received += len(block)
                            if received > pack["archive_bytes"]:
                                raise ValueError("The download exceeds the published collection size.")
                            output.write(block)
                            if progress:
                                progress("Downloading", received, pack["archive_bytes"])
                        output.flush()
                        os.fsync(output.fileno())
                if partial.stat().st_size != pack["archive_bytes"]:
                    raise OSError("The collection download stopped before completion.")
                break
            except (URLError, TimeoutError, OSError, HTTPError):
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)
        if progress:
            progress("Verifying download", pack["archive_bytes"], pack["archive_bytes"])
        try:
            result = self.install_archive(identifier, partial, progress)
        except ValueError:
            if _hash(partial) != pack["archive_sha256"]:
                partial.rename(_inside(self.root, directory / ("invalid-" + uuid4().hex)))
            raise
        if progress:
            progress("Installed", pack["archive_bytes"], pack["archive_bytes"])
        return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Install and inspect Clovis local data collections.")
    parser.add_argument("action", choices=("list", "install"))
    parser.add_argument("collection", nargs="?")
    parser.add_argument("--archive", type=Path, help="Install an already downloaded official collection archive.")
    arguments = parser.parse_args()
    store = PackStore()
    if arguments.action == "list":
        for identifier in sorted({row["id"] for row in store.definitions}):
            pack = store.definition(identifier)
            print(f'{identifier}: {pack["records"]:,} {pack["record_type"]}; {store.status(identifier)["message"]}')
    elif arguments.archive:
        print(json.dumps(store.install_archive(arguments.collection, arguments.archive)))
    else:
        print(json.dumps(store.download(arguments.collection, progress=lambda phase, received, total: print(
            f"{phase}: {received:,}/{total:,} bytes", flush=True))))


if __name__ == "__main__":
    main()
