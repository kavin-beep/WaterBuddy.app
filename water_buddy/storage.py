"""Atomic JSON persistence for a private, local Water Buddy profile."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from collections.abc import Mapping, MutableMapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from water_buddy.domain import default_state, normalize_state, validate_backup_payload


class StorageError(RuntimeError):
    """Raised when Water Buddy data cannot be read or written safely."""


class _PrimaryCommittedStorageError(StorageError):
    """Raised when the primary committed but its recovery copy did not."""


_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[Path, threading.RLock] = {}


def _lock_for(path: Path) -> threading.RLock:
    resolved = path.resolve()
    with _LOCKS_GUARD:
        return _PATH_LOCKS.setdefault(resolved, threading.RLock())


class JsonStore:
    """Read and atomically write one normalized Water Buddy JSON document."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.backup_path = self.path.with_name(f"{self.path.name}.bak")
        self._lock = _lock_for(self.path)
        self.last_recovery_path: Path | None = None
        self.last_backup_recovery_path: Path | None = None

    def load(self) -> dict[str, Any]:
        """Load normalized data, recovering from the last-known-good copy."""

        with self._lock:
            self.last_recovery_path = None
            self.last_backup_recovery_path = None
            now = datetime.now(timezone.utc).astimezone().replace(tzinfo=None)

            if not self.path.exists():
                state = self._recover_backup_or_default(now)
                self._persist(state)
                return state
            if not self.path.is_file():
                raise StorageError(f"Data path is not a file: {self.path}")

            try:
                raw_data, normalized = self._read_and_validate(self.path, now)
            except (UnicodeError, json.JSONDecodeError, ValueError, TypeError):
                self.last_recovery_path = self._preserve_required(self.path)
                state = self._recover_backup_or_default(now)
                self._persist(state)
                return state
            except OSError as error:
                raise StorageError(
                    f"Could not read Water Buddy data at {self.path}"
                ) from error

            backup_needs_healing = False
            if not self.backup_path.exists():
                backup_needs_healing = True
            elif not self.backup_path.is_file():
                raise StorageError(f"Backup path is not a file: {self.backup_path}")
            else:
                try:
                    _, backup_state = self._read_and_validate(self.backup_path, now)
                    backup_needs_healing = backup_state != normalized
                except (UnicodeError, json.JSONDecodeError, ValueError, TypeError):
                    self.last_backup_recovery_path = self._preserve_required(
                        self.backup_path
                    )
                    backup_needs_healing = True
                except OSError as error:
                    raise StorageError(
                        f"Could not read Water Buddy backup at {self.backup_path}"
                    ) from error

            if normalized != raw_data or backup_needs_healing:
                self._persist(normalized)
            return normalized

    def save(self, data: Mapping[str, Any]) -> None:
        """Normalize and atomically persist a state snapshot and recovery copy."""

        if not isinstance(data, Mapping):
            raise TypeError("Water Buddy state must be a mapping.")
        with self._lock:
            now = datetime.now(timezone.utc).astimezone().replace(tzinfo=None)
            normalized = normalize_state(data, now)
            normalized["metadata"]["updated_at"] = now.isoformat(timespec="seconds")
            try:
                self._persist(normalized)
            except StorageError:
                if isinstance(data, MutableMapping):
                    self._synchronize_from_primary_best_effort(data, now)
                raise
            if isinstance(data, MutableMapping):
                self._replace_mutable_state(data, normalized)

    def _read_and_validate(
        self,
        source: Path,
        now: datetime,
    ) -> tuple[Any, dict[str, Any]]:
        raw = json.loads(source.read_text(encoding="utf-8"))
        return raw, validate_backup_payload(raw, now)

    def _recover_backup_or_default(self, now: datetime) -> dict[str, Any]:
        if not self.backup_path.exists():
            return default_state(now)
        if not self.backup_path.is_file():
            raise StorageError(f"Backup path is not a file: {self.backup_path}")
        try:
            _, normalized = self._read_and_validate(self.backup_path, now)
            return normalized
        except (UnicodeError, json.JSONDecodeError, ValueError, TypeError):
            self.last_backup_recovery_path = self._preserve_required(self.backup_path)
            return default_state(now)
        except OSError as error:
            raise StorageError(
                f"Could not read Water Buddy backup at {self.backup_path}"
            ) from error

    def _persist(self, data: Mapping[str, Any]) -> None:
        try:
            payload = json.dumps(
                data,
                indent=2,
                # ASCII escaping keeps even unusual but parseable JSON strings
                # (including lone surrogate escapes) safely writable as UTF-8.
                ensure_ascii=True,
                sort_keys=True,
                allow_nan=False,
            ) + "\n"
        except (TypeError, ValueError, OverflowError) as error:
            raise StorageError("Water Buddy data cannot be encoded as JSON.") from error

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            for target, label in (
                (self.path, "Data"),
                (self.backup_path, "Backup"),
            ):
                if (target.exists() or target.is_symlink()) and not target.is_file():
                    raise StorageError(f"{label} path is not a file: {target}")
        except StorageError:
            raise
        except (OSError, UnicodeError) as error:
            raise StorageError(
                f"Could not save Water Buddy data at {self.path}"
            ) from error

        # Commit the authoritative primary first. If the backup write is
        # interrupted, the next load can heal it from the newer primary;
        # writing backup first could let an older primary erase newer data.
        try:
            self._atomic_replace(self.path, payload)
        except (OSError, UnicodeError) as error:
            raise StorageError(
                f"Could not save Water Buddy data at {self.path}"
            ) from error

        try:
            self._atomic_replace(self.backup_path, payload)
        except (OSError, UnicodeError) as error:
            raise _PrimaryCommittedStorageError(
                f"Could not save Water Buddy data at {self.path}"
            ) from error

    def _synchronize_from_primary_best_effort(
        self,
        data: MutableMapping[str, Any],
        now: datetime,
    ) -> None:
        try:
            if not self.path.is_file():
                return
            _, normalized = self._read_and_validate(self.path, now)
            self._replace_mutable_state(data, normalized)
        except Exception:  # noqa: BLE001 - recovery must not mask the save error.
            return

    @staticmethod
    def _replace_mutable_state(
        data: MutableMapping[str, Any],
        normalized: Mapping[str, Any],
    ) -> None:
        data.clear()
        data.update(normalized)

    @staticmethod
    def _atomic_replace(target: Path, payload: str) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
            text=True,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                descriptor = -1
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, target)
        except BaseException:
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def _preserve_required(self, source: Path) -> Path:
        preserved = self._preserve_corrupt_file(source)
        if preserved is None:
            raise StorageError(f"Could not preserve corrupt data at {source}")
        return preserved

    @staticmethod
    def _preserve_corrupt_file(source: Path) -> Path | None:
        if not source.exists():
            return None
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        candidate = source.with_name(f"{source.name}.corrupt-{stamp}.bak")
        counter = 1
        while candidate.exists():
            candidate = source.with_name(
                f"{source.name}.corrupt-{stamp}-{counter}.bak"
            )
            counter += 1
        try:
            shutil.copy2(source, candidate)
            return candidate
        except OSError:
            return None
