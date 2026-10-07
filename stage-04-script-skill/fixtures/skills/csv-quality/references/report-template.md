# Báo cáo kiểm tra chất lượng & Tải công việc: `{đường dẫn CSV}`

Công cụ: `skills/csv-quality/scripts/check_csv.py` | Ngưỡng giờ: {max_hours} | exit code: {exit_code}

## 1. Tổng quan tải công việc
- **Ngưỡng quá tải:** {max_hours} giờ

### Bảng tổng giờ theo người
| Người phụ trách (Owner) | Tổng giờ hợp lệ | Trạng thái |
|---|---|---|
| {owner} | {total_hours} | {Quá tải / Bình thường} |

### Danh sách người quá tải
{Nếu có người quá tải: liệt kê từng người và số giờ; Nếu không có: ghi "Không có người quá tải."}

## 2. Các dòng bị loại khỏi tổng giờ
| Dòng (Line) | Task ID | Lý do loại trừ |
|---|---|---|
| {line} | {task_id} | {reasons} |

## 3. Tổng quan chất lượng dữ liệu
| Chỉ số | Giá trị |
|---|---|
| Số dòng dữ liệu (không tính header) | {row_count} |
| Dòng thiếu owner | {missing_owner_count} |
| Dòng hours không hợp lệ | {invalid_hours_count} |
| Số task_id bị lặp (distinct) | {duplicate_id_count} ({duplicate_ids}) |

## 4. Chi tiết lỗi dữ liệu
| Line | Cột | Loại lỗi | task_id | Mô tả |
|---|---|---|---|---|
| {line} | {column} | {type} | {task_id} | {message} |

## 5. Khuyến nghị
- {Đề xuất hướng xử lý cho các dòng bị loại và các dòng dữ liệu lỗi; không tự sửa file nguồn}
