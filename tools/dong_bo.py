#!/usr/bin/env python3
"""Kho nhạc thiệp cưới Phạm Đức Studio → n/<mã>.mp3 + list.json (GitHub Pages). Hai đường đưa nhạc vào:

1) TẢI LÊN THẲNG GITHUB — không cần Google Drive (dùng được cả khi Google đầy bộ nhớ):
   - https://github.com/phamducstudio-creator/nhac-thiep/upload/main/tai-len        → nhạc CHUNG (khách được chọn ở thiệp mẫu,
     form đặt thiệp, bảng nhạc của mọi thiệp)
   - https://github.com/phamducstudio-creator/nhac-thiep/upload/main/tai-len/rieng  → nhạc RIÊNG (chỉ thiệp nào chọn bài đó mới phát;
     không hiện công khai — nên dùng cho bài hát có bản quyền)
   Chọn file → "Commit changes". Máy đổi mp3, thêm vào list.json rồi xoá file gốc khỏi tai-len/ (giữ README.md).
   Mã bài = "t" + 12 ký tự đầu SHA-1 file gốc → tải lại đúng file đó chỉ cập nhật tên/loại, không sinh bài trùng.
   Lệnh cho bài đã tải thẳng (trang quản lý nhạc tạo sẵn file, anh chỉ bấm Commit): tai-len/lenh/go-<mã>.txt = gỡ bài (hoặc bỏ
   mục lỗi) · tai-len/lenh/doi-ten-<mã>.txt (nội dung = tên mới) = đổi tên. Bài từ Drive thì đổi/xoá ngay trên Drive.
2) GOOGLE DRIVE — thư mục "Nhạc thiệp cưới – Phạm Đức Studio" (DRIVE_FOLDER_ID): bỏ thẳng vào thư mục = chung, thư mục con tên
   bắt đầu "Riêng" = riêng; đổi tên / xoá file trên Drive = đổi tên / gỡ bài. Chỉ đối chiếu với bài nguồn Drive — bài tải thẳng
   không bao giờ bị gỡ theo Drive. Chốt an toàn: đọc Drive lỗi / ra 0 file / thiếu quá nửa bài Drive → không gỡ gì.

Nhận mọi file âm thanh/video (mp3, m4a, wav, aac, flac, ogg, mp4, mov…) → mp3 128 kbps, cắt lặng đầu bài, chuẩn âm lượng −18 LUFS
(nghe đều tai với 3 bài có sẵn), tối đa 10 phút. File không phải nhạc → ghi mục lỗi (bài tải thẳng: tự hết sau 7 ngày).
Chạy bằng GitHub Actions (.github/workflows/dong-bo.yml): mỗi lần có file tải lên + ~10 phút/lần cho Drive.
Chạy thử ở máy: NHAC_ROOT=<thư mục kho> DRIVE_FOLDER_ID= python tools/dong_bo.py   (bỏ trống DRIVE_FOLDER_ID = bỏ qua Drive)
"""
import datetime
import hashlib
import html
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID', '').strip()
ROOT = pathlib.Path(os.environ.get('NHAC_ROOT') or pathlib.Path(__file__).resolve().parent.parent)
LIST = ROOT / 'list.json'
NDIR = ROOT / 'n'
TAI = ROOT / 'tai-len'
GIU_LAI = {'readme.md', '.gitkeep'}   # file luôn giữ trong tai-len/
MAX_MB = 150            # file lớn hơn → bỏ (video dài)
MAX_GIAY = 600          # cắt tối đa 10 phút
NGAY_GIU_LOI_TAI = 7    # mục lỗi của file tải thẳng tự hết sau 7 ngày (file gốc đã xoá, không có gì để sửa)
KHONG_PHAI_NHAC = {'.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png', '.gif',
                   '.webp', '.heic', '.zip', '.rar', '.7z', '.psd', '.ai', '.svg', '.html', '.htm', '.json', '.csv', '.md'}
VN = datetime.timezone(datetime.timedelta(hours=7))


def log(*a):
    print(*a, flush=True)


def out(name, value):
    gh = os.environ.get('GITHUB_OUTPUT')
    if gh:
        with open(gh, 'a', encoding='utf-8') as f:
            f.write(f'{name}={value}\n')
    log(f'[output] {name}={value}')


def bay_gio():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def hom_nay():
    return datetime.datetime.now(VN).date().isoformat()


def bo_dau(s):
    return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode().lower()


# tên file tải từ web thường dính rác: "y2mate.com - …", "(Official Music Video)", "_320kbps"…
RAC_DAU = re.compile(r'^\s*[\[(]?\s*[\w.-]*(?:y2mate|y2meta|ytmp3|yt1s|savefrom|snaptik|ssyoutube|x2download|notube|tubidy|'
                     r'mp3juices?|spotify-?downloader|spotifydown|loader\.to)[\w.-]*\s*[\])]?\s*[-_–—|:]*\s*', re.I)
RAC_NGOAC = re.compile(r'\s*[(\[{【][^)\]}】]*(?:official|\bmv\b|m/v|lyrics?|\baudio\b|video|visuali[sz]er|\bhd\b|\b4k\b|kbps|'
                       r'\bfull\b|vietsub)[^)\]}】]*[)\]}】]', re.I)
RAC_CUM = re.compile(r'(?:\s*[-–|:]\s*)?\b(?:official(?:\s+(?:music|lyrics?))?\s+(?:video|mv|audio)|lyrics?\s+video|\d{3}\s*kbps)\b', re.I)
RAC_DUOI = re.compile(r'(?:\s*[-–|:]\s*|\s+)(?:m/?v|audio|lyrics?)\s*$', re.I)


def lam_sach_ten(s):
    s = unicodedata.normalize('NFC', str(s or ''))
    s = ''.join(c for c in s if c in '\n\t' or ord(c) >= 32).replace('\n', ' ').replace('\t', ' ')
    s = re.sub(r'[<>{}`\\|"]', '', RAC_CUM.sub(' ', RAC_NGOAC.sub('', RAC_DAU.sub('', s))))
    for _ in range(2):
        s = RAC_DUOI.sub('', re.sub(r'\s+', ' ', s).strip(' -–—._'))
    s = re.sub(r'\s+', ' ', s).strip(' -–—._')
    return s[:80].strip() if re.search(r'[^\W\d_]', s) else ''     # chỉ còn số/ký hiệu → coi như không có tên


def ten_bai(path):
    name = pathlib.PurePosixPath(str(path).replace('\\', '/')).name
    stem = re.sub(r'\.[A-Za-z0-9]{1,5}$', '', name).replace('_', ' ')
    return lam_sach_ten(stem) or ('Bài mới ' + datetime.datetime.now(VN).strftime('%d/%m'))


def la_rieng(path):
    parts = pathlib.PurePosixPath(path).parts
    return len(parts) >= 2 and bo_dau(parts[0]).strip().startswith('rieng')


# ---------------- đọc danh sách file trong thư mục Drive (công khai) ----------------
def _doc_bang_gdown():
    import gdown
    files = gdown.download_folder(id=FOLDER_ID, skip_download=True, quiet=True)
    return [{'id': f.id, 'path': str(f.path).replace('\\', '/')} for f in files]


def _doc_thu_cong(folder_id, prefix='', depth=0, sess=None):
    """Dự phòng khi gdown lỗi (vd có Google Docs trong thư mục): tự đọc trang embeddedfolderview."""
    import requests
    sess = sess or requests.Session()
    r = sess.get('https://drive.google.com/embeddedfolderview', params={'id': folder_id}, timeout=30,
                 headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'})
    r.raise_for_status()
    res = []
    for href, inner in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r.text, flags=re.S):
        href = html.unescape(href)
        name = html.unescape(re.sub(r'<[^>]+>', ' ', inner))
        name = re.sub(r'\s+', ' ', name).strip().replace('/', '_')
        m = re.match(r'https://drive\.google\.com/file/d/([-\w]{25,})/', href)
        if m:
            res.append({'id': m.group(1), 'path': prefix + name})
            continue
        m = re.search(r'/folders/([-\w]{25,})', href)
        if m and depth < 3:
            res += _doc_thu_cong(m.group(1), prefix + name + '/', depth + 1, sess)
    return res


def doc_drive():
    try:
        return _doc_bang_gdown()
    except Exception as e:  # noqa: BLE001
        log('gdown không đọc được thư mục (' + repr(e)[:200] + ') → đọc dự phòng')
        return _doc_thu_cong(FOLDER_ID)


def tai_file(fid, dst):
    try:
        import gdown
        got = gdown.download(id=fid, output=dst, quiet=True)
        if got and os.path.exists(dst) and os.path.getsize(dst) > 0:
            return
    except Exception as e:  # noqa: BLE001
        log('gdown tải lỗi:', repr(e)[:200], '→ tải trực tiếp')
    import requests
    with requests.get('https://drive.usercontent.google.com/download',
                      params={'id': fid, 'export': 'download', 'confirm': 't'}, stream=True, timeout=120) as r:
        r.raise_for_status()
        if 'text/html' in r.headers.get('Content-Type', ''):
            raise RuntimeError('Drive trả về trang web thay vì file (file chưa để công khai?)')
        with open(dst, 'wb') as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)


# ---------------- đổi định dạng ----------------
def can_ffmpeg():
    if shutil.which('ffmpeg') and shutil.which('ffprobe'):
        return
    log('Cài ffmpeg...')
    subprocess.run('sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg >/dev/null',
                   shell=True, check=True)


def doi_mp3(src, dst):
    af = ('silenceremove=start_periods=1:start_duration=0.05:start_threshold=-50dB,'
          'loudnorm=I=-18:TP=-1.5:LRA=11')
    cmd = ['ffmpeg', '-nostdin', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(src),
           '-vn', '-sn', '-dn', '-map_metadata', '-1', '-t', str(MAX_GIAY), '-af', af,
           '-ac', '2', '-ar', '44100', '-c:a', 'libmp3lame', '-b:a', '128k', str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if r.returncode != 0 or not os.path.exists(dst):
        raise RuntimeError('không đọc được âm thanh trong file')


def thoi_luong(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', str(p)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def lam_mp3(src, fid):
    """File âm thanh/video → n/<fid>.mp3. Trả về số giây. Lỗi → RuntimeError (lý do tiếng Việt)."""
    mb = os.path.getsize(src) / 1048576
    if mb > MAX_MB:
        raise RuntimeError(f'file nặng {mb:.0f} MB (tối đa {MAX_MB} MB)')
    can_ffmpeg()
    with tempfile.TemporaryDirectory() as td:
        dst = os.path.join(td, 'ra.mp3')
        doi_mp3(src, dst)
        giay = thoi_luong(dst)
        if giay < 5:
            raise RuntimeError('không có tiếng hoặc dưới 5 giây')
        NDIR.mkdir(exist_ok=True)
        shutil.move(dst, NDIR / f'{fid}.mp3')
    return giay


def khoa_sap_xep(b):
    return (bool(b.get('rieng')), bo_dau(b.get('ten', '')), b.get('id', ''))


# ---------------- 1) tải lên thẳng GitHub ----------------
def xu_ly_tai_len(bai, loi, tk):
    if not TAI.is_dir():
        return
    for p in sorted(TAI.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(TAI)
        if p.name.lower() in GIU_LAI or bo_dau(rel.parts[0]) == 'lenh':
            continue
        rieng = len(rel.parts) >= 2 and bo_dau(rel.parts[0]).strip().startswith('rieng')
        fid = 't' + hashlib.sha1(p.read_bytes()).hexdigest()[:12]
        ten = ten_bai(p.name)
        try:
            if p.suffix.lower() in KHONG_PHAI_NHAC:
                raise RuntimeError('không phải file nhạc')
            b = bai.get(fid)
            if b and (NDIR / f'{fid}.mp3').exists():      # tải lại đúng file cũ → chỉ cập nhật tên/loại
                if b.get('ten') != ten or bool(b.get('rieng')) != rieng:
                    b['ten'], b['rieng'] = ten, rieng
                    tk['doi'] += 1
                log('ĐÃ CÓ', rel, '→', fid)
            else:
                giay = lam_mp3(p, fid)
                bai[fid] = {'id': fid, 'ten': ten, 'file': f'n/{fid}.mp3', 'giay': round(giay), 'rieng': rieng,
                            'them': hom_nay(), 'nguon': 'tai'}
                tk['tai'] += 1
                log('TẢI LÊN', rel, f'{giay:.0f} giây', '(riêng)' if rieng else '(chung)', '→', fid)
            loi.pop(fid, None)
        except Exception as e:  # noqa: BLE001
            log('LỖI', rel, '→', e)
            loi[fid] = {'id': fid, 'ten': p.name, 'ly_do': str(e)[:160], 'luc': bay_gio(), 'nguon': 'tai'}
        p.unlink()
        tk['xoa'] += 1
    lenh = TAI / 'lenh'
    if lenh.is_dir():
        for p in sorted(lenh.iterdir()):
            if not p.is_file() or p.name.lower() in GIU_LAI:
                continue
            m = re.match(r'^(go|doi-ten)-(t[0-9a-f]{12})(?:\.txt)?$', p.name.strip(), re.I)
            if not m:
                log('LỆNH LẠ (bỏ):', p.name)
            else:
                viec, fid = m.group(1).lower(), m.group(2).lower()
                b = bai.get(fid)
                if viec == 'go':
                    if b and b.get('nguon') == 'tai':
                        del bai[fid]
                        (NDIR / f'{fid}.mp3').unlink(missing_ok=True)
                        tk['go'] += 1
                        log('GỠ', b.get('ten'))
                    elif fid in loi:
                        del loi[fid]
                        log('BỎ MỤC LỖI', fid)
                    else:
                        log('GỠ: không có bài tải thẳng', fid)
                elif b and b.get('nguon') == 'tai':
                    ten = lam_sach_ten(p.read_text('utf-8', 'replace'))
                    if ten and ten != b.get('ten'):
                        log('ĐỔI TÊN', b.get('ten'), '→', ten)
                        b['ten'] = ten
                        tk['doi'] += 1
                else:
                    log('ĐỔI TÊN: không có bài tải thẳng', fid)
            p.unlink()
            tk['xoa'] += 1


# ---------------- 2) Google Drive ----------------
def dong_bo_drive(bai, loi, tk):
    cu = {i: b for i, b in bai.items() if b.get('nguon') != 'tai'}
    loi_cu = {i: x for i, x in loi.items() if x.get('nguon') != 'tai'}
    try:
        drive = doc_drive()
    except Exception as e:  # noqa: BLE001
        log('KHÔNG đọc được thư mục Drive:', repr(e)[:300], '→ giữ nguyên bài Drive')
        return
    log(f'Drive: {len(drive)} file · kho: {len(cu)} bài từ Drive')
    if not drive and cu:
        log('Drive trả về 0 file trong khi kho đang có bài Drive → coi như đọc lỗi, không đổi bài Drive')
        return
    moi, loi_moi, thay = {}, {}, set()
    for f in drive:
        fid, path = f['id'], f['path']
        thay.add(fid)
        ten, rieng = ten_bai(path), la_rieng(path)
        if fid in cu and (NDIR / f'{fid}.mp3').exists():
            b = dict(cu[fid])
            if b.get('ten') != ten or bool(b.get('rieng')) != rieng:
                b['ten'], b['rieng'] = ten, rieng
                tk['doi'] += 1
            moi[fid] = b
            continue
        duoi = pathlib.PurePosixPath(path).suffix.lower()
        if duoi in KHONG_PHAI_NHAC:
            continue                                   # ảnh/tài liệu lỡ bỏ vào: bỏ qua, không báo lỗi
        if fid in loi_cu and loi_cu[fid].get('ten') == pathlib.PurePosixPath(path).name:
            loi_moi[fid] = loi_cu[fid]                 # đã thử và lỗi → không tải lại mỗi 10 phút
            continue
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, 'vao' + (duoi if len(duoi) <= 6 else ''))
            try:
                tai_file(fid, src)
                giay = lam_mp3(src, fid)
            except Exception as e:  # noqa: BLE001
                log('LỖI', path, '→', e)
                loi_moi[fid] = {'id': fid, 'ten': pathlib.PurePosixPath(path).name, 'ly_do': str(e)[:160], 'luc': bay_gio()}
                continue
        moi[fid] = {'id': fid, 'ten': ten, 'file': f'n/{fid}.mp3', 'giay': round(giay), 'rieng': rieng, 'them': hom_nay()}
        tk['drive'] += 1
        log('THÊM (Drive)', path, f'{giay:.0f} giây', '(riêng)' if rieng else '(chung)')
    mat = [i for i in cu if i not in thay]
    if mat and len(mat) > max(2, len(cu) // 2):
        log(f'Drive thiếu {len(mat)}/{len(cu)} bài (quá nửa) → nghi đọc lỗi, KHÔNG gỡ lần này')
        for i in mat:
            moi[i] = cu[i]
    else:
        for i in mat:
            (NDIR / f'{i}.mp3').unlink(missing_ok=True)
            tk['go'] += 1
            log('GỠ (Drive)', cu[i].get('ten'))
    for i in cu:
        bai.pop(i, None)
    bai.update(moi)
    for i in loi_cu:
        loi.pop(i, None)
    loi.update(loi_moi)


def main():
    data = json.loads(LIST.read_text('utf-8')) if LIST.exists() else {}
    bai = {b['id']: dict(b) for b in data.get('bai', []) if b.get('id')}
    loi = {x['id']: dict(x) for x in data.get('loi', []) if x.get('id')}
    truoc = json.dumps([sorted(bai.values(), key=khoa_sap_xep), sorted(loi)], ensure_ascii=False, sort_keys=True)
    tk = {'tai': 0, 'drive': 0, 'go': 0, 'doi': 0, 'xoa': 0}

    xu_ly_tai_len(bai, loi, tk)
    if FOLDER_ID:
        dong_bo_drive(bai, loi, tk)
    else:
        log('Không có DRIVE_FOLDER_ID → bỏ qua Drive')
    han = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=NGAY_GIU_LOI_TAI)).strftime('%Y-%m-%dT%H:%M:%SZ')
    for i in [i for i, x in loi.items() if x.get('nguon') == 'tai' and str(x.get('luc') or '') < han]:
        del loi[i]                                     # lỗi của file tải thẳng: hết hạn sau 7 ngày
    for p in (NDIR.glob('*.mp3') if NDIR.is_dir() else []):
        if p.stem not in bai:                          # mp3 mồ côi (vd sửa tay) → dọn
            p.unlink()
            log('DỌN mp3 thừa', p.name)
            tk['xoa'] += 1

    ds = sorted(bai.values(), key=khoa_sap_xep)
    ds_loi = sorted(loi.values(), key=lambda x: (bo_dau(x.get('ten', '')), x.get('id', '')))
    sau = json.dumps([ds, sorted(loi)], ensure_ascii=False, sort_keys=True)
    doi = (not LIST.exists()) or sau != truoc
    if doi:
        LIST.write_text(json.dumps({'cap_nhat': bay_gio(), 'bai': ds, 'loi': ds_loi}, ensure_ascii=False, indent=1) + '\n', 'utf-8')
    out('changed', '1' if (doi or tk['xoa']) else '0')
    out('summary', f"tai len {tk['tai']}, drive them {tk['drive']}, go {tk['go']}, doi ten {tk['doi']}, loi {len(ds_loi)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
