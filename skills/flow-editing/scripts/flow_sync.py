"""flow_sync.py <ref> <render> [--json out.json] [--plot out.png] [--max-lag 24] [--ref-range a:b] [--ren-range a:b]
Scores how well a remake follows a reference: per-frame luma, per-frame speed, cut/strobe timing. One number, 0-100.
The render is read on the reference's frame grid (fps filter only if the rates differ). Constant black bars are cropped first.

  L = max(0, Pearson r of mean luma per frame)                           (light curve shape)
  M = max(0, 1 - MAE / MAE0)     MAE0 = ref against itself, time-shifted  (light level; 0 = as wrong as a random shift)
  V = max(0, Pearson r of log(1+speed))                                   (speed curve shape; speed = median flow, % of width per frame)
  C = (F - Fc) / (1 - Fc), >= 0   F = 2*sum(w)/(n_ref+n_ren), one-to-one pairs, w = 1 / .5 / .25 at 0 / 1 / 2 frames off, else 0
                                  Fc = mean F over all time shifts (chance level for these two cut densities)
  D = shorter / longer duration
  SCORE = 100 * D * (0.25 L + 0.15 M + 0.25 V + 0.35 C)      measured at lag 0 (the best lag is printed, never scored)

"cuts" are flow_measure's detector: hard cuts AND 1-frame strobes (both must be copied). It misses cuts through black or light.
The score says nothing about which pictures, colour, type or sound are used. Audio lag is printed as a check, not scored."""
import sys, os, re, json, subprocess, numpy as np, cv2
import shutil
FF=os.environ.get('FFMPEG') or shutil.which('ffmpeg') or sys.exit('ffmpeg not found: install it or set FFMPEG=/path/to/ffmpeg')
W = 480

def probe(v):
    s = subprocess.run([FF, '-hide_banner', '-i', v], capture_output=True, text=True).stderr
    w, h = map(int, re.search(r'Video:.*? (\d{2,5})x(\d{2,5})', s).groups())
    f = re.search(r'([\d.]+) fps', s)
    f = float(f.group(1)); f = {23.98: 24000 / 1001, 29.97: 30000 / 1001, 59.94: 60000 / 1001}.get(f, f)
    return w, h, f, 'Audio:' in s

def frames(v, fps=None):
    w, h, f, _ = probe(v); H = int(round(W * h / w / 2) * 2)
    vf = ('fps=%.6f:round=near,' % fps if fps and abs(fps - f) > 0.02 else '') + 'scale=%d:%d' % (W, H)
    raw = subprocess.run([FF, '-v', 'error', '-i', v, '-vf', vf, '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    mx = fr.max(3).max(0); r = np.where(np.percentile(mx, 98, 1) > 20)[0]; c = np.where(np.percentile(mx, 98, 0) > 20)[0]
    if len(r) and len(c) and (r[0] > 4 or c[0] > 4 or r[-1] < H - 5 or c[-1] < W - 5): fr = fr[:, r[0]:r[-1] + 1, c[0]:c[-1] + 1]
    return fr, (fps or f)

def loc(x, k=9): return np.array([np.median(x[max(0, i - k):i + k + 1]) for i in range(len(x))])

def features(v, fps=None, rng=None):
    fr, f = frames(v, fps)
    if rng: fr = fr[rng[0]:rng[1]]
    N, H, w = fr.shape[0], fr.shape[1], fr.shape[2]
    g = [cv2.cvtColor(x, cv2.COLOR_BGR2GRAY) for x in fr]
    hist = [cv2.normalize(cv2.calcHist([cv2.cvtColor(x, cv2.COLOR_BGR2HSV)], [0, 1, 2], None, [16, 8, 8], [0, 180, 0, 256, 0, 256]), None, 1, 0, cv2.NORM_L1).ravel() for x in fr]
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    yy, xx = np.mgrid[0:H, 0:w].astype(np.float32); sp = np.zeros(N); res = np.zeros(N); hd = np.zeros(N)
    for i in range(1, N):
        fl = dis.calc(g[i - 1], g[i], None); q = fl[::12, ::12].reshape(-1, 2); sp[i] = np.median(np.hypot(q[:, 0], q[:, 1])) / w * 100
        wp = cv2.remap(g[i], xx + fl[..., 0], yy + fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        res[i] = np.abs(wp.astype(int) - g[i - 1]).mean(); hd[i] = 0.5 * np.abs(hist[i] - hist[i - 1]).sum()
    sc = (res / (loc(res) + 3)) * 0.5 + (hd / (loc(hd) + 0.06)) * 0.35
    cuts = [i for i in range(2, N) if sc[i] > 1.55 and hd[i] > 0.16 and sc[i] == sc[max(0, i - 2):i + 3].max()]
    return dict(fps=f, n=N, luma=np.array([x.mean() for x in g]), speed=sp, cuts=np.array(cuts, int))

def r(a, b): return float(np.corrcoef(a, b)[0, 1]) if len(a) > 2 and a.std() > 1e-6 and b.std() > 1e-6 else 0.0
WT = {0: 1.0, 1: 0.5, 2: 0.25}
def cutF(a, b):
    """one-to-one tent match, closest pairs first; returns F and the list of signed offsets b-a"""
    if len(a) == 0 or len(b) == 0: return (1.0 if len(a) == len(b) else 0.0), []
    d = b[None, :] - a[:, None]; pr = [(abs(d[i, j]), i, j) for i, j in zip(*np.where(np.abs(d) <= 2))]; pr.sort()
    ua, ub, s, off = set(), set(), 0, []
    for dd, i, j in pr:
        if i in ua or j in ub: continue
        ua.add(i); ub.add(j); s += WT[int(dd)]; off.append(int(d[i, j]))
    return 2 * s / (len(a) + len(b)), off
def lagged(a, b, k):  # b shifted k frames later than a
    n = min(len(a), len(b)); return (a[:n - k], b[k:n]) if k >= 0 else (a[-k:n], b[:n + k])

def score(A, B, maxlag=24):
    n = min(A['n'], B['n']); la, lb = A['luma'][:n], B['luma'][:n]; va, vb = np.log1p(A['speed'][:n]), np.log1p(B['speed'][:n])
    L = r(la, lb); mae = float(np.abs(la - lb).mean())
    sh = [k for k in range(max(3, int(A['fps'] / 2)), n - max(3, int(A['fps'] / 2)))] or [max(1, n // 2)]
    mae0 = float(np.mean([np.abs(la - np.roll(la, k)).mean() for k in sh])); Mq = max(0.0, 1 - mae / mae0) if mae0 > 0.2 else float(mae < 0.2)
    V = r(va, vb); ca, cb = A['cuts'][A['cuts'] < n], B['cuts'][B['cuts'] < n]; F, off = cutF(ca, cb)
    Fc = float(np.mean([cutF(ca, np.sort((cb + k) % n))[0] for k in range(3, n - 2)])) if n > 8 else 0.0
    C = max(0.0, (F - Fc) / (1 - Fc)) if Fc < 1 else F
    D = min(A['n'] / A['fps'], B['n'] / B['fps']) / max(A['n'] / A['fps'], B['n'] / B['fps'])
    S = 100 * D * (0.25 * max(0, L) + 0.15 * Mq + 0.25 * max(0, V) + 0.35 * C)
    best = max(range(-maxlag, maxlag + 1), key=lambda k: (r(*lagged(la, lb, k)) + r(*lagged(va, vb, k))) if n - abs(k) > 10 else -9)
    miss = [int(c) for c in ca if not len(cb) or np.abs(cb - c).min() > 2]; extra = [int(c) for c in cb if not len(ca) or np.abs(ca - c).min() > 2]
    return dict(score=round(S, 1), luma_r=round(L, 3), luma_mae=round(mae, 2), luma_mae_random=round(mae0, 2), level_M=round(Mq, 3), speed_r=round(V, 3),
        cut_F=round(F, 3), cut_F_chance=round(Fc, 3), cut_C=round(C, 3), cuts_ref=len(ca), cuts_render=len(cb), cut_offsets={str(k): off.count(k) for k in (-2, -1, 0, 1, 2)},
        cut_mean_abs_off=round(float(np.mean(np.abs(off))), 2) if off else None, missed=miss, extra=extra, duration_D=round(D, 3), best_lag_f=int(best), frames=[A['n'], B['n']], fps=round(A['fps'], 3)), la, lb

def audio_lag(a, b, rngs):
    sr = 8000; e = []
    for v, rg, f in rngs_iter(a, b, rngs):
        y = np.frombuffer(subprocess.run([FF, '-v', 'error', '-i', v, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'], capture_output=True).stdout, np.float32)
        if rg: y = y[int(rg[0] / f * sr):int(rg[1] / f * sr)]
        e.append(y)
    n = 2 ** int(np.ceil(np.log2(len(e[0]) + len(e[1])))); X = np.fft.rfft(e[0], n); Y = np.fft.rfft(e[1], n)
    c = np.fft.irfft(np.conj(X) * Y, n); m = 2 * sr; c = np.r_[c[-m:], c[:m]]; k = int(np.argmax(c)); den = np.sqrt((e[0] ** 2).sum() * (e[1] ** 2).sum()) + 1e-9
    return (k - m) / sr, float(c[k] / den)
def rngs_iter(a, b, rngs): return [(a,) + rngs[0], (b,) + rngs[1]]

if __name__ == '__main__':
    av = sys.argv[1:]; opt = {}
    while any(x.startswith('--') for x in av):
        i = [j for j, x in enumerate(av) if x.startswith('--')][0]; opt[av[i]] = av[i + 1]; del av[i:i + 2]
    if len(av) != 2: sys.exit(__doc__)
    rg = lambda k: tuple(map(int, opt[k].split(':'))) if k in opt else None
    A = features(av[0], None, rg('--ref-range')); B = features(av[1], A['fps'], rg('--ren-range'))
    R, la, lb = score(A, B, int(opt.get('--max-lag', 24)))
    if probe(av[0])[3] and probe(av[1])[3]:
        try: lag, pk = audio_lag(av[0], av[1], [(rg('--ref-range'), A['fps']), (rg('--ren-range'), A['fps'])]); R['audio_lag_ms'] = round(lag * 1000, 1); R['audio_match'] = round(pk, 3)
        except Exception as e: R['audio'] = str(e)
    print('%s  vs  %s' % (os.path.basename(av[0]), os.path.basename(av[1])))
    print('SCORE %.1f / 100   = 100*D*(0.25 L + 0.15 M + 0.25 V + 0.35 C)' % R['score'])
    print('  L luma r %.3f | M level %.3f (MAE %.2f, random %.2f) | V speed r %.3f | C cuts %.3f (F %.3f, chance %.3f, %d vs %d cuts) | D %.3f' % (R['luma_r'], R['level_M'], R['luma_mae'], R['luma_mae_random'], R['speed_r'], R['cut_C'], R['cut_F'], R['cut_F_chance'], R['cuts_ref'], R['cuts_render'], R['duration_D']))
    print('  cut offsets (render-ref, frames): %s | missed %s | extra %s' % (R['cut_offsets'], R['missed'], R['extra']))
    print('  best lag %+d f (0 = aligned) | audio lag %s ms, waveform match %s' % (R['best_lag_f'], R.get('audio_lag_ms'), R.get('audio_match')))
    if '--json' in opt: json.dump(R, open(opt['--json'], 'w'), indent=1)
    if '--plot' in opt:
        n = len(la); im = np.full((220, max(600, n * 4), 3), 20, np.uint8); ph = 200
        for s, col in ((la, (90, 200, 255)), (lb, (255, 160, 80))):
            p = np.array([[i * 4, int(ph - v / 255 * 190)] for i, v in enumerate(s)]); cv2.polylines(im, [p], False, col, 1, cv2.LINE_AA)
        for c in A['cuts']: cv2.line(im, (int(c) * 4, 0), (int(c) * 4, 10), (90, 200, 255), 1)
        for c in B['cuts']: cv2.line(im, (int(c) * 4, 10), (int(c) * 4, 20), (255, 160, 80), 1)
        cv2.imwrite(opt['--plot'], im)
