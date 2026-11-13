# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only

import re


def matching_pulls(pulls, issue_key, repo):
    pattern = re.compile(r"(?<![\w])" + re.escape(issue_key) + r"(?![\w])", re.IGNORECASE)
    matches = []
    for pr in pulls:
        if not pattern.search(pr["title"]):
            continue
        state = "merged" if pr["merged_at"] else "closed" if pr["state"] == "closed" else (
            "draft" if pr["draft"] else "open"
        )
        matches.append({"url": pr["html_url"], "number": pr["number"], "repository": repo,
                        "status": state, "head_sha": pr["head"]["sha"]})
    return matches


