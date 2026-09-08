// datasets/system.json -> system.html
//
//   node build_system_page.mjs --style-from ".../local-use-case-collector/OVERVIEW.html"
//
// WHAT THIS IS. The page a person reads to understand what is here and how the
// parts fit. Every word comes from datasets/system.json, which is written by
// hand and is the thing to edit.
//
// BUILT ON A REFERENCE PAGE. The density target is a page of about 960 visible
// words, no tables, no SVG, a sidebar of contents and numbered sections.
//
//                        OVERVIEW.html     the version this replaces
//   visible words              960                    2,239
//   tables                       0                       11
//   svg diagrams                 0                        2
//   sections                     8                        7 plus 9 cards
//
// It gets there with a sidebar of contents, numbered section labels, and short
// prose broken by four small components. So the vocabulary here is that file's:
//   .shell + .sidebar + .main + .inner        the frame
//   .header-label / -title / -sub             who this is and one claim
//   .section + .section-label + .section-title   "01 · The problem"
//   .conceptgrid + .concept + .concept-title + .concept-status   peer things
//        and how settled each is
//   .deflist + .defrow + .defkey + .defval    a label and its meaning
//   .step + .step-number + .step-text         a numbered move
//   .callout + .callout-label                 the one line that matters
//   .hl / .hl--sky                            inline highlight
// The stylesheet is lifted whole and no CSS is authored here.

import { readFileSync, writeFileSync, existsSync, statSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join, basename } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const flag = (n) => { const i = args.indexOf("--" + n); return i === -1 ? null : args[i + 1]; };
const styleFrom = flag("style-from");
if (!styleFrom) { console.error("--style-from OVERVIEW.html is required. The stylesheet is inherited, never written."); process.exit(1); }
if (!existsSync(styleFrom)) { console.error("Parent not found: " + styleFrom); process.exit(1); }

const parent = readFileSync(styleFrom, "utf8");
const STYLE = [...parent.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((m) => m[1]).join("\n");
if (!STYLE) { console.error("Parent has no style block."); process.exit(1); }
const STYLE_HASH = createHash("sha256").update(STYLE).digest("hex");
const DEFINED = new Set([...STYLE.matchAll(/\.([a-zA-Z][\w-]*)/g)].map((m) => m[1]));

const liftAudit = (src) => {
  const at = src.indexOf("Cuts Layout Audit");
  if (at === -1) return "";
  const s = src.indexOf("<script", at), e = src.indexOf("</script>", s);
  return s !== -1 && e !== -1 ? src.slice(src.lastIndexOf("<!--", at), e + 9) : "";
};
const auditFrom = flag("audit-from");
let AUDIT = liftAudit(parent);
if (!AUDIT && auditFrom && existsSync(auditFrom)) AUDIT = liftAudit(readFileSync(auditFrom, "utf8"));

const d = JSON.parse(readFileSync(join(HERE, "datasets", "system.json"), "utf8"));
const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const lc = (s) => { const w = String(s ?? ""); return /^[A-Z]{2,}/.test(w) ? w : w.charAt(0).toLowerCase() + w.slice(1); };

// The reference has two states. built maps to settled, everything unfinished to
// open, so a colour on this page always means the same thing.
const state = (s) => s === "built"
  ? ["settled", "runs"]
  : ["open", s === "written, refused by the tool" ? "blocked" : "not general"];

const NAV = [
  ["what", "What it is"], ["out", "What comes out"], ["jobs", "The four workflows"],
  ["tools", "The five tools"], ["use", "How to use it"], ["repo", "What is in the repo"],
  ["not", "What it will not do"], ["open", "Still open"],
];

const section = (id, label, title, inner) => `<section class="section" id="${id}">
<div class="section-label">${esc(label)}</div>
<h2 class="section-title">${esc(title)}</h2>
${inner}
</section>`;

const callout = (tint, label, inner) => `<div class="callout callout--${tint}">
  <div class="callout-label">${esc(label)}</div>
  ${inner}
</div>`;

const deflist = (rows) => `<div class="deflist">${rows.map(([k, v]) =>
  `<div class="defrow"><div class="defkey">${esc(k)}</div><div class="defval">${v}</div></div>`).join("")}</div>`;

const concepts = (items) => `<div class="conceptgrid">${items.map(([title, status, cls, body]) =>
  `<div class="concept"><div class="concept-title">${esc(title)}${status
    ? ` <span class="concept-status concept-status--${cls}">${esc(status)}</span>` : ""}</div>
  <p class="concept-body">${esc(body)}</p></div>`).join("")}</div>`;

const steps = (items) => items.map((s, i) => `<div class="step"><div class="step-number">${String(i + 1).padStart(2, "0")}</div><div class="step-text">
  <strong>${esc(s.do)}</strong>
  <code>${esc(s.how)}</code> ${esc(s.check)}
</div></div>`).join("");

const wf = d.workflows.items;
const built = wf.filter((w) => w.status === "built").length;

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(d.title)}</title>
<style>${STYLE}</style>
</head>
<body>
<nav class="mobile-nav">${NAV.map(([id, t]) => `<a href="#${id}">${esc(t.split(" ").slice(-1)[0])}</a>`).join("")}</nav>
<div class="shell">
<aside class="sidebar">
  <div class="sidebar-title">Contents</div>
  ${NAV.map(([id, t]) => `<a class="sidebar-link" href="#${id}">${esc(t)}</a>`).join("\n  ")}
  <div class="sidebar-title" style="margin-top:26px">In the repo</div>
  <div class="sidebar-link" style="cursor:default">README.md</div>
  <div class="sidebar-link" style="cursor:default">TODO.md</div>
  <div class="sidebar-link" style="cursor:default">readthrough/README.md</div>
</aside>
<main class="main"><div class="inner">

<header class="header">
  <div class="header-label">Video tools</div>
  <h1 class="header-title">Five tools that read a recording so you do not have to watch it twice</h1>
  <p class="header-sub">${esc(d.lede)}</p>
</header>

${section("what", "01 · The problem", "What it is",
`<p>You have three hours of footage and forty seconds of it are worth posting. Finding
which forty seconds means watching all of it, and watching it again when somebody asks
for a different clip.</p>
<p>These tools do the parts a machine can measure. <span class="hl">They measure,
they narrow, and they never choose.</span> Geometry comes off pixels, loudness off the
file, cut points off the waveform. What is worth saying stays yours.</p>
${callout("sage", "The thing that comes out",
  `<p><code>readthrough.html</code></p><p class="concept-body" style="margin-top:6px">One page
  saying who was up, when, what each stretch was about, and the lines worth cutting, with
  the frames embedded. Opens by double-clicking.</p>`)}`)}

${section("out", "02 · The shape", "What comes out",
`<p>Every workflow ends in a file you can open. None of them needs a server and none of
them uploads anything.</p>
${deflist(d.artifacts.items.map((a) => [a.file, `${esc(a.what)} <span class="hl--sky">${esc(a.from)}</span>`]))}`)}

${section("jobs", "03 · The jobs", "The four workflows",
`<p>A tool does one measurable thing. A workflow is the order to do them in, plus the
judgement that is not in a JSON file. ${built} of the four run end to end.</p>
${concepts(wf.map((w) => { const [cls, label] = state(w.status); return [w.name, label, cls, w.job]; }))}
<p class="subsection-title">Where a person sits</p>
<p>${esc(d.workflows.human_note)}</p>`)}

${section("tools", "04 · The parts", "The five tools",
`<p>Each runs on its own, on any video, and none of them knows about a particular show or
client. Each folder holds a <code>README.md</code> for a person and a <code>SKILL.md</code>
for an agent.</p>
${deflist(d.tools.map((t) => [t.name, `${esc(t.one_line)} <span class="hl--sky">${esc(lc(t.in))} in, ${esc(lc(t.out))} out</span>`]))}`)}

${section("use", "05 · Getting going", "How to use it",
`${steps(d.start_here.steps)}
<p>${esc(d.start_here.first_run)}</p>`)}

${section("repo", "06 · The map", "What is in the repo",
`<p>Two folders. <code>video-tools</code> holds the tools and is what becomes the repo.
<code>video-processing-pipeline</code> is where they get run on real recordings.</p>
${deflist(d.folders.pipeline_rooms.slice(0, 6).map((r) => [r.name, esc(r.what)]))}
<p>${esc(d.folders.how_they_relate[1])}</p>`)}

${section("not", "07 · Limits", "What it will not do",
`<p>It does not say who is speaking. A name is read out of the sentence beside it and
travels with that sentence, because a transcript returns words and not speakers.
${esc(d.known_wrong[0].split(": ")[1] || "")}</p>
<p>It cannot place a cut. Every time is a caption timing, wrong by tens of milliseconds.
A cut point has to land inside measured silence.</p>
${callout("blush", "And it publishes nothing",
  "<p>These tools write files. No upload, no post, no push. What leaves an account is your decision, per action.</p>")}`)}

${section("open", "08 · Still open", "Still open",
`${deflist(d.not_built.map((n) => [n.what, esc(n.detail)]))}
<p class="np np--top">This page is written, not scanned. Change a tool, change
<code>datasets/system.json</code>, rebuild.</p>`)}

</div></main>
</div>
${AUDIT}
</body>
</html>`;

const mine = AUDIT ? html.replace(AUDIT, "") : html;
const bad = [...new Set([...mine.matchAll(/class="([^"]+)"/g)].flatMap((m) => m[1].split(/\s+/)).filter(Boolean))]
  .filter((c) => !DEFINED.has(c)).sort();
if (bad.length) { console.error("Classes the parent sheet does not define:\n  " + bad.join(", ")); process.exit(1); }

const out = join(HERE, "system.html");
writeFileSync(out, html, "utf8");
const words = html.replace(/<(style|script)[\s\S]*?<\/\1>/g, " ").replace(/<[^>]+>/g, " ").split(/\s+/).filter(Boolean).length;
console.log("wrote  " + out + "  " + statSync(out).size.toLocaleString() + " bytes");
console.log("style  " + STYLE.length + " bytes from " + basename(styleFrom) + ", sha " + STYLE_HASH.slice(0, 12));
console.log("shape  " + (html.match(/class="section"/g) || []).length + " sections, " +
  (html.match(/class="concept"/g) || []).length + " concepts, " +
  (html.match(/class="defrow"/g) || []).length + " deflist rows, " +
  (html.match(/class="step"/g) || []).length + " steps");
console.log("words  " + words + " visible, against 960 in the reference");
