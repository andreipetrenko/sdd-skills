from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from sdd_auto_story_to_release.settings import ComponentRepo


class BitbucketUrlError(ValueError):
    pass


@dataclass(frozen=True)
class BitbucketRef:
    workspace: str
    repo_slug: str
    project: str | None = None
    host: str = "bitbucket.org"
    https_url: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.workspace}/{self.repo_slug}"


def parse_bitbucket_url(url: str) -> BitbucketRef:
    raw = url.strip()
    if not raw:
        raise BitbucketUrlError("bitbucket.repository is empty")

    if raw.startswith("git@"):
        host_path = raw[4:]
        host, _, path = host_path.partition(":")
        path = path.removesuffix(".git").strip("/")
        return _from_host_path(host, path, raw)

    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or parsed.netloc.split("@")[-1].split(":")[0]).strip()
    path = parsed.path.strip("/").removesuffix(".git")
    return _from_host_path(host, path, raw)


def repo_plan(cfg: ComponentRepo) -> dict[str, str | None]:
    ref = parse_bitbucket_url(cfg.repository)
    return {
        "name": cfg.name,
        "repository": cfg.repository,
        "workspace": ref.workspace,
        "repo_slug": ref.repo_slug,
        "project": ref.project,
        "host": ref.host,
        "default_branch": cfg.default_branch,
        "story_branch_pattern": cfg.story_branch_pattern,
    }


def _from_host_path(host: str, path: str, original: str) -> BitbucketRef:
    parts = [part for part in path.split("/") if part]
    project = None
    workspace: str
    repo_slug: str
    if "projects" in parts and "repos" in parts:
        project = parts[parts.index("projects") + 1]
        repo_slug = parts[parts.index("repos") + 1]
        workspace = project
    elif len(parts) >= 3 and parts[0] == "scm":
        project = parts[1]
        repo_slug = parts[2]
        workspace = project
    elif len(parts) >= 2:
        workspace, repo_slug = parts[0], parts[1]
    else:
        raise BitbucketUrlError(f"Cannot parse Bitbucket repository URL: {original}")

    slug = repo_slug.removesuffix(".git")
    host = host or "bitbucket.org"
    if project:
        https_url = f"https://{host}/projects/{project}/repos/{slug}"
    else:
        https_url = f"https://{host}/{workspace}/{slug}"
    return BitbucketRef(
        workspace=workspace,
        repo_slug=slug,
        project=project,
        host=host,
        https_url=https_url,
    )
