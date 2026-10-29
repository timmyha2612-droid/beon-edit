#!/usr/bin/env python3
"""Where the music lifts and breathes, in timeline frames.
usage: music_sections.py SONG.wav IN_FRAMES [FPS=24]
SONG.wav: mono decode of the song (ffmpeg -i song.m4a -ac 1 -ar 22050 song.wav).
IN_FRAMES: the music clip's In (left offset) on the timeline, from the DRT <In> field.
Prints the tempo, where the full band comes in, and the dips (phrase changes). Compare these to
story beats, the break and the end card."""
import sys, wave, numpy as np
w=wave.open(sys.argv[1]); SR=w.getframerate(); x=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768
fps=float(sys.argv[3]) if len(sys.argv)>3 else 24; off=int(sys.argv[2])/fps
def rms(a,b): s=x[int(a*SR):int(b*SR)]; return 20*np.log10(np.sqrt((s**2).mean())+1e-9)
T=np.arange(0,len(x)/SR-off-0.1,0.1); E=np.array([rms(off+t,off+t+0.1) for t in T]); sm=np.convolve(E,np.ones(3)/3,'same')
hop=256;n=2048;fr=SR/hop
F=np.lib.stride_tricks.sliding_window_view(x,n)[::hop]*np.hanning(n); S=np.log1p(10*np.abs(np.fft.rfft(F,axis=1)))
flux=np.r_[0,np.maximum(0,np.diff(S,axis=0)).sum(1)]; f=flux-np.convolve(flux,np.ones(int(fr))/int(fr),'same')
ac=np.correlate(f,f,'full')[len(f)-1:]; lags=np.arange(len(ac))/fr; m=(lags>60/180)&(lags<60/60)
L=lags[m][np.argmax(ac[m])]
loud=np.percentile(sm,75)
print(f"tempo ~{60/L:.1f} BPM (beat = {L*fps:.1f} frames; could be half/double)")
print(f"full band in at frame {int(T[np.argmax(sm>loud-4)]*fps)}")
d=[(int(T[i]*fps),round(float(sm[i]),1)) for i in range(5,len(T)-5) if sm[i]==sm[i-5:i+6].min() and sm[i]<loud-8]
print("dips (frame, dB):",d)
