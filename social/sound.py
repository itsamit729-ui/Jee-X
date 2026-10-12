"""Original synthesized transition cues. No third-party samples or voice service."""
import math
import wave
from array import array
from social.storyboard import beats


def render(path,plan):
    rate=24000;duration=beats(plan)[-1];data=array('h',[0])*(duration*rate)
    transitions=(0,)+beats(plan)[:3]
    for index,at in enumerate(transitions):
        length=.22 if index else .13
        for i in range(int(rate*length)):
            t=i/rate;fade=(1-t/length)**2
            # Soft two-note pluck, below music peaks. No harsh noise sweeps.
            value=int(1900*fade*(math.sin(2*math.pi*660*t)+.3*math.sin(2*math.pi*990*t)))
            data[int(at*rate)+i]=value
    with wave.open(str(path),'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(data.tobytes())
    return path


def bed(path, plan):
    """Four original quiet rhythm beds; no downloads, samples or music fees."""
    rate=24000; duration=beats(plan)[-1]; variant=plan.get('soundtrack',0)%4
    bpm=(88,104,76,96)[variant]; beat=60/bpm
    data=array('h',[0])*int(duration*rate)
    def note(at, hz, length, volume):
        start=int(at*rate)
        for i in range(min(int(length*rate),len(data)-start)):
            t=i/rate
            attack=min(1,t/.008);release=(1-t/length)**3
            # Fundamental plus a very quiet harmonic, both synthesized locally.
            value=volume*attack*release*(math.sin(2*math.pi*hz*t)+.12*math.sin(4*math.pi*hz*t))
            data[start+i]=max(-30000,min(30000,data[start+i]+int(value)))
    roots=(130.81,146.83,110,164.81)
    steps=(0,7,12,7,0,3,7,3)
    for j in range(int(duration/beat)):
        at=j*beat
        note(at,roots[variant]/2,.22,2200 if j%4==0 else 1250)
        if j%2==variant%2:
            note(at+.5*beat,roots[variant]*2**(steps[j%8]/12),.18,1050)
        note(at,1800 if j%2 else 1200,.025,260)
    for i in range(len(data)):
        seconds=i/rate
        data[i]=int(data[i]*min(1,seconds/.3,max(0,(duration-seconds)/.7)))
    with wave.open(str(path),'wb') as wav:
        wav.setparams((1,2,rate,0,'NONE','not compressed'));wav.writeframes(data.tobytes())
    return path
