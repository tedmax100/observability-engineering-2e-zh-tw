import json, sys
sys.path.insert(0, "/home/nathan/Documents/book/web")
from convert_chapter import render_chapter

tm = json.load(open("/tmp/claude-1000/-home-nathan-Documents-book/ce832d83-2b6c-40ee-b9f6-cfe68fa98c1c/scratchpad/toc_titlemap.json"))
chapters = {int(k): v for k, v in tm["chapters"].items()}
parts = {k: v[0] for k, v in tm["parts"].items()}

PART_TITLES = {
    "I": "可觀測性導論", "II": "檢測基礎", "III": "分析工作流程",
    "IV": "可觀測性技術深度剖析", "V": "可觀測性應用案例", "VI": "可觀測性治理",
}
PART_NUM_CN = {"I": "一", "II": "二", "III": "三", "IV": "四", "V": "五", "VI": "六"}

# chapter n -> starting part (based on part start page <= chapter start page)
part_starts_sorted = sorted(parts.items(), key=lambda kv: kv[1])

def part_for_chapter(start_pn):
    cur = None
    for roman, pn in part_starts_sorted:
        if pn <= start_pn:
            cur = roman
        else:
            break
    return cur

INDEX_START = 617
ns = sorted(chapters.keys())
for i, n in enumerate(ns):
    start_pn = chapters[n][0]
    end_pn = (chapters[ns[i+1]][0] - 1) if i + 1 < len(ns) else INDEX_START - 1
    title_cn = chapters[n][2].split("　")[-1] if False else None
    # title_cn should come from CHAPTER_TITLES map for consistency
    sys.path.insert(0, "/tmp/claude-1000/-home-nathan-Documents-book/ce832d83-2b6c-40ee-b9f6-cfe68fa98c1c/scratchpad")
    from toc_titles import CHAPTER_TITLES
    title_cn = CHAPTER_TITLES[n]

    roman = part_for_chapter(start_pn)
    part_label = None
    if roman and start_pn == parts[roman]:
        part_label = f"PART {roman} · {PART_TITLES[roman]}"

    prev_link = f"ch{ns[i-1]:02d}.html" if i > 0 else "preface.html"
    next_link = f"ch{ns[i+1]:02d}.html" if i + 1 < len(ns) else None

    render_chapter(n, start_pn, end_pn, title_cn, part_label, prev_link, next_link)
