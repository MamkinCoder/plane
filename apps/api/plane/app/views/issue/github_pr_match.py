# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only

def normalize_title(title):
    return " ".join(title.split()).casefold()


def matching_pulls(pulls, title, repo):
    matches = []
    for pr in pulls:
        if normalize_title(pr["title"]) != normalize_title(title):
            continue
        state = "merged" if pr["merged_at"] else "closed" if pr["state"] == "closed" else (
            "draft" if pr["draft"] else "open"
        )
        matches.append({"url": pr["html_url"], "number": pr["number"], "repository": repo, "status": state})
    return matches


