"""Guard: every GitHub Actions workflow must be parseable YAML.

A workflow that does not parse fails the run in zero seconds with only
"This run likely failed because of a workflow file issue" — no line number,
no job log. That happened here: an unquoted step name containing ": " was
read as a nested mapping.
"""

from pathlib import Path

import pytest
import yaml

WORKFLOW_DIR = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def workflow_files() -> list[Path]:
    return sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))


def test_at_least_one_workflow_exists():
    assert workflow_files(), f"no workflow files found under {WORKFLOW_DIR}"


@pytest.mark.parametrize("path", workflow_files(), ids=lambda p: p.name)
def test_workflow_parses(path: Path):
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        pytest.fail(f"{path.name} is not valid YAML: {error}")
    assert isinstance(document, dict), f"{path.name} must parse to a mapping"


@pytest.mark.parametrize("path", workflow_files(), ids=lambda p: p.name)
def test_workflow_declares_jobs_with_steps(path: Path):
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    jobs = document.get("jobs")
    assert jobs, f"{path.name} declares no jobs"
    for name, job in jobs.items():
        assert job.get("runs-on"), f"{path.name}: job '{name}' has no runs-on"
        assert job.get("steps"), f"{path.name}: job '{name}' has no steps"
