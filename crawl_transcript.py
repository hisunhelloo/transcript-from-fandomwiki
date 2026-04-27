"""
crawl_transcript.py
====================
Crawls a Fandom wiki /Transcript page via the MediaWiki Action API and exports to:
  - Markdown  (.md)
  - PDF       (.pdf)

Usage:
    python crawl_transcript.py [URL] [--out OUTPUT_DIR] [--format md|pdf|both]

Defaults:
    URL     = https://phineasandferb.fandom.com/wiki/Rollercoaster/Transcript
    --out   = ./output
    --format= both

Structure of the Fandom transcript HTML (from API):
    <p>
      <i>(stage direction)</i><br/>
      <b>Character:</b> dialogue text <i>(inline direction)</i><br/>
      <b>Character:</b> more dialogue<br/>
      ...
    </p>
Each <br/> separates individual transcript lines within one paragraph/scene block.
"""

import argparse
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, urlencode, unquote

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_URL = "https://phineasandferb.fandom.com/wiki/Rollercoaster/Transcript"
REQUEST_TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "TranscriptCrawler/1.0 (educational; "
        "+https://github.com/user/transcript-from-fandom)"
    ),
    "Accept": "application/json",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
class Line:
    DIALOGUE = "dialogue"
    DIRECTION = "direction"
    SONG = "song"

    def __init__(self, kind: str, character: str | None, text: str):
        self.kind = kind
        self.character = character
        self.text = text.strip()

    def __repr__(self):
        if self.kind == self.DIALOGUE:
            return f"[{self.character}] {self.text}"
        return f"({self.kind}) {self.text}"


# ---------------------------------------------------------------------------
# Fetch via MediaWiki Action API
# ---------------------------------------------------------------------------
def _wiki_api_url(fandom_url: str) -> tuple[str, str]:
    parsed = urlparse(fandom_url)
    api_base = f"{parsed.scheme}://{parsed.netloc}/api.php"
    # unquote() decodes percent-encoded chars: %27 → ', %28 → (, etc.
    title = unquote(re.sub(r"^/wiki/", "", parsed.path))
    return api_base, title


def fetch_page(url: str) -> BeautifulSoup:
    api_url, page_title = _wiki_api_url(url)
    params = {
        "action": "parse",
        "page": page_title,
        "prop": "text",
        "format": "json",
        "disablelimitreport": 1,
    }
    full_url = f"{api_url}?{urlencode(params)}"
    print(f"[fetch] API -> {full_url}")

    resp = requests.get(full_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise RuntimeError(f"MediaWiki API error: {data['error']}")

    html = data["parse"]["text"]["*"]
    return BeautifulSoup(html, "lxml")


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------
def get_page_title_from_url(url: str) -> str:
    _, title = _wiki_api_url(url)
    return title.replace("_", " ").replace("/", " - ")


def _split_p_by_br(p_tag: Tag) -> list[list]:
    """
    Split the children of a <p> tag on <br> boundaries.
    Returns a list of 'rows', each row being a list of child nodes
    that belong to that line segment.
    """
    rows = []
    current: list = []
    for child in p_tag.children:
        if isinstance(child, Tag) and child.name == "br":
            rows.append(current)
            current = []
        else:
            current.append(child)
    if current:
        rows.append(current)
    return rows


def _nodes_to_text(nodes: list) -> str:
    """Flatten a list of BS4 nodes to plain text, stripping links etc."""
    parts = []
    for node in nodes:
        if isinstance(node, NavigableString):
            parts.append(str(node))
        elif isinstance(node, Tag):
            parts.append(node.get_text())
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _classify_row(nodes: list) -> "Line | None":
    """
    Given a list of nodes forming one <br>-delimited row, return a Line.

    Fandom structure:
      - Stage direction:   <i>(text)</i>  (entire row is italic, starts with '(')
      - Dialogue:          <b>Character:</b> text <i>(optional inline dir)</i>
      - Song:              line starting with a music note or 'Song:'
    """
    if not nodes:
        return None

    raw_text = _nodes_to_text(nodes).strip()
    if not raw_text:
        return None

    # Check if there's a leading <b> tag (character name)
    first_tag = next(
        (n for n in nodes if isinstance(n, Tag) and n.name not in ("br",)),
        None
    )

    if first_tag and first_tag.name == "b":
        char_name = first_tag.get_text(strip=True).rstrip(":")
        # Build dialogue text from everything after the <b>
        after_bold = []
        past_bold = False
        for node in nodes:
            if node is first_tag:
                past_bold = True
                continue
            if past_bold:
                after_bold.append(node)
        dialogue = _nodes_to_text(after_bold).lstrip(": ").strip()
        if not dialogue and not char_name:
            return None
        return Line(Line.DIALOGUE, char_name, dialogue)

    # Check if entire row is wrapped in <i> or starts with '(' — stage direction
    if all(
        isinstance(n, NavigableString) or (isinstance(n, Tag) and n.name == "i")
        for n in nodes
        if not (isinstance(n, NavigableString) and n.strip() == "")
    ):
        text = raw_text
        # A typical direction looks like "(something)"
        if text.startswith("(") or (first_tag and first_tag.name == "i"):
            return Line(Line.DIRECTION, None, text)

    # Song lines often start with a music note or have <i> content
    if raw_text.startswith(("\u266a", "\u266b", "Song:", "\u2665")):
        return Line(Line.SONG, None, raw_text)

    # Fallback: treat as stage direction if mostly italic
    italic_nodes = [n for n in nodes if isinstance(n, Tag) and n.name == "i"]
    if italic_nodes and first_tag and first_tag.name == "i":
        return Line(Line.DIRECTION, None, raw_text)

    # If there's readable text that doesn't fit above patterns,
    # treat as a plain direction/description
    if len(raw_text) > 1:
        return Line(Line.DIRECTION, None, raw_text)

    return None


def parse_transcript(soup: BeautifulSoup) -> list[Line]:
    content = soup.find("div", class_="mw-parser-output") or soup
    lines: list[Line] = []

    for p_tag in content.find_all("p", recursive=False):
        rows = _split_p_by_br(p_tag)
        for row_nodes in rows:
            line = _classify_row(row_nodes)
            if line and len(line.text) > 1:
                lines.append(line)

    print(f"[parse] Extracted {len(lines)} lines "
          f"({sum(1 for l in lines if l.kind == Line.DIALOGUE)} dialogue, "
          f"{sum(1 for l in lines if l.kind == Line.DIRECTION)} directions, "
          f"{sum(1 for l in lines if l.kind == Line.SONG)} song).")
    return lines


# ---------------------------------------------------------------------------
# Markdown export
# ---------------------------------------------------------------------------
def build_markdown(title: str, url: str, lines: list[Line]) -> str:
    parts = [
        f"# {title}",
        "",
        f"> Source: <{url}>",
        "",
        "---",
        "",
    ]

    for line in lines:
        if line.kind == Line.DIALOGUE:
            parts.append(f"**{line.character}:** {line.text}")
        elif line.kind == Line.SONG:
            parts.append(f"> *{line.text}*")
        else:
            parts.append(f"*{line.text}*")
        parts.append("")

    return "\n".join(parts)


def save_markdown(content: str, path: Path):
    path.write_text(content, encoding="utf-8")
    print(f"[md]  Saved -> {path}")


# ---------------------------------------------------------------------------
# Font helper
# ---------------------------------------------------------------------------
FONT_DIR = Path(__file__).parent / "_fonts"
FONT_REGULAR = FONT_DIR / "DejaVuSans.ttf"
FONT_BOLD    = FONT_DIR / "DejaVuSans-Bold.ttf"
FONT_ITALIC  = FONT_DIR / "DejaVuSans-Oblique.ttf"

FONT_URLS = {
    FONT_REGULAR: "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37.3/ttf/DejaVuSans.ttf",
    FONT_BOLD:    "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37.3/ttf/DejaVuSans-Bold.ttf",
    FONT_ITALIC:  "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37.3/ttf/DejaVuSans-Oblique.ttf",
}


def ensure_fonts():
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for dest, src_url in FONT_URLS.items():
        if not dest.exists():
            print(f"[font] Downloading {dest.name} ...")
            urllib.request.urlretrieve(src_url, dest)
            print(f"[font] Cached -> {dest}")


# ---------------------------------------------------------------------------
# PDF export
# ---------------------------------------------------------------------------
def save_pdf(title: str, url: str, lines: list[Line], path: Path):
    ensure_fonts()

    from fpdf import FPDF

    class TranscriptPDF(FPDF):
        def header(self):
            self.set_font("DejaVu", "B", 14)
            self.set_text_color(30, 30, 30)
            self.cell(0, 10, title, align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_font("DejaVu", "I", 8)
            self.set_text_color(130, 130, 130)
            short_url = url if len(url) <= 90 else url[:87] + "..."
            self.cell(0, 5, f"Source: {short_url}",
                      align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(200, 200, 200)
            self.set_line_width(0.3)
            self.ln(2)
            self.line(self.l_margin, self.get_y(),
                      self.w - self.r_margin, self.get_y())
            self.ln(3)
            self.set_text_color(0, 0, 0)

        def footer(self):
            self.set_y(-15)
            self.set_font("DejaVu", "I", 8)
            self.set_text_color(160, 160, 160)
            self.cell(0, 10, f"Page {self.page_no()}", align="C")

    pdf = TranscriptPDF(orientation="P", unit="mm", format="A4")
    pdf.add_font("DejaVu",  "",  str(FONT_REGULAR))
    pdf.add_font("DejaVu",  "B", str(FONT_BOLD))
    pdf.add_font("DejaVu",  "I", str(FONT_ITALIC))
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    PAGE_W = pdf.w - pdf.l_margin - pdf.r_margin

    for line in lines:
        if line.kind == Line.DIALOGUE:
            # Character label: bold blue
            pdf.set_font("DejaVu", "B", 10)
            pdf.set_text_color(25, 75, 160)
            char_label = f"{line.character}: "
            char_w = min(pdf.get_string_width(char_label) + 1, PAGE_W * 0.35)

            start_x = pdf.l_margin
            start_y = pdf.get_y()

            pdf.set_xy(start_x, start_y)
            pdf.cell(char_w, 6, char_label, new_x="RIGHT", new_y="LAST")

            # Dialogue text: regular black
            pdf.set_font("DejaVu", "", 10)
            pdf.set_text_color(20, 20, 20)
            pdf.multi_cell(PAGE_W - char_w, 6, line.text)

        elif line.kind == Line.SONG:
            pdf.set_font("DejaVu", "I", 10)
            pdf.set_text_color(100, 60, 160)
            pdf.set_x(pdf.l_margin + 5)
            pdf.multi_cell(PAGE_W - 5, 5, line.text)

        else:  # DIRECTION
            pdf.set_font("DejaVu", "I", 9)
            pdf.set_text_color(90, 90, 90)
            pdf.multi_cell(PAGE_W, 5, line.text)

        pdf.ln(1)

    pdf.output(str(path))
    print(f"[pdf] Saved -> {path}")


# ---------------------------------------------------------------------------
# Filename helper
# ---------------------------------------------------------------------------
def slug_from_url(url: str) -> str:
    path = urlparse(url).path
    slug = path.strip("/").replace("/", "_")
    slug = re.sub(r"^wiki_", "", slug)
    slug = re.sub(r"[^\w]", "_", slug)
    return slug


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Crawl a Fandom /Transcript wiki page and save as "
            "Markdown and/or PDF."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: crawl Rollercoaster transcript, output both md + pdf
  python crawl_transcript.py

  # Markdown only, custom episode
  python crawl_transcript.py https://phineasandferb.fandom.com/wiki/Lawn_Gnome_Beach_Party_of_Terror/Transcript --format md

  # Custom output directory
  python crawl_transcript.py --out ./transcripts
        """,
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=DEFAULT_URL,
        help=f"Fandom transcript URL (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--out",
        default="./output",
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "--format",
        choices=["md", "pdf", "both"],
        default="both",
        help="Output format: md, pdf, or both (default: both)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    args = parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = slug_from_url(args.url)
    title = get_page_title_from_url(args.url)

    print(f"[meta] Title : {title}")
    print(f"[meta] Output: {out_dir.resolve()}")

    # Fetch
    soup = fetch_page(args.url)

    # Parse
    lines = parse_transcript(soup)

    if not lines:
        print("[warn] No transcript lines found. "
              "The page structure may have changed.")
        sys.exit(1)

    # Export
    if args.format in ("md", "both"):
        md_path = out_dir / f"{stem}.md"
        md_content = build_markdown(title, args.url, lines)
        save_markdown(md_content, md_path)

    if args.format in ("pdf", "both"):
        pdf_path = out_dir / f"{stem}.pdf"
        save_pdf(title, args.url, lines, pdf_path)

    print(f"\nDone! Files saved to: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
