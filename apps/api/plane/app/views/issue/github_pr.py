# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
import hashlib
import os
import re
import time
import uuid

import requests
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from plane.app.views.base import BaseAPIView
from plane.db.models import Issue, ProjectMember
from .github_pr_match import matching_pulls


def fetch_pulls(repo, token):
    key = "pr-panel-v2:" + hashlib.sha256(f"{repo}:{token}".encode()).hexdigest()
    lock_key = key + ":lock"
    deadline = time.monotonic() + 30
    owner = uuid.uuid4().hex
    while True:
        pulls = cache.get(key)
        if pulls is not None:
            return pulls
        if cache.add(lock_key, owner, timeout=300):
            try:
                pulls = cache.get(key)
                if pulls is not None:
                    return pulls
                pulls = []
                page = 1
                while True:
                    response = requests.get(
                        f"https://api.github.com/repos/{repo}/pulls",
                        params={"state": "all", "per_page": 100, "page": page},
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                        timeout=15,
                        allow_redirects=False,
                    )
                    response.raise_for_status()
                    batch = response.json()
                    if not isinstance(batch, list):
                        raise ValueError("Unexpected GitHub response")
                    fields = ("title", "merged_at", "state", "draft", "html_url", "number")
                    pulls.extend(
                        {**{key: pr[key] for key in fields}, "head": {"sha": pr["head"]["sha"]}} for pr in batch
                    )
                    if len(batch) < 100:
                        break
                    page += 1
                cache.set(key, pulls, 5)
                return pulls
            finally:
                if cache.get(lock_key) == owner:
                    cache.delete(lock_key)
        if time.monotonic() >= deadline:
            raise TimeoutError("Timed out waiting for GitHub lookup")
        time.sleep(0.1)


def latest_commit_date(repo, number, head_sha, token):
    key = "pr-panel-commit:" + hashlib.sha256(f"{repo}:{number}:{head_sha}:{token}".encode()).hexdigest()
    date = cache.get(key)
    if date is not None:
        return date
    owner, name = repo.split("/", 1)
    try:
        response = requests.post(
            "https://api.github.com/graphql",
            json={
                "query": "query($owner:String!, $name:String!, $number:Int!) { "
                         "repository(owner:$owner, name:$name) { pullRequest(number:$number) { "
                         "commits(last:1) { nodes { commit { committedDate } } } } } }",
                "variables": {"owner": owner, "name": name, "number": number},
            },
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=15,
            allow_redirects=False,
        )
        response.raise_for_status()
        result = response.json()
        date = result["data"]["repository"]["pullRequest"]["commits"]["nodes"][0]["commit"]["committedDate"]
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
        return None
    if date:
        cache.set(key, date, 86400)
    return date


class IssueGithubPullRequestsEndpoint(BaseAPIView):
    def get(self, request, slug, project_id, issue_id):
        get_object_or_404(ProjectMember, workspace__slug=slug, project_id=project_id, member=request.user,
                          is_active=True, role__gt=5)
        issue = get_object_or_404(Issue, workspace__slug=slug, project_id=project_id, pk=issue_id)
        repos = [r.strip() for r in os.environ.get("PR_PANEL_REPOSITORIES", "").split(",") if r.strip()]
        token = os.environ.get("PR_PANEL_GITHUB_TOKEN", "")
        if not token or not repos or len(repos) > 6 or any(
            not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", r) for r in repos
        ):
            return Response({"error": "PR panel is not configured correctly."}, status=503)
        try:
            issue_key = f"{issue.project.identifier}-{issue.sequence_id}"
            matches = [pr for repo in repos for pr in matching_pulls(fetch_pulls(repo, token), issue_key, repo)]
        except (requests.RequestException, ValueError, KeyError, TimeoutError):
            return Response({"error": "Could not load pull requests from GitHub."}, status=502)
        for pr in matches:
            pr["latest_commit_at"] = latest_commit_date(pr["repository"], pr["number"], pr.pop("head_sha"), token)
        return Response({"enabled": True, "pulls": matches})
