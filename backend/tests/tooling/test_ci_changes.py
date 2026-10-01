import pytest

from tests.tooling.ci_helpers import ROOT, git, load_ci_module

changes = load_ci_module("changes")
pr_title = load_ci_module("pr_title")


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (["docs/ci-cd.md", "README.md"], set()),
        (["docs/diagrama.png"], set()),
        (["backend/app/main.py"], {"backend", "docker"}),
        (["backend/tests/test_x.py"], {"backend"}),
        (["frontend/src/App.tsx"], {"frontend"}),
        (["frontend/package-lock.json"], {"frontend", "deps"}),
        (["backend/requirements.txt"], {"backend", "docker", "deps"}),
        (["backend/Dockerfile"], {"backend", "docker"}),
        ([".hadolint.yaml"], {"docker"}),
        (["docs/ci-cd.md", "backend/app/main.py"], {"backend", "docker"}),
        (["scripts/quality_gate.py"], {"backend", "frontend"}),
        (["scripts/ci/changes.py"], {"backend", "frontend", "workflows"}),
        ([".github/dependabot.yml"], {"workflows"}),
        ([".github/workflows/ci.yml"], {"backend", "frontend", "docker", "deps", "workflows"}),
        (["backend/app/main.py", "frontend/src/App.tsx"], {"backend", "docker", "frontend"}),
        (["backend/alembic/versions/0005_x.py"], {"backend", "docker"}),
        (["scripts/ci/smoke.sh"], {"backend", "frontend", "workflows", "docker"}),
    ],
)
def test_classify_marks_only_the_jobs_the_diff_can_affect(paths, expected):
    result = changes.classify(paths)

    assert {name for name, needed in result.items() if needed} == expected


@pytest.mark.parametrize(
    "path",
    [
        ".claude/hooks/guard_bash.py",
        ".claude/agents/code-reviewer.md",
        ".mypy-baseline.json",
        ".coverage-baseline.json",
        ".jscpd.json",
        ".pre-commit-config.yaml",
        "Makefile",
        "docs/checklist-engenharia.md",
        "docs/tech-debt.md",
        "arquivo-novo-na-raiz.toml",
    ],
)
def test_classify_runs_everything_for_a_path_no_group_recognizes(path):
    assert all(changes.classify([path, "docs/a.md"]).values())


def test_every_versioned_file_outside_the_docs_turns_at_least_one_job_on():
    files = git(ROOT, "ls-files").splitlines()
    candidates = [path for path in files if not changes._is_docs(path)]

    silent = [path for path in candidates if not any(changes.classify([path]).values())]

    assert silent == []


def test_classify_always_reports_every_group():
    assert set(changes.classify([])) == {"backend", "frontend", "docker", "deps", "workflows"}


def test_everything_runs_when_there_is_nothing_to_compare():
    assert all(changes.classify(None).values())


def test_changed_files_lists_what_the_pr_touched(repo):
    base = git(repo, "rev-parse", "HEAD")
    (repo / "backend").mkdir()
    (repo / "backend" / "app.py").write_text("x")
    (repo / "docs" / "a.md").write_text("b")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "change")
    head = git(repo, "rev-parse", "HEAD")

    files = changes.changed_files(base, head, cwd=repo)

    assert sorted(files) == ["backend/app.py", "docs/a.md"]


def test_changed_files_lists_both_sides_of_a_rename(repo):
    base = git(repo, "rev-parse", "HEAD")
    (repo / "backend").mkdir()
    (repo / "backend" / "x.py").write_text("x = 1\n" * 20)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "add")
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "mv", "backend/x.py", "docs/x.md")
    git(repo, "commit", "-q", "-m", "move to docs")

    files = changes.changed_files(base, "HEAD", cwd=repo)

    assert sorted(files) == ["backend/x.py", "docs/x.md"]
    assert changes.classify(files)["backend"]


def test_changed_files_keeps_accented_names_unquoted(repo):
    base = git(repo, "rev-parse", "HEAD")
    (repo / "backend").mkdir()
    (repo / "backend" / "ação.py").write_text("x")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "accent")

    files = changes.changed_files(base, "HEAD", cwd=repo)

    assert files == ["backend/ação.py"]
    assert changes.classify(files)["backend"]


def test_main_prints_every_group_as_github_output(repo, monkeypatch, capsys):
    base = git(repo, "rev-parse", "HEAD")
    (repo / "frontend").mkdir()
    (repo / "frontend" / "x.ts").write_text("x")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "ui")
    monkeypatch.chdir(repo)

    assert changes.main(["--base", base, "--head", "HEAD"]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert sorted(lines) == [
        "backend=false",
        "deps=false",
        "docker=false",
        "frontend=true",
        "workflows=false",
    ]


def test_main_runs_everything_without_a_base(capsys):
    assert changes.main([]) == 0

    assert set(capsys.readouterr().out.splitlines()) == {
        f"{group}=true" for group in ("backend", "frontend", "docker", "deps", "workflows")
    }


@pytest.mark.parametrize("ref", ["--output=/tmp/x", "-p", "a b", "a;b", "", "x" * 101])
def test_changed_files_refuses_refs_that_could_be_git_options(repo, ref):
    assert changes.changed_files(ref, "HEAD", cwd=repo) is None
    assert changes.changed_files("HEAD", ref, cwd=repo) is None


def test_changed_files_gives_up_on_an_unknown_commit(repo):
    assert changes.changed_files("0" * 40, "HEAD", cwd=repo) is None


@pytest.mark.parametrize(
    "title",
    [
        "feat: add the booking calendar",
        "fix: reject webhook with invalid signature",
        "chore(deps): bump zod from 4.6.4 to 4.6.5",
        "ci: add the nightly security scan",
        "feat!: drop the old endpoint",
        "docs: explain the pipeline",
    ],
)
def test_pr_title_accepts_conventional_commits(title):
    assert pr_title.is_valid(title)


def test_pr_title_description_is_limited_to_100_characters():
    prefix = "feat: "

    assert pr_title.is_valid(prefix + "a" * 100)
    assert not pr_title.is_valid(prefix + "a" * 101)


def test_pr_title_main_exits_zero_for_a_valid_title(capsys):
    assert pr_title.main(["fix: handle empty webhook"]) == 0
    assert "Conventional Commits" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [["Add stuff"], []])
def test_pr_title_main_explains_the_format_when_the_title_is_invalid(argv, capsys):
    assert pr_title.main(argv) == 1
    assert "::error::" in capsys.readouterr().err


@pytest.mark.parametrize(
    "title",
    [
        "Add booking calendar",
        "feat add the calendar",
        "feat:",
        "feat: ",
        "Feat: capital type",
        "wip: not a type",
        "",
        "feat: " + "x" * 200,
    ],
)
def test_pr_title_rejects_everything_else(title):
    assert not pr_title.is_valid(title)
