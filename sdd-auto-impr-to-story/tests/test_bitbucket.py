from __future__ import annotations

import pytest

from sdd_auto_impr_to_story.bitbucket import BitbucketUrlError, parse_bitbucket_url


def test_cloud_https_and_ssh():
    https = parse_bitbucket_url("https://bitbucket.org/acme/app.git")
    assert https.workspace == "acme"
    assert https.repo_slug == "app"
    assert https.project is None
    assert https.full_name == "acme/app"

    ssh = parse_bitbucket_url("git@bitbucket.org:acme/app.git")
    assert ssh.workspace == "acme"
    assert ssh.repo_slug == "app"


def test_server_projects_repos_url():
    ref = parse_bitbucket_url(
        "https://bitbucket.example.com/projects/APP/repos/payments/browse"
    )
    assert ref.project == "APP"
    assert ref.workspace == "APP"
    assert ref.repo_slug == "payments"
    assert ref.https_url.endswith("/projects/APP/repos/payments")


def test_scm_path():
    ref = parse_bitbucket_url("ssh://git@bitbucket.example.com/scm/APP/payments.git")
    assert ref.project == "APP"
    assert ref.repo_slug == "payments"


def test_empty_url():
    with pytest.raises(BitbucketUrlError):
        parse_bitbucket_url("   ")
