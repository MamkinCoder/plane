# Deploy the Plane PR panel

This fork is based on Plane Community Edition **v1.4.3**. It adds the PR panel to the web and API services. It does not require a separate database or a new Plane installation.

## Before you start

- Record the running Plane version, deployment method, Compose project name, configuration, image tags, database and object storage locations. This guide assumes Docker Compose; adapt it for other deployment methods.
- Back up the existing PostgreSQL database, uploaded files/object storage and configuration, and verify that the backup can be restored. Upgrading Plane can run database migrations; rolling back images alone might not reverse them. Use [Plane's upgrade guide](https://developers.plane.so/self-hosting/manage/upgrade-plane).
- If running 1.4.2, follow Plane's supported 1.4.3 upgrade procedure, including its migrator. Keep the database, uploads, volumes and Compose project name. Use matching **v1.4.3** official images for the other Plane services. Do not create a fresh installation or run `docker compose down -v`.
- The published custom images are **linux/amd64**. For an ARM64 server, build suitable images from source and test them before rollout.

## Configure access

Set these values in the existing deployment's environment file (often `plane.env`) or secret manager:

```dotenv
PR_PANEL_REPOSITORIES=your-org/repo-one,your-org/repo-two
PR_PANEL_GITHUB_TOKEN=your-read-only-token
```

Use a GitHub fine-grained token with **Pull requests: read-only** access to the listed repositories. List at most six `owner/repo` names. Pass both variables into the **API container**, as shown below; an environment file alone may not pass them through. Never commit the token.

Every active non-guest member of any Plane project can see matching PR repository names, numbers, links and status, even without GitHub access. Only configure repositories whose PR metadata is appropriate for that audience. The API needs outbound HTTPS access to `api.github.com`.

## Choose images

Use the **same commit** for both images. The [Build PR panel images workflow](https://github.com/MamkinCoder/plane/actions/workflows/pr-panel-images.yml) publishes public, commit-tagged images when the fork's `codex/pr-panel-1.4.3` branch is pushed. Select a successful run and copy its full commit SHA as `IMAGE_TAG` below. Public GHCR images can be pulled without GitHub login.

### Option A: pull images built by GitHub Actions

```sh
# Replace with the full commit SHA from a successful workflow run.
export IMAGE_TAG='<full-commit-sha>'
docker pull "ghcr.io/mamkincoder/plane-pr-panel-web:$IMAGE_TAG"
docker pull "ghcr.io/mamkincoder/plane-pr-panel-api:$IMAGE_TAG"
```

### Option B: build from the fork

On the build machine, clone the fork or set your existing **Plane source checkout's** Git remote to `https://github.com/MamkinCoder/plane.git`. Changing a Git remote alone does not update the running containers. Check out the exact commit to deploy and build both images:

```sh
git clone https://github.com/MamkinCoder/plane.git plane-pr-panel
cd plane-pr-panel
git checkout '<full-commit-sha>'
export IMAGE_TAG="$(git rev-parse HEAD)"
docker build -f apps/web/Dockerfile.web -t "ghcr.io/mamkincoder/plane-pr-panel-web:$IMAGE_TAG" .
docker build -f apps/api/Dockerfile.api -t "ghcr.io/mamkincoder/plane-pr-panel-api:$IMAGE_TAG" apps/api
```

If building on a different machine, transfer or publish both images to a registry the server can access. Build for the server's architecture.

## Apply to the existing Compose deployment

In the directory containing your **existing** production Compose file, create a separate `pr-panel.override.yml`:

```yaml
services:
  web:
    image: ghcr.io/mamkincoder/plane-pr-panel-web:${IMAGE_TAG:?Set IMAGE_TAG}
  api:
    image: ghcr.io/mamkincoder/plane-pr-panel-api:${IMAGE_TAG:?Set IMAGE_TAG}
    environment:
      PR_PANEL_REPOSITORIES: ${PR_PANEL_REPOSITORIES:?Set PR_PANEL_REPOSITORIES}
      PR_PANEL_GITHUB_TOKEN: ${PR_PANEL_GITHUB_TOKEN:?Set PR_PANEL_GITHUB_TOKEN}
```

Keep the same `IMAGE_TAG` in the shell used to run Compose, and use the existing environment file, base Compose file and project name. For example, **after replacing the filenames with those used by your installation**:

```sh
docker compose --env-file plane.env -f docker-compose.yml -f pr-panel.override.yml config --quiet
docker compose --env-file plane.env -f docker-compose.yml -f pr-panel.override.yml up -d --no-deps web api
```

If your installation uses `-p` / `--project-name`, supply the same value on both commands. Ensure the selected images are available on the server first. Preserve the override when using Plane's upgrade tooling: an ordinary upstream upgrade may replace the custom services. Do not print the expanded Compose config in shared logs because it can contain secrets.

## Verify and maintain

1. Confirm login, existing projects, tasks and attachments. Check API, web and migrator logs for errors.
2. Open a work item such as `ASD-8` and check that a PR whose title contains `ASD-8` or `asd-8:` appears in **GitHub pull requests**. Open its link and check its status. The panel is visible with no matches. It fetches on opening and on manual refresh, with a five-second shared cache; a refresh inside that window can return cached results.
3. Check a project member and a guest account. Guests cannot fetch PR details. If the panel reports an error, check the API container's configuration, GitHub token access, outbound network and GitHub rate limits.
4. Retain the backup and prior deployment configuration. If rollback is necessary after database migrations, use the tested restore procedure for the matching database and file backup.

The matching logic searches PR titles, not descriptions or branch names. It reads all PRs, including closed ones, in each configured repo. Large repos can slow requests or exhaust GitHub API limits. Identical project identifiers across workspaces can match the same PR. The fork and deployment should be reviewed and tested again before upgrading Plane beyond 1.4.3.
