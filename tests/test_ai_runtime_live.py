from __future__ import annotations

import os
import unittest


@unittest.skipUnless(os.environ.get("CIS_RUN_LIVE_AI_TESTS") == "1", "Live AI tests are opt-in only.")
class AIRuntimeLiveTests(unittest.TestCase):
    def test_live_placeholder_is_not_run_in_ci(self) -> None:
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
