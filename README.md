# Kho nhạc thiệp cưới — Phạm Đức Studio

Nhạc nền cho thiệp cưới online trên phamducstudio.vn. **Không sửa tay thư mục `n/` và `list.json`** — máy tự làm.

## Thêm / đổi / gỡ bài (không cần code)

1. Mở thư mục Google Drive **"Nhạc thiệp cưới – Phạm Đức Studio"** (link ở trang quản lý: https://www.phamducstudio.vn/quan-ly-nhac.html).
2. Tải file nhạc lên:
   - Bỏ thẳng vào thư mục = **nhạc chung**: khách được chọn trên thiệp mẫu, form đặt thiệp và thiệp thật.
   - Bỏ vào thư mục con **"Riêng …"** = bài riêng của 1 cặp: không hiện cho khách khác.
3. Khoảng 10–20 phút sau bài có trên web. Tên bài = tên file (đổi tên file = đổi tên bài). Xoá file = gỡ bài.

Nhận mp3, m4a, wav, aac, flac, ogg và cả video (mp4, mov…): máy tự lấy tiếng, đổi mp3 128 kbps, cắt lặng đầu bài,
chuẩn âm lượng, tối đa 10 phút. File không phải nhạc được ghi vào mục lỗi ở trang quản lý.

## Cách chạy

- `.github/workflows/dong-bo.yml`: GitHub Actions ~10 phút/lần (hoặc tab Actions → Run workflow) chạy `tools/dong_bo.py`,
  lưu `n/<mã Drive>.mp3` + `list.json`, rồi đăng GitHub Pages: https://phamducstudio-creator.github.io/nhac-thiep/
- Thư mục Drive phải để "Bất kỳ ai có đường liên kết → Người xem".
- Chốt an toàn: đọc Drive lỗi / ra 0 file / thiếu quá nửa kho → không xoá bài nào.
- Mã bài dùng trong thiệp: `d:<mã Drive>` (ví dụ gắn vào cột `nhac` của thiệp từng cặp).

Nhạc có bản quyền: studio tự chịu trách nhiệm khi đưa lên kho này. Kho tách riêng khỏi website chính.
