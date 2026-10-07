---
name: csv-quality
description: Kiểm tra chất lượng file CSV công việc và tính tổng giờ theo người, xác định người quá tải theo ngưỡng giờ bằng script có sẵn, rồi ghi báo cáo Markdown dưới output/. Dùng khi người dùng yêu cầu kiểm tra chất lượng CSV, rà soát dữ liệu công việc, tính tổng giờ theo người hoặc xác định người quá tải.
---

# CSV quality & Workload analysis

Kiểm tra chất lượng CSV công việc và phân tích tải công việc bằng script, không tự đếm bằng mắt.

## Xác định tham số & Chạy script

1. **Kiểm tra ngưỡng giờ (`--max-hours`):**
   - Tham số `--max-hours` là bắt buộc.
   - Nếu người dùng chưa cung cấp ngưỡng giờ tối đa, **phải hỏi lại người dùng để lấy ngưỡng trước khi chạy script**. Tuyệt đối không tự bịa ngưỡng và không dùng ngưỡng từ cuộc trò chuyện cũ.
2. **Chạy script:**
   Dùng tool `bash` (cwd là workspace). Lệnh đầy đủ:
   ```
   python skills/csv-quality/scripts/check_csv.py --input <đường dẫn CSV> --max-hours <ngưỡng>
   ```
   Ví dụ: `python skills/csv-quality/scripts/check_csv.py --input data/workload.csv --max-hours 8`

   Không cần đọc source script để chạy.

## Kiểm tra kết quả

- `exit_code` 0: phân tích thành công. `stdout` là JSON gồm:
  - `max_hours`: ngưỡng giờ đã dùng.
  - `hours_by_owner`: tổng giờ hợp lệ theo từng người.
  - `overloaded_owners`: danh sách người vượt ngưỡng giờ (chỉ tính khi `total_hours > max_hours`, bằng ngưỡng không tính quá tải).
  - `excluded_rows`: các dòng bị loại kèm line, task_id và danh sách lý do loại (`wrong_field_count`, `missing_task_id`, `duplicate_id`, `missing_owner`, `invalid_hours`).
  - Các trường chất lượng dữ liệu: `row_count`, `missing_owner_count`, `invalid_hours_count`, `duplicate_id_count`, `duplicate_ids`, `issues`.
- `exit_code` 1: **lỗi thực thi** (thiếu hoặc sai `--max-hours`, file không tồn tại, thiếu cột bắt buộc, lỗi parse CSV). Đọc `stderr`, báo lỗi cho người dùng. Không bịa thống kê, không ghi báo cáo như thể đã phân tích.
- `timed_out` true hoặc `ok` false: lệnh không chạy xong; báo lỗi, không suy đoán kết quả.
- Phân biệt rõ **lỗi dữ liệu** (dòng bị loại trong `excluded_rows`, script vẫn exit 0) với **lỗi thực thi** (exit khác 0).

## Viết báo cáo

1. Đọc template `references/report-template.md` trong thư mục skill này, tức `skills/csv-quality/references/report-template.md`.
2. Lấy mọi con số từ JSON của script, không tự tính toán lại bằng mắt.
3. Điền đầy đủ các mục:
   - Ngưỡng giờ áp dụng (`max_hours`).
   - Bảng tổng giờ theo người (`hours_by_owner`).
   - Danh sách người quá tải (`overloaded_owners`) kèm số giờ vượt ngưỡng. Nếu không có ai quá tải, ghi rõ "Không có người quá tải".
   - Bảng các dòng bị loại kèm số dòng, task_id và mã lý do (`excluded_rows`).
   - Chi tiết các lỗi dữ liệu (`issues`).
4. Không sửa file CSV đầu vào.
5. Ghi báo cáo bằng `write_file` vào đường dẫn người dùng yêu cầu (mặc định `output/workload.md` hoặc `output/csv-quality.md`), rồi trả lời tóm tắt ngắn và đường dẫn file đã ghi.
