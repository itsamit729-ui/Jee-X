"""Original synthesized transition cues. No third-party samples or voice service."""
import math
import wave
from array import array
from social.storyboard import beats


def render(path,plan):
    rate=24000;duration=28;data=array('h',[0])*(duration*rate)
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
