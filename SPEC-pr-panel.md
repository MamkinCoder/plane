# GitHub pull requests panel

Source: user request on 2026-11-10; self-hosted Plane 1.4.2. Original base: upstream v1.4.2 commit 5f7d92784c403f76284f0f16718f320221dc7fec. On 2026-11-10 the user requested the latest stable release; implementation moved to v1.4.3 commit 37a15d99231042b3ff5a4401fed479fdbec9effe. Scope: API, task UI, focused tests and deployment notes.

The initial idea of writing status into Plane links was rejected by the user on 2026-11-10: use a dedicated UI without changing task content or links. Proposed implementation: a read-only panel finds PRs whose title equals the task title (case-insensitive, normalized whitespace), lists GitHub links and draft/open/closed/merged status, and reports errors. API configuration limits access to explicit repositories, projects and a workspace; the token stays server-side. Only project members may read the panel. Repo information is visible to eligible members; configure repositories accordingly. No task state changes, data writes or fuzzy matching.

On 2026-11-10 the user removed the project allowlist: the panel applies to all projects in the configured workspace, with existing project-member access checks. Hide it when there are no matching PRs; keep errors visible so failures are not mistaken for no matches. Repository and workspace restrictions remain.

Acceptance: task views display matches and hide the panel for no matches; upstream errors are visible; tokens stay server-side; workspace scope and project membership are enforced; matching/status have tests. Real deployment compatibility and access remain to be verified.

On 2026-11-10 the user requested a GitHub fork and remotely built images. Add a fork-owned GitHub Actions workflow using the upstream API and web Dockerfiles and GitHub Container Registry; leave Plane's upstream publishing workflow unchanged. Publish versioned images from the feature branch. This does not deploy to the running instance.

Later on 2026-11-10 the user also removed the workspace setting. The panel now applies across the instance, still requiring an active project member and a work item within that project. The shared GitHub token therefore exposes matching PR metadata to members of all projects in all workspaces; configure repository access accordingly.

On 2026-11-10 the user replaced title equality with an explicit work-item key (for example ASD-8) appearing in the PR title, case-insensitively with boundaries so ASD-8 does not match ASD-80. Task title changes no longer affect matching. Show only the repository name and PR number, with GitHub-like state colors and icons for draft, open, closed and merged. Duplicate project identifiers across workspaces can produce the same matches; configure repositories accordingly.

On 2026-11-10 the user changed the refresh flow: always show the panel, check once when a task opens, and provide a manual refresh button. No periodic, focus, or reconnect refresh. A shared five-second cache and per-repository lock deduplicate concurrent lookups. Manual refresh also respects this cache, so a click within five seconds may return the cached result. Keep errors visible and retryable.

On 2026-11-10 the user requested a root deployment guide and publication of the current implementation and images to their fork and GHCR. Document both prebuilt images and source builds, preservation of the existing Plane database and file storage, configuration and verification. Deployment remains the operator's responsibility.

On 2026-11-13 the user requested the latest commit date on each pull request, displayed as day and abbreviated month without a year (for example 25 Oct). Use the PR's latest commit timestamp, not its updated or merged timestamp. If GitHub cannot provide a date, keep showing the PR without one. No extra token permissions or refresh behavior changes.
