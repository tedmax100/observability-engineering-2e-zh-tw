import sys, re, os, json
import fitz

PDF_PATH = "/home/nathan/Documents/book/ObsEng_2nd_TC.pdf"
ORIG_PDF_PATH = "/home/nathan/Documents/book/Observability Engineering_2ndEd.pdf"
OUT_DIR = "/home/nathan/Documents/book/web"
IMG_DIR = os.path.join(OUT_DIR, "images")
os.makedirs(IMG_DIR, exist_ok=True)

doc = fitz.open(PDF_PATH)
orig_doc = fitz.open(ORIG_PDF_PATH)

def get_term_y0s(pn0):
    """Scan the ORIGINAL English page for short standalone italic/bold runs
    at body size — these are O'Reilly-style definition-list terms whose
    emphasis got flattened away during translation. Returns rounded y0 set."""
    if pn0 >= orig_doc.page_count:
        return set()
    page = orig_doc[pn0]
    out = set()
    for b in page.get_text("dict")["blocks"]:
        if "lines" not in b or len(b["lines"]) != 1:
            continue
        spans = b["lines"][0]["spans"]
        if not spans:
            continue
        text = "".join(s["text"] for s in spans).strip()
        if not text or len(text) > 30:
            continue
        if re.search(r'[.?!:,;]$', text):
            continue
        sizes = [s["size"] for s in spans]
        if not all(9.0 <= sz <= 11.5 for sz in sizes):
            continue
        fonts = [s["font"] for s in spans]
        emphasized = all(("-It" in f or "Italic" in f or "Bold" in f or "Semibold" in f) for f in fonts)
        if emphasized:
            out.add(round(b["bbox"][1]))
    return out

def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def is_mono(font):
    return any(k in font for k in ("Mono", "Courier", "Consol"))

def _is_ascii_wordchar(c):
    return c.isascii() and (c.isalnum() or c in "._-")

def smart_join(lines):
    """Join wrapped PDF lines without injecting spurious spaces into CJK
    running text. Only keep a space at a line break when both sides are
    ASCII word characters (i.e. an actual Latin word was split)."""
    out = lines[0]
    for line in lines[1:]:
        if out and line and _is_ascii_wordchar(out[-1]) and _is_ascii_wordchar(line[0]):
            out += " " + line
        else:
            out += line
    return out

CODE_KEYWORDS = set("""
    public private protected static final void class interface extends implements
    new return if else for while try catch finally throw throws import package
    this super null true false break continue switch case default enum abstract
    def class import from as with lambda yield async await pass elif in is not and or
    func type struct interface package go chan defer select
    const let var function export default async function
    SELECT FROM WHERE GROUP BY ORDER LIMIT JOIN ON AS COUNT_DISTINCT
""".split())

_CODE_TOKEN_RE = re.compile(
    r'(?P<comment>//[^\n]*|#[^\n]*)'
    r'|(?P<string>"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\')'
    r'|(?P<number>\b\d[\d.]*\b)'
    r'|(?P<word>[A-Za-z_][A-Za-z0-9_]*)'
)

def highlight_code(text):
    out = []
    pos = 0
    for m in _CODE_TOKEN_RE.finditer(text):
        if m.start() > pos:
            out.append(esc(text[pos:m.start()]))
        pos = m.end()
        if m.lastgroup == "comment":
            out.append(f'<span class="tok-comment">{esc(m.group())}</span>')
        elif m.lastgroup == "string":
            out.append(f'<span class="tok-string">{esc(m.group())}</span>')
        elif m.lastgroup == "number":
            out.append(f'<span class="tok-number">{esc(m.group())}</span>')
        elif m.lastgroup == "word":
            if m.group() in CODE_KEYWORDS:
                out.append(f'<span class="tok-keyword">{esc(m.group())}</span>')
            else:
                out.append(esc(m.group()))
    out.append(esc(text[pos:]))
    return "".join(out)

def classify_and_render(pn0, chapter_slug):
    """Returns list of html fragment strings for one page."""
    page = doc[pn0]
    items = []  # (y0, kind, payload)

    # images
    for info in page.get_image_info(xrefs=True):
        bbox = info["bbox"]
        xref = info.get("xref", 0)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if bbox[1] > 600 or w < 20 or h < 20:
            continue
        try:
            pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha >= 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            fname = f"{chapter_slug}_p{pn0+1}_x{xref}.png"
            pix.save(os.path.join(IMG_DIR, fname))
            # small square-ish images are admonition icons (tip/note/warning),
            # not figures — the real diagrams in this book are much larger.
            if w < 60 and h < 70:
                items.append((bbox[1], "icon", fname))
            else:
                items.append((bbox[1], "image", fname))
        except Exception:
            pass

    term_y0s = get_term_y0s(pn0)

    d = page.get_text("dict")
    for b in d["blocks"]:
        if "lines" not in b:
            continue
        # merge all lines of this block into one text + representative style
        texts = []
        sizes = []
        fonts = []
        bolds = []
        block_is_mono = is_mono(b["lines"][0]["spans"][0]["font"]) if b["lines"] and b["lines"][0]["spans"] else False
        for l in b["lines"]:
            raw = "".join(s["text"] for s in l["spans"])
            # code keeps leading indentation (it's meaningful); prose strips it
            t = raw.rstrip() if block_is_mono else raw.strip()
            if not t.strip():
                continue
            texts.append(t)
            for s in l["spans"]:
                sizes.append(s["size"])
                fonts.append(s["font"])
                bolds.append("Bold" in s["font"] or "Semibold" in s["font"])
        if not texts:
            continue
        y0 = b["bbox"][1]
        if y0 > 600:
            continue  # footer/page-number junk
        size = max(sizes) if sizes else 10.5
        bold = any(bolds)
        font = fonts[0] if fonts else ""
        mono = is_mono(font)
        # code listings must keep their real line breaks; prose should not
        # gain spurious spaces or newlines from PDF line-wrapping.
        text = "\n".join(texts) if mono else smart_join(texts)
        is_term = (
            len(texts) == 1 and not mono and not bold and
            round(y0) in term_y0s and
            not re.search(r'[。？！，、]$', text)
        )
        items.append((y0, "text", {"text": text, "size": size, "bold": bold, "mono": mono, "is_term": is_term}))

    items.sort(key=lambda x: x[0])

    html = []
    for y0, kind, payload in items:
        if kind == "image":
            html.append(("__IMG__", payload))
            continue
        if kind == "icon":
            html.append(("__ICON__", payload))
            continue
        text = payload["text"]
        size = payload["size"]
        bold = payload["bold"]
        mono = payload["mono"]

        if re.match(r'^(圖[\s\xa0]*[\d‑\-]|Figure\s*\d)', text):
            html.append(("__CAPTION__", esc(text)))
            continue
        if payload.get("is_term"):
            html.append(("term", esc(text)))
            continue
        if size >= 18 and bold:
            html.append(("h1", esc(text)))
            continue
        if 12 <= size < 18 and bold:
            html.append(("h2", esc(text)))
            continue
        if mono:
            html.append(("code", text))  # raw, escaped+highlighted at render time
            continue
        if bold and size >= 9.5 and len(text) < 60 and not re.search(r'[。？！，、]$', text):
            html.append(("h3", esc(text)))
            continue
        if size <= 8.5:
            html.append(("fn", esc(text)))
            continue
        html.append(("p", esc(text)))
    return html

def render_chapter(n, start_pn, end_pn, title_cn, part_label=None, prev_link=None, next_link=None):
    slug = f"ch{n:02d}"
    blocks = []
    for pn0 in range(start_pn - 1, end_pn):
        blocks.extend(classify_and_render(pn0, slug))

    # merge adjacent code blocks (a listing is often split across PDF text
    # blocks — and across a page break — even though it's one example).
    merged_blocks = []
    for kind, val in blocks:
        if kind == "code" and merged_blocks and merged_blocks[-1][0] == "code":
            merged_blocks[-1] = ("code", merged_blocks[-1][1] + "\n" + val)
        else:
            merged_blocks.append((kind, val))
    blocks = merged_blocks

    # group consecutive (term, paragraph) runs into a definition list, matching
    # the source book's dt/dd-style convention (term emphasis got flattened in
    # translation, so we rebuild it here instead of leaving bare paragraphs).
    grouped = []
    i = 0
    while i < len(blocks):
        kind, val = blocks[i]
        if kind == "term":
            pairs = []
            while i < len(blocks) and blocks[i][0] == "term":
                term_val = blocks[i][1]
                desc_val = ""
                if i + 1 < len(blocks) and blocks[i+1][0] == "p":
                    desc_val = blocks[i+1][1]
                    i += 2
                else:
                    i += 1
                pairs.append((term_val, desc_val))
            grouped.append(("dl", pairs))
        elif kind == "__ICON__":
            desc_val = ""
            if i + 1 < len(blocks) and blocks[i+1][0] == "p":
                # text follows the icon
                desc_val = blocks[i+1][1]
                i += 2
            elif grouped and grouped[-1][0] == "p":
                # text preceded the icon (side-by-side layout sorted text first)
                desc_val = grouped.pop()[1]
                i += 1
            else:
                i += 1
            grouped.append(("callout", (val, desc_val)))
        else:
            grouped.append((kind, val))
            i += 1

    body = []
    pending_caption = None
    for kind, val in grouped:
        if kind == "__IMG__":
            body.append(f'<figure class="plate"><img src="images/{val}" alt="" />')
            pending_caption = "OPEN"
        elif kind == "__CAPTION__":
            if pending_caption == "OPEN":
                body.append(f'<figcaption>{val}</figcaption></figure>')
                pending_caption = None
            else:
                body.append(f'<p class="fn">{val}</p>')
        else:
            if pending_caption == "OPEN":
                body.append("</figure>")
                pending_caption = None
            if kind == "h1":
                continue  # chapter title handled separately below
            elif kind == "h2":
                body.append(f'<h2 class="section serif">{val}</h2>')
            elif kind == "h3":
                body.append(f'<h3 class="subsection">{val}</h3>')
            elif kind == "code":
                body.append(f'<pre class="code">{highlight_code(val)}</pre>')
            elif kind == "fn":
                body.append(f'<p class="fn">{val}</p>')
            elif kind == "dl":
                items = "".join(
                    f'<dt>{t}</dt><dd>{d}</dd>' if d else f'<dt>{t}</dt>'
                    for t, d in val
                )
                body.append(f'<dl class="deflist">{items}</dl>')
            elif kind == "callout":
                icon_fname, desc_val = val
                body.append(
                    f'<div class="callout"><img src="images/{icon_fname}" alt="" />'
                    f'<p>{desc_val}</p></div>'
                )
            else:
                body.append(f'<p>{val}</p>')
    if pending_caption == "OPEN":
        body.append("</figure>")

    prev_a = f'<a href="{prev_link}">← 上一章</a>' if prev_link else '<span></span>'
    next_a = f'<a href="{next_link}">下一章 →</a>' if next_link else '<span></span>'
    nav = f'''<nav class="chapnav">
    {prev_a}
    <a href="index.html">目錄</a>
    {next_a}
  </nav>'''

    part_html = f'<div class="part-label">{esc(part_label)}</div>' if part_label else ""

    html = f'''<title>第 {n} 章　{esc(title_cn)} — 《可觀測性工程》第二版</title>
<link rel="stylesheet" href="style.css">

{nav}
<main>
  <header class="masthead">
    <span class="eyebrow">Observability Engineering · Second Edition</span>
    {part_html}
    <h1 class="title serif">第 {n} 章<br>{esc(title_cn)}</h1>
    <div class="rule"></div>
  </header>

  {chr(10).join(body)}

  <footer class="colophon">
    <span>《可觀測性工程》第二版 · 第 {n} 章</span>
    <span>{esc(title_cn)}</span>
  </footer>
</main>
'''
    out_path = os.path.join(OUT_DIR, f"{slug}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", out_path, len(body), "blocks")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("start", type=int)
    ap.add_argument("end", type=int)
    ap.add_argument("title")
    ap.add_argument("--part", default=None)
    ap.add_argument("--prev", default=None)
    ap.add_argument("--next", default=None)
    args = ap.parse_args()
    render_chapter(args.n, args.start, args.end, args.title, args.part, args.prev, args.next)
