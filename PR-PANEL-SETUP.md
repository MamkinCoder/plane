# GitHub PR panel for Plane 1.4.3

For rollout instructions, see [deploy.md](deploy.md).

This fork adds a read-only panel to task detail and peek views. It does not change task descriptions, links, or state. It finds PRs whose title contains the task key, such as `ASD-8`, case-insensitively; punctuation around the key is supported and multiple matches are shown. Draft, open, closed and merged status is checked on opening the task and when the refresh button is pressed; the panel stays visible even when no PRs match. PRs are linked to GitHub.

Configure the **API container's environment**, using your deployment's secret mechanism:

```dotenv
PR_PANEL_REPOSITORIES=your-org/repo-one,your-org/repo-two
PR_PANEL_GITHUB_TOKEN=your-read-only-token
```

List only repositories whose PR metadata can be shared with **every project member** across the Plane instance. The panel uses one server-side token, not each viewer's GitHub permissions. Guests cannot access it. Anyone with access to the API container environment can access the token. Use a fine-grained GitHub token with pull-request read permission on the selected repositories. Limit to six repositories. Task titles are compared on the server and are not sent to GitHub.

Build and deploy **both** the web and API images from this fork at its 1.4.3 base, using the existing production deployment's image build and rollout process. Set the two variables on the API service and restart it. Do not replace the production compose file with this repository's development compose file. The exact image names and rollout commands depend on your installation. No database migration is required. After rollout, open a task whose key appears in a PR title and verify its link and status; check an unauthorized user as well.

The API reads all PRs (including closed) in each configured repository and caches the display fields for five seconds, including for manual refreshes. Concurrent lookups for the same repository share one fetch. Large repositories can make requests slow and consume API quota; failures appear in the panel. PR titles without the task key do not match; duplicate project identifiers across workspaces can produce the same matches. Data depends on the GitHub token's access. Cached metadata lives in Plane's configured cache. Version compatibility beyond Plane 1.4.3 and behavior against the actual deployment have not been verified.

Quick matcher check: `python3 apps/api/plane/tests/unit/views/test_github_pr_match.py`. Run the API unit tests with your existing Plane test environment. Do not commit tokens.

## GitHub image builds

The fork's `Build PR panel images` workflow builds the upstream web and API Dockerfiles for `linux/amd64` and publishes commit-tagged images to GitHub Container Registry. It runs when `codex/pr-panel-1.4.3` is pushed. The workflow can also be run manually from the fork’s default branch. The current image packages are public. The tags contain the full commit SHA so both images can be pinned to the same build.
