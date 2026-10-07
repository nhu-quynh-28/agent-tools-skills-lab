# Báo cáo Phân tích Bài luyện tập 01: Tra cứu chính sách đúng phiên bản

## 1. Mục tiêu và Thay đổi đã thực hiện

### 1.1. Mục tiêu
Nâng cấp AI Agent từ **Stage 00 $\to$ Stage 02** để đạt được hai năng lực:
1. **Tìm tài liệu động (Dynamic Document Discovery):** Cài đặt tool `list_files` giúp Agent liệt kê nội dung thư mục trong workspace, tìm kiếm tài liệu ngay cả khi tên file bị thay đổi.
2. **Kỹ năng tra cứu & áp dụng chính sách (Skill-based Policy Selection):** Xây dựng skill `refund-policy` theo nguyên tắc **Progressive Disclosure**, tự động chọn chính sách dựa trên ngày mua, xử lý ngày tháng độc lập với giờ hệ thống và hỏi lại khi thiếu dữ liệu đầu vào.

### 1.2. Danh sách các thành phần đã sửa đổi & bổ sung
- **Dữ liệu chính sách:**
  - `workspace/data/policies/policy-before-oct.md` & `fixtures/data/policies/policy-before-oct.md`
  - `workspace/data/policies/policy-from-oct.md` & `fixtures/data/policies/policy-from-oct.md`
- **Mã nguồn Stage 01 (`stage-01-files`):**
  - `tools/files.py`: Cài đặt hàm `_list()` và `@tool def list_files(path: str = ".")`.
  - `tools/__init__.py`: Export `list_files`.
  - `agent.py`: Đăng ký `list_files` vào `TOOLS`.
  - `prompts.py`: Bổ sung hướng dẫn `list_files` trong `CAPABILITY_PROMPT`.
  - `config.py`: Cập nhật `CAPABILITY_TEXT`.
  - `tests/test_files.py`, `tests/test_agent.py`, `tests/test_app.py`: Bổ sung kiểm thử cho `list_files`.
- **Mã nguồn Stage 02 (`stage-02-skills`):**
  - Cập nhật `tools/files.py`, `tools/__init__.py`, `agent.py`, `prompts.py`, `config.py` tương tự Stage 01.
  - Tạo skill `refund-policy`:
    - `workspace/skills/refund-policy/SKILL.md` (và đồng bộ sang `fixtures/skills/`)
    - `workspace/skills/refund-policy/references/answer-template.md` (và đồng bộ sang `fixtures/skills/`)
  - Cập nhật tests: `tests/test_files.py`, `tests/test_agent.py`, `tests/test_app.py`, `tests/test_skill_catalog.py`, `tests/test_project.py`.

---

## 2. Thiết kế Tool `list_files` và Cơ chế An toàn

### 2.1. Cấu trúc trả về của tool
`list_files(path: str = ".")` trả về chuỗi JSON có cấu trúc:
- **Thành công:**
  ```json
  {
    "ok": true,
    "path": "data/policies",
    "entries": [
      {
        "name": "policy-before-oct.md",
        "path": "data/policies/policy-before-oct.md",
        "type": "file"
      },
      {
        "name": "policy-from-oct.md",
        "path": "data/policies/policy-from-oct.md",
        "type": "file"
      }
    ]
  }
  ```
- **Lỗi dự kiến:** Trả về `{"ok": false, "error": {"code": "...", "message": "..."}}`.

### 2.2. Kiểm thử bảo mật trực tiếp
| Trường hợp kiểm tra | Đầu vào | Mã lỗi trả về | Kết quả đánh giá |
| :--- | :--- | :--- | :--- |
| **Thư mục hợp lệ** | `data/policies` | Không lỗi (`ok: true`) | Trả danh sách 2 file chính sách, sắp xếp A-Z |
| **Đường dẫn là file** | `data/weekly_notes.md` | `NOT_A_DIRECTORY` | Báo lỗi rõ ràng: "Đây là file, không phải thư mục" |
| **Đường dẫn không tồn tại** | `data/khong-ton-tai` | `DIRECTORY_NOT_FOUND` | Báo lỗi rõ ràng: "Không tìm thấy thư mục" |
| **Path Traversal (`..`)** | `../secret.txt` | `PATH_OUTSIDE_WORKSPACE` | Chặn đứng hành vi thoát ra ngoài workspace |
| **Đường dẫn tuyệt đối** | `/etc` hoặc `/Users/...` | `PATH_OUTSIDE_WORKSPACE` | Chặn tuyệt đối các đường dẫn không tương đối |
| **Symlink Escape** | `data/link_ra_ngoai` | `PATH_OUTSIDE_WORKSPACE` | Chặn symlink trỏ ra ngoài workspace |

---

## 3. Thiết kế Skill `refund-policy`

### 3.1. YAML Frontmatter
```yaml
---
name: refund-policy
description: Tra cứu chính sách hoàn tiền theo ngày mua của khách hàng từ các tài liệu trong data/policies/ và đưa ra kết luận đủ hoặc không đủ điều kiện hoàn tiền. Dùng khi người dùng hỏi về hoàn tiền, trả hàng, chính sách hoàn tiền hoặc yêu cầu hoàn tiền cho đơn hàng.
---
```

### 3.2. Quy tắc nghiệp vụ trong `SKILL.md`
1. **Tìm kiếm động:** Không hardcode tên file. Gọi `list_files("data/policies")` để lấy danh sách file thực tế, sau đó dùng `read_file` để đọc nội dung từng file chính sách.
2. **Kiểm tra thông tin bắt buộc:** Phải đủ 3 yếu tố: Ngày mua hàng, Ngày yêu cầu hoàn tiền, và Trạng thái kích hoạt. Nếu thiếu bất kỳ thông tin nào, **bắt buộc phải hỏi lại khách hàng, không được tự suy đoán**.
3. **Quy tắc phân loại & tính toán:**
   - Ngày mua trước 2026-10-01: Chính sách cũ (tối đa 7 ngày, phí 10%).
   - Ngày mua từ 2026-10-01: Chính sách mới (tối đa 14 ngày, phí 0%).
   - Số ngày đã qua = `ngày yêu cầu` - `ngày mua` (tính theo ngày lịch, dùng ngày trong câu hỏi, không lấy ngày hệ thống).
   - Sản phẩm đã kích hoạt $\to$ Không được hoàn tiền trong mọi trường hợp.
4. **Định dạng trả lời:** Tuân thủ mẫu quy định tại `references/answer-template.md`.

---

## 4. Kết quả Thực nghiệm các Kịch bản

### Trường hợp A: Mua trước ngày đổi chính sách
- **Câu hỏi:** *"Tôi mua ngày 28/09/2026, yêu cầu hoàn ngày 06/10/2026, chưa kích hoạt. Tôi có được hoàn không?"*
- **Hành vi Agent:**
  1. Gọi `list_files` quét `data/policies/`.
  2. Gọi `read_file` đọc các chính sách trong thư mục.
  3. Chọn chính sách trước tháng 10 (`policy-before-oct.md`).
  4. Tính toán: từ 28/09/2026 đến 06/10/2026 là **8 ngày**.
  5. Đối chiếu điều kiện: giới hạn 7 ngày $\to$ 8 ngày đã vượt quá hạn.
- **Kết luận:** **Không đủ điều kiện hoàn tiền** vì đã quá hạn 7 ngày quy định. Dẫn chứng tài liệu: `data/policies/policy-before-oct.md`.

### Trường hợp B: Mua từ ngày đổi chính sách
- **Câu hỏi:** *"Tôi mua ngày 02/10/2026, yêu cầu hoàn ngày 12/10/2026, chưa kích hoạt. Tôi có được hoàn không?"*
- **Hành vi Agent:**
  1. Quét và đọc chính sách từ thư mục `data/policies/`.
  2. Chọn chính sách từ tháng 10 (`policy-from-oct.md`).
  3. Tính toán: từ 02/10/2026 đến 12/10/2026 là **10 ngày**.
  4. Đối chiếu điều kiện: trong hạn 14 ngày, sản phẩm chưa kích hoạt.
- **Kết luận:** **Đủ điều kiện hoàn tiền**, phí hoàn tiền là **0% (miễn phí)**. Dẫn chứng tài liệu: `data/policies/policy-from-oct.md`.

### Kịch bản Đổi tên file (Robustness Test)
- **Thử nghiệm:** Đổi tên file `policy-before-oct.md` thành `policy_2026_q3.md` và `policy-from-oct.md` thành `policy_2026_q4.md`.
- **Kết quả:** Agent vẫn gọi `list_files("data/policies")`, nhận diện được 2 tên file mới, đọc nội dung và đưa ra kết luận chính xác như cũ. Không bị ảnh hưởng bởi việc đổi tên file.

### Kịch bản Thiếu thông tin
- **Câu hỏi:** *"Tôi mua ngày 02/10/2026, muốn hoàn ngày 12/10/2026."*
- **Hành vi Agent:** Nhận thấy người dùng chưa cung cấp trạng thái sản phẩm đã kích hoạt hay chưa. Agent phản hồi hỏi lại: *"Vui lòng cho biết sản phẩm của bạn đã được kích hoạt hay chưa để chúng tôi kiểm tra chính sách hoàn tiền chính xác."* (Không tự tiện giả định là chưa kích hoạt).

---

## 5. Trả lời Câu hỏi Lý thuyết Cuối bài

> **Câu hỏi 1: Vì sao cần tool để tìm file và skill để hướng dẫn chọn chính sách?**

1. **Vì sao cần tool tìm file (`list_files`):**
   - LLM không có giác quan vật lý để biết hệ thống file đang chứa những tệp tin nào. Nếu không có tool liệt kê thư mục, LLM buộc phải đoán mò tên file (hallucination). Tool `list_files` cung cấp khả năng khám phá động (Dynamic Discovery), giúp Agent thích ứng khi cấu trúc dữ liệu thay đổi, tên file được cập nhật hoặc phiên bản tài liệu mới được thêm vào.
2. **Vì sao cần skill (`refund-policy`):**
   - System prompt ban đầu không nên chứa toàn bộ các quy tắc nghiệp vụ rườm rà (gây tốn token, loãng context và tăng nguy cơ nhầm lẫn).
   - Kỹ năng (Skill) đóng vai trò là tài liệu hướng dẫn chuyên biệt (Standard Operating Procedure - SOP). Khi có yêu cầu liên quan đến hoàn tiền, Agent mới nạp `SKILL.md` (Progressive Disclosure) để tuân thủ nghiêm ngặt quy trình: cách tính ngày, quy định hỏi lại khi thiếu thông tin, và cấu trúc phản hồi chuẩn hóa.

> **Câu hỏi 2: Nếu agent chưa có tool tìm file, việc sửa prompt có giải quyết được yêu cầu đổi tên file không? Giải thích.**

- **Không thể giải quyết triệt để.**
- **Giải thích:**
  - Nếu chỉ sửa prompt mà không có tool `list_files`, lập trình viên buộc phải **hardcode** tên các file chính sách vào prompt (ví dụ: *"Đọc file A và file B"*). Khi người dùng hoặc quản trị viên đổi tên file thành file C, thông tin trong prompt lập tức trở nên lỗi thời (stale), và lệnh `read_file` của Agent sẽ báo lỗi `FILE_NOT_FOUND`.
  - Prompt là văn bản tĩnh (hoặc bán tĩnh), không thể tự phản ánh trạng thái thực tế của hệ điều hành. Chỉ có **Tool** mới cung cấp khả năng tương tác với môi trường bên ngoài thời gian thực để tìm ra đúng tệp tin hiện hành.
