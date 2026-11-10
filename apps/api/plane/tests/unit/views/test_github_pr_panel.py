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
def test_github_failure_is_reported():
    env = {"PR_PANEL_REPOSITORIES": "a/b", "PR_PANEL_GITHUB_TOKEN": "token"}
    with patch.dict("os.environ", env), \
         patch("plane.app.views.issue.github_pr.get_object_or_404", side_effect=[Mock(), Mock(name="task")]), \
         patch("plane.app.views.issue.github_pr.fetch_pulls", side_effect=requests.RequestException):
        response = IssueGithubPullRequestsEndpoint().get(Mock(), "workspace", "project", "issue")
    assert response.status_code == 502


@pytest.mark.unit
def test_any_workspace_and_project_checks_membership_and_returns_matches():
    env = {"PR_PANEL_REPOSITORIES": "a/b", "PR_PANEL_GITHUB_TOKEN": "token"}
    request = Mock()
    issue = Mock()
    issue.project.identifier = "ASD"
    issue.sequence_id = 8
    pull = {"title": "asd-8: Task title", "state": "open", "draft": False, "merged_at": None,
            "html_url": "https://github.com/a/b/pull/1", "number": 1}
    with patch.dict("os.environ", env), \
         patch("plane.app.views.issue.github_pr.get_object_or_404", side_effect=[Mock(), issue]) as lookup, \
         patch("plane.app.views.issue.github_pr.fetch_pulls", return_value=[pull]):
        response = IssueGithubPullRequestsEndpoint().get(request, "workspace", "any-project", "issue")
    assert response.data["pulls"][0]["number"] == 1
    assert lookup.call_args_list[0].kwargs["project_id"] == "any-project"
    assert lookup.call_args_list[0].kwargs["member"] == request.user


@pytest.mark.unit
def test_concurrent_fetches_share_a_five_second_cache():
    from concurrent.futures import ThreadPoolExecutor
    from time import sleep
    from django.core.cache.backends.locmem import LocMemCache

    local_cache = LocMemCache("pr-panel-test", {})
    response = Mock()
    response.json.return_value = []

    def get(*args, **kwargs):
        sleep(0.2)
        return response

    with patch("plane.app.views.issue.github_pr.cache", local_cache), \
         patch("plane.app.views.issue.github_pr.requests.get", side_effect=get) as request:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: fetch_pulls("a/b", "token"), range(2)))
        assert results == [[], []]
        assert request.call_count == 1
        assert fetch_pulls("a/b", "token") == []
        assert request.call_count == 1
