import datetime as _dt
import html
import re
import zipfile
from pathlib import Path


class UnsupportedFormat(Exception): ...


def _docx(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = xml.replace("</w:p>", "\n")
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    xml = re.sub(r"<w:br[^>]*/>", "\n", xml)
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def _vtt(path: Path) -> str:
    out = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip() in ("WEBVTT", "") or "-->" in line or line.strip().isdigit():
            continue
        out.append(line)
    return "\n".join(out)


def extract_text(path: Path) -> str:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".docx":
        return _docx(path)
    if ext == ".vtt":
        return _vtt(path)
    if ext == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    raise UnsupportedFormat(f"unsupported transcript format: {ext}")


def parse_header(text: str) -> dict:
    head = "\n".join(text.splitlines()[:3])
    m_utc = re.search(r"-(\d{8})_\d{6}UTC", head)
    m_hd = re.search(r"([A-Z][a-z]+ \d{1,2}, \d{4}),\s*\d{1,2}:\d{2}\s*[AP]M", head)
    date = None
    if m_utc:
        d = m_utc.group(1)
        date = f"{d[0:4]}-{d[4:6]}-{d[6:8]}"
    elif m_hd:
        date = _dt.datetime.strptime(m_hd.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
    title = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    return {"meeting_date": date, "title": title}


def detect_type(text: str, title: str) -> str:
    t = title.lower()
    if "stand up" in t or "standup" in t or "daily scrum" in t:
        return "standup"
    return "generic"
