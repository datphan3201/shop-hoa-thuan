# Data model và quy tắc toàn vẹn

## Quy ước

- SQLite là database duy nhất ở bản đầu.
- Timestamp lưu UTC; giao diện/báo cáo quy đổi `Asia/Ho_Chi_Minh`.
- Tiền là số nguyên VND (`PositiveBigIntegerField`).
- Category, product, variant đã tham chiếu không bị hard-delete; quan hệ lịch sử dùng `PROTECT`.
- `TimeStampedModel` có `created_at`, `updated_at`, `revision` cho optimistic concurrency.

## Quan hệ

```text
Category 1 ── * Product 1 ── * ProductVariant 1 ── * InventoryMovement
                                      │
                                      └──────────── 1 ── * SaleItem * ── 1 Sale

Anonymous browser session 1 ── * IdempotencyRecord
ShopSecuritySettings (singleton, pk=1)
```

## Catalog và tồn kho

| Model | Dữ liệu chính | Constraint/quy tắc |
|---|---|---|
| `Category` | name, description, active | Tên unique không phân biệt hoa/thường. |
| `Product` | category, name, brand, color, image, thumbnail, active | Không xóa khi còn variant/sale tham chiếu. |
| `ProductVariant` | product, size, SKU, cost/selling price, quantity, low-stock threshold, active | Unique product+size; SKU khác rỗng unique; giá/tồn không âm. |
| `InventoryMovement` | variant, type, before/change/after, reference, note | `after = before + change`; balance không âm; audit trail. |

`ProductVariant.quantity` là balance hiện tại và chỉ inventory service được phép cập nhật.
Movement type gồm `initial`, `import`, `sale`, `sale_return`, `adjustment`.

## Sale và lịch sử bất biến

| Model | Dữ liệu chính | Constraint/quy tắc |
|---|---|---|
| `Sale` | sale code, sold time, subtotal, discount, final total, payment, status, cancellation | Sale code unique; total đúng `subtotal - discount`; trạng thái hủy nhất quán. |
| `SaleItem` | variant, snapshot product/category/size/color/SKU, quantity, listed/actual/cost snapshot, line total | quantity dương; `line_total = quantity × actual_unit_price`. |

Khi sale commit, snapshot giữ tên/size/SKU/giá tại thời điểm bán để việc sửa catalog sau này
không thay đổi lịch sử. `unit_cost_snapshot` chỉ thuộc server/database; không render hoặc export
khi cost lock đóng. Hủy sale cập nhật trạng thái, lý do/thời điểm và tạo `sale_return` đúng một
lần; sale hủy không đóng góp doanh thu report.

## Bảo mật và retry

| Model | Mục đích | Constraint |
|---|---|---|
| `ShopSecuritySettings` | PIN hash và timeout cost lock | Singleton pk=1; timeout 1–120 phút; không lưu PIN gốc. |
| `IdempotencyRecord` | Replay record thao tác ghi | Unique `(client_key, operation, key)`; fingerprint chặn same key/different payload. |

`response_location` chỉ lưu đường dẫn kết quả đã commit, không lưu payload nhạy cảm. Retention
được xử lý bằng `purge_idempotency --days 30`.

## Lifecycle nghiệp vụ

```text
Tạo product + variants
      │
      ├── Nhập/điều chỉnh → InventoryMovement → quantity mới
      │
      └── Hoàn tất sale (atomic)
              ├── Sale + SaleItem snapshots
              ├── InventoryMovement(sale)
              └── giảm quantity

Hủy sale (atomic, một lần)
      ├── Sale cancelled + lý do
      └── InventoryMovement(sale_return) + hoàn quantity
```

Migration phải commit cùng model. Server production chỉ kiểm tra schema rồi listen; migration
runner riêng lấy maintenance lock, chạy migration, kiểm tra compatibility và luôn release lock.
