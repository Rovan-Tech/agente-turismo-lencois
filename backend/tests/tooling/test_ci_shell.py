"""Scripts de shell de `scripts/ci/`: fumaça, verificação de deploy, espera, fuzz e migrations."""

import pytest

from tests.tooling.ci_helpers import executable, run_script


def test_smoke_passes_on_a_healthy_closed_api_with_a_valid_token(fake_api):
    result = run_script("smoke.sh", fake_api["url"], "segredo")

    assert result.returncode == 0, result.stderr
    assert "FALHA" not in result.stderr


def test_smoke_without_a_token_only_checks_the_public_surface(fake_api):
    assert run_script("smoke.sh", fake_api["url"]).returncode == 0


def test_smoke_fails_when_the_token_is_not_accepted(fake_api):
    result = run_script("smoke.sh", fake_api["url"], "token-errado")

    assert result.returncode == 1
    assert "GET /api/tours com token" in result.stderr


def test_smoke_fails_when_the_api_is_open_without_credentials(fake_api):
    fake_api["open"] = True  # a API deixou de exigir credencial

    result = run_script("smoke.sh", fake_api["url"])

    assert result.returncode == 1
    assert "sem token é negado" in result.stderr or "token inválido é negado" in result.stderr


def test_smoke_fails_when_health_is_not_ok(fake_api):
    fake_api["health_body"] = {"status": "degradado"}

    result = run_script("smoke.sh", fake_api["url"])

    assert result.returncode == 1
    assert "/health devolve status ok" in result.stderr


def test_smoke_fails_when_nothing_is_listening():
    result = run_script("smoke.sh", "http://127.0.0.1:9")

    assert result.returncode == 1


def test_a_healthy_revision_keeps_the_traffic(deploy_env):
    log, make_smoke, run = deploy_env

    result = run(make_smoke(fail_first=0), "https://svc.example", "svc", "sa-east1", "rev-1", "tok")

    assert result.returncode == 0
    assert "gcloud" not in log.read_text()


def test_a_cold_start_is_retried_before_giving_up(deploy_env):
    log, make_smoke, run = deploy_env

    result = run(make_smoke(fail_first=2), "https://svc.example", "svc", "sa-east1", "rev-1", "tok")

    assert result.returncode == 0
    assert log.read_text().count("smoke ") == 3
    assert "gcloud" not in log.read_text()


def test_an_unhealthy_revision_sends_the_traffic_back_to_the_previous_one(deploy_env):
    log, make_smoke, run = deploy_env

    result = run(
        make_smoke(fail_first=99), "https://svc.example", "svc", "sa-east1", "rev-1", "tok"
    )

    assert result.returncode == 1
    calls = log.read_text()
    assert calls.count("smoke ") == 3
    assert (
        "gcloud run services update-traffic svc --region sa-east1 --to-revisions rev-1=100" in calls
    )


def test_the_smoke_receives_the_url_and_the_token(deploy_env):
    log, make_smoke, run = deploy_env

    run(make_smoke(fail_first=0), "https://svc.example", "svc", "sa-east1", "rev-1", "tok")

    assert "smoke https://svc.example tok" in log.read_text()


def test_without_a_previous_revision_it_fails_but_does_not_touch_the_traffic(deploy_env):
    log, make_smoke, run = deploy_env

    result = run(make_smoke(fail_first=99), "https://svc.example", "svc", "sa-east1", "", "tok")

    assert result.returncode == 1
    assert "gcloud" not in log.read_text()
    assert "sem revisão anterior" in result.stdout + result.stderr


def test_wait_for_url_returns_as_soon_as_the_url_answers(fake_api):
    assert run_script("wait_for_url.sh", f"{fake_api['url']}/health", "5").returncode == 0


def test_wait_for_url_gives_up_after_the_timeout():
    result = run_script("wait_for_url.sh", "http://127.0.0.1:9/health", "1")

    assert result.returncode == 1
    assert "não respondeu" in result.stderr


def test_fuzz_runs_the_robustness_checks_with_the_dashboard_token(tmp_path):
    log = tmp_path / "args.log"
    fake = executable(tmp_path / "schemathesis", f'printf "%s\\n" "$@" > "{log}"\n')

    result = run_script(
        "fuzz_api.sh", "http://api.test", "tok", env={"SCHEMATHESIS_BIN": str(fake)}
    )

    args = log.read_text().splitlines()
    assert result.returncode == 0
    assert args[:3] == ["run", "http://api.test/openapi.json", "--url"]
    assert "Authorization: Bearer tok" in args
    checks = args[args.index("--checks") + 1].split(",")
    assert "not_a_server_error" in checks
    assert "status_code_conformance" not in checks


def test_fuzz_checks_and_examples_can_be_overridden_for_the_nightly_run(tmp_path):
    log = tmp_path / "args.log"
    fake = executable(tmp_path / "schemathesis", f'printf "%s\\n" "$@" > "{log}"\n')
    env = {"SCHEMATHESIS_BIN": str(fake), "FUZZ_CHECKS": "all", "FUZZ_EXAMPLES": "200"}

    run_script("fuzz_api.sh", "http://api.test", env=env)

    args = log.read_text().splitlines()
    assert args[args.index("--checks") + 1] == "all"
    assert args[args.index("--max-examples") + 1] == "200"


def test_fuzz_fails_when_the_tool_reports_a_failure(tmp_path):
    fake = executable(tmp_path / "schemathesis", "exit 1\n")

    assert (
        run_script("fuzz_api.sh", "http://api.test", env={"SCHEMATHESIS_BIN": str(fake)}).returncode
        == 1
    )


def _run_migrations_check(tmp_path, fake_python_body):
    """Roda `check_migrations.sh` com um `python` falso; devolve o resultado e as chamadas."""
    log = tmp_path / "calls.log"
    fake = executable(tmp_path / "python", f'echo "$*" >> "{log}"\n{fake_python_body}')
    env = {"PYTHON": str(fake), "DATABASE_URL": "postgresql://x/y"}

    result = run_script("check_migrations.sh", env=env)

    return result, log.read_text().splitlines()


def test_check_migrations_runs_up_check_down_up_in_order(tmp_path):
    result, calls = _run_migrations_check(tmp_path, "")

    assert result.returncode == 0
    assert calls == [
        "-m alembic upgrade head",
        "-m alembic check",
        "-m alembic downgrade base",
        "-m alembic upgrade head",
    ]


def test_check_migrations_stops_at_the_first_failing_step(tmp_path):
    result, calls = _run_migrations_check(tmp_path, '[ "$3" != "check" ] || exit 1\n')

    assert result.returncode == 1
    assert calls == ["-m alembic upgrade head", "-m alembic check"]


def test_check_migrations_requires_a_database_url():
    result = run_script("check_migrations.sh", env={"DATABASE_URL": ""})

    assert result.returncode != 0


# --- previous_revision.sh ------------------------------------------------------------------------


def _previous_revision(tmp_path, gcloud_body):
    gcloud = executable(tmp_path / "gcloud", gcloud_body)
    return run_script("previous_revision.sh", "svc", "sa-east1", env={"GCLOUD_BIN": str(gcloud)})


def test_previous_revision_prints_the_revision_serving_traffic(tmp_path):
    result = _previous_revision(tmp_path, 'echo "svc-00012-abc"\n')

    assert result.returncode == 0
    assert result.stdout == "svc-00012-abc\n"


def test_previous_revision_keeps_gcloud_warnings_out_of_the_output(tmp_path):
    body = 'echo "WARNING: nova versão do gcloud disponível" >&2\necho "svc-00012-abc"\n'

    result = _previous_revision(tmp_path, body)

    assert result.returncode == 0
    assert result.stdout == "svc-00012-abc\n"


def test_previous_revision_only_warns_on_the_first_deploy(tmp_path):
    body = 'echo "ERROR: (gcloud.run.services.describe) Cannot find service [svc]" >&2\nexit 1\n'

    result = _previous_revision(tmp_path, body)

    assert result.returncode == 0
    assert result.stdout == ""
    assert "::warning::" in result.stderr


@pytest.mark.parametrize(
    "message",
    [
        "ERROR: (gcloud.run.services.describe) PERMISSION_DENIED: caller lacks permission",
        "ERROR: (gcloud.run.services.describe) Unavailable: tente de novo",
        "ERROR: Project [meu-projeto] not found or permission denied",
        "gcloud: command not found",
    ],
)
def test_previous_revision_fails_on_any_other_gcloud_error(tmp_path, message):
    result = _previous_revision(tmp_path, f'echo "{message}" >&2\nexit 1\n')

    assert result.returncode == 1
    assert message in result.stderr
    assert result.stdout == ""
