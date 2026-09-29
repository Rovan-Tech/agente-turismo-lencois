from pathlib import Path

import check_design_tokens as cdt
import pytest


def test_contrast_ratio_black_on_white_is_21():
    assert round(cdt.contrast_ratio("#000000", "#ffffff"), 1) == 21.0


def test_real_tokens_pass_wcag_aa_in_both_themes():
    css = cdt.TOKENS_FILE.read_text(encoding="utf-8")

    assert cdt.check_contrast(css) == []


def test_check_contrast_reports_low_contrast_pair():
    css = ":root { --color-text-primary: #ffffff; --color-bg-page: #fefefe; }"

    errors = cdt.check_contrast(css)

    assert any("texto principal na página" in e for e in errors)


@pytest.mark.parametrize(
    "line",
    [
        'const c = "#0F7A8C";',
        "color: rgb(1, 2, 3);",
        "font-family: Arial;",
        '<div className="bg-gray-100">',
        '<div className="text-lagoa">',
        '<p className="opacity-70">',
    ],
)
def test_scan_file_flags_values_outside_tokens(tmp_path, line):
    target = tmp_path / "Comp.tsx"
    target.write_text(line + "\n", encoding="utf-8")

    assert len(cdt.scan_file(target)) >= 1


def test_scan_file_accepts_semantic_classes(tmp_path):
    target = tmp_path / "Comp.tsx"
    target.write_text('<p className="bg-surface text-neutral-subtle">ok</p>\n', encoding="utf-8")

    assert cdt.scan_file(target) == []


def test_scan_file_skips_the_tokens_file():
    assert cdt.scan_file(Path(cdt.TOKENS_FILE)) == []


def test_frontend_sources_have_no_violations():
    violations = [v for f in cdt.default_targets() for v in cdt.scan_file(f)]

    assert violations == []
