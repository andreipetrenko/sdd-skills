from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from sdd_auto_impr_to_story.models import JiraIssue
from sdd_auto_impr_to_story.settings import Settings

CAPABILITY_META = {
    "business-requirements": {
        "title": "Business requirements",
        "purpose": (
            "Business requirements describe the value, actors, outcomes and constraints "
            "of the change in terms a product owner can accept as done."
        ),
    },
    "functional-requirements": {
        "title": "Functional requirements",
        "purpose": (
            "Functional requirements describe observable system behavior, inputs, outputs "
            "and error cases that can be verified by tests or review."
        ),
    },
    "code-changes": {
        "title": "Code changes",
        "purpose": (
            "Code-change requirements describe how the component must be modified "
            "so that the accepted business and functional requirements can be implemented."
        ),
    },
}


class OpenspecError(RuntimeError):
    pass


def change_dir(repo: Path, change_id: str) -> Path:
    return repo / "openspec" / "changes" / change_id


def scaffold_change(
    repo: Path,
    settings: Settings,
    source: JiraIssue,
    story_key: str | None = None,
) -> Path:
    change_id = settings.change_id(source.key)
    target = change_dir(repo, change_id)
    target.mkdir(parents=True, exist_ok=True)
    (target / ".openspec.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
    (target / "proposal.md").write_text(
        render_proposal(settings, source, story_key), encoding="utf-8"
    )
    for capability in settings.openspec.capabilities:
        spec_path = target / "specs" / capability / "spec.md"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            render_capability_spec(capability, source),
            encoding="utf-8",
        )
    _ensure_openspec_root(repo)
    return target


def scaffold_implementation_change(
    repo: Path,
    settings: Settings,
    source: JiraIssue,
    story_key: str,
    task_key: str,
    component: str | None = None,
) -> Path:
    change_id = settings.implementation_change_id(task_key, source.key)
    capability = settings.openspec.implementation_capability
    target = change_dir(repo, change_id)
    target.mkdir(parents=True, exist_ok=True)
    (target / ".openspec.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
    (target / "proposal.md").write_text(
        render_implementation_proposal(settings, source, story_key, task_key, component),
        encoding="utf-8",
    )
    spec_path = target / "specs" / capability / "spec.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        render_capability_spec(capability, source, component=component),
        encoding="utf-8",
    )
    (target / "design.md").write_text(
        render_implementation_design(source, story_key, task_key, component),
        encoding="utf-8",
    )
    _ensure_openspec_root(repo)
    return target


def render_implementation_proposal(
    settings: Settings,
    source: JiraIssue,
    story_key: str,
    task_key: str,
    component: str | None,
) -> str:
    capability = settings.openspec.implementation_capability
    title = CAPABILITY_META.get(capability, {}).get("title", capability)
    why = source.summary.strip() or "Implement the accepted requirements in the component."
    body = source.description.strip() or "See the source Jira issue and BR/FR specs."
    component_name = component or settings.related.component or "unspecified"
    return f"""# Proposal

## Why

{why}

After business and functional requirements for `{source.key}` are merged, the `{component_name}` component needs an implementation spec.

## What Changes

- Capture code-change requirements for component `{component_name}`.
- Scope the work to Jira task `{task_key}` under story `{story_key}`.

## Capabilities

### New Capabilities
- `{capability}`: {title}

### Modified Capabilities

## Impact

- Jira: `{source.key}` / `{story_key}` / `{task_key}`
- Specs repository: `{settings.bitbucket.repository}`
- Component repository: `{settings.component.repository}`

## Source description

{body}
"""


def render_implementation_design(
    source: JiraIssue,
    story_key: str,
    task_key: str,
    component: str | None,
) -> str:
    component_name = component or "unspecified"
    return f"""# Design

## Context

Implement `{source.key}` ({source.summary}) in component `{component_name}` as task `{task_key}` of story `{story_key}`.

## Goals

- Change only the `{component_name}` component.
- Satisfy the merged business and functional requirements.

## Non-Goals

- Unrelated refactors
- Changes outside `{component_name}`

## Approach

Describe modules, interfaces and data flow for `{component_name}` that realize the code-change spec.
"""


def render_proposal(settings: Settings, source: JiraIssue, story_key: str | None) -> str:
    capabilities = "\n".join(
        f"- `{name}`: {CAPABILITY_META.get(name, {}).get('title', name)}"
        for name in settings.openspec.capabilities
    )
    story_line = f"- Jira story: `{story_key}`\n" if story_key else ""
    why = source.summary.strip() or "Convert the source improvement into implementable requirements."
    body = source.description.strip() or "See the source Jira issue."
    return f"""# Proposal

## Why

{why}

Source improvement `{source.key}` needs business and functional requirements before implementation.

## What Changes

- Capture business requirements for `{source.key}`.
- Capture functional requirements for `{source.key}`.
{story_line}- Keep the OpenSpec change id `{settings.change_id(source.key)}`.

## Capabilities

### New Capabilities
{capabilities}

### Modified Capabilities

## Impact

- Jira: `{source.key}`
- Repository: `{settings.bitbucket.repository}`

## Source description

{body}
"""


def render_capability_spec(
    capability: str,
    source: JiraIssue,
    component: str | None = None,
) -> str:
    meta = CAPABILITY_META.get(capability, {})
    title = meta.get("title", capability.replace("-", " ").title())
    purpose = meta.get("purpose", f"Requirements for {capability}.")
    bullets = _extract_needles(source.description) or [source.summary]
    requirements = [
        _requirement_block(index, capability, source, needle, component=component)
        for index, needle in enumerate(bullets, start=1)
    ]
    joined = "\n\n".join(requirements)
    return f"""# Spec Delta: {title}

## Purpose

{purpose} Source issue: `{source.key}` — {source.summary}.

## ADDED Requirements

{joined}
"""


def validate_change(path: Path) -> list[str]:
    errors: list[str] = []
    proposal = path / "proposal.md"
    if not proposal.is_file():
        errors.append("missing proposal.md")
    else:
        text = proposal.read_text(encoding="utf-8")
        for header in ("## Why", "## What Changes", "## Capabilities"):
            if header not in text:
                errors.append(f"proposal.md missing {header}")
    specs_root = path / "specs"
    if not specs_root.is_dir():
        errors.append("missing specs/")
        return errors
    spec_files = list(specs_root.glob("*/spec.md"))
    if not spec_files:
        errors.append("no specs/*/spec.md files")
    for spec in spec_files:
        text = spec.read_text(encoding="utf-8")
        if "### Requirement:" not in text:
            errors.append(f"{spec.relative_to(path)} has no ### Requirement:")
        if "#### Scenario:" not in text:
            errors.append(f"{spec.relative_to(path)} has no #### Scenario:")
        if "SHALL" not in text and "MUST" not in text:
            errors.append(f"{spec.relative_to(path)} has no SHALL/MUST statement")
    return errors


def try_openspec_cli(repo: Path, change_id: str, args: list[str]) -> str | None:
    binary = shutil.which("openspec")
    if not binary:
        return None
    result = subprocess.run(
        [binary, *args],
        cwd=repo,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise OpenspecError(
            f"openspec {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout


def openspec_available() -> bool:
    return shutil.which("openspec") is not None


def _extract_needles(description: str) -> list[str]:
    lines: list[str] = []
    for raw in description.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        stripped = re.sub(r"^[-*]\s+", "", stripped)
        stripped = re.sub(r"^\d+[.)]\s+", "", stripped)
        if len(stripped) < 8:
            continue
        lines.append(stripped.rstrip("."))
        if len(lines) >= 5:
            break
    return lines


def _requirement_block(
    index: int,
    capability: str,
    source: JiraIssue,
    needle: str,
    component: str | None = None,
) -> str:
    if capability.startswith("business"):
        kind = "business"
    elif capability in {"code-changes", "implementation"} or capability.startswith("code"):
        kind = "code"
    else:
        kind = "functional"
    name = _requirement_name(kind, index, needle)
    if kind == "business":
        statement = (
            f"The product SHALL deliver the outcome described as \"{needle}\" "
            f"for stakeholders of `{source.key}`."
        )
        scenario_name = "Stakeholder accepts the outcome"
        given = f"the improvement `{source.key}` is in scope"
        then = "the documented business outcome is considered met"
    else:
        statement = (
            f"The system SHALL implement observable behavior that satisfies \"{needle}\" "
            f"from `{source.key}`."
        )
        scenario_name = "Primary flow succeeds"
        given = "the system is available and the actor is authorized"
        then = "the functional outcome is visible to the actor"
    if kind == "code":
        component_name = component or "the component"
        statement = (
            f"The `{component_name}` component SHALL implement \"{needle}\" "
            f"from `{source.key}` without changing unrelated modules."
        )
        scenario_name = "Component change is complete"
        given = f"the `{component_name}` codebase is on the task branch"
        then = "the code change is present and the requirement is satisfied"
    return f"""### Requirement: {name}

{statement}

#### Scenario: {scenario_name}
- **GIVEN** {given}
- **WHEN** the change is exercised
- **THEN** {then}
"""


def _requirement_name(kind: str, index: int, needle: str) -> str:
    words = re.findall(r"[A-Za-zА-Яа-я0-9]+", needle)
    title = " ".join(words[:6]) or f"{kind} outcome {index}"
    return title[:80]


def _ensure_openspec_root(repo: Path) -> None:
    root = repo / "openspec"
    root.mkdir(parents=True, exist_ok=True)
    (root / "specs").mkdir(exist_ok=True)
    config = root / "config.yaml"
    if not config.exists():
        config.write_text("schema: spec-driven\n", encoding="utf-8")
