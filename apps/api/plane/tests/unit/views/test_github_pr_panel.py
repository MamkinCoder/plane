# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
from unittest.mock import Mock, patch

import pytest
import requests

from plane.app.views.issue.github_pr import IssueGithubPullRequestsEndpoint, fetch_pulls


@pytest.mark.unit
def test_fetch_pulls_paginates_and_caches_only_display_fields():
    pull = {"title": "A", "state": "open", "draft": False, "merged_at": None,
            "html_url": "https://github.com/a/b/pull/1", "number": 1, "head": {"sha": "abc"}, "body": "private"}
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
            "html_url": "https://github.com/a/b/pull/1", "number": 1, "head": {"sha": "abc"}}
    with patch.dict("os.environ", env), \
         patch("plane.app.views.issue.github_pr.get_object_or_404", side_effect=[Mock(), issue]) as lookup, \
         patch("plane.app.views.issue.github_pr.fetch_pulls", return_value=[pull]), \
         patch("plane.app.views.issue.github_pr.pull_request_details",
               return_value={"latest_commit_at": "2026-10-25T00:00:00Z"}):
        response = IssueGithubPullRequestsEndpoint().get(request, "workspace", "any-project", "issue")
    assert response.data["pulls"][0]["number"] == 1
    assert response.data["pulls"][0]["latest_commit_at"] == "2026-10-25T00:00:00Z"
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


@pytest.mark.unit
def test_review_details_paginate_and_cache():
    from django.core.cache.backends.locmem import LocMemCache
    from plane.app.views.issue.github_pr import pull_request_details

    local_cache = LocMemCache("pr-panel-commit-test", {})
    response = Mock()
    response.json.return_value = {"data": {"repository": {"pullRequest": {
        "commits": {"nodes": [{"commit": {"committedDate": "2026-10-25T08:00:00Z"}}]}
    }}}}
    pull = response.json.return_value["data"]["repository"]["pullRequest"]
    pull["reviewDecision"] = "CHANGES_REQUESTED"
    pull["reviewThreads"] = {
        "nodes": [{"isResolved": True}, {"isResolved": False, "comments": {"nodes": []}}],
        "pageInfo": {"hasNextPage": True, "endCursor": "next"},
    }
    last = Mock()
    last.json.return_value = {"data": {"repository": {"pullRequest": {"reviewThreads": {
        "nodes": [{"isResolved": False, "comments": {"nodes": [{"url": "https://github.com/a/b/pull/1#discussion_r1"}]}}],
        "pageInfo": {"hasNextPage": False},
    }}}}}
    with patch("plane.app.views.issue.github_pr.cache", local_cache), \
         patch("plane.app.views.issue.github_pr.requests.post", side_effect=[response, last]) as post:
        details = pull_request_details("a/b", 1, "sha1", "token")
        assert details == {
            "latest_commit_at": "2026-10-25T08:00:00Z",
            "review_decision": "CHANGES_REQUESTED",
            "unresolved_threads": 2,
            "first_unresolved_url": "https://github.com/a/b/pull/1#discussion_r1",
        }
        assert post.call_args.kwargs["json"]["variables"]["cursor"] == "next"
        assert pull_request_details("a/b", 1, "sha1", "token") == details
        assert post.call_count == 2


@pytest.mark.unit
def test_latest_commit_failure_does_not_hide_pull_request():
    from plane.app.views.issue.github_pr import pull_request_details

    with patch("plane.app.views.issue.github_pr.cache") as cache, \
         patch("plane.app.views.issue.github_pr.requests.post", side_effect=requests.RequestException):
        cache.get.return_value = None
        assert pull_request_details("a/b", 1, "sha", "token") == {}
