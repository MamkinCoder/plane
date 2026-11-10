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
    def test_exact_title_and_statuses(self):
        def pr(title, state="open", draft=False, merged_at=None):
            return {"title": title, "state": state, "draft": draft, "merged_at": merged_at,
                    "html_url": "https://github.com/acme/app/pull/1", "number": 1}

        pulls = [pr("  Fix   Login "), pr("fix login", draft=True), pr("fix login", state="closed"),
                 pr("fix login", state="closed", merged_at="now"), pr("fix login screen")]
        result = module.matching_pulls(pulls, "fix login", "acme/app")
        self.assertEqual([p["status"] for p in result], ["open", "draft", "closed", "merged"])
        self.assertTrue(all(p["repository"] == "acme/app" for p in result))


if __name__ == "__main__":
    unittest.main()
