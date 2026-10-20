from __future__ import annotations

from sdd_auto_story_to_release.bitbucket import parse_bitbucket_url, repo_plan
from sdd_auto_story_to_release.settings import ComponentRepo


def test_parse_and_repo_plan():
    ref = parse_bitbucket_url("https://bitbucket.org/acme/payments.git")
    assert ref.workspace == "acme"
    assert ref.repo_slug == "payments"
    plan = repo_plan(
        ComponentRepo(
            name="backend",
            repository="https://bitbucket.org/acme/payments.git",
            default_branch="master",
        )
    )
    assert plan["repo_slug"] == "payments"
    assert plan["name"] == "backend"
