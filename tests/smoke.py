"""Builds three synthetic clips (no real footage), checks a plan, renders it small, measures it and scores it against itself."""
import os, sys, json, subprocess, tempfile, cv2, numpy as np
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'skills', 'flow-editing', 'scripts'); T = tempfile.mkdtemp(); run = lambda *a: subprocess.run([sys.executable, *a], capture_output=True, text=True)
for n, (bg, r) in enumerate([(40, 90), (60, 120), (30, 70)]):
    v = cv2.VideoWriter(f'{T}/c{n}.mp4', cv2.VideoWriter_fourcc(*'mp4v'), 30, (360, 640))
    for i in range(90):
        im = np.full((640, 360, 3), bg, np.uint8); im[::40] = bg + 25; cv2.circle(im, (150 + i // 2, 330), r, (235, 235, 235), -1); cv2.circle(im, (150 + i // 2, 330), r // 3, (30, 30, 210), -1); v.write(im)
    v.release()
sh = lambda i, f, **k: dict({'id': f'S{i}', 'file': f'c{i % 3}.mp4', 'f': f, 't': 1.4, 'anc': [.5, .52], 'at': [.5, .5], 'z': [1, 1.1], 'block': 'A', 'carrier': 'match', 'eye': 'circle', 'out': 2, 'in': 5, 'mv': [.3, 0, 4, .1]}, **k)
P = {'fps': 24, 'size': [360, 640], 'end': 48, 'clips': '.', 'accent': 'red', 'shots': [sh(0, 0, light='reveal', hide=[[1.4, .4, .45, .6, .6]]), sh(1, 18, carrier='black', light='hot'), sh(2, 33, carrier='light', mv=[0, 0, 12, .2])], 'treat': [{'f': 17, 'kind': 'black'}, {'f': 32, 'kind': 'negative'}] + [{'f': 36 + i, 'kind': k} for i, k in enumerate(('crush', 'threshold', 'duotone', 'solid'))] + [{'f': 42 + i, 'kind': k} for i, k in enumerate(('edge', 'rgb', 'slit', 'pop'))], 'captions': [[4, 16, 'ONE'], [16, 30, 'ONE TWO']], 'end_fade': [44, 4]}
json.dump(P, open(f'{T}/p.json', 'w')); out = []
for name, a in (('plan', [f'{D}/flowplan.py', f'{T}/p.json']), ('selftest', [f'{D}/flowplan.py', '--selftest']), ('render', [f'{D}/flow_render.py', f'{T}/p.json', f'{T}/o.mp4']), ('measure', [f'{D}/flow_measure.py', f'{T}/o.mp4', f'{T}/m', '--sheet']), ('sync', [f'{D}/flow_sync.py', f'{T}/o.mp4', f'{T}/o.mp4'])):
    r = run(*a); ok = r.returncode == 0; out.append(ok)
    if name == 'sync': ok = 'SCORE 100.0' in r.stdout; out[-1] = ok
    print(('ok   ' if ok else 'FAIL ') + name, '' if ok else (r.stdout + r.stderr)[-600:])
c = cv2.VideoCapture(f'{T}/o.mp4'); n = int(c.get(7)); print('frames', n); sys.exit(0 if all(out) and n == 48 else 1)
