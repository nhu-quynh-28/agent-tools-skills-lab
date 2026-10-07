---
name: refund-policy
description: Tra cứu chính sách hoàn tiền theo ngày mua của khách hàng từ các tài liệu trong data/policies/ và đưa ra kết luận đủ hoặc không đủ điều kiện hoàn tiền. Dùng khi người dùng hỏi về hoàn tiền, trả hàng, chính sách hoàn tiền hoặc yêu cầu hoàn tiền cho đơn hàng.
---

# Refund policy

Hướng dẫn tra cứu và áp dụng chính sách hoàn tiền theo ngày mua của khách hàng.

## Quy trình thực hiện

1. **Tìm kiếm tài liệu chính sách:**
   - Dùng tool `list_files` liệt kê các file trong thư mục `data/policies/`. Không giả định trước tên file vì tên file có thể thay đổi.
   - Dùng tool `read_file` đọc nội dung các file chính sách tìm được để nắm rõ phạm vi áp dụng (ngày mua), thời hạn yêu cầu hoàn tiền, phí hoàn tiền và điều kiện kích hoạt.

2. **Kiểm tra thông tin đầu vào:**
   - Để kết luận chính xác, cần có đủ 3 thông tin:
     1. Ngày mua hàng (purchase date).
     2. Ngày yêu cầu hoàn tiền (request date).
     3. Trạng thái kích hoạt của sản phẩm (đã kích hoạt hay chưa kích hoạt).
   - **QUAN TRỌNG:** Nếu người dùng chưa cung cấp đủ một trong các thông tin trên (ví dụ: thiếu trạng thái kích hoạt, hoặc thiếu ngày yêu cầu), **phải hỏi lại người dùng để làm rõ trước khi đưa ra kết luận**. Tuyệt đối không tự ý giả định (không tự đoán "chưa kích hoạt").

3. **Chọn và áp dụng chính sách:**
   - Đối chiếu ngày mua của khách hàng với phạm vi hiệu lực của các chính sách đã đọc để chọn đúng văn bản áp dụng:
     - Ngày mua trước 2026-10-01: Áp dụng chính sách trước tháng 10 (thời hạn 7 ngày, phí hoàn tiền 10%).
     - Ngày mua từ 2026-10-01 (bao gồm ngày này): Áp dụng chính sách từ tháng 10 (thời hạn 14 ngày, không thu phí).
   - **Cách tính số ngày đã qua (chênh lệch ngày lịch):**
     - Đếm chính xác số ngày lịch giữa ngày yêu cầu hoàn tiền và ngày mua (Dùng ngày yêu cầu trong câu hỏi của người dùng, không dùng ngày hiện tại của máy tính).
     - **Lưu ý số ngày trong tháng:** Tháng 9 có 30 ngày. Ví dụ: từ ngày mua 28/09/2026 đến ngày yêu cầu 06/10/2026 là **8 ngày** (còn 2 ngày trong tháng 9 là ngày 29 và 30; cộng với 6 ngày của tháng 10: 2 + 6 = 8 ngày).
     - So sánh số ngày đã qua với giới hạn ngày của chính sách:
       - Nếu số ngày > giới hạn ngày quy định: **KHÔNG ĐỦ ĐIỀU KIỆN HOÀN TIỀN** (quá hạn). Ví dụ: 8 ngày > 7 ngày thì KHÔNG được hoàn tiền.
       - Nếu số ngày <= giới hạn ngày quy định: Đủ điều kiện về mặt thời gian.
   - Kiểm tra điều kiện kích hoạt: Sản phẩm đã kích hoạt thì không được hoàn tiền theo bất kỳ chính sách nào.

4. **Định dạng câu trả lời:**
   - Dùng tool `read_file` đọc template `references/answer-template.md` trong thư mục skill này, tức `skills/refund-policy/references/answer-template.md`.
   - Trình bày câu trả lời đầy đủ các mục theo template:
     - Chính sách áp dụng và đường dẫn file căn cứ.
     - Số ngày đã qua (nêu rõ số ngày tính được).
     - Kết luận rõ ràng: Đủ điều kiện hay Không đủ điều kiện hoàn tiền.
     - Lý do cụ thể.
     - Phí hoàn tiền nếu đủ điều kiện (hoặc thông báo không mất phí).
     - Căn cứ tài liệu.
