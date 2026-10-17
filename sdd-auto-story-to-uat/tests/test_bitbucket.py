from __future__ import annotations

import pytest

from sdd_auto_story_to_uat.bitbucket import BitbucketUrlError, parse_bitbucket_url, repo_plans
from sdd_auto_story_to_uat.settings import BitbucketConfig


def test_cloud_https_and_ssh():
    https = parse_bitbucket_url("https://bitbucket.org/acme/app.git")
    assert https.workspace == "acme"
    assert https.repo_slug == "app"
    assert https.full_name == "acme/app"

    ssh = parse_bitbucket_url("git@bitbucket.org:acme/app.git")
    assert ssh.repo_slug == "app"


def test_server_projects_repos_url():
    ref = parse_bitbucket_url(
        "https://bitbucket.example.com/projects/APP/repos/payments/browse"
    )
    assert ref.project == "APP"
    assert ref.repo_slug == "payments"


def test_repo_plans_uses_settings_override():
    plans = repo_plans(
        BitbucketConfig(
            repositories=("https://bitbucket.org/acme/app.git",),
            workspace="team",
        )
    )
    assert plans[0]["workspace"] == "team"
    assert plans[0]["repo_slug"] == "app"


def test_empty_url():
    with pytest.raises(BitbucketUrlError):
        parse_bitbucket_url("   ")
