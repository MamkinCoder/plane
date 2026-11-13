# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
import importlib.util
from pathlib import Path
import unittest

# The matcher is pure and can be checked without starting Plane.
spec = importlib.util.spec_from_file_location(
    "github_pr_match", Path(__file__).resolve().parents[3] / "app/views/issue/github_pr_match.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PullRequestMatchingTest(unittest.TestCase):
    def test_key_boundaries_and_statuses(self):
        def pr(title, state="open", draft=False, merged_at=None):
            return {"title": title, "state": state, "draft": draft, "merged_at": merged_at,
                    "html_url": "https://github.com/acme/app/pull/1", "number": 1, "head": {"sha": "abc"}}

        pulls = [pr("ASD-8: Fix login"), pr("[asd-8] Fix", draft=True), pr("Fix asd-8; done", state="closed"),
                 pr("asd-8!", state="closed", merged_at="now"), pr("asd-80: another task"),
                 pr("XASD-8: another task"), pr("No task key")]
        result = module.matching_pulls(pulls, "ASD-8", "acme/app")
        self.assertEqual([p["status"] for p in result], ["open", "draft", "closed", "merged"])
        self.assertTrue(all(p["repository"] == "acme/app" for p in result))


if __name__ == "__main__":
    unittest.main()
