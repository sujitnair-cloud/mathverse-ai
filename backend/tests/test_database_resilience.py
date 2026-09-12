"""
Regression test for a production incident: a just-added Postgres plugin's
internal DNS name wasn't resolvable yet on the first deploy, and init_db()
treated that as immediately fatal, crash-looping the whole app before it
ever served a request. init_db() must retry transient connection failures
instead of giving up on the first one.
"""
import unittest
from unittest.mock import AsyncMock, patch

from app.core import database


class InitDbRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_retries_on_transient_failure_then_succeeds(self):
        calls = {"n": 0}

        class FakeConn:
            async def __aenter__(self):
                calls["n"] += 1
                if calls["n"] < 3:
                    raise OSError("Name or service not known")
                return self

            async def __aexit__(self, *a):
                return False

            async def run_sync(self, fn):
                return None

        with patch.object(database, "engine") as fake_engine, \
             patch("asyncio.sleep", new=AsyncMock()):
            fake_engine.begin = lambda: FakeConn()
            await database.init_db(retries=5, delay=0.01)

        self.assertEqual(calls["n"], 3)

    async def test_gives_up_after_exhausting_retries(self):
        class AlwaysFails:
            async def __aenter__(self):
                raise OSError("Name or service not known")

            async def __aexit__(self, *a):
                return False

        with patch.object(database, "engine") as fake_engine, \
             patch("asyncio.sleep", new=AsyncMock()):
            fake_engine.begin = lambda: AlwaysFails()
            with self.assertRaises(OSError):
                await database.init_db(retries=3, delay=0.01)


if __name__ == "__main__":
    unittest.main()
