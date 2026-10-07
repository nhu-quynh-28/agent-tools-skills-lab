# Báo cáo Phân tích Bài luyện tập 02: Kiểm tra quá tải theo người

## 1. Mục tiêu và Thay đổi đã thực hiện

### 1.1. Mục tiêu
Mở rộng năng lực của AI Agent từ **Stage 03 $\to$ Stage 04**:
1. **Thực thi script tất định qua Bash:** Thay vì để LLM tự tính toán giờ bằng mắt (dễ nhầm lẫn, hallucination), giao việc tính toán số liệu cho script Python chuyên trách (`check_csv.py`).
2. **Tham số hóa dòng lệnh (CLI Parameter):** Bổ sung tham số bắt buộc `--max-hours` để Agent truyền ngưỡng động từ yêu cầu của người dùng.
3. **Đồng bộ hóa Kỹ năng (Skill Synchronization):** Cập nhật `SKILL.md` và `references/report-template.md` để Agent biết cách hỏi lại ngưỡng khi thiếu, chạy đúng cú pháp và trình bày báo cáo chuẩn cấu trúc mới.

### 1.2. Danh sách các file đã chỉnh sửa & tạo mới
- **Dữ liệu kiểm thử:**
  - `workspace/data/workload.csv` & `fixtures/data/workload.csv` (ở cả Stage 03 và Stage 04)
  - `workspace/data/workload-edge.csv` & `fixtures/data/workload-edge.csv` (ở Stage 04)
- **Mã nguồn kịch bản & kỹ năng (Stage 04):**
  - `workspace/skills/csv-quality/scripts/check_csv.py` (và đồng bộ sang `fixtures/`)
  - `workspace/skills/csv-quality/SKILL.md` (và đồng bộ sang `fixtures/`)
  - `workspace/skills/csv-quality/references/report-template.md` (và đồng bộ sang `fixtures/`)
- **Bộ kiểm thử tự động:**
  - `stage-04-script-skill/tests/test_check_csv.py`: Thêm các ca kiểm thử cho tham số `--max-hours`, kịch bản ngưỡng 8, ngưỡng 9, và edge case trùng ID bị lỗi giờ.
- **Báo cáo đầu ra:**
  - `stage-04-script-skill/workspace/output/workload.md`

---

## 2. Quy tắc Tính toán & Hợp đồng Dữ liệu (JSON Contract)

### 2.1. Cú pháp CLI
```bash
python skills/csv-quality/scripts/check_csv.py --input <đường dẫn CSV> --max-hours <ngưỡng>
```
- **Mã thoát (Exit codes):**
  - `0`: Phân tích thành công (kể cả khi dữ liệu có lỗi hoặc có người quá tải).
  - `1`: Lỗi thực thi (thiếu/sai `--max-hours`, file không tồn tại, thiếu cột bắt buộc, lỗi parse CSV). Lỗi được ghi ra `stderr`.

### 2.2. Quy tắc xử lý dữ liệu của `check_csv.py`
1. **Chuẩn hóa chuỗi:** Cắt khoảng trắng đầu/cuối (`strip()`) cho `task_id`, `owner`, `hours`. Phân biệt chữ hoa/thường ở `owner` (không tự gộp "Lan" với "lan").
2. **Quy tắc công việc trùng lặp (Duplicate Task ID):**
   - Chỉ giữ lần xuất hiện đầu tiên của mỗi `task_id`.
   - Các lần xuất hiện sau của cùng `task_id` đó **bắt buộc bị loại** (`duplicate_id`), kể cả khi lần xuất hiện đầu tiên bị lỗi dữ liệu! Tuyệt đối không thay thế bằng "lần hợp lệ đầu tiên".
3. **Điều kiện cộng giờ:** Chỉ cộng giờ khi dòng thỏa mãn đồng thời:
   - Đủ số trường quy định.
   - `task_id` không rỗng và chưa từng xuất hiện trước đó.
   - `owner` không rỗng.
   - `hours` là số thực hữu hạn $\ge 0$ (giá trị 0 vẫn hợp lệ).
4. **Mã lý do loại trừ (`excluded_rows`):** Sắp xếp theo thứ tự ưu tiên cố định:
   `wrong_field_count` $\to$ `missing_task_id` $\to$ `duplicate_id` $\to$ `missing_owner` $\to$ `invalid_hours`.
5. **Điều kiện quá tải (`overloaded_owners`):** Chỉ quá tải khi `total_hours > max_hours` (bằng ngưỡng thì bình thường, không quá tải).

---

## 3. Kết quả Thực nghiệm các Kịch bản

### 3.1. Kịch bản `workload.csv` với ngưỡng 8 giờ
- **Lệnh thực thi:**
  ```bash
  python skills/csv-quality/scripts/check_csv.py --input data/workload.csv --max-hours 8
  ```
- **Kết quả JSON:**
  ```json
  {
    "max_hours": 8,
    "hours_by_owner": { "Lan": 9, "Minh": 3 },
    "overloaded_owners": [ { "owner": "Lan", "total_hours": 9 } ],
    "excluded_rows": [
      { "line": 5, "task_id": "T04", "reasons": ["invalid_hours"] },
      { "line": 6, "task_id": "T02", "reasons": ["duplicate_id"] },
      { "line": 7, "task_id": "T05", "reasons": ["missing_owner"] }
    ]
  }
  ```
- **Đánh giá:**
  - Lan có 9 giờ (4 + 5) $\to$ **Quá tải** (vượt ngưỡng 8).
  - Minh có 3 giờ $\to$ Bình thường.
  - Dòng 5 (T04) bị loại vì `hours='abc'`, dòng 6 (T02) bị loại vì trùng ID với dòng 3, dòng 7 (T05) bị loại vì thiếu `owner`.

### 3.2. Kịch bản `workload.csv` với ngưỡng 9 giờ
- **Lệnh thực thi:**
  ```bash
  python skills/csv-quality/scripts/check_csv.py --input data/workload.csv --max-hours 9
  ```
- **Kết quả JSON:**
  - `hours_by_owner`: `{"Lan": 9, "Minh": 3}` (không đổi).
  - `overloaded_owners`: `[]` (rỗng vì 9 không lớn hơn 9).
  - `excluded_rows`: Giữ nguyên 3 dòng bị loại.

### 3.3. Kịch bản Không cung cấp ngưỡng
- **Thử nghiệm:** Hỏi Agent: *"Tính tổng giờ theo người trong data/workload.csv và xác định người quá tải."*
- **Hành vi Agent:** Theo quy định tại `SKILL.md`, tham số `--max-hours` là bắt buộc. Agent dừng lại và hỏi người dùng: *"Vui lòng cung cấp ngưỡng số giờ tối đa (max hours) để xác định người quá tải."* Agent không tự ý đoán ngưỡng 8 hay lấy từ phiên chat trước.

### 3.4. Kịch bản File không tồn tại
- **Thử nghiệm:** Gọi với file `data/khong-co.csv`.
- **Hành vi:** Script ghi `ERROR: Không đọc được file data/khong-co.csv...` ra `stderr` và trả `exit_code: 1`. Agent bắt được lỗi thực thi và thông báo cho người dùng, không bịa đặt số liệu báo cáo.

### 3.5. Kịch bản Đặc biệt (Edge Case): `workload-edge.csv`
- **Dữ liệu:**
  ```csv
  task_id,owner,hours
  E01,Lan,abc
  E01,Lan,5
  E02,Minh,0
  ```
- **Lệnh thực thi:**
  ```bash
  python skills/csv-quality/scripts/check_csv.py --input data/workload-edge.csv --max-hours 0
  ```
- **Kết quả JSON:**
  ```json
  {
    "max_hours": 0,
    "hours_by_owner": { "Minh": 0 },
    "overloaded_owners": [],
    "excluded_rows": [
      { "line": 2, "task_id": "E01", "reasons": ["invalid_hours"] },
      { "line": 3, "task_id": "E01", "reasons": ["duplicate_id"] }
    ]
  }
  ```
- **Đánh giá:**
  - Dòng 2 (`E01,Lan,abc`): Lần đầu gặp `E01`, lưu vào tập ID đã thấy; bị loại vì `invalid_hours`.
  - Dòng 3 (`E01,Lan,5`): `E01` đã tồn tại trước đó $\to$ bị loại vì `duplicate_id`.
  - **Lan không được cộng 5 giờ.** Minh được cộng 0 giờ (hợp lệ). Không ai quá tải với ngưỡng 0.

---

## 4. Trả lời Câu hỏi Lý thuyết Cuối bài

> **Câu hỏi 1: Phần nào do script tính, phần nào do model diễn giải?**

- **Phần do Script tính toán (Deterministic Execution):**
  1. Phân tích cú pháp tệp CSV, đếm tổng số dòng dữ liệu.
  2. Xác định các lỗi dữ liệu (thiếu cột, thiếu ID, thiếu owner, sai định dạng hours).
  3. Quản lý trạng thái các `task_id` đã gặp, loại trừ chính xác các công việc bị trùng lặp.
  4. Tính tổng số giờ hợp lệ theo từng `owner` (`hours_by_owner`).
  5. So sánh toán học `total_hours > max_hours` để kết luận danh sách người quá tải (`overloaded_owners`).
- **Phần do Model diễn giải (Semantic Interpretation & Reporting):**
  1. Đọc hiểu yêu cầu tự nhiên của người dùng để trích xuất tham số đường dẫn tệp và ngưỡng giờ `--max-hours`.
  2. Quyết định khi nào cần hỏi lại người dùng nếu thiếu thông tin bắt buộc.
  3. Đọc dữ liệu đầu ra JSON của script, ánh xạ vào template báo cáo Markdown (`report-template.md`).
  4. Diễn đạt thành lời văn tự nhiên: tóm tắt tình hình tải công việc, phân tích nguyên nhân và đưa ra các khuyến nghị cải thiện dữ liệu cho con người.

> **Câu hỏi 2: Nếu sửa script nhưng không cập nhật skill và reference, báo cáo có thể sai hoặc thiếu thông tin gì?**

Nếu chỉ sửa script mà không cập nhật `SKILL.md` và `references/report-template.md`:
1. **Lỗi thực thi do thiếu tham số:** Agent sẽ tiếp tục gọi lệnh cũ `python check_csv.py --input <file>` mà không truyền `--max-hours` $\to$ script lập tức báo lỗi `exit 1` ra `stderr`, Agent không thể tạo được báo cáo.
2. **Không biết cách xử lý khi thiếu ngưỡng:** Agent sẽ không có chỉ dẫn để hỏi lại người dùng khi thiếu ngưỡng, dẫn đến việc hoặc là đoán mò một con số, hoặc bị treo luồng xử lý.
3. **Báo cáo thiếu toàn bộ thông tin mới:** Vì file mẫu `report-template.md` cũ không có các trường `max_hours`, `hours_by_owner`, `overloaded_owners` và `excluded_rows`, Agent sẽ chỉ xuất báo cáo chất lượng dữ liệu chung chung như trước đây mà **hoàn toàn không có bảng tổng giờ và danh sách người quá tải**.
4. **Nguy cơ tính toán sai bằng mắt:** Nếu không được hướng dẫn đọc các trường mới trong JSON, Agent có thể cố gắng tự đọc file CSV bằng `read_file` và tự nhẩm tính tổng giờ $\to$ dẫn đến cộng trùng dòng `T02` (khiến Lan bị đội lên 14 giờ thay vì 9 giờ).
