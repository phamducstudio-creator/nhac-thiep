#!/usr/bin/env python3
"""Đồng bộ nhạc thiệp cưới Phạm Đức Studio: thư mục Google Drive → kho này (n/<mã Drive>.mp3 + list.json).

Cách dùng (cho studio):
- Bỏ file nhạc vào THƯ MỤC GỐC trên Drive  = nhạc CHUNG: khách được chọn trên thiệp mẫu, form đặt thiệp và thiệp thật.
- Bỏ vào thư mục con tên bắt đầu bằng "Riêng" = bài RIÊNG của 1 cặp: không hiện cho khách khác, gắn vào thiệp bằng mã d:<mã>.
- Tên bài = tên file (bỏ đuôi). Đổi tên file trên Drive → đổi tên bài. Xoá file trên Drive → gỡ bài.
- Nhận mọi file âm thanh/video (mp3, m4a, wav, aac, flac, ogg, mp4, mov...) → đổi sang mp3 128 kbps, cắt lặng đầu bài,
  chuẩn âm lượng −18 LUFS (nghe đều tai với 3 bài có sẵn), tối đa 10 phút. File không phải nhạc → ghi vào mục lỗi, bỏ qua.

Chạy tự động bằng GitHub Actions (.github/workflows/dong-bo.yml) ~10 phút/lần. Thư mục Drive phải để
"Bất kỳ ai có đường liên kết → Người xem". Chốt an toàn: đọc Drive lỗi / ra 0 file / thiếu quá nửa kho → không xoá gì.
"""
import datetime
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
MAX_MB = 150            # file lớn hơn → bỏ (video dài)
MAX_GIAY = 600          # cắt tối đa 10 phút
KHONG_PHAI_NHAC = {'.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png', '.gif',
                   '.webp', '.heic', '.zip', '.rar', '.7z', '.psd', '.ai', '.svg', '.html', '.htm', '.json', '.csv'}


def log(*a):
    print(*a, flush=True)


def out(name, value):
    gh = os.environ.get('GITHUB_OUTPUT')
    if gh:
        with open(gh, 'a', encoding='utf-8') as f:
            f.write(f'{name}={value}\n')
    log(f'[output] {name}={value}')


def bo_dau(s):
    return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode().lower()


def ten_bai(path):
    name = pathlib.PurePosixPath(path).name
    stem = re.sub(r'\.[A-Za-z0-9]{1,5}$', '', name)
    stem = stem.replace('_', ' ')
    stem = re.sub(r'\s+', ' ', stem).strip(' -–—.')
    return (stem or 'Nhạc nền')[:80]


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
    cmd = ['ffmpeg', '-nostdin', '-y', '-hide_banner', '-loglevel', 'error', '-i', src,
           '-vn', '-sn', '-dn', '-map_metadata', '-1', '-t', str(MAX_GIAY), '-af', af,
           '-ac', '2', '-ar', '44100', '-c:a', 'libmp3lame', '-b:a', '128k', dst]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if r.returncode != 0 or not os.path.exists(dst):
        raise RuntimeError('không đọc được âm thanh trong file')


def thoi_luong(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', p],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def khoa_sap_xep(b):
    return (bool(b.get('rieng')), bo_dau(b.get('ten', '')))


def main():
    if not FOLDER_ID:
        log('Thiếu DRIVE_FOLDER_ID')
        out('changed', '0')
        return 1
    data = json.loads(LIST.read_text('utf-8')) if LIST.exists() else {}
    cu = {b['id']: b for b in data.get('bai', []) if b.get('id')}
    loi_cu = {x['id']: x for x in data.get('loi', []) if x.get('id')}

    try:
        drive = doc_drive()
    except Exception as e:  # noqa: BLE001
        log('KHÔNG đọc được thư mục Drive:', repr(e)[:300])
        out('changed', '0')
        return 1
    log(f'Drive: {len(drive)} file · kho: {len(cu)} bài')
    if not drive and cu:
        log('Drive trả về 0 file trong khi kho đang có bài → coi như đọc lỗi, không đổi gì')
        out('changed', '0')
        return 0

    moi, loi = [], []
    them = go = doi = 0
    thay = set()
    for f in drive:
        fid, path = f['id'], f['path']
        thay.add(fid)
        ten, rieng = ten_bai(path), la_rieng(path)
        if fid in cu and (NDIR / f'{fid}.mp3').exists():
            b = dict(cu[fid])
            if b.get('ten') != ten or bool(b.get('rieng')) != rieng:
                b['ten'], b['rieng'] = ten, rieng
                doi += 1
            moi.append(b)
            continue
        duoi = pathlib.PurePosixPath(path).suffix.lower()
        if duoi in KHONG_PHAI_NHAC:
            continue                                   # ảnh/tài liệu lỡ bỏ vào: bỏ qua, không báo lỗi
        if fid in loi_cu and loi_cu[fid].get('ten') == pathlib.PurePosixPath(path).name:
            loi.append(loi_cu[fid])                    # đã thử và lỗi → không tải lại mỗi 10 phút
            continue
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, 'vao' + (duoi if len(duoi) <= 6 else ''))
            dst = os.path.join(td, 'ra.mp3')
            try:
                tai_file(fid, src)
                mb = os.path.getsize(src) / 1048576
                if mb > MAX_MB:
                    raise RuntimeError(f'file nặng {mb:.0f} MB (tối đa {MAX_MB} MB)')
                can_ffmpeg()
                doi_mp3(src, dst)
                giay = thoi_luong(dst)
                if giay < 5:
                    raise RuntimeError('không có tiếng hoặc dưới 5 giây')
                NDIR.mkdir(exist_ok=True)
                shutil.move(dst, NDIR / f'{fid}.mp3')
            except Exception as e:  # noqa: BLE001
                log('LỖI', path, '→', e)
                loi.append({'id': fid, 'ten': pathlib.PurePosixPath(path).name, 'ly_do': str(e)[:160],
                            'luc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')})
                continue
        moi.append({'id': fid, 'ten': ten, 'file': f'n/{fid}.mp3', 'giay': round(giay), 'rieng': rieng,
                    'them': datetime.date.today().isoformat()})
        them += 1
        log('THÊM', path, f'{giay:.0f} giây', '(riêng)' if rieng else '(chung)')

    mat = [i for i in cu if i not in thay]
    if mat and len(mat) > max(2, len(cu) // 2):
        log(f'Drive thiếu {len(mat)}/{len(cu)} bài (quá nửa kho) → nghi đọc lỗi, KHÔNG gỡ lần này')
        moi += [cu[i] for i in mat]
    else:
        for i in mat:
            p = NDIR / f'{i}.mp3'
            if p.exists():
                p.unlink()
            go += 1
            log('GỠ', cu[i].get('ten'))

    moi.sort(key=khoa_sap_xep)
    loi.sort(key=lambda x: bo_dau(x.get('ten', '')))
    can_ghi = (not LIST.exists()) or (moi != sorted(cu.values(), key=khoa_sap_xep)) or \
              ([x['id'] for x in loi] != sorted(loi_cu, key=lambda i: bo_dau(loi_cu[i].get('ten', ''))))
    if can_ghi:
        LIST.write_text(json.dumps({
            'cap_nhat': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'bai': moi, 'loi': loi}, ensure_ascii=False, indent=1) + '\n', 'utf-8')
    out('changed', '1' if can_ghi else '0')
    out('summary', f'them {them}, go {go}, doi ten {doi}, loi {len(loi)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
