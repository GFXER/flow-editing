#!/usr/bin/env python3
"""flow_render.py plan.json out.mp4 [--scale 0.5] [--frames a:b]
Renders a flow edit (picture only, no sound) from a plan: matched anchors, exponential ramps, motion blur, light reveals,
light streaks from the footage itself, 1-frame treatments, one-colour grade, growing captions. numpy + opencv + Pillow + ffmpeg.

plan.json
 {"fps":24, "size":[1080,1920], "end":345, "clips":"path/to/clips", "accent":"red"|"none"|"all", "kicks":[72.7,...],
  "font":"optional.ttf", "shots":[...], "treat":[{"f":58,"kind":"black","n":2}], "captions":[[8,33,"WHITE"],[33,47,"WHITE OUTSIDE"]],
  "end_fade":[331,8]}
 shot: {"id":"S1","file":"a.mov","f":0,"t":4.2,"anc":[.5,.62],"at":[.5,.56],"z":[1,1.1],"sp":0.5,"mv":[vx,vy,roll,logzoom],
        "out":3,"in":5,"carrier":"whip","light":"reveal|hot|revealhot","flip":false,"accent":1,"gain":1,"lights_only":[start,end],
        "edge":"mirror|black","hide":[[t,x0,y0,x1,y1]]}
 f = first frame. t = source second at the middle of the shot. anc = the feature in the source (0-1), at = where it sits in the frame.
 sp = speed in the middle (ends are fast). mv = the move INTO this shot, in frame widths, degrees and log zoom.
 lights_only: how much of the picture is reduced to lights at the start and end of the shot (0-1).
 hide: tracked soft cover for plates or faces, box at source second t (0-1 coordinates).
 treat kinds: black negative crush threshold duotone solid edge rgb slit pop."""
import sys, os, json, math, shutil, argparse, subprocess, numpy as np, cv2
FF = os.environ.get('FFMPEG') or shutil.which('ffmpeg')
ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('out'); ap.add_argument('--scale', type=float, default=1.0); ap.add_argument('--frames')
A = ap.parse_args()
if not FF: sys.exit('ffmpeg not found: install it or set FFMPEG=/path/to/ffmpeg')
P = json.load(open(A.plan)); S = sorted(P['shots'], key=lambda s: s['f']); FPS = P['fps']; SC = A.scale
BASE = os.path.join(os.path.dirname(os.path.abspath(A.plan)), P.get('clips', '.')); W, H = P.get('size', [1080, 1920]); w, h = int(W * SC) // 2 * 2, int(H * SC) // 2 * 2
END = P['end']; rng = np.random.default_rng(7); ACC = P.get('accent', 'none'); KICK = P.get('kicks', [])
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); xx /= w; yy /= h
sm = lambda x, a, b: np.clip((x - a) / (b - a), 0, 1)
U = SC * W / 1080
def ends(i): return S[i + 1]['f'] if i + 1 < len(S) else END
def times(s, n):
    k = np.arange(n); sp = s.get('sp', .5); e = max(2.6, sp); v = sp + (e - sp) * (np.exp(-k / 1.1) + np.exp(-(n - 1 - k) / 1.1))
    t = np.cumsum(v / FPS); return s['t'] + t - t[n // 2]
DIS = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_FAST)
class Clip:
    def __init__(s, path, t0, t1, hide):
        c = cv2.VideoCapture(path); n = int(c.get(7)); s.fps = c.get(5)
        if n < 2 or not s.fps: sys.exit('cannot read ' + path)
        s.a = min(max(0, int(t0 * s.fps) - 1), n - 2); b = max(s.a + 1, min(n - 1, int(t1 * s.fps) + 2)); c.set(1, s.a); s.f = []
        for _ in range(s.a, b + 1):
            ok, im = c.read()
            if not ok: break
            s.f.append(im)
        if not s.f: sys.exit('no frames at %.2f s in %s' % (t0, path))
        if len(s.f) == 1: s.f *= 2
        s.H, s.W = s.f[0].shape[:2]
        for q in hide: s.cover(q)
    def cover(s, q):
        t, box = q[0], q[1:]; k = min(len(s.f) - 1, max(0, int(t * s.fps) - s.a)); r = [box[0] * s.W, box[1] * s.H, box[2] * s.W, box[3] * s.H]
        g = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in s.f]; pos = [None] * len(s.f)
        for order in (range(k, len(s.f)), range(k, -1, -1)):
            q_, prev = list(r), g[k]
            for i in order:
                if i != k:
                    x0, y0, x1, y1 = map(int, q_); m = np.zeros_like(prev); px = int(.25 * (x1 - x0) + 20); m[max(0, y0 - px):y1 + px, max(0, x0 - px):x1 + px] = 255
                    p = cv2.goodFeaturesToTrack(prev, 120, .005, 6, mask=m)
                    if p is not None and len(p) > 6:
                        nx, st, _ = cv2.calcOpticalFlowPyrLK(prev, g[i], p, None, winSize=(31, 31), maxLevel=4); ok = st.ravel() == 1
                        M = cv2.estimateAffinePartial2D(p[ok], nx[ok], ransacReprojThreshold=3)[0] if ok.sum() > 5 else None
                        if M is not None:
                            c = np.array([[q_[0], q_[1]], [q_[2], q_[3]], [q_[0], q_[3]], [q_[2], q_[1]]]) @ M[:, :2].T + M[:, 2]; q_ = [c[:, 0].min(), c[:, 1].min(), c[:, 0].max(), c[:, 1].max()]
                pos[i] = list(q_); prev = g[i]
        for i, p in enumerate(pos):
            x0, y0, x1, y1 = map(int, p); e = int(.06 * (x1 - x0) + 6); x0, x1, y0, y1 = max(0, x0 - e), min(s.W, x1 + e), max(0, y0 - e), min(s.H, y1 + e)
            if x1 - x0 < 4 or y1 - y0 < 4: continue
            im = s.f[i].copy(); sub = im[y0:y1, x0:x1]; bl = cv2.resize(cv2.resize(sub, (5, 3), interpolation=cv2.INTER_AREA), (sub.shape[1], sub.shape[0]), interpolation=cv2.INTER_CUBIC) * .42
            m = np.zeros(sub.shape[:2], np.float32); d = max(3, e // 2); m[d:-d, d:-d] = 1; m = cv2.GaussianBlur(m, (0, 0), d * .8)[..., None]; im[y0:y1, x0:x1] = (sub * (1 - m) + bl * m).astype(np.uint8); s.f[i] = im
    def at(s, t):
        x = np.clip(t * s.fps - s.a, 0, len(s.f) - 1.001); i = int(x); a = float(x - i)
        if a < .1: return s.f[i]
        if a > .9: return s.f[i + 1]
        P0, P1 = s.f[i], s.f[i + 1]; g0, g1 = [cv2.resize(cv2.cvtColor(z, cv2.COLOR_BGR2GRAY), None, fx=.4, fy=.4, interpolation=cv2.INTER_AREA) for z in (P0, P1)]
        fl = cv2.resize(DIS.calc(g0, g1, None), (s.W, s.H)) / .4; Y, X = np.mgrid[0:s.H, 0:s.W].astype(np.float32)
        p = cv2.remap(P0, X - a * fl[..., 0], Y - a * fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        q = cv2.remap(P1, X + (1 - a) * fl[..., 0], Y + (1 - a) * fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return cv2.addWeighted(p, 1 - a, q, a, 0)
def mv(s): return s.get('mv', [0, 0, 0, 0])
def mat(i, tau, c):
    s = S[i]; f0, f1 = s['f'], ends(i); u = np.clip((tau - f0) / max(1, f1 - f0), 0, 1); z0, z1 = s.get('z', [1, 1]); z = z0 + (z1 - z0) * u; dx = dy = ro = lz = 0.
    e = math.exp(-.74 * max(0, tau - f0) * (5 / max(3, s.get('in', 5)))); m = mv(s); dx -= m[0] * e; dy -= m[1] * e; ro -= m[2] * e; lz -= m[3] * e * .6
    if i + 1 < len(S):
        m = mv(S[i + 1]); o = S[i + 1].get('out', 3); k = max(0, (tau - (f1 - o - .5)) / (o + .5)); e = k ** 2.6 * .62; dx += m[0] * e; dy += m[1] * e; ro += m[2] * e; lz += m[3] * e
    ro += .35 * math.sin(tau * .21 + i); dx += .004 * math.sin(tau * .17 + i * 2); dy += .003 * math.cos(tau * .13 + i)
    for kf in KICK:
        if 0 <= tau - kf < 5: lz += .035 * math.exp(-.8 * (tau - kf))
    fit = max(w / c.W, h / c.H) * z * math.exp(lz); a = math.radians(ro); fx = -1 if s.get('flip') else 1; ca, sa = math.cos(a) * fit, math.sin(a) * fit
    M = np.array([[ca * fx, -sa, 0], [sa * fx, ca, 0]], np.float32); anc, at = s.get('anc', [.5, .5]), s.get('at', [.5, .5]); p = M[:, :2] @ np.array([anc[0] * c.W, anc[1] * c.H])
    M[0, 2] = (at[0] + dx) * w - p[0]; M[1, 2] = at[1] * h + dy * w - p[1]
    if abs(ro) < 3:
        x0, x1 = sorted((M[0, 2], M[0, 2] + ca * fx * c.W)); y0, y1 = sorted((M[1, 2], M[1, 2] + ca * c.H)); d = abs(dx) + abs(dy); k = 1 - min(1, (d - .02) / .05) if d > .02 else 1
        if x1 - x0 >= w: M[0, 2] += k * (max(0, w - x1) - max(0, x0))
        if y1 - y0 >= h: M[1, 2] += k * (max(0, h - y1) - max(0, y0))
    return M
def spot(s, flo=.14):
    at = s.get('at', [.5, .5]); rx, ry = (.78, .36) if h > w else (.42, .62); r = np.sqrt(((xx - at[0]) / rx) ** 2 + ((yy - at[1]) / ry) ** 2); return (flo + (1 - flo) * np.exp(-r ** 2.6))[..., None].astype(np.float32)
def grade(im, s, gain=1., black=0., ag=1.):
    d = np.clip(im, 0, 4) ** (1 / 2.2); L = (d @ np.array([.114, .587, .299], np.float32))[..., None]; mx, mn = d.max(2, keepdims=True), d.min(2, keepdims=True); sat = (mx - mn) / (mx + 1e-4); B, G, R = d[..., :1], d[..., 1:2], d[..., 2:]
    acc = np.zeros_like(L)
    if ACC == 'red': acc = sm(R - np.maximum(G, B), .035, .11) * sm(sat, .34, .50) * (1 - sm(G - B, .04, .11)) * s.get('accent', 1.)
    sp = spot(s); x = (L * gain) ** 1.42 * 1.12 * sp
    if black > 0: x = np.clip((x - black) / (1 - black), 0, 9)
    x = x / (1 + .44 * np.maximum(x - .55, 0)); t = np.clip(x * 1.6, 0, 1); g = x * (np.array([1.05, .95, 1.], np.float32) * (1 - t) + np.array([.945, .985, 1.], np.float32) * t)
    if ACC == 'all': return d * (x / (L + 1e-3)), np.ones_like(L) * sm(sat, .4, .7), x
    rv = np.clip(R * gain, 0, 2.2) ** 1.25 * 1.15 * ag * (.35 + .65 * sp); return g * (1 - acc) + np.concatenate([rv * .17, rv * .10, rv], 2) * acc + g * acc * .12, acc, x
def glow(o, thr=.5, amt=.55):
    q = cv2.resize(np.clip(o - thr, 0, None), (w // 6, h // 6), interpolation=cv2.INTER_AREA); a = cv2.GaussianBlur(q, (0, 0), w * .0032) * .8 + cv2.GaussianBlur(q, (0, 0), w * .0147) * .9 * np.array([.75, .8, 1.25], np.float32); return o + amt * cv2.resize(a.astype(np.float32), (w, h))
def treat(o, kind):
    L = o.mean(2, keepdims=True)
    if kind == 'black': return np.zeros_like(o) + np.array([.016, .008, .014], np.float32)
    if kind == 'negative': return np.clip(.50 - L * .85, 0, 1) * np.array([1, .97, .96], np.float32)
    if kind == 'crush': return np.clip((o - .38) / .62, 0, 1) * 1.15
    if kind == 'threshold': return (cv2.GaussianBlur(L[..., 0], (0, 0), max(.6, 2 * U)) > .30).astype(np.float32)[..., None] * .83 * np.array([.95, .98, 1], np.float32)
    if kind == 'duotone': return np.concatenate([L * .10 + .02, L * .05, np.clip(L * 1.35, 0, .82)], 2)
    if kind == 'solid': return np.concatenate([np.full_like(L, .05), np.full_like(L, .03), np.full_like(L, .62)], 2) * (.55 + .45 * np.clip(L * 2, 0, 1))
    if kind == 'edge':
        g = cv2.GaussianBlur(L[..., 0], (0, 0), max(.6, 1.5 * U)); return np.repeat(np.clip(np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)) * 2.6, 0, 1)[..., None] * .85 + .01, 3, 2)
    if kind == 'rgb': d = int(.02 * w); return np.concatenate([np.roll(o[..., :1], d, 1), o[..., 1:2], np.roll(o[..., 2:], -d, 1)], 2) * 1.1
    if kind == 'slit':
        r = o.copy(); b = max(2, int(6 * U)); n = h // b + 1; sh = (rng.normal(0, .10, n) * w * (rng.random(n) < .55)).astype(int)
        for k in range(n): r[k * b:(k + 1) * b] = np.roll(o[k * b:(k + 1) * b], sh[k], 1)
        return r
    if kind == 'pop': return np.clip(o * 2.4, 0, 1)
    sys.exit('unknown treatment ' + kind)
from PIL import Image, ImageDraw, ImageFont
def font(px):
    try: return ImageFont.truetype(P['font'], px) if P.get('font') else ImageFont.load_default(px)
    except TypeError: return ImageFont.load_default()
FN = font(max(8, int(30 * U)))
def caption(o, s, only):
    im = Image.new('L', (w, h), 0); d = ImageDraw.Draw(im); tr = 7 * U; ws = [d.textlength(c, font=FN) + tr for c in s]; X = (w - sum(ws) + tr) / 2
    for k, c in enumerate(s):
        if k in only: d.text((X, .885 * h), c, font=FN, fill=255)
        X += ws[k]
    m = np.asarray(im, np.float32)[..., None] / 255 * .85; return o * (1 - m) + .86 * m + cv2.GaussianBlur(m[..., 0], (0, 0), max(1, 9 * U))[..., None] * .22 * np.array([.8, .85, 1.1], np.float32)
TR = {t['f'] + k: t['kind'] for t in P.get('treat', []) for k in range(t.get('n', 1))}; clips = {}
def get(i):
    if i not in clips:
        s = S[i]; t = times(s, ends(i) - s['f']); clips[i] = (Clip(os.path.join(BASE, s['file']), t.min() - .1, t.max() + .1, s.get('hide', [])), t)
        for j in [j for j in clips if j < i - 1]: del clips[j]
    return clips[i]
def shoot(i, f, streak):
    s = S[i]; c, t = get(i); lin = (c.at(t[min(max(f - s['f'], 0), len(t) - 1)]).astype(np.float32) / 255) ** 2.2; cr = np.array([[0, 0, 1], [c.W, 0, 1], [0, c.H, 1], [c.W, c.H, 1]], np.float32).T
    d = np.abs((mat(i, f - .475, c) - mat(i, f + .475, c)) @ cr).max() / SC; n = 1 if d < 2.5 else int(min(26, max(5, d / 10))); acc = np.zeros((h, w, 3), np.float32); st = None; bm = cv2.BORDER_CONSTANT if s.get('edge') == 'black' else cv2.BORDER_REFLECT_101
    for q in range(n): acc += cv2.warpAffine(lin, mat(i, max(s['f'], f + .95 * ((q + .5) / n - .5)) if n > 1 else f, c), (w, h), flags=cv2.INTER_LINEAR, borderMode=bm)
    if streak:
        st = np.zeros((h, w, 3), np.float32); hl = np.where(((lin.max(2) > .62) | ((lin[..., 2] > .10) & (lin[..., 2] > 2.2 * lin[..., 1])))[..., None], lin, 0).astype(np.float32); hl = cv2.GaussianBlur(hl, (0, 0), 1.2)
        for q in range(52): st = np.maximum(st, cv2.warpAffine(hl, mat(i, max(s['f'] - 2, f + 2.6 * (q / 51 - .5)), c), (w, h), flags=cv2.INTER_LINEAR))
    return acc / n, st
RNG = range(*map(int, A.frames.split(':'))) if A.frames else range(END)
px = subprocess.Popen([FF, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '%dx%d' % (w, h), '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '12', '-vf', 'scale=out_color_matrix=bt709:out_range=tv', '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', A.out], stdin=subprocess.PIPE)
big = lambda s: abs(mv(s)[0]) + abs(mv(s)[1]) > .08
for f in RNG:
    i = max(j for j, s in enumerate(S) if s['f'] <= f); s = S[i]; k = f - s['f']; n = ends(i) - s['f']; left = n - 1 - k; nxt = S[i + 1] if i + 1 < len(S) else None
    fast = (i > 0 and k < 4 and big(s)) or (nxt is not None and left < 3 and big(nxt)); acc, st = shoot(i, f, fast); gain, black, ag, li = s.get('gain', 1.), 0., 1., s.get('light', '')
    if li == 'hot' and k < 5: gain *= [1.75, 1.32, 1.14, 1.06, 1.02][k]
    if li in ('reveal', 'revealhot'):
        black = [.72, .50, .33, .21, .12, .06, .03][k] if k < 7 else 0; ag = 1.25 if k < 5 else 1
        if li == 'revealhot' and k < 6: gain *= [1.5, 1.6, 1.4, 1.25, 1.12, 1.06][k]
    if left == 0 and nxt and n > 6 and f not in TR: gain *= .55
    o, red, x = grade(acc, s, gain, black, ag); lo = s.get('lights_only')
    if lo:
        m = lo[0] + (lo[1] - lo[0]) * k / max(1, n - 1); o = o * (1 - m) + (np.concatenate([o[..., :1] * red * .8, o[..., 1:2] * red * .8, np.clip(o[..., 2:] * 1.5, 0, 1) * red], 2) + (0 if ACC == 'red' else np.clip((x - .62) / .38, 0, 1) * .55)) * m
    if st is not None:
        g = st ** (1 / 2.2); R = g[..., 2:]; L = g.mean(2, keepdims=True); rr = (sm(R - g[..., 1:2], .08, .2) if ACC == 'red' else 0 * L) * s.get('accent', 1.); sw = [1, .72, .4, .18][k] if k < 4 and i > 0 and big(s) else [1, .6, .3][left] if left < 3 else 0
        o = np.maximum(o, np.concatenate([L * .9 * (1 - rr) + R * .15 * rr, L * .95 * (1 - rr) + R * .08 * rr, L * (1 - rr) + R * 1.1 * rr], 2) * .85 * sw * spot(s, .40))
    if nxt and nxt.get('carrier') == 'light' and left < 4:
        c2, t2 = get(i + 1); nx = cv2.warpAffine((c2.at(t2[0]).astype(np.float32) / 255) ** 2.2, mat(i + 1, nxt['f'] + 3, c2), (w, h)); o2, r2, x2 = grade(nx, nxt, 1.1); o = np.maximum(o, o2 * np.maximum(r2, np.clip((x2 - .6) * 3, 0, 1)) * (.3 + .2 * (3 - left)))
    if P.get('end_fade') and f > P['end_fade'][0]: o = o * max(0, 1 - (f - P['end_fade'][0]) / P['end_fade'][1]) ** 1.5
    if f in TR and TR[f] != 'black': o = treat(o, TR[f])
    o = glow(o); o = o * .93 + cv2.resize(cv2.GaussianBlur(cv2.resize(o, (w // 4, h // 4), interpolation=cv2.INTER_AREA), (0, 0), max(1, 5 * U)), (w, h)) * .10
    o = np.array([.034, .027, .031], np.float32) * (1 if f not in TR else .4) + np.clip(o, 0, None) * .96
    for a, b, tx in P.get('captions', []):
        if a <= f < b:
            base = max([len(c[2]) for c in P['captions'] if c[1] == a] or [0]); new = sorted(range(base, len(tx)), key=lambda q: (q * 7919) % 23); o = caption(o, tx, set(range(base)) | set(new[:(f - a + 1) * 2]))
    if TR.get(f) == 'black': o = treat(o, 'black')
    o = o + cv2.resize(rng.normal(0, 1, (h // 2, w // 2)).astype(np.float32), (w, h))[..., None] * .016; o = np.clip(o, 0, 1); o = np.where(o > .72, .72 + (o - .72) * .48, o)
    px.stdin.write((o * 255 + .5).astype(np.uint8).tobytes())
    if f % 24 == 0: print('%d/%d %s' % (f, END, s.get('id', s['file'])), flush=True)
px.stdin.close(); px.wait(); print('done', A.out)
