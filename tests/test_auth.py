"""Tests for Water Buddy's local account store.

The suite uses only :mod:`unittest`, so it can run in a clean Python 3.12+
environment before optional development dependencies are installed.
"""

from __future__ import annotations

import json
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from water_buddy.auth import (
    AccountError,
    AccountLockedError,
    AccountStore,
    AuthValidationError,
    DuplicateAccountError,
    InvalidCredentialsError,
    authenticate,
    normalize_email,
    register,
    validate_display_name,
)

TEST_ITERATIONS = 100_000


class MutableClock:
    """Small deterministic clock used to test lockout expiry."""

    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value

    def advance(self, **kwargs: int) -> None:
        """Advance the current test time by a ``timedelta``."""

        self.value += timedelta(**kwargs)


class AccountStoreTests(unittest.TestCase):
    """Exercise validation, password handling, lockout, and recovery."""

    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self.root = Path(self._temporary_directory.name)

    def make_store(self, filename: str = "accounts.json", **kwargs: object) -> AccountStore:
        """Construct a store with a production-valid test work factor."""

        return AccountStore(
            self.root / filename,
            pbkdf2_iterations=TEST_ITERATIONS,
            **kwargs,
        )

    def test_email_and_display_name_normalization(self) -> None:
        self.assertEqual(
            normalize_email("  Person@EXAMPLE.com "),
            "person@example.com",
        )
        self.assertEqual(
            normalize_email("hello@bücher.de"),
            "hello@xn--bcher-kva.de",
        )
        self.assertEqual(validate_display_name("  River   Song  "), "River Song")

        for invalid in ("missing-at.example.com", "a@localhost", ".a@example.com"):
            with self.subTest(email=invalid), self.assertRaises(AuthValidationError):
                normalize_email(invalid)
        for invalid_name in ("A", "<script>", "A\x00B"):
            with self.subTest(name=invalid_name), self.assertRaises(AuthValidationError):
                validate_display_name(invalid_name)

    def test_registration_persists_without_plaintext(self) -> None:
        path = self.root / "accounts.json"
        store = self.make_store()
        account = store.register(
            "  Aqua   Friend ",
            " FRIEND@Example.COM ",
            "A-strong-local-password",
        )

        self.assertEqual(
            set(account),
            {"user_id", "display_name", "email", "created_at"},
        )
        self.assertEqual(account["display_name"], "Aqua Friend")
        self.assertEqual(account["email"], "friend@example.com")
        self.assertEqual(uuid.UUID(account["user_id"]).version, 4)
        self.assertTrue(path.exists())
        self.assertTrue(path.with_name("accounts.json.bak").exists())

        serialized = path.read_text(encoding="utf-8")
        self.assertNotIn("A-strong-local-password", serialized)
        record = json.loads(serialized)["accounts"]["friend@example.com"]
        verifier = record["password_verifier"]
        self.assertEqual(verifier["algorithm"], "pbkdf2_hmac_sha256")
        self.assertEqual(verifier["iterations"], TEST_ITERATIONS)
        self.assertTrue(verifier["salt"])
        self.assertTrue(verifier["digest"])

        reopened = self.make_store()
        self.assertEqual(
            reopened.authenticate("friend@example.com", "A-strong-local-password"),
            account,
        )

    def test_registration_validation_and_duplicates(self) -> None:
        store = self.make_store()
        with self.assertRaises(AuthValidationError):
            store.register("Valid Name", "not-an-email", "long-enough-password")
        with self.assertRaises(AuthValidationError):
            store.register("Valid Name", "valid@example.com", "short")

        store.register("First Person", "same@example.com", "long-enough-password")
        with self.assertRaises(DuplicateAccountError) as raised:
            store.register("Second Person", " SAME@example.com ", "different-password")
        self.assertIsInstance(raised.exception, AccountError)
        self.assertEqual(raised.exception.user_message, str(raised.exception))

    def test_invalid_credentials_use_one_safe_error(self) -> None:
        store = self.make_store()
        store.register("Aqua Friend", "friend@example.com", "correct-password")

        with self.assertRaises(InvalidCredentialsError) as wrong_password:
            store.authenticate("friend@example.com", "incorrect-password")
        with self.assertRaises(InvalidCredentialsError) as unknown_email:
            store.authenticate("unknown@example.com", "incorrect-password")
        with self.assertRaises(InvalidCredentialsError):
            store.authenticate("malformed", "incorrect-password")

        self.assertEqual(
            wrong_password.exception.user_message,
            unknown_email.exception.user_message,
        )
        self.assertNotIn("friend@example.com", wrong_password.exception.user_message)

    def test_login_lockout_is_bounded_and_expires(self) -> None:
        clock = MutableClock(datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc))
        store = self.make_store(
            max_attempts=3,
            lockout_seconds=60,
            clock=clock,
        )
        store.register("Aqua Friend", "friend@example.com", "correct-password")

        for _ in range(2):
            with self.assertRaises(InvalidCredentialsError):
                store.authenticate("friend@example.com", "wrong-password")
        with self.assertRaises(AccountLockedError) as threshold_error:
            store.authenticate("friend@example.com", "wrong-password")
        self.assertEqual(threshold_error.exception.retry_after_seconds, 60)

        with self.assertRaises(AccountLockedError) as still_locked:
            store.authenticate("friend@example.com", "correct-password")
        self.assertLessEqual(still_locked.exception.retry_after_seconds, 60)
        self.assertGreaterEqual(still_locked.exception.retry_after_seconds, 1)

        clock.advance(seconds=61)
        account = store.authenticate("friend@example.com", "correct-password")
        self.assertEqual(account["email"], "friend@example.com")
        with self.assertRaises(InvalidCredentialsError):
            store.authenticate("friend@example.com", "wrong-password")

    def test_corrupt_primary_recovers_latest_backup_and_preserves_evidence(self) -> None:
        path = self.root / "accounts.json"
        store = self.make_store()
        expected = store.register(
            "Backup User",
            "backup@example.com",
            "correct-password",
        )
        corrupt_bytes = b'{"accounts": this is not valid JSON'
        path.write_bytes(corrupt_bytes)

        recovered = self.make_store()
        self.assertEqual(
            recovered.authenticate("backup@example.com", "correct-password"),
            expected,
        )
        self.assertEqual(
            json.loads(path.read_text(encoding="utf-8"))["schema_version"],
            1,
        )
        preserved = list(self.root.glob("accounts.json.corrupt-*.bak"))
        self.assertEqual(len(preserved), 1)
        self.assertEqual(preserved[0].read_bytes(), corrupt_bytes)

    def test_corrupt_primary_and_backup_recover_cleanly(self) -> None:
        path = self.root / "accounts.json"
        store = self.make_store()
        store.register("Old User", "old@example.com", "correct-password")
        path.write_text("not-json-primary", encoding="utf-8")
        path.with_name("accounts.json.bak").write_text(
            "not-json-backup",
            encoding="utf-8",
        )

        recovered = self.make_store()
        with self.assertRaises(InvalidCredentialsError):
            recovered.authenticate("old@example.com", "correct-password")
        self.assertTrue(list(self.root.glob("accounts.json.corrupt-*.bak")))
        self.assertTrue(list(self.root.glob("accounts.json.bak.corrupt-*.bak")))
        document = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(document["accounts"], {})

    def test_module_wrappers(self) -> None:
        store = self.make_store()
        created = register(
            store,
            "Wrapper User",
            "wrapper@example.com",
            "correct-password",
        )
        signed_in = authenticate(store, "wrapper@example.com", "correct-password")
        self.assertEqual(signed_in, created)

    def test_constructor_rejects_unbounded_settings(self) -> None:
        path = self.root / "settings.json"
        with self.assertRaises(ValueError):
            AccountStore(path, max_attempts=1)
        with self.assertRaises(ValueError):
            AccountStore(path, lockout_seconds=86_401)
        with self.assertRaises(ValueError):
            AccountStore(path, pbkdf2_iterations=99_999)


if __name__ == "__main__":
    unittest.main()
