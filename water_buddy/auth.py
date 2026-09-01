"""Secure, local-only account management for Water Buddy.

The module deliberately keeps authentication independent from Streamlit.  It
stores only salted PBKDF2 password verifiers, serializes updates atomically,
and returns small dictionaries that are safe to place in ``session_state``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import tempfile
import threading
import unicodedata
import uuid
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final, TypedDict

SCHEMA_VERSION: Final[int] = 1
PBKDF2_ALGORITHM: Final[str] = "pbkdf2_hmac_sha256"
DEFAULT_PBKDF2_ITERATIONS: Final[int] = 600_000
DEFAULT_MAX_ATTEMPTS: Final[int] = 5
DEFAULT_LOCKOUT_SECONDS: Final[int] = 300
_SALT_BYTES: Final[int] = 16
_DERIVED_KEY_BYTES: Final[int] = 32
_MIN_PASSWORD_LENGTH: Final[int] = 8
_MAX_PASSWORD_BYTES: Final[int] = 1_024
_LOCAL_PART_RE: Final[re.Pattern[str]] = re.compile(
    r"^[a-z0-9!#$%&'*+/=?^_`{|}~.-]+$",
    re.IGNORECASE,
)
_DOMAIN_LABEL_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9-]+$", re.IGNORECASE)


class PublicAccount(TypedDict):
    """Account fields that are safe to expose to application code."""

    user_id: str
    display_name: str
    email: str
    created_at: str


class AccountError(Exception):
    """Base class for expected authentication errors.

    ``user_message`` is intentionally safe to show in a UI.  Internal file or
    password details are never included in it.
    """

    default_message: str = "Authentication could not be completed."

    def __init__(self, user_message: str | None = None) -> None:
        self.user_message = user_message or self.default_message
        super().__init__(self.user_message)


class AuthValidationError(AccountError, ValueError):
    """Raised when registration input is not acceptable."""

    default_message = "Please check the account details and try again."


class DuplicateAccountError(AccountError):
    """Raised when a normalized email address is already registered."""

    default_message = "An account with that email address already exists."


class InvalidCredentialsError(AccountError):
    """Raised for an unknown email or incorrect password."""

    default_message = "The email or password is incorrect."


class AccountLockedError(AccountError):
    """Raised while a temporary login lockout is active."""

    default_message = "Too many login attempts. Please try again shortly."

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = max(1, int(retry_after_seconds))
        super().__init__(self.default_message)


class AccountStorageError(AccountError):
    """Raised when local account data cannot be accessed without risking loss."""

    default_message = "Local account data could not be opened safely."


def normalize_email(email: str) -> str:
    """Return a canonical email address or raise :class:`AuthValidationError`.

    The local part is case-folded for predictable duplicate detection in this
    single-user application, and internationalized domains are stored in their
    ASCII IDNA form.
    """

    if not isinstance(email, str):
        raise AuthValidationError("Enter a valid email address.")
    candidate = unicodedata.normalize("NFKC", email).strip().casefold()
    if len(candidate) > 254 or candidate.count("@") != 1:
        raise AuthValidationError("Enter a valid email address.")

    local, domain = candidate.rsplit("@", 1)
    if (
        not local
        or len(local.encode("utf-8")) > 64
        or local.startswith(".")
        or local.endswith(".")
        or ".." in local
        or _LOCAL_PART_RE.fullmatch(local) is None
    ):
        raise AuthValidationError("Enter a valid email address.")

    try:
        ascii_domain = domain.rstrip(".").encode("idna").decode("ascii").casefold()
    except (UnicodeError, ValueError) as exc:
        raise AuthValidationError("Enter a valid email address.") from exc

    labels = ascii_domain.split(".")
    if len(ascii_domain) > 253 or len(labels) < 2:
        raise AuthValidationError("Enter a valid email address.")
    if any(
        not label
        or len(label) > 63
        or label.startswith("-")
        or label.endswith("-")
        or _DOMAIN_LABEL_RE.fullmatch(label) is None
        for label in labels
    ):
        raise AuthValidationError("Enter a valid email address.")
    if len(labels[-1]) < 2 or labels[-1].isdigit():
        raise AuthValidationError("Enter a valid email address.")
    return f"{local}@{ascii_domain}"


def validate_display_name(display_name: str) -> str:
    """Normalize and validate a user-facing display name."""

    if not isinstance(display_name, str):
        raise AuthValidationError("Enter a display name between 2 and 60 characters.")
    normalized = " ".join(unicodedata.normalize("NFKC", display_name).split())
    if not 2 <= len(normalized) <= 60:
        raise AuthValidationError("Enter a display name between 2 and 60 characters.")
    if any(unicodedata.category(char).startswith("C") for char in normalized):
        raise AuthValidationError("The display name contains unsupported characters.")
    if "<" in normalized or ">" in normalized:
        raise AuthValidationError("The display name contains unsupported characters.")
    return normalized


def validate_password(password: str) -> None:
    """Validate password length without imposing brittle composition rules."""

    if not isinstance(password, str):
        raise AuthValidationError("Use a password with at least 8 characters.")
    encoded = password.encode("utf-8")
    if len(password) < _MIN_PASSWORD_LENGTH:
        raise AuthValidationError("Use a password with at least 8 characters.")
    if len(encoded) > _MAX_PASSWORD_BYTES or "\x00" in password:
        raise AuthValidationError("The password is too long or contains unsupported characters.")


class AccountStore:
    """Thread-safe JSON account store backed by atomic filesystem updates.

    Args:
        path: Location of the private JSON account database.
        pbkdf2_iterations: Work factor for newly registered passwords.
        max_attempts: Failed attempts allowed before a temporary lockout.
        lockout_seconds: Fixed lockout duration, capped at 24 hours.
        clock: Optional UTC clock used for deterministic testing.
    """

    _locks_guard: Final[threading.Lock] = threading.Lock()
    _path_locks: Final[dict[str, threading.RLock]] = {}

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        pbkdf2_iterations: int = DEFAULT_PBKDF2_ITERATIONS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        lockout_seconds: int = DEFAULT_LOCKOUT_SECONDS,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = Path(path).expanduser().resolve()
        self.backup_path = self.path.with_name(f"{self.path.name}.bak")
        if not 100_000 <= pbkdf2_iterations <= 10_000_000:
            raise ValueError("pbkdf2_iterations must be between 100,000 and 10,000,000")
        if not 2 <= max_attempts <= 20:
            raise ValueError("max_attempts must be between 2 and 20")
        if not 1 <= lockout_seconds <= 86_400:
            raise ValueError("lockout_seconds must be between 1 and 86,400")
        self.pbkdf2_iterations = int(pbkdf2_iterations)
        self.max_attempts = int(max_attempts)
        self.lockout_seconds = int(lockout_seconds)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = self._lock_for_path(self.path)

        # Eager initialization catches corruption before the first form submit.
        with self._lock:
            self._load_document_unlocked()

    @classmethod
    def _lock_for_path(cls, path: Path) -> threading.RLock:
        key = os.path.normcase(str(path))
        with cls._locks_guard:
            return cls._path_locks.setdefault(key, threading.RLock())

    def register(self, display_name: str, email: str, password: str) -> PublicAccount:
        """Create an account and return its public, session-safe fields.

        Raises:
            AuthValidationError: If any registration field is invalid.
            DuplicateAccountError: If the normalized email already exists.
        """

        clean_name = validate_display_name(display_name)
        clean_email = normalize_email(email)
        validate_password(password)
        now = self._now()

        with self._lock:
            document = self._load_document_unlocked()
            accounts = document["accounts"]
            if clean_email in accounts:
                raise DuplicateAccountError()

            account: dict[str, Any] = {
                "user_id": str(uuid.uuid4()),
                "display_name": clean_name,
                "email": clean_email,
                "created_at": self._format_time(now),
                "updated_at": self._format_time(now),
                "password_verifier": self._new_password_verifier(password),
                "security": {
                    "failed_attempts": 0,
                    "locked_until": None,
                    "last_failed_at": None,
                },
            }
            accounts[clean_email] = account
            document["metadata"]["updated_at"] = self._format_time(now)
            self._write_document_unlocked(document)
            return self._public_account(account)

    def authenticate(self, email: str, password: str) -> PublicAccount:
        """Authenticate credentials and return public account fields.

        Unknown emails and wrong passwords both raise
        :class:`InvalidCredentialsError`.  Repeated failures produce a fixed,
        bounded lockout and raise :class:`AccountLockedError`.
        """

        try:
            clean_email = normalize_email(email)
        except AuthValidationError:
            clean_email = ""
        supplied_password = password if isinstance(password, str) else ""
        now = self._now()

        with self._lock:
            document = self._load_document_unlocked()
            account = document["accounts"].get(clean_email)
            if not isinstance(account, dict):
                # Equalize the expensive part of unknown-user and wrong-password paths.
                self._verify_password(
                    supplied_password,
                    self._dummy_password_verifier(),
                )
                raise InvalidCredentialsError()

            security = account["security"]
            locked_until = self._parse_time(security.get("locked_until"))
            if locked_until is not None and locked_until > now:
                retry = max(1, int((locked_until - now).total_seconds() + 0.999))
                raise AccountLockedError(retry)
            if locked_until is not None:
                security["failed_attempts"] = 0
                security["locked_until"] = None

            verifier = account["password_verifier"]
            if not self._verify_password(supplied_password, verifier):
                attempts = min(
                    self.max_attempts,
                    int(security.get("failed_attempts", 0)) + 1,
                )
                security["failed_attempts"] = attempts
                security["last_failed_at"] = self._format_time(now)
                document["metadata"]["updated_at"] = self._format_time(now)
                if attempts >= self.max_attempts:
                    locked_until = now + timedelta(seconds=self.lockout_seconds)
                    security["locked_until"] = self._format_time(locked_until)
                    self._write_document_unlocked(document)
                    raise AccountLockedError(self.lockout_seconds)
                self._write_document_unlocked(document)
                raise InvalidCredentialsError()

            security["failed_attempts"] = 0
            security["locked_until"] = None
            security["last_failed_at"] = None
            account["updated_at"] = self._format_time(now)
            if int(verifier["iterations"]) < self.pbkdf2_iterations:
                account["password_verifier"] = self._new_password_verifier(supplied_password)
            document["metadata"]["updated_at"] = self._format_time(now)
            self._write_document_unlocked(document)
            return self._public_account(account)

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime):
            raise TypeError("clock must return a datetime")
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _new_document(self) -> dict[str, Any]:
        timestamp = self._format_time(self._now())
        return {
            "schema_version": SCHEMA_VERSION,
            "accounts": {},
            "metadata": {"created_at": timestamp, "updated_at": timestamp},
        }

    def _new_password_verifier(self, password: str) -> dict[str, Any]:
        salt = secrets.token_bytes(_SALT_BYTES)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            self.pbkdf2_iterations,
            dklen=_DERIVED_KEY_BYTES,
        )
        return {
            "algorithm": PBKDF2_ALGORITHM,
            "iterations": self.pbkdf2_iterations,
            "salt": base64.b64encode(salt).decode("ascii"),
            "digest": base64.b64encode(digest).decode("ascii"),
        }

    def _dummy_password_verifier(self) -> dict[str, Any]:
        # The expected value need not correspond to a real password.  Keeping it
        # static means an unknown-user attempt performs exactly one PBKDF2 (in
        # ``_verify_password``), just like a wrong-password attempt.
        salt = hashlib.sha256(b"water-buddy-invalid-account").digest()[:_SALT_BYTES]
        digest = hashlib.sha256(b"water-buddy-dummy-verifier").digest()
        return {
            "algorithm": PBKDF2_ALGORITHM,
            "iterations": self.pbkdf2_iterations,
            "salt": base64.b64encode(salt).decode("ascii"),
            "digest": base64.b64encode(digest).decode("ascii"),
        }

    @staticmethod
    def _verify_password(password: str, verifier: Mapping[str, Any]) -> bool:
        try:
            if verifier.get("algorithm") != PBKDF2_ALGORITHM:
                return False
            iterations = int(verifier["iterations"])
            if not 100_000 <= iterations <= 10_000_000:
                return False
            salt = base64.b64decode(str(verifier["salt"]), validate=True)
            expected = base64.b64decode(str(verifier["digest"]), validate=True)
            if len(salt) < 16 or len(expected) != _DERIVED_KEY_BYTES:
                return False
            candidate = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                iterations,
                dklen=len(expected),
            )
        except (KeyError, TypeError, ValueError, UnicodeError):
            return False
        return hmac.compare_digest(candidate, expected)

    @staticmethod
    def _public_account(account: Mapping[str, Any]) -> PublicAccount:
        return {
            "user_id": str(account["user_id"]),
            "display_name": str(account["display_name"]),
            "email": str(account["email"]),
            "created_at": str(account["created_at"]),
        }

    def _load_document_unlocked(self) -> dict[str, Any]:
        try:
            if not self.path.exists():
                document = self._new_document()
                self._write_document_unlocked(document)
                return document
            document = self._read_and_validate(self.path)
        except FileNotFoundError:
            # Another process may have removed the file between ``exists`` and
            # ``read_text``. Recreate a valid empty store atomically.
            document = self._new_document()
            self._write_document_unlocked(document)
            return document
        except (UnicodeError, json.JSONDecodeError, ValueError, TypeError):
            if self._preserve_corrupt_file(self.path) is None and self.path.exists():
                raise AccountStorageError()
            document = self._recover_backup_unlocked()
            self._write_document_unlocked(document)
        except OSError as exc:
            raise AccountStorageError() from exc
        return document

    def _recover_backup_unlocked(self) -> dict[str, Any]:
        if self.backup_path.exists():
            try:
                return self._read_and_validate(self.backup_path)
            except (UnicodeError, json.JSONDecodeError, ValueError, TypeError):
                if self._preserve_corrupt_file(self.backup_path) is None:
                    raise AccountStorageError()
            except OSError as exc:
                raise AccountStorageError() from exc
        return self._new_document()

    def _read_and_validate(self, path: Path) -> dict[str, Any]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not isinstance(raw.get("accounts"), dict):
            raise ValueError("invalid account document")
        if int(raw.get("schema_version", 0)) != SCHEMA_VERSION:
            raise ValueError("unsupported account schema")
        metadata = raw.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError("invalid account metadata")

        for email_key, account in raw["accounts"].items():
            if not isinstance(email_key, str) or not isinstance(account, dict):
                raise ValueError("invalid account entry")
            if normalize_email(email_key) != email_key or account.get("email") != email_key:
                raise ValueError("invalid account email")
            try:
                uuid.UUID(str(account["user_id"]))
                validate_display_name(str(account["display_name"]))
            except (KeyError, ValueError, AuthValidationError) as exc:
                raise ValueError("invalid account identity") from exc
            verifier = account.get("password_verifier")
            security = account.get("security")
            if not isinstance(verifier, dict) or not isinstance(security, dict):
                raise ValueError("invalid account security data")
            if verifier.get("algorithm") != PBKDF2_ALGORITHM:
                raise ValueError("unsupported password verifier")
            try:
                iterations = int(verifier["iterations"])
                salt = base64.b64decode(str(verifier["salt"]), validate=True)
                digest = base64.b64decode(str(verifier["digest"]), validate=True)
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("invalid password verifier") from exc
            if not 100_000 <= iterations <= 10_000_000:
                raise ValueError("invalid password work factor")
            if len(salt) < _SALT_BYTES or len(digest) != _DERIVED_KEY_BYTES:
                raise ValueError("invalid password verifier size")
            attempts = security.get("failed_attempts", 0)
            if isinstance(attempts, bool) or not isinstance(attempts, int):
                raise ValueError("invalid failed-attempt count")
            security["failed_attempts"] = min(self.max_attempts, max(0, attempts))
        return raw

    def _write_document_unlocked(self, document: Mapping[str, Any]) -> None:
        payload = json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # The backup mirrors the latest committed state, allowing exact
            # recovery if another process or manual edit damages the primary.
            self._atomic_replace(self.backup_path, payload)
            self._atomic_replace(self.path, payload)
        except OSError as exc:
            raise AccountStorageError() from exc

    @staticmethod
    def _atomic_replace(target: Path, payload: str) -> None:
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_name = handle.name
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, target)
            try:
                os.chmod(target, 0o600)
            except OSError:
                pass
        finally:
            if temporary_name is not None:
                try:
                    Path(temporary_name).unlink(missing_ok=True)
                except OSError:
                    pass

    def _preserve_corrupt_file(self, source: Path) -> Path | None:
        if not source.exists():
            return None
        stamp = self._now().strftime("%Y%m%dT%H%M%S%fZ")
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
            # The caller refuses to overwrite the damaged source when this
            # forensic copy cannot be made.
            return None

    @staticmethod
    def _format_time(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00",
            "Z",
        )

    @staticmethod
    def _parse_time(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)


def register(
    store: AccountStore,
    display_name: str,
    email: str,
    password: str,
) -> PublicAccount:
    """Register through ``store``; convenient for callback-oriented UIs."""

    return store.register(display_name, email, password)


def authenticate(store: AccountStore, email: str, password: str) -> PublicAccount:
    """Authenticate through ``store``; convenient for callback-oriented UIs."""

    return store.authenticate(email, password)


__all__ = [
    "AccountError",
    "AccountLockedError",
    "AccountStorageError",
    "AccountStore",
    "AuthValidationError",
    "DuplicateAccountError",
    "InvalidCredentialsError",
    "PublicAccount",
    "authenticate",
    "normalize_email",
    "register",
    "validate_display_name",
    "validate_password",
]
