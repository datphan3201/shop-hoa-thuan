# Mobile và PWA

Shop Hoà Thuận giữ giao diện desktop có sidebar, đồng thời dùng menu off-canvas và thanh điều
hướng dưới màn hình nhỏ. Các luồng chính (sản phẩm, tồn kho, bán hàng và lịch sử bán) có card
mobile riêng; bảng desktop chỉ hiện từ breakpoint `lg`.

## Bán hàng và mạng chập chờn

Mỗi lần gửi bán hàng, điều chỉnh tồn kho hoặc hủy giao dịch, trình duyệt gửi một idempotency key.
Máy chủ lưu key theo tài khoản, loại thao tác và fingerprint của dữ liệu trong cùng transaction
với nghiệp vụ. Gửi lại cùng key/cùng dữ liệu trả về giao dịch đã commit; cùng key nhưng dữ liệu
khác bị từ chối. Endpoint đã đăng nhập
`/operations/idempotency/<operation>/<key>/` chỉ trả trạng thái hoàn thành và URL kết quả cho
chính chủ sở hữu key.

Không có offline write hoặc hàng đợi đồng bộ. Nếu mạng mất sau khi bấm hoàn tất, không tạo đơn
mới bằng tay: mở lại trang từ lịch sử hoặc gửi lại đúng request/key nếu trình duyệt còn trang đó.
Chỉ thông báo thành công sau redirect từ transaction đã commit.

## Sửa cùng lúc

Category, sản phẩm, size và thiết lập timeout giá vốn có `revision` tăng dần. Form gửi revision
đã tải; server claim revision kế tiếp bằng update có điều kiện trong transaction. Nếu một thiết
bị khác đã lưu trước, thao tác sau nhận thông báo tiếng Việt và không ghi đè dữ liệu mới hơn.
Tồn kho và bán hàng vẫn dùng transaction phía server, không dùng optimistic concurrency.

## Ảnh từ điện thoại

Input ảnh chấp nhận JPEG, PNG và WebP, gợi ý camera sau (`capture=environment`) và hiển thị
preview cục bộ. Máy chủ không tin extension hay MIME client: Pillow decode/verify nội dung thực,
giới hạn file 10 MB và 30 megapixel, xử lý EXIF orientation, nén ảnh và tạo thumbnail. Media chỉ
được phục vụ sau đăng nhập và server kiểm tra lại nội dung ảnh trước khi trả response.

## Cache PWA

Manifest dùng tên `Shop Hoà Thuận`, display standalone và shortcut Bán hàng/Sản phẩm/Tồn kho.
Service worker chỉ cache GET cùng origin trong `/static/`; không cache HTML đã đăng nhập, HTMX,
media, POST, giao dịch, tồn kho, giá vốn hoặc lợi nhuận. Cache cũ được xóa khi activate worker
mới.

## Giới hạn kiểm thử thiết bị

Test tự động hiện xác minh route/layout mobile, manifest, policy worker, idempotency,
optimistic-concurrency và upload/media. Camera phần cứng, Add to Home Screen, gesture touch,
viewport trình duyệt thật và mạng điện thoại phải được xác minh trong checklist thiết bị của
Phase 13; chúng không được coi là đã PASS chỉ từ test server-side.
