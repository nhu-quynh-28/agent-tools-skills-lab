"""csv-quality script: thống kê fixture, tính tải công việc, lỗi input/schema/parse exit 1, lỗi dữ liệu exit 0."""

import json
import subprocess
import sys

import pytest

import paths

SCRIPT = paths.FIXTURES_DIR / "skills" / "csv-quality" / "scripts" / "check_csv.py"


def run(path, max_hours=8, extra_args=None):
    cmd = [sys.executable, str(SCRIPT), "--input", str(path)]
    if max_hours is not None:
        cmd.extend(["--max-hours", str(max_hours)])
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=10)


def write_csv(tmp_path, text):
    path = tmp_path / "t.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_fixture_statistics():
    result = run(paths.FIXTURES_DIR / "data" / "tasks.csv", max_hours=8)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["row_count"] == 6
    assert data["missing_owner_count"] == 1
    assert data["invalid_hours_count"] == 1
    assert data["duplicate_id_count"] == 1
    assert data["duplicate_ids"] == ["T02"]
    assert [(i["line"], i["column"], i["type"]) for i in data["issues"]] == [
        (4, "owner", "missing_owner"),
        (5, "hours", "invalid_hours"),
        (6, "task_id", "duplicate_id"),
    ]
    assert data["max_hours"] == 8


@pytest.mark.parametrize("hours", ["NaN", "nan", "Infinity", "-inf", "-1", ""])
def test_non_finite_negative_or_empty_hours_rejected(tmp_path, hours):
    data = json.loads(run(write_csv(tmp_path, f"task_id,owner,hours\nT01,Lan,{hours}\n"), max_hours=8).stdout)
    assert data["invalid_hours_count"] == 1
    assert data["issues"][0]["line"] == 2


def test_clean_data_exit_0_without_issues(tmp_path):
    result = run(write_csv(tmp_path, "task_id,owner,hours\nT01,Lan,4\nT02,Minh,2.5\n"), max_hours=8)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["issues"] == []
    assert data["hours_by_owner"] == {"Lan": 4, "Minh": 2.5}
    assert data["overloaded_owners"] == []
    assert data["excluded_rows"] == []


def test_missing_file_exit_1(tmp_path):
    result = run(tmp_path / "khong-co.csv", max_hours=8)
    assert result.returncode == 1
    assert result.stdout == ""
    assert "Không đọc được file" in result.stderr


def test_missing_column_exit_1(tmp_path):
    result = run(write_csv(tmp_path, "task_id,owner\nT01,Lan\n"), max_hours=8)
    assert result.returncode == 1
    assert "Thiếu cột bắt buộc: hours" in result.stderr


def test_parse_error_exit_1(tmp_path):
    result = run(write_csv(tmp_path, 'task_id,owner,hours\nT01,"La"n,4\n'), max_hours=8)
    assert result.returncode == 1
    assert "Lỗi parse CSV" in result.stderr


def test_missing_max_hours_exit_1(tmp_path):
    result = run(write_csv(tmp_path, "task_id,owner,hours\nT01,Lan,4\n"), max_hours=None)
    assert result.returncode == 1
    assert "Thiếu tham số bắt buộc --max-hours" in result.stderr


@pytest.mark.parametrize("bad_max", ["-1", "NaN", "Infinity", "abc"])
def test_invalid_max_hours_exit_1(tmp_path, bad_max):
    csv_file = write_csv(tmp_path, "task_id,owner,hours\nT01,Lan,4\n")
    result = subprocess.run([sys.executable, str(SCRIPT), "--input", str(csv_file), "--max-hours", bad_max],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 1
    assert "không phải số hữu hạn không âm" in result.stderr


def test_workload_threshold_8():
    csv_path = paths.FIXTURES_DIR / "data" / "workload.csv"
    result = run(csv_path, max_hours=8)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["hours_by_owner"] == {"Lan": 9, "Minh": 3}
    assert data["overloaded_owners"] == [{"owner": "Lan", "total_hours": 9}]
    assert [(r["line"], r["task_id"], r["reasons"]) for r in data["excluded_rows"]] == [
        (5, "T04", ["invalid_hours"]),
        (6, "T02", ["duplicate_id"]),
        (7, "T05", ["missing_owner"]),
    ]


def test_workload_threshold_9():
    csv_path = paths.FIXTURES_DIR / "data" / "workload.csv"
    result = run(csv_path, max_hours=9)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["hours_by_owner"] == {"Lan": 9, "Minh": 3}
    assert data["overloaded_owners"] == []
    assert len(data["excluded_rows"]) == 3


def test_edge_case_first_id_has_invalid_hours():
    """Trường hợp đặc biệt: lần xuất hiện đầu tiên của ID có hours không hợp lệ.

    Lần 1 (dòng 2): E01 có hours='abc' -> loại vì invalid_hours.
    Lần 2 (dòng 3): E01 có hours='5' -> loại vì duplicate_id (không giữ lần hợp lệ đầu tiên).
    Lan không được cộng 5 giờ. Chỉ Minh có tổng 0 giờ. Ngưỡng 0 không ai quá tải.
    """
    csv_path = paths.FIXTURES_DIR / "data" / "workload-edge.csv"
    result = run(csv_path, max_hours=0)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["hours_by_owner"] == {"Minh": 0}
    assert "Lan" not in data["hours_by_owner"]
    assert data["overloaded_owners"] == []
    assert [(r["line"], r["task_id"], r["reasons"]) for r in data["excluded_rows"]] == [
        (2, "E01", ["invalid_hours"]),
        (3, "E01", ["duplicate_id"]),
    ]


def test_script_does_not_modify_input():
    source = paths.FIXTURES_DIR / "data" / "workload.csv"
    before = source.read_bytes()
    run(source, max_hours=8)
    assert source.read_bytes() == before
