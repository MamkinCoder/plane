# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
import hashlib
import os
import re

import requests
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from plane.app.views.base import BaseAPIView
from plane.db.models import Issue, ProjectMember
from .github_pr_match import matching_pulls


def fetch_pulls(repo, token):
    key = "pr-panel:" + hashlib.sha256(f"{repo}:{token}".encode()).hexdigest()
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
        pulls.extend({key: pr[key] for key in fields} for pr in batch)
        if len(batch) < 100:
            break
        page += 1
    cache.set(key, pulls, 60)
    return pulls


class IssueGithubPullRequestsEndpoint(BaseAPIView):
    def get(self, request, slug, project_id, issue_id):
        workspace = os.environ.get("PR_PANEL_WORKSPACE", "")
        if slug != workspace:
            return Response({"enabled": False, "pulls": []})
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
            matches = [pr for repo in repos for pr in matching_pulls(fetch_pulls(repo, token), issue.name, repo)]
        except (requests.RequestException, ValueError, KeyError):
            return Response({"error": "Could not load pull requests from GitHub."}, status=502)
        return Response({"enabled": True, "pulls": matches})
