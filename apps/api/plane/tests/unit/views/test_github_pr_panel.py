# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
from unittest.mock import Mock, patch

import pytest
import requests

from plane.app.views.issue.github_pr import IssueGithubPullRequestsEndpoint, fetch_pulls


@pytest.mark.unit
def test_fetch_pulls_paginates_and_caches_only_display_fields():
    pull = {"title": "A", "state": "open", "draft": False, "merged_at": None,
            "html_url": "https://github.com/a/b/pull/1", "number": 1, "body": "private"}
    first = Mock()
    first.json.return_value = [pull] * 100
    second = Mock()
    second.json.return_value = []
    with patch("plane.app.views.issue.github_pr.cache") as cache, \
         patch("plane.app.views.issue.github_pr.requests.get", side_effect=[first, second]) as get:
        cache.get.return_value = None
        result = fetch_pulls("a/b", "token")
    assert get.call_count == 2
    assert len(result) == 100
    assert "body" not in result[0]
    cache.set.assert_called_once()


@pytest.mark.unit
def test_unconfigured_workspace_does_not_query_github():
    with patch.dict("os.environ", {"PR_PANEL_WORKSPACE": "workspace"}), \
         patch("plane.app.views.issue.github_pr.fetch_pulls") as fetch:
        response = IssueGithubPullRequestsEndpoint().get(Mock(), "other", "project", "issue")
    assert response.data == {"enabled": False, "pulls": []}
    fetch.assert_not_called()


@pytest.mark.unit
def test_github_failure_is_reported():
    env = {"PR_PANEL_WORKSPACE": "workspace", "PR_PANEL_REPOSITORIES": "a/b", "PR_PANEL_GITHUB_TOKEN": "token"}
    with patch.dict("os.environ", env), \
         patch("plane.app.views.issue.github_pr.get_object_or_404", side_effect=[Mock(), Mock(name="task")]), \
         patch("plane.app.views.issue.github_pr.fetch_pulls", side_effect=requests.RequestException):
        response = IssueGithubPullRequestsEndpoint().get(Mock(), "workspace", "project", "issue")
    assert response.status_code == 502


@pytest.mark.unit
def test_any_project_in_workspace_checks_membership_and_returns_matches():
    env = {"PR_PANEL_WORKSPACE": "workspace", "PR_PANEL_REPOSITORIES": "a/b", "PR_PANEL_GITHUB_TOKEN": "token"}
    request = Mock()
    issue = Mock()
    issue.name = "Task title"
    pull = {"title": "Task title", "state": "open", "draft": False, "merged_at": None,
            "html_url": "https://github.com/a/b/pull/1", "number": 1}
    with patch.dict("os.environ", env), \
         patch("plane.app.views.issue.github_pr.get_object_or_404", side_effect=[Mock(), issue]) as lookup, \
         patch("plane.app.views.issue.github_pr.fetch_pulls", return_value=[pull]):
        response = IssueGithubPullRequestsEndpoint().get(request, "workspace", "any-project", "issue")
    assert response.data["pulls"][0]["number"] == 1
    assert lookup.call_args_list[0].kwargs["project_id"] == "any-project"
    assert lookup.call_args_list[0].kwargs["member"] == request.user
