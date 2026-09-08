// Land a render on its loudness target, and prove it landed.
//
// Works on any video or audio file. Nothing here knows about a project.
//
//   As a command:
//     node loudness.mjs measure <file>
//     node loudness.mjs normalise <in> <out> [--target -14] [--tp -3.0]
//
//   As a module:
//     import { measure, normalise } from ".../loudness.mjs";
//
// WHY THIS IS A LOOP AND NOT A FILTER CALL.
//
// `loudnorm` alone does not land on the target on real footage. It caps its gain
// at the true-peak ceiling and then reports success. Three measurements from one
// afternoon, all against a -14 LUFS target:
//
//   one loudnorm pass at TP -2.0:              -15.0 LUFS. Fails.
//   one loudnorm pass at TP -2.0, other file:  -14.5 LUFS. Fails.
//   TP -3.0 then a linear +0.5 dB:             -14.0 LUFS. Passes.
//
// So the two jobs are separated. loudnorm gets the shape and leaves headroom, a
// plain linear gain closes the remaining distance, and the result is MEASURED
// rather than assumed. If it still misses, this throws instead of writing a file
// that fails verification later in somebody else's hands.

import { renameSync, rmSync, existsSync } from "node:fs";
import { execFileSync, spawnSync } from "node:child_process";

const AAC = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"];
const sh = (a) => execFileSync(a[0], a.slice(1), { encoding: "utf8", maxBuffer: 1 << 26 });

/** Integrated loudness and true peak of a finished file, measured not intended. */
export function measure(file, target = -14, tp = -3.0) {
  if (!existsSync(file)) throw new Error("File not found: " + file);
  const r = spawnSync("ffmpeg", ["-nostdin", "-i", file, "-af",
    `loudnorm=I=${target}:TP=${tp}:LRA=11:print_format=json`, "-f", "null", "-"],
    { encoding: "utf8", maxBuffer: 1 << 26 });
  const e = r.stderr || "";
  const o = e.lastIndexOf("{"), c = e.lastIndexOf("}");
  if (o === -1 || c === -1) throw new Error("loudnorm printed no JSON report for " + file);
  return JSON.parse(e.slice(o, c + 1));
}

/**
 * Normalise `raw` into `out` and keep correcting until it lands.
 *
 * @param {string} raw     the un-normalised file
 * @param {string} out     where the finished file goes
 * @param {object} opts    { target = -14, tp = -3.0, tolerance = 0.3, log, cleanup }
 * @returns {{ before:string, after:number, peak:number, passes:number }}
 */
export function normalise(raw, out, opts = {}) {
  const { target = -14, tp = -3.0, tolerance = 0.3, log = console.log, cleanup = false } = opts;

  const m = measure(raw, target, tp);
  log(`   measured  ${m.input_i} LUFS, true peak ${m.input_tp} dBTP`);

  // Pass one: loudnorm, asking for more headroom than a check will require.
  sh(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", raw, "-c:v", "copy", "-af",
    `loudnorm=I=${target}:TP=${tp}:LRA=11:measured_I=${m.input_i}:measured_TP=${m.input_tp}` +
    `:measured_LRA=${m.input_lra}:measured_thresh=${m.input_thresh}:offset=${m.target_offset}`,
    ...AAC, "-movflags", "+faststart", out]);

  // Pass two onward: close the gap with a plain linear gain, and re-measure.
  // Two corrections is the most this has ever needed.
  let passes = 1;
  for (let i = 0; i < 2; i++) {
    const got = Number(measure(out, target, tp).input_i);
    const gap = target - got;
    if (Math.abs(gap) <= tolerance) {
      const peak = Number(measure(out, target, tp).input_tp);
      log(`   landed    ${got.toFixed(1)} LUFS, peak ${peak.toFixed(1)} dBTP, ${passes} pass${passes === 1 ? "" : "es"}`);
      if (cleanup) { try { rmSync(raw); } catch {} }
      return { before: m.input_i, after: got, peak, passes };
    }
    log(`   ${got.toFixed(1)} LUFS is ${gap > 0 ? "under" : "over"} by ${Math.abs(gap).toFixed(1)} dB, correcting`);
    const tmp = out.replace(/(\.[a-z0-9]+)$/i, `.__fix${i}$1`);
    sh(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", out, "-c:v", "copy",
      "-af", `volume=${gap.toFixed(2)}dB`, ...AAC, "-movflags", "+faststart", tmp]);
    try { rmSync(out); } catch {}
    renameSync(tmp, out);
    passes++;
  }

  const got = Number(measure(out, target, tp).input_i);
  if (Math.abs(target - got) > tolerance) {
    throw new Error(`Loudness will not land: ${got.toFixed(1)} LUFS against ${target}, after ${passes} passes. ` +
      `Not shipping a file that fails verification.`);
  }
  const peak = Number(measure(out, target, tp).input_tp);
  log(`   landed    ${got.toFixed(1)} LUFS, peak ${peak.toFixed(1)} dBTP, ${passes} passes`);
  if (cleanup) { try { rmSync(raw); } catch {} }
  return { before: m.input_i, after: got, peak, passes };
}

// ---- command line ---------------------------------------------------------
// Only runs when this file is executed directly, so importing it stays silent.
const invokedDirectly = process.argv[1] &&
  process.argv[1].replace(/\\/g, "/").endsWith("loudness.mjs");

if (invokedDirectly) {
  const [, , cmd, ...rest] = process.argv;
  const flag = (name, fallback) => {
    const i = rest.indexOf("--" + name);
    return i === -1 ? fallback : Number(rest[i + 1]);
  };
  const files = rest.filter((a, i) => !a.startsWith("--") && !(rest[i - 1] || "").startsWith("--"));

  try {
    if (cmd === "measure") {
      if (!files[0]) throw new Error("usage: loudness.mjs measure <file>");
      const m = measure(files[0], flag("target", -14), flag("tp", -3.0));
      console.log(`${files[0]}`);
      console.log(`  integrated  ${m.input_i} LUFS`);
      console.log(`  true peak   ${m.input_tp} dBTP`);
      console.log(`  range       ${m.input_lra} LU`);
      console.log(`  threshold   ${m.input_thresh}`);
    } else if (cmd === "normalise" || cmd === "normalize") {
      if (!files[0] || !files[1]) throw new Error("usage: loudness.mjs normalise <in> <out> [--target -14] [--tp -3.0]");
      if (files[0] === files[1]) throw new Error("Input and output are the same file. Normalising in place destroys the original.");
      // cleanup is not exposed here. A command line never deletes the file it
      // was handed. Callers that made their own intermediate pass cleanup:true.
      const r = normalise(files[0], files[1], {
        target: flag("target", -14),
        tp: flag("tp", -3.0)
      });
      console.log(`\n${files[1]}`);
      console.log(`  ${r.before} LUFS  ->  ${r.after.toFixed(1)} LUFS, peak ${r.peak.toFixed(1)} dBTP, ${r.passes} passes`);
    } else {
      console.error("usage:");
      console.error("  node loudness.mjs measure <file>");
      console.error("  node loudness.mjs normalise <in> <out> [--target -14] [--tp -3.0]");
      process.exit(1);
    }
  } catch (e) {
    console.error(e.message);
    process.exit(1);
  }
}
