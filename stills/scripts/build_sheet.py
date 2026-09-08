#!/usr/bin/env python
"""
A page to pick from. Point it at a folder of stills and it renders one HTML page
holding every picture under it, grouped, filterable, click through to full size.

It reads the manifests `pick_stills.py` and `crop_stills.py` left beside the
pictures, so the page states where each frame came from and at what timecode
without anybody retyping it. **The source table is derived, never written by
hand.** An earlier version kept the bitrates in a metadata file beside the
builder and they had to be hand-corrected in two places when a measurement
changed.

Structure is whatever is on disk. Any folder under the root holding a manifest
becomes a group, and the folder above it becomes the filter it sits under. So
this works on a flat folder and on a `full frames/` plus `feed crops/` split
without being told which it is.

Output is `contact-sheet.html` plus a `_thumbs/` folder, both in the root. Both
are build output. Change this file, then run it again.

Usage:
    python build_sheet.py --root DIR
    python build_sheet.py --root DIR --title "Stills"
"""
import argparse
import html
import json
import re
import shutil
from datetime import date
from pathlib import Path

import cv2

THUMB_W = 420


def pretty_tc(tc):
    """Manifests store 37-32.000, because a colon cannot go in a filename."""
    m = re.match(r"^(\d+)-(\d+)\.\d+$", tc or "")
    return "%s:%s" % (m.group(1), m.group(2)) if m else (tc or "")


def hms(seconds):
    if not seconds:
        return ""
    s = int(round(seconds))
    return "%d:%02d:%02d" % (s // 3600, (s % 3600) // 60, s % 60)


def load_manifests(folder):
    rows, sources = {}, []
    for mf in sorted(folder.glob("*.stills.json")) + sorted(folder.glob("*.crops.json")):
        try:
            d = json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            continue
        src = d.get("source")
        if isinstance(src, dict):
            sources.append(src)
        for r in d.get("picks", []) + d.get("crops", []):
            rows[r["file"]] = r
    return rows, sources


def thumb_for(img, key, thumbs):
    out = thumbs / key.replace("/", "__")
    im = cv2.imread(str(img))
    if im is None:
        return False
    h, w = im.shape[:2]
    im = cv2.resize(im, (THUMB_W, max(1, round(h * THUMB_W / w))), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(out), im, [cv2.IMWRITE_JPEG_QUALITY, 82])
    return True


def collect(root, thumbs):
    groups, sources = [], {}
    for folder in sorted(p for p in root.rglob("*") if p.is_dir()):
        if thumbs == folder or thumbs in folder.parents or folder.name.startswith("_"):
            continue
        man, srcs = load_manifests(folder)
        if not man:
            continue
        for s in srcs:
            sources.setdefault(s.get("path") or s.get("name", "?"), s)

        rel_folder = folder.relative_to(root)
        section = rel_folder.parts[0] if len(rel_folder.parts) > 1 else "Stills"
        items = []
        for img in sorted(folder.glob("*.jpg")):
            key = "%s/%s" % (rel_folder.as_posix(), img.name)
            if not thumb_for(img, key, thumbs):
                continue
            m = man.get(img.name, {})
            px = m.get("crop_px") or ([m["width"], m["height"]] if m.get("width") else None)
            items.append({
                "href": key,
                "thumb": "_thumbs/" + key.replace("/", "__"),
                "name": img.name,
                "tc": pretty_tc(m.get("at_timecode", "")),
                "px": ("%d x %d" % tuple(px)) if px else "",
                "kb": round(img.stat().st_size / 1024),
                "note": m.get("centred_on", "") if m.get("subject") else "",
            })
        if items:
            groups.append({"section": section.replace("_", " "),
                           "folder": rel_folder.parts[-1], "items": items})
    return groups, list(sources.values())


CSS = """
/* The same palette and type as the readthrough page: the First Look tokens
   (paper, ink, sage, butter) and its three faces, with system fallbacks. This
   tool stands alone, so the tokens are written here rather than read from
   readthrough/. Restyled 2026-09-08; the first version had its own purple. */
:root{--paper:#faf6ee;--paper-warm:#f5eede;--paper-deep:#ece1c7;--ink:#1f1d1a;--ink-soft:#44403c;
      --ink-faint:#6e6760;--rule:#e7dec9;--sage:#6fa67f;--sage-deep:#1f5028;--sage-soft:#dcebd7;
      --butter:#f5d88e;--butter-soft:#fbefc8;
      --display:"Plus Jakarta Sans",system-ui,sans-serif;--sans:"Space Grotesk",system-ui,sans-serif;
      --mono:"JetBrains Mono",ui-monospace,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 var(--sans)}
header{padding:56px 24px 28px;background:linear-gradient(180deg,var(--paper) 0%,var(--paper-warm) 100%)}
.wrap{max-width:1040px;margin:0 auto}
.stamp{display:inline-block;font-family:var(--mono);font-size:.7rem;letter-spacing:.18em;text-transform:uppercase;
       color:var(--sage-deep);background:var(--sage-soft);padding:6px 12px;border-radius:20px;margin-bottom:18px}
h1{margin:0 0 12px;font-family:var(--display);font-weight:800;font-size:clamp(1.8rem,4vw,2.5rem);letter-spacing:-.02em}
.sub{color:var(--ink-soft);max-width:60ch;margin:0 0 18px;font-size:1.05rem}
table.q{border-collapse:collapse;font-family:var(--mono);font-size:12px}
table.q th,table.q td{border:1.5px solid var(--ink);padding:6px 11px;text-align:left}
table.q th{background:var(--paper-warm);font-weight:700;letter-spacing:.06em;text-transform:uppercase;font-size:10.5px}
nav{position:sticky;top:0;z-index:5;background:var(--paper);border-bottom:1px solid var(--rule);
    padding:12px 24px;display:flex;flex-wrap:wrap;gap:8px}
nav button{font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;padding:6px 10px;
           border:1.5px solid var(--ink);border-radius:3px;background:var(--paper-warm);color:var(--ink);cursor:pointer}
nav button[aria-pressed=true]{background:var(--ink);color:var(--paper)}
main{padding:26px 24px 60px;max-width:1088px;margin:0 auto}
section h2{font-family:var(--mono);font-size:.7rem;letter-spacing:.18em;text-transform:uppercase;color:var(--sage-deep);
           margin:32px 0 3px;font-weight:700}
section .count{color:var(--ink-faint);font-family:var(--mono);font-size:12px;margin:0 0 14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
figure{margin:0;background:var(--paper);border:2px solid var(--ink);border-radius:6px;overflow:hidden;box-shadow:3px 3px 0 var(--ink)}
figure a{display:block;line-height:0}
figure img{width:100%;height:auto;display:block;border-bottom:2px solid var(--ink)}
figcaption{padding:10px 12px;font-family:var(--mono);font-size:11px;color:var(--ink-faint);line-height:1.5}
figcaption b{display:block;color:var(--ink);font-weight:700;font-size:12px;word-break:break-word;margin-bottom:2px}
footer{padding:22px 24px 50px;color:var(--ink-faint);font-family:var(--mono);font-size:12px;border-top:1px solid var(--rule);text-align:center}
@media (max-width:640px){header{padding:36px 16px 20px}main{padding:18px 16px 40px}nav{padding:10px 16px}.grid{grid-template-columns:1fr}}
"""

JS = """
const btns=[...document.querySelectorAll('nav button')];
btns.forEach(b=>b.addEventListener('click',()=>{
  btns.forEach(o=>o.setAttribute('aria-pressed',String(o===b)));
  const f=b.dataset.filter;
  document.querySelectorAll('section').forEach(s=>{
    s.hidden = !(f==='all' || s.dataset.section===f);
  });
}));
"""


def render(groups, sources, title, blurb):
    sections = sorted({g["section"] for g in groups})
    nav = ['<button data-filter="all" aria-pressed="true">Everything</button>']
    nav += ['<button data-filter="%s" aria-pressed="false">%s</button>'
            % (html.escape(s), html.escape(s)) for s in sections]

    body = []
    for g in groups:
        cards = []
        for it in g["items"]:
            bits = [b for b in (it["tc"] and "at " + it["tc"], it["px"], "%d KB" % it["kb"]) if b]
            note = ("<br>" + html.escape(it["note"])) if it["note"] else ""
            cards.append(
                '<figure><a href="%s" target="_blank" rel="noopener">'
                '<img src="%s" loading="lazy" alt=""></a>'
                "<figcaption><b>%s</b>%s%s</figcaption></figure>"
                % (html.escape(it["href"]), html.escape(it["thumb"]),
                   html.escape(it["name"]),
                   " &middot; ".join(html.escape(b) for b in bits), note))
        body.append(
            '<section data-section="%s"><h2>%s &middot; %s</h2>'
            '<p class="count">%d pictures</p><div class="grid">%s</div></section>'
            % (html.escape(g["section"]), html.escape(g["section"]),
               html.escape(g["folder"]), len(g["items"]), "".join(cards)))

    qrows = []
    for s in sorted(sources, key=lambda s: -(s.get("video_bitrate_bps") or 0)):
        br = s.get("video_bitrate_bps")
        qrows.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            html.escape(Path(s.get("path", "?")).name),
            html.escape("%s x %s%s%s" % (
                s.get("width", "?"), s.get("height", "?"),
                ", %s fps" % s["fps"] if s.get("fps") else "",
                ", " + hms(s.get("duration_s")) if s.get("duration_s") else "")),
            html.escape("%.1f Mbit/s" % (br / 1e6) if br else "not reported")))

    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title><style>%s</style></head>
<body>
<header><div class="wrap">
<span class="stamp">Stills</span>
<h1>%s</h1>
<p class="sub">%s</p>
<table class="q"><tr><th>Cut from</th><th>Picture</th><th>Video bitrate</th></tr>%s</table>
</div></header>
<nav>%s</nav>
<main>%s</main>
<footer>Built %s. Click any picture to open it full size.</footer>
<script>%s</script>
</body></html>
""" % (html.escape(title), CSS, html.escape(title), html.escape(blurb),
       "".join(qrows), "".join(nav), "".join(body), date.today().isoformat(), JS)


def main():
    ap = argparse.ArgumentParser(description="Render a page to pick stills from.")
    ap.add_argument("--root", required=True)
    ap.add_argument("--title", default="Stills")
    ap.add_argument("--blurb", default="Every frame here came straight out of the source "
                                       "at full resolution, and nothing was scaled up. "
                                       "Click a picture to open it, then save the one you want.")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    thumbs = root / "_thumbs"
    if thumbs.exists():
        shutil.rmtree(thumbs)
    thumbs.mkdir(parents=True, exist_ok=True)

    groups, sources = collect(root, thumbs)
    (root / "contact-sheet.html").write_text(
        render(groups, sources, args.title, args.blurb), encoding="utf-8")
    n = sum(len(g["items"]) for g in groups)
    print("  contact-sheet.html: %d pictures across %d folders, %d source%s"
          % (n, len(groups), len(sources), "" if len(sources) == 1 else "s"))


if __name__ == "__main__":
    main()
