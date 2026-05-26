#!/usr/bin/env python3
"""File responsibility: Generate local development metrics summary.

Project Metrics Summary Script.

Provides a concise overview of project statistics including:
- Source code metrics (files, SLOC, complexity)
- Test code metrics (coverage, test counts)
- Code quality metrics (duplication, risk analysis)

Architecture:
1. Data gathering phase - collect all metrics into data structures
2. Report generation phase - format and display results
"""

from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path
from typing import Any


# ANSI color codes
class Colors:
    """ANSI color codes for terminal output."""

    BOLD = "\033[1m"
    CYAN = "\033[0;36m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[0;33m"
    RED = "\033[0;31m"
    NC = "\033[0m"  # No Color


def output(message: str = "") -> None:
    print(message)  # noqa: T201


def run_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a shell command and return the result."""
    return subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603


def gather_complexity_metrics(src_paths: list[Path]) -> dict[str, Any]:
    """Gather complexity metrics using radon."""
    result = run_command(["uv", "run", "radon", "cc", "-a", "-j", *_path_list_to_str_parts(src_paths)])
    if result.returncode != 0:
        return {}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


def _path_list_to_str_parts(path_list: list[Path]) -> list[str]:
    return [str(p) for p in path_list]


def calculate_complexity_stats(data: dict[str, Any]) -> dict[str, Any]:
    """Calculate complexity statistics from radon JSON output."""
    file_complexities = []
    total_paths = 0
    file_code_paths = []

    for filepath, blocks in data.items():
        if not blocks:
            continue
        max_complexity = max(block.get("complexity", 0) for block in blocks)
        file_complexities.append((filepath, max_complexity))

        file_total = sum(block.get("complexity", 0) for block in blocks)
        file_code_paths.append(file_total)
        total_paths += file_total

    file_complexities.sort(key=lambda x: x[1], reverse=True)

    avg_paths = total_paths / len(file_code_paths) if file_code_paths else 0
    max_paths = max(file_code_paths) if file_code_paths else 0
    files_high_cc = sum(1 for _, complexity in file_complexities if complexity > 5)

    return {
        "top5": file_complexities[:5],
        "total_paths": total_paths,
        "avg_paths": avg_paths,
        "max_paths": max_paths,
        "files_high_cc": files_high_cc,
    }


def gather_source_metrics(src_paths: list[Path]) -> dict[str, Any]:
    """Gather source code metrics."""
    py_files = []
    for src_path in src_paths:
        py_files.extend(list(src_path.rglob("*.py")))

    total_files = len(py_files)

    line_counts = [len(f.read_text().splitlines()) for f in py_files]
    max_lines = max(line_counts) if line_counts else 0
    avg_lines = sum(line_counts) // len(line_counts) if line_counts else 0

    total_sloc = 0
    for f in py_files:
        lines = f.read_text().splitlines()
        total_sloc += sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))

    return {
        "total_files": total_files,
        "max_lines": max_lines,
        "avg_lines": avg_lines,
        "total_sloc": total_sloc,
    }


def gather_test_metrics(tests_paths: list[Path], package: str) -> dict[str, Any]:
    """Gather test code metrics."""
    test_files = []
    for tests_path in tests_paths:
        test_files.extend(tests_path.rglob("test_*.py"))

    total_test_files = len(test_files)

    total_test_sloc = 0
    for f in test_files:
        lines = f.read_text().splitlines()
        total_test_sloc += sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))

    # Count test functions
    test_function_count = 0
    for f in test_files:
        content = f.read_text()
        test_function_count += sum(1 for line in content.splitlines() if line.strip().startswith("def test_"))

    return {
        "total_test_files": total_test_files,
        "total_test_sloc": total_test_sloc,
        "test_function_count": test_function_count,
    }


def get_coverage_metrics(package: str, tests_paths: list[Path]) -> dict[str, Any]:
    """Get coverage metrics from pytest."""
    result = run_command(
        [
            "uv",
            "run",
            "pytest",
            *_path_list_to_str_parts(tests_paths),
            f"--cov={package}",
            "--cov-report=json:coverage.json",
            "--quiet",
            "--no-header",
            "--tb=no",
        ]
    )

    test_results = ""
    for line in result.stdout.split("\n"):
        if "passed" in line or "failed" in line:
            test_results = line.strip()
            break

    if not Path("coverage.json").exists():
        return {"test_results": test_results, "overall_coverage": "N/A"}

    try:
        with open("coverage.json") as f:
            data = json.load(f)
        percent_covered = data.get("totals", {}).get("percent_covered", 0)
        return {
            "test_results": test_results,
            "overall_coverage": f"{percent_covered:.1f}%",
        }
    except Exception:
        return {"test_results": test_results, "overall_coverage": "N/A"}


def output_header(text: str) -> None:
    output(f"\n{Colors.BOLD}{Colors.GREEN}{text}{Colors.NC}")


def report_summary(src: dict, complexity: dict, tests: dict, coverage: dict) -> None:
    """Display summary statistics."""
    output_header("=== Project Metrics Summary ===")

    output(f"{Colors.BOLD}Source Code:{Colors.NC}")
    output(f"  Files: {src['total_files']} | SLOC: {src['total_sloc']}")
    output(f"  Avg file size: {src['avg_lines']} lines | Max: {src['max_lines']} lines")

    output(f"\n{Colors.BOLD}Complexity:{Colors.NC}")
    if complexity.get("top5"):
        output(f"  Total code paths: {complexity['total_paths']:.0f}")
        output(f"  Avg paths/file: {complexity['avg_paths']:.1f}")
        output(f"  Max paths/file: {complexity['max_paths']}")
        output(f"  Files with complexity > 5: {complexity['files_high_cc']}")
        output("  Top 5 most complex files:")
        for filepath, cc in complexity["top5"]:
            output(f"    {filepath:60s} (cc: {cc})")
    else:
        output(f"  {Colors.YELLOW}No complexity data available{Colors.NC}")

    output(f"\n{Colors.BOLD}Tests:{Colors.NC}")
    output(f"  Test files: {tests['total_test_files']} | Test functions: {tests['test_function_count']}")
    output(f"  Test SLOC: {tests['total_test_sloc']}")

    output(f"\n{Colors.BOLD}Coverage:{Colors.NC}")
    output(f"  {coverage['overall_coverage']}")
    if coverage.get("test_results"):
        output(f"  {coverage['test_results']}")

    output("")


def main() -> None:
    """Main entry point."""
    # Load config from pyproject.toml
    try:
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        package = data.get("project", {}).get("name", "").replace("-", "_")
    except Exception:
        package = "history_wb"

    src_paths = [Path("freecad/history_wb")]
    tests_paths = [Path("tests")]
    coverage_tests_paths = [Path("tests/unit")]

    # Gather metrics
    output("Gathering metrics...")

    src_metrics = gather_source_metrics(src_paths)

    complexity_data = gather_complexity_metrics(src_paths)
    complexity_metrics = calculate_complexity_stats(complexity_data)

    test_metrics = gather_test_metrics(tests_paths, package)

    coverage_metrics = get_coverage_metrics(package, coverage_tests_paths)

    # Report
    report_summary(src_metrics, complexity_metrics, test_metrics, coverage_metrics)


if __name__ == "__main__":
    main()
