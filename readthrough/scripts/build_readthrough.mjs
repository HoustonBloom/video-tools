// moments.json + segments.json -> the readthrough page.
//
//   node build_readthrough.mjs FOLDER [--out readthrough.html] [--title "..."]
//
// THE OBJECTIVE IS THIS FILE. Everything before it writes JSON so a person can
// check it. A run that produces moments.json and stops has not finished.
//
// THE SHAPE IS THE CUT-PROPOSALS PAGE. A show timeline with sections cut out
// showing where the featured parts lived, and that is this page's shape: stat cards, the show as a timeline with every segment a
// proportional block, the segment list, the guest and the featured founders
// as their own section with a frame and their words, then the ranked cards
// with a cut prompt each. Its timeline and founder styles are vendored beside
// this file as cut-proposals.template.css; the First Look sheet still carries
// the hero, the stat cards, the ranked cards and the final call.
//
// TWO FILES, TWO READS. moments.json is the mechanical pass: phrases matched
// in captions, fast and the same every time. segments.json is the read: an
// agent going through the whole transcript against the checklist in SKILL.md
// and writing down who was up, when, and what they said. The first cannot
// find "Today, our guest speaker is [name]" unless somebody typed that phrase in
// beforehand; the second can. The page draws the timeline from segments.json
// when it exists. Without it the page still builds, from the mechanical
// stretches, and says at the top that the recording has not been read yet,
// with the prompt to paste.
//
// THE FILTERS. Every kind looked for sits at the top with its count, zeros
// included, because a zero on the page is a miss somebody can see and a zero
// in a JSON is not. Click one and the timeline marks and the moment list show
// only that kind.
//
// WHAT COMES FROM THE PICTURE. Slides on screen and screen-only runs are read
// from the stills manifests, never guessed: see graphicBlocks and shareRuns.
// A demo, as defined for these tools, is a full-screen share, and a run with
// nobody in shot that is not a still slide is the screen and nothing else. On
// one recording every such run was a capture. On a filmed talk the room
// camera zoomed onto the TV 21 times, which reads the same and is not a
// share. So the page says "screen only", which is what was measured, and the
// reader writes the demos into segments.json with who and what.
//
// It proposes; a person chooses. Every time here is a caption timing and
// locates a passage. A cut point comes off the waveform.

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { resolve, dirname, join, basename } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const folder = args.find((a) => !a.startsWith("--"));
const flag = (n) => { const i = args.indexOf("--" + n); return i === -1 ? null : args[i + 1]; };
if (!folder) { console.error("Usage: node build_readthrough.mjs FOLDER [--out readthrough.html] [--title \"...\"]"); process.exit(1); }

const root = resolve(folder);
const momPath = join(root, "moments.json");
if (!existsSync(momPath)) {
  console.error("No moments.json in " + root + "\nRun this first:\n  python find_moments.py CAPTIONS.vtt --out moments.json");
  process.exit(1);
}
const CSS = readFileSync(join(HERE, "first-look.template.css"), "utf8")
  + "\n" + readFileSync(join(HERE, "cut-proposals.template.css"), "utf8");

const readJson = (p) => existsSync(p) ? JSON.parse(readFileSync(p, "utf8")) : null;
const mom = JSON.parse(readFileSync(momPath, "utf8"));
const seg = readJson(join(root, "segments.json"));
const src = readJson(join(root, "source.json"));
const stretchStills = readJson(join(root, "turn-stills.json"));
const segmentStills = readJson(join(root, "segment-stills.json"));
const stillsByN = new Map((stretchStills?.turns ?? []).map((x) => [x.n, x]));
const stillsById = new Map((segmentStills?.turns ?? []).filter((x) => x.id).map((x) => [x.id, x]));

const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const hms = (s) => { s = Math.round(s); const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(x).padStart(2, "0")}` : `${m}:${String(x).padStart(2, "0")}`; };
const mins = (s) => `${Math.round(s / 60)} min`;
const embed = (f) => existsSync(f) ? "data:image/jpeg;base64," + readFileSync(f).toString("base64") : null;

const stretches = mom.stretches ?? [];
const moments = mom.moments ?? [];
const counts = mom.counts ?? {};
const total = seg?.runs_to_s ?? mom.runs_to_s ?? Math.max(...stretches.map((s) => s.out), 0);

const pretty = (s) => s.split(/[-_]+/).filter(Boolean).map((w) => /^e\d+$/i.test(w)
  ? "Episode " + w.slice(1) : w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
const title = flag("title") || seg?.title || src?.title || pretty(basename(root));

const kindLabel = { handoff: "Someone introduced", "self-intro": "Introduced themselves", "invite-intro": "Asked to introduce",
  "to-room": "Put to the room", sponsor: "Sponsor named", "what-this-is": "The recording describing itself", closing: "Closing",
  guest: "Guest speaker", featured: "Featured founder", demo: "Demo", round: "Round of the couch", questions: "Questions from the room",
  opening: "Opening", slides: "Slides on screen", share: "Screen only", mark: "Marked by the reader" };
const segKindLabel = { opening: "Opening", guest: "Guest speaker", featured: "Featured founder", round: "Round of the couch",
  questions: "Questions from the room", closing: "Closing", sponsor: "Sponsor", demo: "Demo" };

// ---- The picture: slides and screen shares, from every stills manifest, by time.
const MIN_RUN = 4, BLOCK_GAP = 120, NOBODY = 0.05, SHARE_RUN = 3;
// One sampling grid, not two. The stretch manifests cover the whole recording
// at one interval; the segment manifests sample the same footage at another,
// and merging the two grids read 10 screen shares where there were 4.
const manifests = (stretchStills?.turns ?? []).length ? (stretchStills?.turns ?? []) : (segmentStills?.turns ?? []);
const every = manifests.find((t) => t.sampled_every_s)?.sampled_every_s || 6;
const runsOf = (times, minRun) => {
  const runs = []; let cur = null;
  for (const x of [...new Set(times)].sort((a, b) => a - b)) {
    if (cur && x - cur.last <= every * 1.5) { cur.last = x; cur.n += 1; }
    else { if (cur) runs.push(cur); cur = { first: x, last: x, n: 1 }; }
  }
  if (cur) runs.push(cur);
  return runs.filter((r) => r.n >= minRun).map((r) => ({ in: r.first, out: r.last + every, n: r.n }));
};
const graphicTimes = manifests.flatMap((t) => t.graphics_at_s ?? []);
const graphicsRead = manifests.some((t) => Array.isArray(t.graphics_at_s));
const slideBlocks = (() => {
  const blocks = [];
  for (const r of runsOf(graphicTimes, MIN_RUN)) {
    const b = blocks[blocks.length - 1];
    if (b && r.in - b.out <= BLOCK_GAP) b.out = r.out; else blocks.push({ in: r.in, out: r.out });
  }
  return blocks;
})();
const samplesRead = manifests.some((t) => Array.isArray(t.samples));
const shareRuns = (() => {
  const graphic = new Set(graphicTimes.map((x) => Math.round(x)));
  const nobody = [];
  for (const t of manifests) {
    const f = t.samples_fields || ["t", "sharpness", "motion", "subject_frac"];
    const iT = f.indexOf("t"), iS = f.indexOf("subject_frac");
    for (const row of t.samples ?? []) if (row[iS] < NOBODY && !graphic.has(Math.round(row[iT]))) nobody.push(row[iT]);
  }
  return runsOf(nobody, SHARE_RUN);
})();
const within = (list, lo, hi) => list.filter((r) => r.in < hi && r.out > lo);

// ---- The spans the page is built on: segments when read, stretches when not.
const read = !!(seg && Array.isArray(seg.segments) && seg.segments.length);
const allCandidates = stretches.flatMap((s) => s.candidates ?? []);
const linesIn = (lo, hi) => allCandidates.filter((c) => c.at_s >= lo && c.at_s < hi).sort((a, b) => b.score - a.score || a.at_s - b.at_s);
const momentsIn = (lo, hi) => moments.filter((m) => m.at_s >= lo && m.at_s < hi);

const spans = read
  ? seg.segments.map((s, i) => ({
      id: s.id || "seg" + (i + 1), n: i + 1, kind: s.kind || "segment", title: s.title || s.id, who: s.who || null, company: s.company || null,
      in: s.in, out: s.out, what: s.what || "", quotes: s.quotes ?? [], marks: s.marks ?? [], order: s.order || null,
      lines: linesIn(s.in, s.out), still: stillsById.get(s.id) || null }))
  : stretches.map((s) => ({
      id: "s" + s.n, n: s.n, kind: "stretch",
      title: s.opened_by ? (s.opened_by.name_read || s.opened_by.label) : (stretches.length > 1 && s.n === 1 ? "The opening" : "The whole recording"),
      who: s.opened_by?.name_read || null, company: null, in: s.in, out: s.out, what: s.opened_by ? s.opened_by.said : "",
      quotes: [], marks: [], order: null, lines: s.candidates ?? [], still: stillsByN.get(s.n) || null }));

const people = spans.filter((s) => s.kind === "featured" || s.kind === "guest");
const demos = read ? (seg.demos ?? []) : [];
const linesTotal = spans.reduce((n, s) => n + s.lines.length, 0);

// ---- Every moment, from both reads, in one list for the filters.
const allMoments = [
  ...moments.map((m) => ({ at: m.at_s, kind: m.kind, label: kindLabel[m.kind] || m.kind, text: m.said, who: m.name_read })),
  ...people.map((s) => ({ at: s.in, kind: s.kind, label: kindLabel[s.kind], text: `${s.who}${s.company ? ", " + s.company : ""}: ${s.title.toLowerCase()}`, who: s.who })),
  ...demos.map((d) => ({ at: d.in, kind: "demo", label: "Demo", text: `${d.who}: ${d.what} (${hms(d.in)} to ${hms(d.out)})`, who: d.who })),
  ...spans.flatMap((s) => s.marks.map((m) => ({ at: m.at, kind: "mark", label: "Marked by the reader", text: m.what, who: null }))),
  ...(read && seg.sponsor && !moments.some((m) => m.kind === "sponsor") ? [{ at: seg.sponsor.at, kind: "sponsor", label: "Sponsor named", text: seg.sponsor.said, who: seg.sponsor.who }] : []),
  ...slideBlocks.map((b) => ({ at: b.in, kind: "slides", label: "Slides on screen", text: `${hms(b.in)} to ${hms(b.out)}, from the picture`, who: null })),
  ...shareRuns.map((r) => ({ at: r.in, kind: "share", label: "Screen only", text: `${hms(r.in)} to ${hms(r.out)}, nobody in shot and not a still slide, from the picture`, who: null })),
].sort((a, b) => a.at - b.at);

// The checklist: every caption kind in registry order with its count (zeros
// included), then what the read adds, then what the picture adds.
const filters = [
  ...Object.keys(counts).map((k) => ({ kind: k, label: kindLabel[k] || k, n: counts[k] })),
  { kind: "guest", label: "Guest speaker", n: allMoments.filter((m) => m.kind === "guest").length, from: "read" },
  { kind: "featured", label: "Featured founder", n: allMoments.filter((m) => m.kind === "featured").length, from: "read" },
  { kind: "demo", label: "Demo", n: demos.length, from: "read" },
  { kind: "mark", label: "Marked by the reader", n: allMoments.filter((m) => m.kind === "mark").length, from: "read" },
  { kind: "slides", label: "Slides on screen", n: graphicsRead ? slideBlocks.length : null, from: "picture" },
  { kind: "share", label: "Screen only", n: samplesRead ? shareRuns.length : null, from: "picture" },
];

// ---- Pieces
const stat = (n, label, tint) => `<div class="stat ${tint}"><div class="num">${esc(n)}</div><div class="label">${esc(label)}</div></div>`;
const pct = (s) => (100 * s / total).toFixed(2) + "%";
const segClass = (s) => s.kind === "featured" ? "featured" : s.kind === "guest" ? "guest" : s.lines.length ? "has" : "";
const stillSrc = (s) => s.still?.still ? embed(join(root, s.still.still)) : null;

const cutPrompt = (s) => {
  const q = s.quotes[0] || (s.lines[0] ? { at: s.lines[0].at_s, text: s.lines[0].text } : null);
  const name = s.who ? `${s.who}${s.company ? " of " + s.company : ""}` : s.title;
  return `Cut me a Short from ${name}'s segment of ${title}, ${hms(s.in)} to ${hms(s.out)}. `
    + (q ? `Open on the line at ${hms(q.at)}: "${q.text}". ` : "")
    + `Read video-tools/shorts/SKILL.md first. Write the plan and the render into a renders folder inside this recording's folder in the inbox. Show me the proof frame before rendering.`;
};

const timeline = `
  <div class="tl-track" role="img" aria-label="The recording from start to end, one block per segment">
    ${spans.map((s) => `<a class="tl-seg ${segClass(s)}" href="#${esc(s.id)}" style="left:${pct(s.in)};width:${pct(s.out - s.in)}" title="${esc(s.title)}${s.who ? " · " + esc(s.who) : ""} · ${hms(s.in)} to ${hms(s.out)}"><span>${(s.kind === "featured" || s.kind === "guest") && s.who ? esc(s.who) : s.out - s.in > total / 4 ? esc(s.title) : s.n}</span></a>`).join("")}
  </div>
  <div class="tl-marks" aria-hidden="true">
    ${allMoments.filter((m) => m.kind !== "slides" && m.kind !== "share").map((m) => `<i class="tl-mark ${m.kind === "demo" ? "demo" : m.kind === "sponsor" ? "sponsor" : ""}" data-kind="${esc(m.kind)}" style="left:${pct(m.at)}${m.kind === "demo" ? ";width:" + pct(Math.max(demos.find((d) => d.in === m.at)?.out - m.at, 20)) : ""}" title="${esc(m.label)} · ${hms(m.at)}"></i>`).join("")}
  </div>
  <div class="tl-scale"><span>0:00</span><span>${hms(total)}</span></div>
  <p class="tl-key">${read
    ? `<i class="k-guest"></i> guest <i class="k-featured"></i> featured founder <i class="k-has"></i> a segment with lines that passed the test <i class="k-mark"></i> a moment <i class="k-demo"></i> a demo`
    : `<i class="k-has"></i> a stretch with lines that passed the test <i class="k-mark"></i> a moment. Stretches are the mechanical pass; read the recording to get segments.`}</p>`;

const links = `<div class="links">${spans.map((s) => `
  <a class="link" href="#${esc(s.id)}">
    <span class="link-name">${esc(s.title)}${s.who ? " · " + esc(s.who) : ""}</span>
    <span class="link-meta">${esc(hms(s.in))} · ${esc(hms(s.out - s.in))} · ${s.lines.length} line${s.lines.length === 1 ? "" : "s"} · ${momentsIn(s.in, s.out).length + s.marks.length} moments</span>
    <span class="link-desc">${esc(s.what)}</span>
  </a>`).join("")}</div>`;

const person = (s) => {
  const pic = stillSrc(s);
  const tints = ["moss", "sky", "butter", "lav"];
  return `<article class="founder" id="${esc(s.id)}-person">
  <div class="founder-top">
    ${pic ? `<img src="${pic}" alt="A frame from ${esc(s.who)}'s segment">` : `<div class="chip">no frame picked</div>`}
    <div>
      <p class="kicker-sm">${esc(s.title)}${s.order ? "" : ""} · ${hms(s.in)} to ${hms(s.out)} · ${mins(s.out - s.in)}</p>
      <h3>${esc(s.who)}${s.company ? ` <em>${esc(s.company)}</em>` : ""}</h3>
      <p class="lede-sm">${esc(s.what)}</p>
    </div>
  </div>
  ${s.quotes.length ? `<div class="split">${s.quotes.map((q, i) => `<div class="qcard ${tints[i % 4]}"><h4>${i === 0 ? "In their words" : "At " + hms(q.at)}</h4>
    <figure class="q"><blockquote>${esc(q.text)}</blockquote><figcaption>${hms(q.at)}</figcaption></figure></div>`).join("")}</div>` : ""}
  ${s.marks.length ? `<ul class="marks">${s.marks.map((m) => `<li><span class="at">${hms(m.at)}</span>${esc(m.what)}</li>`).join("")}</ul>` : ""}
  ${within(demos, s.in, s.out).map((d) => `<p class="marks"><span class="at">${hms(d.in)} to ${hms(d.out)}</span>Demo: ${esc(d.what)}${within(shareRuns, d.in, d.out).length ? " · seen in the picture: nobody in shot there" : samplesRead ? " · not seen in the picture: somebody was in shot" : ""}</p>`).join("")}
  <p style="margin-top:14px"><button class="view-btn" type="button" data-prompt="${esc(cutPrompt(s))}">Copy the cut prompt for ${esc(s.who)} <span class="arrow" aria-hidden="true">→</span></button></p>
</article>`;
};

const card = (s, rank) => {
  const top = rank === 0 && s.lines.length > 0;
  const lead = s.lines[0];
  const pic = stillSrc(s);
  const kinds = [...new Set(momentsIn(s.in, s.out).map((m) => kindLabel[m.kind] || m.kind))];
  const slides = within(slideBlocks, s.in, s.out), shares = within(shareRuns, s.in, s.out);
  const preview = pic
    ? `<img src="${pic}" alt="A frame chosen from this segment">`
    : `<svg viewBox="0 0 400 300" preserveAspectRatio="xMidYMid meet"><rect width="400" height="300" fill="#1f1d1a"/><text x="200" y="158" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="14" fill="#f5d88e">no frame picked</text></svg>`;
  return `<section class="lens${top ? " top-ranked" : ""}" id="${esc(s.id)}">
  <div class="wrap">
    <div class="lens-grid">
      <div class="preview">${preview}</div>
      <div class="lens-body">
        <div class="lens-meta">
          <span class="badge ${top ? "best-fit" : s.lines.length ? "ready" : "soon"}">${top ? "★ Best fit" : s.lines.length ? "Ready" : "Thin"}</span>
          <span>${esc(read ? segKindLabel[s.kind] || s.title : "Stretch " + s.n)} · ${hms(s.in)} to ${hms(s.out)} · ${mins(s.out - s.in)}</span>
          ${slides.length ? `<span class="plan-flag">Slides on screen</span>` : ""}
          ${shares.length ? `<span class="plan-flag">Screen only</span>` : ""}
        </div>
        <h2>${esc((s.kind === "featured" || s.kind === "guest" || s.kind === "stretch") && s.who ? `${s.who}${s.company ? ", " + s.company : ""}` : s.title)}</h2>
        <p class="tagline">${esc(s.kind === "featured" || s.kind === "guest" || !s.who ? s.what : s.who + ". " + s.what)}</p>
        <div class="what"><div class="label">What is in it</div>
          <p>${s.lines.length} line${s.lines.length === 1 ? "" : "s"} passed the test${kinds.length ? "; " + esc(kinds.join(", ").toLowerCase()) : ""}${slides.length ? `; slides on screen ${slides.map((b) => `${hms(b.in)} to ${hms(b.out)}`).join(", ")}` : ""}${shares.length ? `; screen only, nobody in shot, ${shares.length > 4 ? shares.length + " runs from " + hms(shares[0].in) + " to " + hms(shares[shares.length - 1].out) : shares.map((r) => `${hms(r.in)} to ${hms(r.out)}`).join(", ")}` : ""}.</p></div>
        ${lead ? `<div class="why"><div class="label">Open on this</div><p>&ldquo;${esc(lead.text)}&rdquo; <span class="dim">${esc(lead.at)}</span></p></div>` : ""}
        ${top ? `<div class="winner-note">★ Best fit : the segment with the most lines that stand on their own.</div>` : ""}
        <button class="view-btn" type="button" data-prompt="${esc(cutPrompt(s))}">Copy the cut prompt <span class="arrow" aria-hidden="true">→</span></button>
      </div>
    </div>
  </div>
</section>`;
};

const ranked = [...spans].sort((a, b) => b.lines.length - a.lines.length || a.n - b.n);

const READ_PROMPT = `Read the whole transcript of this recording end to end, then write segments.json beside it in the readthrough-segments/v1 shape (see video-tools/readthrough/SKILL.md). For every segment give in, out, who, what, and the lines worth quoting with their times. Look for, and say when you find none of: the opening and who is introduced; a guest speaker; each featured founder and their company; a demo (who, in, out); the sponsor; the round of introductions with every name; questions from the room; the closing. Names are as heard unless known. Then rebuild: node scripts/build_readthrough.mjs .`;

const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Readthrough · ${esc(title)}</title>
<style>${CSS}</style>
</head>
<body class="cp">

<section class="hero">
  <div class="wrap">
    <span class="stamp">Readthrough · ${read ? "read " + esc(seg.read?.on || "") : "not yet read"}</span>
    <h1>What is in <span class="ink-accent">${esc(title)}</span>.</h1>
    <p class="sub">${read ? "The show as a timeline, who was up and when, what they said, and a prompt to cut from each part." : "The mechanical pass only: phrases matched in captions. The recording has not been read yet."}</p>
    <div class="meta">${esc(hms(total))} · ${spans.length} ${read ? "segments" : "stretches"} · ${allMoments.length} moments · ${linesTotal} lines proposed</div>
    <div class="stats">
      ${stat(people.length, "people featured", "butter")}
      ${stat(spans.length, read ? "segments" : "stretches", "sage")}
      ${stat(allMoments.length, "moments found", "sky")}
      ${stat(linesTotal, "lines worth cutting", "")}
    </div>
  </div>
</section>

${read ? "" : `<section class="suggested-intro"><div class="wrap"><div class="unread">
  <h3>This recording has not been read yet.</h3>
  <p>What is below came from matching phrases in the captions. It cannot find a guest speaker or a featured founder unless the host used a phrase it already knew. Paste this to your AI in the recording's folder:</p>
  <pre>${esc(READ_PROMPT)}</pre>
  <p style="margin-top:10px"><button class="view-btn" type="button" data-prompt="${esc(READ_PROMPT)}">Copy the read prompt <span class="arrow" aria-hidden="true">→</span></button></p>
</div></div></section>`}

<section class="suggested-intro">
  <div class="wrap">
    <div class="kicker">What we looked for</div>
    <h2>${filters.filter((f) => f.n).length} kinds found, ${filters.filter((f) => f.n === 0).length} looked for and absent${filters.some((f) => f.n === null) ? ", " + filters.filter((f) => f.n === null).length + " not read" : ""}.</h2>
    <div class="filters">
      ${filters.map((f) => `<button class="filter${f.n === 0 ? " zero" : ""}" type="button" data-kind="${esc(f.kind)}"${f.n === null ? " disabled" : ""}>${esc(f.label)}<b>${f.n === null ? "n/a" : f.n}</b></button>`).join("")}
    </div>
    <p class="filter-note">Click one to show only that kind on the timeline and in the list below; click it again for everything. A zero was looked for and not found. "n/a" means no stills manifest carried the numbers. A name is read from the sentence beside it, never a fact about who is speaking.</p>
  </div>
</section>

<section class="suggested-intro">
  <div class="wrap">
    <div class="kicker">The recording</div>
    <h2>Where everything lived.</h2>
    ${timeline}
    ${links}
  </div>
</section>

${people.length ? `<section class="suggested-intro">
  <div class="wrap">
    <div class="kicker">The people</div>
    <h2>${esc(people.map((p) => p.who).reduce((s, w, i, a) => i === 0 ? w : i === a.length - 1 ? s + " and " + w : s + ", " + w, ""))}.</h2>
    ${people.map(person).join("\n")}
  </div>
</section>` : ""}

<section class="suggested-intro">
  <div class="wrap">
    <div class="kicker">Every moment</div>
    <h2>${allMoments.length} moments, in order.</h2>
    <div class="moments" id="moments">
      ${allMoments.map((m) => `<div class="moment" data-kind="${esc(m.kind)}"><span class="at">${hms(m.at)}</span><span><span class="k">${esc(m.label)}</span>${m.who ? `<strong>${esc(m.who)}</strong> · ` : ""}${esc(m.text)}</span></div>`).join("")}
    </div>
  </div>
</section>

<section class="suggested-intro">
  <div class="wrap">
    <div class="kicker">Suggested cuts</div>
    <h2>Every ${read ? "segment" : "stretch"}, ranked by lines that stand on their own.</h2>
  </div>
</section>
${ranked.map(card).join("\n")}

<section class="final">
  <div class="wrap">
    <div class="kicker">Ready when you are</div>
    <h2>Want the best-fit cut made right now?</h2>
    <p>Paste the top card's prompt into your AI in the video-tools folder. You get a plan to approve, a proof frame to look at, and then the render.</p>
    <a href="#" class="big-btn" id="produce-btn" data-prompt="${esc(ranked.length ? cutPrompt(ranked[0]) : "")}">Copy the best-fit prompt <span aria-hidden="true">→</span></a>
    <div class="or-note">or copy any card above</div>
  </div>
</section>

<div class="toast" id="toast" role="status" aria-live="polite"></div>
<script>
(function () {
  var toast = document.getElementById('toast');
  function show(msg) { toast.textContent = msg; toast.classList.add('show'); setTimeout(function () { toast.classList.remove('show'); }, 1800); }
  document.querySelectorAll('[data-prompt]').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var text = btn.getAttribute('data-prompt');
      if (!text) return;
      navigator.clipboard.writeText(text).then(function () { show('Prompt copied : paste into your AI'); },
        function () { show('Copy failed : select manually'); });
    });
  });
  var on = null;
  var chips = document.querySelectorAll('.filter[data-kind]');
  function apply() {
    chips.forEach(function (c) { c.classList.toggle('on', c.getAttribute('data-kind') === on); });
    document.querySelectorAll('.moment[data-kind]').forEach(function (m) { m.classList.toggle('hide', on !== null && m.getAttribute('data-kind') !== on); });
    document.querySelectorAll('.tl-mark[data-kind]').forEach(function (m) { m.classList.toggle('dim', on !== null && m.getAttribute('data-kind') !== on); });
  }
  chips.forEach(function (c) {
    c.addEventListener('click', function () { var k = c.getAttribute('data-kind'); on = (on === k) ? null : k; apply(); });
  });
})();
</script>
</body>
</html>
`;

const outPath = resolve(root, flag("out") || "readthrough.html");
writeFileSync(outPath, html);
console.log("wrote  " + outPath + "  " + html.length.toLocaleString() + " bytes");
console.log("shape  " + (read ? "read: " : "not read: ") + spans.length + (read ? " segments, " : " stretches, ") + people.length + " people, "
  + allMoments.length + " moments, " + linesTotal + " lines, "
  + (graphicsRead ? slideBlocks.length + " slide blocks" : "no slide read") + ", "
  + (samplesRead ? shareRuns.length + " screen-only runs" : "no screen-only read") + " from the picture");
