/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 */
import useSWR from "swr";
import { API_BASE_URL } from "@plane/constants";

type Pull = { url: string; number: number; repository: string; status: string };
type Response = { enabled: boolean; pulls: Pull[] };

type Props = { workspaceSlug: string; projectId: string; issueId: string; title: string };

export function GithubPullRequests({ workspaceSlug, projectId, issueId, title }: Props) {
  const url = `${API_BASE_URL}/api/workspaces/${encodeURIComponent(workspaceSlug)}/projects/${projectId}/issues/${issueId}/github-pull-requests/`;
  const { data, error } = useSWR<Response>([url, title], async ([path]: [string, string]) => {
    const response = await fetch(path, { credentials: "include" });
    if (!response.ok) throw new Error("Could not load pull requests");
    return response.json();
  }, { refreshInterval: 60000 });

  if (!error && (!data?.enabled || data.pulls.length === 0)) return null;
  return (
    <section className="my-4 space-y-2 border-t border-subtle-1 pt-4 text-body-xs-regular" aria-label="GitHub pull requests">
      <h5 className="text-body-xs-medium">GitHub pull requests</h5>
      {error ? <p role="alert">Could not load pull requests.</p> :
        data?.pulls.map((pr) => (
          <div key={pr.url} className="flex items-center justify-between gap-2">
            <a className="truncate underline" href={pr.url} target="_blank" rel="noreferrer">{pr.repository}#{pr.number}</a>
            <span className="shrink-0 capitalize">{pr.status}</span>
          </div>
        ))}
    </section>
  );
}
