"""Four compact compositions with a shared safe text area and exact answer reveal."""
import math
from PIL import Image, ImageDraw
from social import art_direction as art, creative, cinema, storyboard, diagrams

PALETTES = {
 'challenge': ('#141719','#f7f2e8','#f47b45','#252a2c'),
 'answer_first': ('#efe9dd','#242622','#b34422','#fffdf7'),
 'mistake_check': ('#c24825','#fff6e7','#fff0ca','#a6371d'),
 'visual_proof': ('#172325','#f4f1e5','#f88951','#253539'),
}

def text(d, value, box, size=48, color='#f7f2e8', bold=False, minimum=26):
    return art.fit(d, value, box, size, color, bold=bold, min_size=minimum)

def enter(t, at):
    return int(22 * (1-min(1,max(0,(t-at)/.28)))**2)

def tag(d, label, y, accent):
    d.text((54,y),label,font=art.font(18,'mono',True),fill=accent)

def diagram(im, c, t, revealed, box):
    # Preserve the checked math animation. The figure is labelled as a concept
    # illustration because some physical examples differ from the worked numbers.
    layer = Image.new('RGB',(720,1280),cinema.BG)
    if not diagrams.draw(ImageDraw.Draw(layer),c,t,revealed):
        cinema.experiment(ImageDraw.Draw(layer),c,t,revealed,cinema.BLUE,'predict')
    x,y,w,h = box
    cropped = layer.crop((56,375,658,885))
    cropped.thumbnail((w,h),Image.Resampling.LANCZOS)
    im.paste(cropped,(x+(w-cropped.width)//2,y+(h-cropped.height)//2))

def frame(c, p, t):
    kind = p['format']; reveal,worked,close,end = creative.TIMINGS[kind]
    bg,ink,accent,panel = PALETTES[kind]
    im=Image.new('RGB',(720,1280),bg); d=ImageDraw.Draw(im)
    phase=0 if t<reveal else 1 if t<worked else 2 if t<close else 3
    phase_start=(0,reveal,worked,close)[phase]
    shift=enter(t,phase_start)
    # Right rail and lower caption region are kept clear of essential content.
    for x in range(54,650,44):
        for y in range(150,900,44):
            if kind=='visual_proof':d.ellipse((x,y,x+1,y+1),fill='#334345')
    d.rounded_rectangle((54,150,96,187),radius=8,fill=accent)
    d.text((61,156),'JE',font=art.font(20,'sans',True),fill=bg)
    d.text((111,160),'JEE EDGE / '+c['subject'],font=art.font(16,'mono'),fill=ink)
    tag(d,creative.LABELS[kind] if phase==0 else ('THE PAYOFF','THE WORKING','YOUR NEXT STEP')[phase-1],212,accent)
    has_diagram=c['topic'] in storyboard.DIAGRAM_TOPICS or c['topic'] in diagrams.TOPICS
    if phase==0:
        title=c['answer'] if kind=='answer_first' else p.get('hook') or creative.opening(c)
        text(d,title,(54,253+shift,566,182),92 if kind=='answer_first' else 53,ink,True,32)
        d.rounded_rectangle((54,459,628,673),radius=20,fill=panel)
        text(d,c['question'],(77,481,527,176),33,ink,False,26)
        if has_diagram and kind!='mistake_check':
            diagram(im,c,t,False,(58,687,557,201))
            tag(d,'CONCEPT VIEW',884,accent)
        elif kind=='mistake_check':
            tag(d,'THE MOVE TO QUESTION',708,accent)
            text(d,c['trap'],(54,752,557,142),33,ink,True,27)
            # A sketch underline leads the eye without pretending to be a vote.
            d.line((54,908,54+int(556*min(1,t/1.2)),908),fill=accent,width=4)
        elif kind=='answer_first':
            tag(d,'THE REASON IS THE USEFUL PART',730,accent)
            text(d,'Watch how the given becomes the result.',(54,780,560,116),36,ink,False,30)
        else:
            left=max(0,reveal-t)
            d.arc((60,735,176,851),-90,-90+360*left/reveal,fill=accent,width=6)
            d.text((91,760),str(max(1,math.ceil(left))),font=art.font(43,'sans',True),fill=ink)
            text(d,'Pick your method.\nThen check the result.',(209,752,400,135),35,ink,False,28)
    elif phase==1 and has_diagram and t-reveal>=2:
        text(d,c['answer'],(54,254,566,116),77,ink,True,34)
        tag(d,'CONCEPT ILLUSTRATION',387,accent)
        diagram(im,c,t-reveal+3,True,(54,424,574,478))
    elif phase==1:
        title='Here is why.' if kind=='answer_first' else c['answer']
        text(d,title,(54,255+shift,566,190),91 if kind!='answer_first' else 64,ink,True,35)
        why=c.get('why',c['rule'])
        text(d,why,(54,463,558,205),34,ink,False,27)
        if has_diagram:
            diagram(im,c,t-reveal+3,True,(58,684,558,205))
            tag(d,'CONCEPT VIEW',884,accent)
        else:
            d.rounded_rectangle((54,707,628,902),radius=20,fill=panel)
            text(d,c['rule'],(77,731,527,146),32,ink,False,26)
    elif phase==2:
        title='Watch this step.' if kind=='mistake_check' else 'From given to answer.'
        text(d,title,(54,253+shift,563,119),51,ink,True,35)
        d.rounded_rectangle((54,401,628,648),radius=20,fill=panel)
        text(d,c['solution'],(78,427,525,197),38,ink,True,26)
        tag(d,'KEEP THIS CONDITION',683,accent)
        text(d,c['condition'],(54,728,563,169),32,ink,False,26)
        # The answer repeats small here so viewers can pause on a complete recap.
    else:
        target=creative.destination(c)
        text(d,target['heading'],(54,264+shift,560,182),61,ink,True,38)
        text(d,target['detail'],(54,476,558,148),35,ink,False,28)
        d.rounded_rectangle((54,669,628,783),radius=19,fill=accent)
        text(d,'jeeedge.in/start',(77,697,527, 62),43,bg,True,35)
        text(d,target['label'],(54,817,558,91),27,ink,False,24)
    # A dedicated subtitle band never covers the equation, diagram or CTA.
    for cue in p.get('subtitles',[]):
        if cue['start']<=t<cue['end']:
            d.rounded_rectangle((44,937,639,1065),radius=13,fill='#101314')
            text(d,cue['text'],(62,956,559,89),31,'#fff6e7',True,25)
            break
    d.line((54,1104,628,1104),fill=panel,width=3)
    d.line((54,1104,54+574*min(1,max(0,t/end)),1104),fill=accent,width=3)
    return im
