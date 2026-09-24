# Kho nhạc thiệp cưới — Phạm Đức Studio

Nhạc nền cho thiệp cưới online trên phamducstudio.vn. **Không sửa tay thư mục `n/` và `list.json`** — máy tự làm.
Trang quản lý (nghe thử, lấy mã, đổi tên, gỡ bài): https://www.phamducstudio.vn/quan-ly-nhac.html

## Thêm bài — cách 1: tải thẳng lên đây (nhanh nhất, không cần Google Drive)

1. Mở trang tải lên (đăng nhập tài khoản `phamducstudio-creator`):
   - **Nhạc riêng** (nên dùng cho bài hát có bản quyền / bài của từng cặp — chỉ thiệp nào chọn mới phát):
     https://github.com/phamducstudio-creator/nhac-thiep/upload/main/tai-len/rieng
   - **Nhạc chung** (khách được chọn ở thiệp mẫu, form đặt thiệp và bảng nhạc của mọi thiệp):
     https://github.com/phamducstudio-creator/nhac-thiep/upload/main/tai-len
2. Chọn file (tối đa 25 MB/file) → bấm nút xanh **Commit changes**.
3. Khoảng 1–3 phút sau bài có trong kho; chọn bài cho thiệp ở bảng sửa thiệp → Nhạc nền.
   Tên bài = tên file (máy tự bỏ chữ rác kiểu "y2mate.com", "(Official MV)"). Đổi tên / gỡ bài: nút ở trang quản lý.

## Thêm bài — cách 2: Google Drive

Thư mục **"Nhạc thiệp cưới – Phạm Đức Studio"**: bỏ thẳng vào thư mục = nhạc chung, thư mục con **"Riêng …"** = nhạc riêng.
Khoảng 10–20 phút sau bài có trên web. Đổi tên file trên Drive = đổi tên bài · xoá file = gỡ bài. (Drive đầy bộ nhớ thì không tải lên được — dùng cách 1.)

Nhận mp3, m4a, wav, aac, flac, ogg và cả video (mp4, mov…): máy tự lấy tiếng, đổi mp3 128 kbps, cắt lặng đầu bài,
chuẩn âm lượng, tối đa 10 phút. File không phải nhạc được ghi vào mục lỗi ở trang quản lý.

## Cách chạy

- `.github/workflows/dong-bo.yml`: chạy ngay khi có file tải lên `tai-len/` + ~10 phút/lần cho Drive (hoặc tab Actions → Run
  workflow) → `tools/dong_bo.py` lưu `n/<mã>.mp3` + `list.json` → đăng GitHub Pages: https://phamducstudio-creator.github.io/nhac-thiep/
- Mã bài dùng trong thiệp: `d:<mã>` — bài Drive: mã file Drive; bài tải thẳng: `t` + 12 ký tự (SHA-1 file gốc, `nguon: "tai"`).
- Lệnh cho bài tải thẳng: file `tai-len/lenh/go-<mã>.txt` (gỡ) · `tai-len/lenh/doi-ten-<mã>.txt` (nội dung = tên mới).
- Drive chỉ đối chiếu với bài nguồn Drive. Chốt an toàn: đọc Drive lỗi / ra 0 file / thiếu quá nửa bài Drive → không gỡ gì.
- File gốc tải lên được xoá sau khi đổi mp3 nhưng vẫn nằm trong lịch sử git; kho > 1 GB thì nhờ Claude gộp lịch sử.

Nhạc có bản quyền: studio tự chịu trách nhiệm khi đưa lên kho này. Kho tách riêng khỏi website chính — có khiếu nại
thì chỉ kho nhạc bị ảnh hưởng; thiệp tự chuyển sang bài có sẵn khi bài trong kho không phát được.
