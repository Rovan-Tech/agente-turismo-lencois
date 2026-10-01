"""`pr-feedback-clickup.yml`: quando um CI vermelho fecha o PR e quando só comenta."""

import json
import os
import subprocess
import textwrap

import pytest

from tests.tooling.ci_helpers import ROOT, executable

WORKFLOW = ROOT / ".github" / "workflows" / "pr-feedback-clickup.yml"


def _script(tmp_path):
    """O bloco `run:` do workflow, extraído como está, para rodar com `gh` e `curl` falsos."""
    text = WORKFLOW.read_text(encoding="utf-8")
    block = text.split("        run: |\n", 1)[1]
    path = tmp_path / "feedback.sh"
    path.write_text(textwrap.dedent(block))
    return path


def _jobs_json(failed):
    """Jobs de uma execução do CI como o GitHub devolve: o `ci-ok` fica vermelho junto."""
    names = ["changes", "pr-title", "backend", "frontend", "docker", "ci-ok"]
    bad = {*failed, "ci-ok"}
    jobs = [
        {
            "name": name,
            "conclusion": "failure" if name in bad else "success",
            "steps": [
                {"name": f"passo de {name}", "conclusion": "failure" if name in bad else "success"}
            ],
        }
        for name in names
    ]
    return json.dumps({"jobs": jobs})


def _feedback_env(bin_dir):
    return {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "GH_TOKEN": "x",
        "CLICKUP_API_TOKEN": "x",
        "REPO": "o/r",
        "HEAD_SHA": "abc",
        "RUN_URL": "https://run.example",
        "RUN_ID": "1",
        "WORKFLOW_NAME": "CI",
        "CLICKUP_FAILED_STATUS": "PR reprovado",
    }


def _run_feedback(tmp_path, failed):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    jobs = tmp_path / "jobs.json"
    jobs.write_text(_jobs_json(failed))
    executable(
        bin_dir / "gh",
        f"""echo "gh $*" >> "{log}"
expr=""
args=("$@")
for i in "${{!args[@]}}"; do [ "${{args[$i]}}" = "--jq" ] && expr="${{args[$((i + 1))]}}"; done
case "$*" in
  *commits/*/pulls*) echo 7 ;;
  *.user.type*) echo User ;;
  *.user.login*) echo patrick ;;
  *.title*) echo "feat: x" ;;
  *.body*) echo "tarefa https://app.clickup.com/t/abc123" ;;
  "run view"*--log-failed*) echo log ;;
  "run view"*) jq -r "$expr" "{jobs}" ;;
esac
""",
    )
    executable(bin_dir / "curl", f'echo "curl $*" >> "{log}"\nprintf 200\n')
    env = _feedback_env(bin_dir)
    command = ["bash", str(_script(tmp_path))]
    result = subprocess.run(  # noqa: S603  # bash e o script extraído do próprio workflow
        command, env=env, capture_output=True, text=True, check=False
    )
    return result, log.read_text()


def test_a_bad_title_only_comments_and_leaves_the_pr_and_the_task_alone(tmp_path):
    result, calls = _run_feedback(tmp_path, ["pr-title"])

    assert result.returncode == 0
    assert "pr comment" in calls
    assert "pr close" not in calls
    assert "clickup" not in calls


@pytest.mark.parametrize(
    "failed",
    [["backend"], ["pr-title", "backend"], ["docker", "frontend"], ["frontend", "pr-title"]],
)
def test_any_other_failed_job_still_warns_clickup_and_closes_the_pr(tmp_path, failed):
    result, calls = _run_feedback(tmp_path, failed)

    assert result.returncode == 0
    assert "pr close" in calls
    assert "clickup" in calls
