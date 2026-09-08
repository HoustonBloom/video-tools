"""
Measure a finished Short against the things eyes are bad at.

Watching a clip tells you whether you like it. It does not tell you the true
peak is at the clipping ceiling, or that the last word is buried 17 dB down, or
that the caption sits under the title bar. Those get measured.

Usage:
    python verify_short.py OUT.mp4 [--json]
"""

import argparse
import json
import re
import subprocess
import sys

SAFE_BOTTOM = 1660          # nothing readable below this, of 1920
TARGET_LUFS = -14.0
TARGET_TP = -1.5
LUFS_TOL = 1.0
MAX_SHORT_SECONDS = 180.0
TAIL_MIN = 0.30             # clean air after the last word
TAIL_MAX = 1.20


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path):
    p = sh(["ffprobe", "-v", "error", "-show_streams", "-show_format",
            "-of", "json", path])
    if p.returncode != 0:
        sys.exit(f"cannot probe {path}\n{p.stderr}")
    d = json.loads(p.stdout)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    return d, v, a


def loudness(path):
    p = sh(["ffmpeg", "-hide_banner", "-nostats", "-i", path,
            "-af", "loudnorm=I=-14:TP=-1.5:print_format=json",
            "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr, re.S)
    if not m:
        return None
    j = json.loads(m.group(0))
    return {"lufs": float(j["input_i"]), "tp": float(j["input_tp"]),
            "lra": float(j["input_lra"])}


def tail_silence(path, dur):
    """
    Length of the landing: the quiet run at the end of the clip.

    Measured relative to the clip's own speech level, not against an absolute
    floor. After the delivery chain lifts everything to -14 LUFS the room tone
    never falls below -50 dBFS, so an absolute test reports 0.00s on a clip
    that lands perfectly well, and only passes on manufactured digital silence.
    """
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000",
         "-f", "s16le", "-"], capture_output=True)
    import array, math
    raw = array.array("h")
    raw.frombytes(p.stdout[:len(p.stdout) // 2 * 2])
    if not len(raw):
        return 0.0
    hop = 320                                    # 20ms
    n = len(raw) // hop
    db = []
    for i in range(n):
        chunk = raw[i * hop:(i + 1) * hop]
        rms = math.sqrt(sum(v * v for v in chunk) / hop) / 32768.0
        db.append(20 * math.log10(rms + 1e-9))
    speech = sorted(db)[int(n * 0.9)]            # the clip's own loud level
    thr = speech - 22.0
    i = n
    while i > 0 and db[i - 1] < thr:
        i -= 1
    return round((n - i) * 0.02, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    d, v, aud = probe(a.video)
    w, h = int(v["width"]), int(v["height"])
    dur = float(d["format"]["duration"])
    checks = []

    def check(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    check("vertical", h >= w, f"{w}x{h}, aspect {w/h:.3f}")
    check("shorts eligible", dur <= MAX_SHORT_SECONDS and h >= w,
          f"{dur:.2f}s against a {MAX_SHORT_SECONDS:.0f}s ceiling")
    check("canvas 1080x1920", (w, h) == (1080, 1920), f"{w}x{h}")
    check("safe bottom clear", h == 1920,
          f"readable content must end by y={SAFE_BOTTOM}; not measured from pixels, "
          f"confirm on the proof frame")

    if aud is None:
        check("audio present", False, "no audio stream")
    else:
        L = loudness(a.video)
        if L:
            check("loudness", abs(L["lufs"] - TARGET_LUFS) <= LUFS_TOL,
                  f"{L['lufs']:.2f} LUFS against {TARGET_LUFS:.1f} +/- {LUFS_TOL}")
            check("true peak", L["tp"] <= TARGET_TP + 0.3,
                  f"{L['tp']:.2f} dBTP against a {TARGET_TP:.1f} ceiling")
            check("loudness range", L["lra"] <= 12.0, f"{L['lra']:.1f} LU")
        t = tail_silence(a.video, dur)
        check("landing", TAIL_MIN <= t <= TAIL_MAX,
              f"{t:.2f}s of air after the last sound, want {TAIL_MIN} to {TAIL_MAX}")

    failed = [c for c in checks if not c["ok"]]
    if a.json:
        print(json.dumps({"video": a.video, "checks": checks,
                          "passed": not failed}, indent=2))
    else:
        for c in checks:
            print(f"  {'ok  ' if c['ok'] else 'FAIL'}  {c['check']:20s} {c['detail']}")
        print(f"\n{len(checks) - len(failed)}/{len(checks)} passed")
        print("\nNot measured here, and still required:\n"
              "  re-transcribe and compare against the captions, which is how\n"
              "  clipped consonants at splices get caught\n"
              "  look at a proof frame for safe-area and crop aim")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
