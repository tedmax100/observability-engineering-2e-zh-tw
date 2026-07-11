import json, sys
sys.path.insert(0, "/tmp/claude-1000/-home-nathan-Documents-book/ce832d83-2b6c-40ee-b9f6-cfe68fa98c1c/scratchpad")
from toc_titles import CHAPTER_TITLES, PART_TITLES, PART_NUM_CN

tm = json.load(open("/tmp/claude-1000/-home-nathan-Documents-book/ce832d83-2b6c-40ee-b9f6-cfe68fa98c1c/scratchpad/toc_titlemap.json"))
chapters = {int(k): v for k, v in tm["chapters"].items()}
parts = {k: v[0] for k, v in tm["parts"].items()}
part_starts_sorted = sorted(parts.items(), key=lambda kv: kv[1])

def part_for_chapter(start_pn):
    cur = None
    for roman, pn in part_starts_sorted:
        if pn <= start_pn:
            cur = roman
        else:
            break
    return cur

ns = sorted(chapters.keys())
by_part = {}
for n in ns:
    roman = part_for_chapter(chapters[n][0])
    by_part.setdefault(roman, []).append(n)

sections = []
for roman, _ in part_starts_sorted:
    lis = "\n".join(
        f'<li><a href="ch{n:02d}.html"><span class="num">{n:02d}</span>{CHAPTER_TITLES[n]}</a></li>'
        for n in by_part.get(roman, [])
    )
    sections.append(f'''<section class="part-block">
    <h2 class="section serif">第{PART_NUM_CN[roman]}部分　{PART_TITLES[roman]}</h2>
    <ul class="toc-list">
      {lis}
    </ul>
  </section>''')

html = f'''<title>《可觀測性工程》第二版 — 中文譯本</title>
<link rel="stylesheet" href="style.css">
<style>
  .toc-list {{ list-style: none; margin: 0 0 1rem; padding: 0; display: flex; flex-direction: column; gap: 0.15rem; }}
  .toc-list a {{
    display: flex; align-items: baseline; gap: 0.9rem;
    padding: 0.55rem 0.2rem; text-decoration: none; color: var(--ink);
    border-bottom: 1px solid var(--rule);
  }}
  .toc-list a:hover {{ color: var(--accent-ink); }}
  .toc-list .num {{
    font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
    color: var(--ink-faint); font-size: 0.85rem; flex: none; width: 1.6rem;
  }}
  .preface-link {{
    display: block; margin-bottom: 3rem; padding: 1rem 1.2rem;
    background: var(--paper-raised); border-radius: 4px; text-decoration: none;
    color: var(--ink); box-shadow: var(--shadow);
  }}
  .preface-link:hover {{ color: var(--accent-ink); }}
</style>

<main>
  <header class="masthead">
    <span class="eyebrow">Observability Engineering · Second Edition</span>
    <h1 class="title serif">可觀測性工程</h1>
    <div class="rule"></div>
  </header>

  <p class="lede">邁向生產卓越之路。中文譯本網頁閱讀版，依原書結構逐章收錄。</p>

  <a class="preface-link" href="preface.html">序 →</a>

  {chr(10).join(sections)}

  <footer class="colophon">
    <span>《可觀測性工程》第二版</span>
    <span>Charity Majors · Liz Fong-Jones · George Miranda · Austin Parker</span>
  </footer>
</main>
'''
with open("/home/nathan/Documents/book/web/index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("wrote index.html")
