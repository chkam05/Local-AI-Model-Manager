import base64
import hashlib
from pathlib import Path
import re
from typing import ClassVar
import urllib.error
import urllib.parse
import urllib.request


class ChecksumService:
    """Discover and verify source-published SHA-256 checksums."""

    HTTP_TIMEOUT_SECONDS: ClassVar[int] = 10
    MAX_SIDECAR_BYTES: ClassVar[int] = 4096
    SHA256_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?i)(?<![0-9a-f])([0-9a-f]{64})(?![0-9a-f])"
    )
    SIDECAR_SUFFIXES: ClassVar[tuple[str, ...]] = (".sha256", ".sha256sum")

    def published_sha256(self, source: str) -> str | None:
        parsed = urllib.parse.urlparse(source)
        if parsed.scheme.casefold() in {"http", "https"}:
            return self._remote_sha256(source)
        return self._local_sha256(Path(source).expanduser())

    def verify_sha256(self, artifact: Path, expected: str | None) -> bool:
        if expected is None:
            return False
        digest = hashlib.sha256()
        with artifact.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        actual = digest.hexdigest()
        if actual.casefold() != expected.casefold():
            raise ValueError(
                f"SHA-256 checksum mismatch for {artifact.name}: "
                f"expected {expected}, got {actual}."
            )
        return True

    def _local_sha256(self, source: Path) -> str | None:
        candidates = tuple(
            Path(str(source) + suffix) for suffix in self.SIDECAR_SUFFIXES
        )
        for candidate in candidates:
            try:
                value = candidate.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            checksum = self._parse_hex_checksum(value)
            if checksum is not None:
                return checksum
        return None

    def _remote_sha256(self, source: str) -> str | None:
        request = urllib.request.Request(source, method="HEAD")
        try:
            with urllib.request.urlopen(
                request, timeout=self.HTTP_TIMEOUT_SECONDS
            ) as response:
                checksum = self._checksum_from_headers(response.headers)
        except (urllib.error.URLError, OSError, ValueError):
            checksum = None
        if checksum is not None:
            return checksum
        for suffix in self.SIDECAR_SUFFIXES:
            try:
                with urllib.request.urlopen(
                    source + suffix,
                    timeout=self.HTTP_TIMEOUT_SECONDS,
                ) as response:
                    value = response.read(self.MAX_SIDECAR_BYTES).decode(
                        "utf-8", errors="replace"
                    )
            except (urllib.error.URLError, OSError, ValueError):
                continue
            checksum = self._parse_hex_checksum(value)
            if checksum is not None:
                return checksum
        return None

    def _checksum_from_headers(self, headers) -> str | None:
        for name in ("X-Checksum-Sha256", "X-Checksum-SHA256"):
            checksum = self._parse_hex_checksum(headers.get(name, ""))
            if checksum is not None:
                return checksum
        digest = headers.get("Digest", "")
        match = re.search(r"(?i)(?:sha-256|sha256)=([^,;\s]+)", digest)
        if match is not None:
            value = match.group(1).strip('"')
            checksum = self._parse_hex_checksum(value)
            if checksum is not None:
                return checksum
            try:
                decoded = base64.b64decode(value, validate=True)
            except (ValueError, TypeError):
                decoded = b""
            if len(decoded) == 32:
                return decoded.hex()
        for name in ("X-Linked-Etag", "ETag"):
            checksum = self._parse_hex_checksum(headers.get(name, ""))
            if checksum is not None:
                return checksum
        return None

    @classmethod
    def _parse_hex_checksum(cls, value: str) -> str | None:
        match = cls.SHA256_PATTERN.search(value)
        return match.group(1).casefold() if match is not None else None
