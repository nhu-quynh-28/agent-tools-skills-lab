#!/usr/bin/env python3
"""Kiểm tra chất lượng CSV công việc (task_id, owner, hours) và tính tải công việc theo người.

Cách chạy (cwd là workspace):
    python skills/csv-quality/scripts/check_csv.py --input data/workload.csv --max-hours 8

Exit 0: phân tích thành công, kể cả khi dữ liệu có lỗi chất lượng hay có người quá tải.
Exit 1: thiếu/sai tham số --max-hours, file không tồn tại/không đọc được, thiếu cột bắt buộc hoặc lỗi parse CSV.
Script chỉ đọc, không sửa file CSV đầu vào.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys

REQUIRED_COLUMNS = ("task_id", "owner", "hours")
REASON_ORDER = ("wrong_field_count", "missing_task_id", "duplicate_id", "missing_owner", "invalid_hours")


class InputError(Exception):
    pass


def parse_hours(raw: str | None) -> float | None:
    """Số giờ hợp lệ: số hữu hạn, không âm. Trả None nếu không hợp lệ."""
    if raw is None or not raw.strip():
        return None
    try:
        value = float(raw.strip())
    except ValueError:
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def clean_num(val: float | int) -> int | float:
    """Rút gọn số nguyên dạng float (9.0 -> 9), giữ số thập phân và làm tròn tránh sai số nhị phân."""
    if isinstance(val, (int, float)) and float(val).is_integer():
        return int(val)
    return round(float(val), 4)


def parse_max_hours(raw: str | None) -> float | None:
    if raw is None or not str(raw).strip():
        return None
    try:
        value = float(str(raw).strip())
    except ValueError:
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def analyze(path: str, max_hours: float) -> dict:
    try:
        handle = open(path, encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise InputError(f"Không đọc được file {path}: {exc.strerror or exc}") from exc
    with handle:
        reader = csv.reader(handle, strict=True)
        try:
            header = next(reader, None)
            if header is None:
                raise InputError(f"File {path} rỗng, không có header.")
            columns = [c.strip() for c in header]
            missing = [c for c in REQUIRED_COLUMNS if c not in columns]
            if missing:
                raise InputError(f"Thiếu cột bắt buộc: {', '.join(missing)}. Header hiện có: {', '.join(columns)}")
            index = {name: columns.index(name) for name in REQUIRED_COLUMNS}

            row_count = 0
            missing_owner = 0
            invalid_hours = 0
            first_seen: dict[str, int] = {}
            duplicate_ids: list[str] = []
            issues: list[dict] = []

            # Thống kê tải công việc và dòng bị loại
            seen_task_ids: set[str] = set()
            hours_by_owner: dict[str, float] = {}
            excluded_rows: list[dict] = []

            for row in reader:
                line = reader.line_num
                if not any(cell.strip() for cell in row):
                    continue  # bỏ qua dòng trống
                row_count += 1

                def cell(name: str) -> str:
                    position = index[name]
                    return row[position].strip() if position < len(row) else ""

                task_id, owner, hours = cell("task_id"), cell("owner"), cell("hours")

                # 1. Thu thập issues chất lượng dữ liệu cũ
                if len(row) != len(columns):
                    issues.append({
                        "line": line,
                        "column": None,
                        "type": "wrong_field_count",
                        "task_id": task_id or None,
                        "message": f"Có {len(row)} trường, header có {len(columns)} cột.",
                    })
                if not task_id:
                    issues.append({
                        "line": line,
                        "column": "task_id",
                        "type": "missing_task_id",
                        "task_id": None,
                        "message": "task_id trống.",
                    })
                elif task_id in first_seen:
                    if task_id not in duplicate_ids:
                        duplicate_ids.append(task_id)
                    issues.append({
                        "line": line,
                        "column": "task_id",
                        "type": "duplicate_id",
                        "task_id": task_id,
                        "message": f"task_id {task_id} đã xuất hiện ở line {first_seen[task_id]}.",
                    })
                else:
                    first_seen[task_id] = line

                if not owner:
                    missing_owner += 1
                    issues.append({
                        "line": line,
                        "column": "owner",
                        "type": "missing_owner",
                        "task_id": task_id or None,
                        "message": "owner trống.",
                    })

                parsed_h = parse_hours(hours)
                if parsed_h is None:
                    invalid_hours += 1
                    issues.append({
                        "line": line,
                        "column": "hours",
                        "type": "invalid_hours",
                        "task_id": task_id or None,
                        "value": hours,
                        "message": f"hours '{hours}' không phải số hữu hạn không âm.",
                    })

                # 2. Quy tắc loại trừ dòng và tính tổng giờ
                # Mỗi ID không rỗng chỉ giữ lần xuất hiện đầu tiên; lần sau bị loại (duplicate_id)
                is_duplicate = False
                if task_id:
                    if task_id in seen_task_ids:
                        is_duplicate = True
                    else:
                        seen_task_ids.add(task_id)

                reasons: list[str] = []
                if len(row) != len(columns):
                    reasons.append("wrong_field_count")
                if not task_id:
                    reasons.append("missing_task_id")
                if is_duplicate:
                    reasons.append("duplicate_id")
                if not owner:
                    reasons.append("missing_owner")
                if parsed_h is None:
                    reasons.append("invalid_hours")

                if reasons:
                    # Sắp xếp mã lý do theo REASON_ORDER để ổn định
                    ordered_reasons = [r for r in REASON_ORDER if r in reasons]
                    excluded_rows.append({
                        "line": line,
                        "task_id": task_id if task_id else None,
                        "reasons": ordered_reasons,
                    })
                else:
                    # Dòng hợp lệ: cộng giờ cho owner
                    hours_by_owner[owner] = hours_by_owner.get(owner, 0.0) + parsed_h

        except csv.Error as exc:
            raise InputError(f"Lỗi parse CSV ở line {reader.line_num}: {exc}") from exc
        except UnicodeDecodeError as exc:
            raise InputError(f"File {path} không phải UTF-8: {exc}") from exc

    overloaded_owners = [
        {"owner": o, "total_hours": clean_num(h)}
        for o, h in sorted(hours_by_owner.items(), key=lambda item: item[0])
        if h > max_hours
    ]

    return {
        "input": path,
        "max_hours": clean_num(max_hours),
        "row_count": row_count,
        "missing_owner_count": missing_owner,
        "invalid_hours_count": invalid_hours,
        "duplicate_id_count": len(duplicate_ids),
        "duplicate_ids": duplicate_ids,
        "hours_by_owner": {k: clean_num(v) for k, v in hours_by_owner.items()},
        "overloaded_owners": overloaded_owners,
        "excluded_rows": sorted(excluded_rows, key=lambda item: item["line"]),
        "issues": sorted(issues, key=lambda item: item["line"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kiểm tra chất lượng CSV công việc (task_id, owner, hours) và tính tải công việc.")
    parser.add_argument("--input", required=True, help="Đường dẫn CSV, ví dụ data/workload.csv")
    parser.add_argument("--max-hours", required=False, default=None, help="Ngưỡng giờ tối đa (số hữu hạn không âm).")
    args = parser.parse_args(argv)

    if args.max_hours is None:
        print("ERROR: Thiếu tham số bắt buộc --max-hours.", file=sys.stderr)
        return 1

    max_h = parse_max_hours(args.max_hours)
    if max_h is None:
        print(f"ERROR: Tham số --max-hours '{args.max_hours}' không phải số hữu hạn không âm.", file=sys.stderr)
        return 1

    try:
        result = analyze(args.input, max_h)
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
