"""flow_measure.py <video> <outdir> [--sheet]
Measures a flow edit frame by frame. Per frame: global motion (dx, dy in % of frame width, zoom %/f, roll deg/f),
mean speed, sharpness (blur proxy), luma, warp residual. Finds cuts, then reports the motion on both sides of each cut:
direction match (-1..1), speed ratio in/out, blur at cut, luma pop, beat offset. Writes <id>.csv, <id>.json, sheets."""
import sys, os, json, subprocess, re, numpy as np, cv2
import shutil
FF=os.environ.get('FFMPEG') or shutil.which('ffmpeg') or sys.exit('ffmpeg not found: install it or set FFMPEG=/path/to/ffmpeg')
vid,out=sys.argv[1],sys.argv[2]; os.makedirs(out,exist_ok=True)
name=os.path.splitext(os.path.basename(vid))[0]
info=subprocess.run([FF,'-hide_banner','-i',vid],capture_output=True,text=True).stderr
w,h=map(int,re.search(r'Video:.*? (\d{2,5})x(\d{2,5})',info).groups()); fps=float(re.search(r'([\d.]+) fps',info).group(1))
W=480; H=int(round(W*h/w/2)*2)
raw=subprocess.run([FF,'-v','error','-i',vid,'-vf','scale=%d:%d'%(W,H),'-f','rawvideo','-pix_fmt','bgr24','-'],capture_output=True).stdout
fr=np.frombuffer(raw,np.uint8).reshape(-1,H,W,3); N=len(fr)
g=np.array([cv2.cvtColor(f,cv2.COLOR_BGR2GRAY) for f in fr])
hist=[cv2.normalize(cv2.calcHist([cv2.cvtColor(f,cv2.COLOR_BGR2HSV)],[0,1,2],None,[16,8,8],[0,180,0,256,0,256]),None,1,0,cv2.NORM_L1).ravel() for f in fr]
dis=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
yy,xx=np.mgrid[0:H,0:W].astype(np.float32); pts=np.stack([xx[::12,::12].ravel(),yy[::12,::12].ravel()],1)
M=np.zeros((N,10)) # dx dy zoom roll speed sharp luma resid hdiff dup
for i in range(N):
    M[i,5]=cv2.Laplacian(g[i],cv2.CV_64F).var(); M[i,6]=g[i].mean()
    if i==0: continue
    fl=dis.calc(g[i-1],g[i],None); f=fl[::12,::12].reshape(-1,2)
    A,_=cv2.estimateAffinePartial2D(pts,pts+f,method=cv2.RANSAC,ransacReprojThreshold=2.0)
    if A is not None:
        s=np.hypot(A[0,0],A[1,0]); c=A@np.array([W/2,H/2,1]); M[i,0:4]=[(c[0]-W/2)/W*100,(c[1]-H/2)/W*100,(s-1)*100,np.degrees(np.arctan2(A[1,0],A[0,0]))]
    M[i,4]=np.median(np.hypot(f[:,0],f[:,1]))/W*100
    wp=cv2.remap(g[i],xx+fl[...,0],yy+fl[...,1],cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    M[i,7]=np.abs(wp.astype(int)-g[i-1]).mean(); M[i,8]=0.5*np.abs(hist[i]-hist[i-1]).sum(); M[i,9]=float(np.abs(g[i].astype(int)-g[i-1]).mean()<0.35)
res,hd=M[:,7],M[:,8]
def loc(x,k=9): return np.array([np.median(x[max(0,i-k):i+k+1]) for i in range(len(x))])
sc=(res/(loc(res)+3))*0.5+(hd/(loc(hd)+0.06))*0.35
cuts=[i for i in range(2,N) if sc[i]>1.55 and hd[i]>0.16 and sc[i]==sc[max(0,i-2):i+3].max()]
wav=os.path.join(out,name+'.wav'); subprocess.run([FF,'-v','error','-y','-i',vid,'-ac','1','-ar','22050',wav])
beats=np.array([]); on=np.array([]); bpm=0
try:
    import librosa
    y,sr=librosa.load(wav,sr=22050); o=librosa.onset.onset_strength(y=y,sr=sr); t,b=librosa.beat.beat_track(onset_envelope=o,sr=sr); bpm=float(np.atleast_1d(t)[0]); beats=librosa.frames_to_time(b,sr=sr); on=librosa.onset.onset_detect(onset_envelope=o,sr=sr,units='time')
except Exception as e: print('audio',e)
def near(a,t): return None if len(a)==0 else round(float((a-t)[np.argmin(abs(a-t))]*fps),1)
rows=[]
for k,c in enumerate(cuts):
    p=cuts[k-1] if k else 0; n=cuts[k+1] if k+1<len(cuts) else N
    a=M[max(p+1,c-3):c]; z=M[c+1:min(n,c+4)]
    if len(a)==0 or len(z)==0: continue
    va,vz=a[:,:2].mean(0),z[:,:2].mean(0); d=np.linalg.norm(va)*np.linalg.norm(vz)
    sh=M[p+1:c,4]; nx=M[c+1:n,4]
    rows.append(dict(f=c,t=round(c/fps,3),len_f=c-p,dir_match=round(float(va@vz/d),2) if d>0.02 else None,
      pre=[round(float(v),2) for v in a[:,:5].mean(0)],post=[round(float(v),2) for v in z[:,:5].mean(0)],
      zoom_same=bool(a[:,2].mean()*z[:,2].mean()>0),roll_same=bool(a[:,3].mean()*z[:,3].mean()>0),
      ramp_out=round(float(a[:,4].mean()/(np.median(sh)+.05)),2),ramp_in=round(float(z[:,4].mean()/(np.median(nx)+.05)),2) if len(nx) else None,
      blur=round(float(M[c-1:c+2,5].mean()/(np.median(M[p:n,5])+1)),2),luma_pop=round(float(M[c,6]-M[c-1,6]),1),beat_f=near(beats,c/fps),onset_f=near(on,c/fps)))
def med(x): x=[v for v in x if v is not None]; return round(float(np.median(x)),2) if x else None
S=dict(id=name,size=[w,h],fps=fps,frames=N,dur=round(N/fps,2),bpm=round(bpm,1),cuts=len(rows),shot_len_f_median=med([r['len_f'] for r in rows]),
 dir_match_median=med([r['dir_match'] for r in rows]),dir_match_pos_pct=round(100*np.mean([r['dir_match']>0.3 for r in rows if r['dir_match'] is not None] or [0])),
 ramp_out_median=med([r['ramp_out'] for r in rows]),ramp_in_median=med([r['ramp_in'] for r in rows]),blur_at_cut_median=med([r['blur'] for r in rows]),
 on_beat_pct=round(100*np.mean([abs(r['beat_f'])<=1.5 for r in rows if r['beat_f'] is not None] or [0])),on_onset_pct=round(100*np.mean([abs(r['onset_f'])<=1.5 for r in rows if r['onset_f'] is not None] or [0])),
 dup_frames_pct=round(100*M[:,9].mean()),luma_mean=round(float(M[:,6].mean()),1),speed_peak_over_median=round(float(np.percentile(M[:,4],97)/(np.median(M[:,4])+.02)),1))
json.dump(dict(summary=S,cuts=rows),open(os.path.join(out,name+'.json'),'w'),indent=0)
np.savetxt(os.path.join(out,name+'.csv'),np.c_[np.arange(N),np.arange(N)/fps,M],fmt='%.3f',delimiter=',',header='f,t,dx,dy,zoom,roll,speed,sharp,luma,resid,hdiff,dup')
if '--sheet' in sys.argv:
    tw=300; th=int(tw*H/W)
    def tile(i,red=False):
        im=cv2.resize(fr[i],(tw,th)); cv2.rectangle(im,(0,0),(96,16),(0,0,0),-1); cv2.putText(im,'%d %.2fs'%(i,i/fps),(3,12),0,.4,(255,255,255),1)
        if red: cv2.rectangle(im,(0,0),(tw-1,th-1),(0,0,255),3)
        return im
    def sheet(idx,cols,fn,marks=()):
        for pg in range(0,len(idx),cols*8):
            q=idx[pg:pg+cols*8]; T=[tile(i,i in marks) for i in q]; T+=[np.zeros((th,tw,3),np.uint8)]*((-len(T))%cols)
            cv2.imwrite(os.path.join(out,'%s_%s%02d.jpg'%(name,fn,pg//(cols*8))),np.vstack([np.hstack(T[j:j+cols]) for j in range(0,len(T),cols)]),[1,82])
    sheet(list(range(0,N,max(1,int(round(fps/3))))),6,'all',set(cuts))
    sheet([min(N-1,max(0,j)) for c in cuts for j in range(c-4,c+4)],8,'cuts',set(cuts))
print(json.dumps(S))
