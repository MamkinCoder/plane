/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 */
import useSWR from "swr";
import { GitMerge, GitPullRequest, GitPullRequestClosed, GitPullRequestDraft, RefreshCw } from "lucide-react";
import { API_BASE_URL } from "@plane/constants";

type Status = "draft" | "open" | "closed" | "merged";
type Pull = { url: string; number: number; repository: string; status: Status; latest_commit_at: string | null };

const STATUS = {
  draft: { icon: GitPullRequestDraft, color: "text-[#8b949e]" },
  open: { icon: GitPullRequest, color: "text-[#3fb950]" },
  closed: { icon: GitPullRequestClosed, color: "text-[#f85149]" },
  merged: { icon: GitMerge, color: "text-[#a371f7]" },
};
type Response = { enabled: boolean; pulls: Pull[] };

type Props = { workspaceSlug: string; projectId: string; issueId: string };

export function GithubPullRequests({ workspaceSlug, projectId, issueId }: Props) {
  const url = `${API_BASE_URL}/api/workspaces/${encodeURIComponent(workspaceSlug)}/projects/${projectId}/issues/${issueId}/github-pull-requests/`;
  const { data, error, isValidating, mutate } = useSWR<Response>(
    url,
    async (path: string) => {
      const response = await fetch(path, { credentials: "include" });
      if (!response.ok) throw new Error("Could not load pull requests");
      return response.json();
    },
    {
      dedupingInterval: 5000,
      revalidateOnMount: true,
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
      shouldRetryOnError: false,
    }
  );

  return (
    <section
      className="my-4 space-y-2 border-t border-subtle-1 pt-4 text-body-xs-regular"
      aria-label="GitHub pull requests"
    >
      <div className="flex items-center justify-between gap-2">
        <h5 className="text-body-xs-medium">GitHub pull requests</h5>
        <button
          type="button"
          onClick={() => void mutate()}
          disabled={isValidating}
          aria-label="Refresh pull requests"
          className="rounded p-1 text-placeholder hover:text-primary disabled:opacity-50"
        >
          <RefreshCw aria-hidden="true" className={`size-4 ${isValidating ? "animate-spin" : ""}`} />
        </button>
      </div>
      {error ? (
        <p role="alert">Could not load pull requests.</p>
      ) : !data ? (
        <p>Loading pull requests…</p>
      ) : !data.pulls.length ? (
        <p>No matching pull requests.</p>
      ) : (
        data.pulls.map((pr) => {
          const { icon: Icon, color } = STATUS[pr.status];
          return (
            <div key={pr.url} className="flex items-center justify-between gap-2">
              <a className="truncate underline" href={pr.url} target="_blank" rel="noreferrer">
                {pr.repository.split("/").pop()}#{pr.number}
              </a>
              <span className={`flex shrink-0 items-center gap-1 capitalize ${color}`}>
                <Icon aria-hidden="true" className="size-4" />
                {pr.status}
              </span>
              {pr.latest_commit_at && (
                <time className="shrink-0 text-placeholder" dateTime={pr.latest_commit_at} title="Latest commit">
                  {new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }).format(
                    new Date(pr.latest_commit_at)
                  )}
                </time>
              )}
            </div>
          );
        })
      )}
    </section>
  );
}
