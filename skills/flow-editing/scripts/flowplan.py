#!/usr/bin/env python3
"""flowplan.py plan.json | --selftest : print the shot table of a flow edit and check it. Stdlib only.

plan.json: {"fps": 24, "look": "furys-chain|furys-still|izxa-light|anime-package", "no_whoosh": false, "serious": false,
 "beats": [0, 13, ...] (frames, optional), "end": 480,
 "shots": [{"id":"S01","f":0,"block":"A","carrier":"whip","eye":"red tail light, right third","out":3,"in":5,"why":"...", "sfx":""}],
 "treat": [{"f":51,"kind":"black","n":1}]}
f = first frame of the shot. carrier/eye/out/in describe the join INTO this shot (the first shot needs none).
out = frames leaving the previous shot, in = frames settling. Carriers: see CARRIERS. Exit 1 on any FAIL."""
import json, sys, statistics as st
CARRIERS = {"whip","match","black","reveal","light","flash","slit","cover","tiles","still","dissolve","hue","strobe","jump","panel"}
STILL = {"still","jump"}
BAN = {"bulge","fisheye"}
FLASHY = {"white","black","negative","threshold","solid","strobe","invert"}
def check(p):
    fps, look, S = p["fps"], p.get("look",""), sorted(p["shots"], key=lambda s: s["f"]); out = []
    F = lambda lv, s, m: out.append((lv, s, m))
    ends = [s["f"] for s in S[1:]] + [p["end"]]; L = [e - s["f"] for s, e in zip(S, ends)]
    joins = S[1:]
    for s in joins:
        c = s.get("carrier","")
        if c not in CARRIERS: F("FAIL", s, "carrier '%s' is not one of the list" % c)
        if any(b in (c + " " + s.get("why","")).lower() for b in BAN): F("FAIL", s, "banned effect")
        if not s.get("eye"): F("FAIL", s, "what does the eye hold from A to B? (eye is empty)")
        o, i = s.get("out",0), s.get("in",0)
        if c in STILL or c in ("black","strobe","flash"): pass
        elif c in ("whip","cover") and not (1 <= o <= 6 and 3 <= i <= 9): F("WARN", s, "out %d / in %d, measured 2-4 / 4-6" % (o, i))
        if i and o > i and c in ("whip","cover","match","slit"): F("WARN", s, "leaves slower than it lands (out %d > in %d)" % (o, i))
        if "whoosh" in s.get("sfx","").lower() and p.get("no_whoosh"): F("FAIL", s, "this job allows no whooshes")
        if p.get("serious") and c in ("flash","strobe"): F("FAIL", s, "flash in a serious piece")
    for x, y in zip(joins, joins[1:]):
        if x.get("carrier") not in STILL and y["f"] - x["f"] < x.get("in",0) + y.get("out",0): F("FAIL", y, "moves overlap: %d f between cuts, %d needed" % (y["f"] - x["f"], x.get("in",0) + y.get("out",0)))
    fx = [s["carrier"] for s in joins if s.get("carrier") not in STILL]
    if len(fx) >= 6:
        top = max(set(fx), key=fx.count)
        if fx.count(top) / len(fx) > .6: F("WARN", None, "%d of %d joins are '%s' (one transition for everything)" % (fx.count(top), len(fx), top))
    blocks = {}
    for s in joins: blocks.setdefault(s.get("block","?"), set()).add(s.get("carrier"))
    for b, c in blocks.items():
        c = c - STILL - {"black"}
        if len(c) > 6: F("WARN", None, "block %s uses %d carriers (%s): no family" % (b, len(c), ", ".join(sorted(c))))
    med = st.median(L) if L else 0
    lo, hi = (9, 15) if look != "furys-still" else (10, 20)
    if len(L) > 5 and not lo * fps / 24 <= med <= hi * fps / 24 * 1.35: F("WARN", None, "median shot %.0f f, references %d-%d f" % (med, lo, hi))
    busy = 0; worst = 0
    for n in L:
        busy = 0 if n >= 15 * fps / 24 else busy + 1; worst = max(worst, busy)
    if worst > 7: F("WARN", None, "%d busy shots in a row without a hold of 15 f or more" % worst)
    T = sorted(p.get("treat", []), key=lambda t: t["f"])
    for t in T:
        if t.get("n",1) > 2 and t["kind"] != "black": F("WARN", None, "treatment f%d lasts %d f (1 f is the unit)" % (t["f"], t["n"]))
    for a, b in zip(T, T[1:]):
        if b["f"] - a["f"] <= 2 and a["kind"] == b["kind"]: F("FAIL", None, "same treatment twice at f%d" % b["f"])
    run = 1
    for a, b in zip(T, T[1:]):
        run = run + 1 if b["f"] - (a["f"] + a.get("n",1) - 1) <= 1 else 1
        if run == 5: F("WARN", None, "5 treatment frames in a row at f%d (max 4)" % b["f"])
    # every treatment run that has to be read as a flash: count, 1 s window
    fl = sorted([t["f"] for t in T if t["kind"] in FLASHY] + [s["f"] for s in joins if s.get("carrier") in ("flash","strobe")])
    for i in range(len(fl)):
        n = sum(1 for x in fl[i:] if x - fl[i] < fps)
        if n > 3: F("WARN", None, "%d flashes within 1 s from f%d: photosensitivity, warn the viewer or thin them out" % (n, fl[i])); break
    if p.get("serious") and any(t["kind"] in ("negative","invert","white") for t in T): F("FAIL", None, "negative or white frames in a serious piece")
    if p.get("beats") and joins:
        B = p["beats"]; on = sum(1 for s in joins if min(abs(b - s["f"]) for b in B) <= 1.5) / len(joins)
        if on > .8 and look != "furys-still": F("WARN", None, "%d %% of cuts on the beat: references 30-60 %%, use onsets, vocals and picture" % round(100 * on))
    if len(joins) > 4 and not any(s.get("carrier") in ("reveal","light","black") for s in joins): F("WARN", None, "no light carrier at all (reveal, light or black)")
    return S, L, out
def selftest():
    s = lambda f, c="whip", **k: dict({"id": "S%d" % f, "f": f, "block": "A", "carrier": c, "eye": "lamp", "out": 3, "in": 5}, **k)
    P = lambda *a, **k: dict({"fps": 24, "look": "furys-chain", "end": 60, "shots": [{"id": "S0", "f": 0}] + list(a)}, **k)
    m = lambda p: " | ".join(x[2] for x in check(p)[2]); fails = lambda p: [x for x in check(p)[2] if x[0] == "FAIL"]
    assert m(P(s(13), s(30, "black"))) == "", m(P(s(13), s(30, "black")))
    assert "not one of" in m(P(s(13, "sparkle"))); assert "eye is empty" in m(P(s(13, eye="")))
    assert "overlap" in m(P(s(13), s(18))); assert "leaves slower" in m(P(s(13, out=6, **{"in": 4})))
    assert "banned" in m(P(s(13, why="fisheye pop"))); assert "no whooshes" in m(P(s(13, sfx="whoosh"), no_whoosh=True))
    assert "twice" in m(P(s(13), treat=[{"f": 20, "kind": "negative"}, {"f": 21, "kind": "negative"}]))
    assert "photosens" in m(P(s(13), treat=[{"f": f, "kind": "white"} for f in (20, 25, 30, 35)]))
    assert "serious" in m(P(s(13, "flash"), serious=True)); assert not fails(P(s(13), s(30, "reveal")))
    q = P(*[s(12 * i) for i in range(1, 10)], end=125); assert "one transition" in m(q) and "no light carrier" in m(q) and "busy shots" in m(q)
    assert "on the beat" in m(P(s(13), s(26, "reveal"), beats=[0, 13, 26, 39])); print("selftest ok")
def main():
    if "--selftest" in sys.argv: return selftest()
    p = json.load(open(sys.argv[1])); S, L, out = check(p)
    print("| f | t | len | shot | block | carrier | eye holds | out>in | sfx | why |\n|---|---|---|---|---|---|---|---|---|---|")
    for s, n in zip(S, L): print("| %d | %.2f | %d | %s | %s | %s | %s | %s>%s | %s | %s |" % (s["f"], s["f"] / p["fps"], n, s["id"], s.get("block",""), s.get("carrier","-"), s.get("eye","-"), s.get("out","-"), s.get("in","-"), s.get("sfx",""), s.get("why","")))
    for lv, s, m in out: print("%s %s: %s" % (lv, s["id"] + " f%d" % s["f"] if s else "plan", m))
    print("%d FAIL, %d WARN" % (sum(o[0] == "FAIL" for o in out), sum(o[0] == "WARN" for o in out))); sys.exit(any(o[0] == "FAIL" for o in out))
if __name__ == "__main__": main()
