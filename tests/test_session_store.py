"""Windows DPAPI exercised using temporary synthetic sessions only."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "control_center"))
from session_store import SessionStore


class SessionStoreTests(unittest.TestCase):
    def test_dpapi_roundtrip_preserves_expiry_and_hides_tokens(self):
        with tempfile.TemporaryDirectory(prefix="EnuguSessionContract_") as folder:
            path = Path(folder) / "synthetic.dat"
            store = SessionStore(path)
            session = {"tokens": {"access_token": "synthetic-token-never-used", "expires_at": 12345, "refresh_token": "synthetic-refresh"}}
            store.save(session)
            self.assertEqual(session, store.load())
            self.assertNotIn(b"synthetic-token", path.read_bytes())
            self.assertNotIn(b"synthetic-refresh", path.read_bytes())
            store.clear()
            self.assertIsNone(store.load())

    def test_corrupt_saved_session_is_not_restored(self):
        with tempfile.TemporaryDirectory(prefix="EnuguSessionContract_") as folder:
            path = Path(folder) / "corrupt.dat"
            path.write_bytes(b"not a DPAPI blob")
            self.assertIsNone(SessionStore(path).load())
