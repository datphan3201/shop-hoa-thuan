# Vận hành nghiệp vụ Shop Hoà Thuận

## Quy tắc dữ liệu

- Mỗi sản phẩm có thể có nhiều size. Tồn kho nằm ở từng size, không nằm ở sản phẩm chung.
- Nhập, trừ và đặt lại tồn kho luôn tạo lịch sử biến động với lý do bắt buộc.
- Hoàn tất giao dịch chỉ thành công khi toàn bộ dòng hàng và tồn kho cùng được ghi trong một
  giao dịch database. Nếu một size không đủ, không có dòng bán hoặc biến động tồn kho nào được
  lưu.
- Hủy giao dịch chỉ thực hiện một lần, bắt buộc ghi lý do và hoàn tồn bằng biến động
  `sale_return`.
- Lịch sử bán lưu tên, loại hàng, size, SKU, giá niêm yết, giá thực tế và giá vốn tại thời
  điểm bán. Sửa sản phẩm sau này không đổi lịch sử.

## Giá vốn

Giá vốn bị khóa mặc định. Mở khóa yêu cầu PIN và phiên chỉ tồn tại trong phiên trình duyệt;
đăng xuất, khóa thủ công hoặc hết thời hạn sẽ khóa lại. Khi khóa, màn hình, báo cáo, CSV,
hóa đơn và kết quả tìm kiếm không nhận giá vốn hay lợi nhuận suy ra từ giá vốn.

## Báo cáo

Báo cáo chỉ tính giao dịch hoàn thành và xác định ngày theo múi giờ `Asia/Ho_Chi_Minh`.
Giảm giá toàn giao dịch được phân bổ bằng số nguyên cho các dòng bán; tổng doanh thu dòng luôn
bằng tổng tiền thực tế của giao dịch. CSV thường không chứa giá vốn. CSV có giá vốn chỉ tải được
sau khi mở khóa và xác nhận.

## Kiểm tra trước khi dùng dữ liệu thật

Ứng dụng hiện là bản phát triển. Không dùng dữ liệu thật cho đến khi các hạng mục Windows,
mobile, backup/restore và update trong Phase 7–13 được chứng nhận. Trước mỗi thay đổi phát hành,
chạy toàn bộ lệnh trong `AGENTS.md`.
