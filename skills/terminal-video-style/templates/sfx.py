# sfx.py —— 合成音效轨（不需要任何音效素材，全部用代码合成，可商用无版权问题）
# 音效轨（成片时间）：EVENTS 按镜头追加
import numpy as np, soundfile as sf
SR=48000
# 用法：python3 sfx.py events.json 时长秒 → sfx.wav
# events.json = [["whoosh", 0.0], ["tick", 1.2], ...]，时间是成片时间，跟画面动作同一帧
# 对应关系：whoosh=换镜/卡片飞入  pop=徽章/卡片弹出  thump=盖章/砸字  shimmer=完成/高亮
#          rush=快进/粒子冲刺  slash=划掉  tick=打字（每个字一下，间隔 0.24–0.3 秒）
import json, sys
EVENTS = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else [["whoosh", 0.0], ["pop", 0.5], ["thump", 1.0], ["shimmer", 1.05]]
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else max(t for _, t in EVENTS) + 1.0
rng=np.random.default_rng(3)
def env(n,a,r): e=np.ones(n); A=int(a*SR); R=int(r*SR); e[:A]=np.linspace(0,1,A); e[-R:]*=np.linspace(1,0,R); return e
def whoosh(d=0.7):
    n=int(d*SR); x=rng.standard_normal(n); t=np.arange(n)/SR
    f=np.cumsum(np.interp(t,[0,d],[300,2400]))/SR; y=np.convolve(x,np.ones(6)/6,'same')*np.sin(2*np.pi*f)*0.5+np.convolve(x,np.ones(30)/30,'same')
    return y*env(n,0.45,0.25)*0.25
def pop(d=0.12):
    n=int(d*SR); t=np.arange(n)/SR; return np.sin(2*np.pi*(900-3000*t)*t)*np.exp(-t*40)*0.35
def shimmer(d=0.6):
    n=int(d*SR); t=np.arange(n)/SR; y=sum(np.sin(2*np.pi*f*t)*np.exp(-t*(6+i)) for i,f in enumerate((2093,2637,3136,4186)))
    return y*env(n,0.01,0.2)*0.06
def rush(d=0.5):
    n=int(d*SR); x=rng.standard_normal(n); return np.convolve(x,np.ones(4)/4,'same')*env(n,0.05,0.35)*0.18
def slash(d=0.22):
    n=int(d*SR); t=np.arange(n)/SR; x=rng.standard_normal(n); f=np.cumsum(np.interp(t,[0,d],[4000,800]))/SR
    return x*np.sin(2*np.pi*f)*env(n,0.01,0.15)*0.3
def thump(d=0.3):
    n=int(d*SR); t=np.arange(n)/SR; return np.sin(2*np.pi*(90-60*t)*t)*np.exp(-t*14)*0.5
def tick(d=0.08):
    n=int(d*SR); t=np.arange(n)/SR; return np.sin(2*np.pi*2400*t)*np.exp(-t*80)*0.25
out=np.zeros(int(DUR*SR))
for k,t0 in EVENTS:
    i=int(t0*SR)
    if i>=len(out): continue          # 超出时长的事件跳过
    s=globals()[k](); out[i:i+len(s)]+=s[:len(out)-i]
sf.write("sfx.wav",out.astype(np.float32),SR)
