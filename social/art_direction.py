"""Four authored editorial structures, with deterministic per-slot rotation.

Only presentation varies. Questions, conditions and worked answers are immutable.
No external fonts, stock media, invented student anecdotes or paid generation.
"""
import hashlib
import json
import math
import re
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HUMOR = json.loads(Path(__file__).with_name('humor.json').read_text())

STYLES = ('notebook', 'casefile', 'poster', 'comparison')
BRIEFS = {
    'notebook': 'A compact worked note. Start with the actual calculation or the useful step. Use plain sentences, like a tutor writing beside a worked solution. No closing question required.',
    'casefile': 'An original brain-versus-question meme. Use the supplied brain/reality joke as clearly fictional personification. A short dry punchline, then the real explanation and essential condition. Do not invent student quotes, statistics, exam stories, humiliation, or unrelated jokes.',
    'poster': 'A concise answer-led caption. Begin with the supplied answer or the concrete hook, then one explanation and the essential condition. Leave the fuller working to the slides. No generic motivational ending.',
    'comparison': 'A constraint comparison. Lead with what changes between the worked example and the transfer question. Explain the resulting difference using only those facts. Do not invent A/B options or turn the caption into a chapter summary.',
}
CAPTION_LIMITS = {'notebook':(100,700),'casefile':(100,750),'poster':(80,500),'comparison':(100,850)}
LABELS = {'notebook':'WORKING NOTES','casefile':'BRAIN VS QUESTION','poster':'ONE QUESTION','comparison':'CHANGE ONE THING'}
COLORS = {
    'notebook':('#f0e9dc','#222a30','#b94e29'),
    'casefile':('#161719','#f5eee0','#ff8951'),
    'poster':('#f58046','#191b1e','#191b1e'),
    'comparison':('#e6edf0','#202831','#235b75'),
}


def style(content):
    chosen=content.get('art_direction')
    if chosen in STYLES:return chosen
    n=int(hashlib.sha256(content['lesson_id'].encode()).hexdigest()[:8],16)
    return STYLES[n%len(STYLES)]


def attach(content, serial, ordinal):
    return {**content,'art_direction':STYLES[(serial+ordinal)%len(STYLES)],'design_version':3}


def caption(content):
    c=content;kind=style(c);why=c.get('why',c['rule'])
    if kind=='notebook':
        return f"{c['question']}\n\n{c['solution']}\n\n{why}\n{c['condition']}"
    if kind=='casefile':
        brain,reality=joke(c)
        return f"My brain: {brain}\nThe question: {reality}\n\n{why}\n{c['condition']}"
    if kind=='poster':
        return f"{c['question']}\n\n{c['answer']}. {why}\n\n{c['condition']}"
    return (f"{c.get('transfer_question',c['question'])}\n\n"
            f"{c.get('transfer_answer',c['solution'])}\n\n{c['condition']}")


def cards(c,copy):
    """Different reading sequences and lengths; no empty filler/CTA slides."""
    kind=style(c)
    cover=('cover',copy['hook'],c['question'])
    working=('working',c['answer'],c['solution'])
    reasoning=('reasoning','Why that step works',c['why'])
    condition=('condition','The condition matters',c['condition']+'\n\nMistake to avoid: '+c['trap'])
    transfer=('transfer',c['transfer_question'],c['transfer_answer'])
    if kind=='notebook':return [cover,working,reasoning,condition,transfer]
    if kind=='casefile':return [cover,('working',c['answer'],c['question']+'\n\n'+c['solution']),('condition','Okay, here is why.',c['why']+'\n\n'+c['condition']),transfer]
    if kind=='poster':return [cover,working,('condition',c['rule'],c['why']+'\n\n'+c['condition']),transfer]
    return [cover,('condition','Keep this fixed',c['condition']),working,reasoning,
            ('question','Now change the situation',c['transfer_question']),
            ('transfer','What changes in the answer?',c['transfer_answer']+'\n\n'+c['rule'])]


@lru_cache(maxsize=128)
def font(size,face='sans',bold=False):
    family={'sans':'DejaVuSans','serif':'DejaVuSerif','mono':'DejaVuSansMono'}[face]
    suffix='-Bold' if bold else ''
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/'+family+suffix+'.ttf',size)


def typography(text):
    text=re.sub(r'\^([23])(?!\d)',lambda m:{'2':'²','3':'³'}[m[1]],str(text))
    return text.replace('->','→').replace('theta','θ').replace('alpha','α').replace('beta','β')


def fit(d,text,box,size=56,color='#222a30',face='sans',bold=False,min_size=26):
    from social import worker
    text=typography(text);x,y,w,h=box
    for pts in range(size,min(min_size,size)-1,-2):
        f=font(pts,face,bold);lines=worker.wrapped(d,text,f,w)
        if len(lines)*(pts+12)<=h and all(d.textlength(line,font=f)<=w for line in lines):
            for j,line in enumerate(lines):d.text((x,y+j*(pts+12)),line,font=f,fill=color)
            return len(lines)*(pts+12)
    raise worker.ServiceError('Art direction text exceeds safe layout; holding publication.')


def page(kind,index,total,size=(1080,1350)):
    bg,ink,accent=COLORS[kind];im=Image.new('RGB',size,bg);d=ImageDraw.Draw(im)
    if kind=='notebook':
        for y in range(180,1220,54):d.line((54,y,size[0]-54,y),fill='#d8d4ca',width=1)
        d.line((86,150,86,1210),fill='#c98770',width=2)
    elif kind=='casefile':
        d.rectangle((0,0,size[0],22),fill=accent)
        d.rectangle((56,170,68,1175),fill=accent)
    elif kind=='poster':
        # Off-centre disc and a large counter supply hierarchy, not random decor.
        d.ellipse((size[0]-245,-145,size[0]+145,245),fill='#f9a676')
    else:
        d.rectangle((0,0,size[0],145),fill='#202831')
        d.rectangle((size[0]-30,145,size[0],size[1]),fill=accent)
    head='#f5eee0' if kind=='comparison' else ink
    d.text((60,65),'JEEEDGE',font=font(29,'sans',True),fill=head)
    d.text((size[0]-180,65),f'{index+1:02} / {total:02}',font=font(25,'mono'),fill=head)
    d.text((60,size[1]-83),'@jeeedge',font=font(25),fill=ink)
    return im,d,ink,accent



def joke(content):
    return HUMOR.get(content['topic'], ('I can skip the conditions.', 'The conditions are part of the question.'))


def comic_panel(d,label,text,box,deadpan,progress):
    """Original doodles and speech, no celebrity/image-macro assets."""
    x,y,w,h=box
    y+=int(25*(1-progress))
    bg='#f3e8d7' if deadpan else '#ff945c';ink='#1c2228'
    d.rounded_rectangle((x,y,x+w,y+h),radius=22,fill=bg)
    fit(d,label,(x+25,y+22,w-50,48),24,ink,face='mono',bold=True)
    # A simple expressive face occupies its own column, outside the text box.
    cx=x+70;cy=y+h-105;r=43
    d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=ink,width=4)
    for dx in (-15,15):
        if deadpan:d.line((cx+dx-7,cy-8,cx+dx+7,cy-8),fill=ink,width=4)
        else:d.ellipse((cx+dx-4,cy-13,cx+dx+4,cy-5),fill=ink)
    if deadpan:d.line((cx-16,cy+17,cx+16,cy+17),fill=ink,width=4)
    else:d.arc((cx-20,cy-3,cx+20,cy+26),0,180,fill=ink,width=4)
    d.line((cx,cy+r,cx,cy+r+30),fill=ink,width=4)
    fit(d,text,(x+140,y+90,w-175,h-115),48 if w>700 else 37,ink,bold=True,min_size=24)

def carousel(c,copy,output):
    kind=style(c);slides=cards(c,copy);paths=[]
    for index,(role,title,body) in enumerate(slides):
        im,d,ink,accent=page(kind,index,len(slides))
        face='serif' if kind=='notebook' else 'sans'
        d.text((112 if kind=='notebook' else 98,173),LABELS[kind],font=font(22,'mono'),fill=accent)
        if role=='cover' and kind=='casefile':
            brain,reality=joke(c)
            comic_panel(d,'MY BRAIN',brain,(96,236,884,375),False,1)
            comic_panel(d,'THE QUESTION',reality,(96,656,884,465),True,1)
        elif role=='cover':
            if kind=='poster':
                fit(d,title,(62,245,940,490),88,ink,bold=True)
                d.rectangle((54,790,1010,1205),fill='#191b1e')
                fit(d,body,(85,840,875,310),43,'#f6eee2')
            elif kind=='comparison':
                fit(d,title,(62,235,910,355),70,ink,bold=True)
                d.rectangle((58,630,996,1210),fill='#fcfaf5')
                d.text((90,670),'THE GIVEN',font=font(23,'mono'),fill=accent)
                fit(d,body,(90,737,865,400),50,ink)
            elif kind=='casefile':
                fit(d,title,(98,247,890,350),76,ink,bold=True)
                d.line((98,642,990,642),fill=accent,width=5)
                fit(d,body,(98,704,880,330),46,ink)
                fit(d,'Check the assumption.',(98,1120,880,65),32,accent,face='mono')
            else:
                fit(d,title,(112,246,866,350),72,ink,face=face,bold=True)
                fit(d,body,(112,705,866,405),49,ink,face=face)
        elif kind=='comparison':
            # Two stacked panels make the condition/result relationship explicit.
            d.rectangle((60,236,995,598),fill='#202831')
            fit(d,title,(95,277,860,280),130 if role=='working' else 61,'#f7eee1',bold=True)
            d.rectangle((60,640,995,1208),fill='#fcfaf5')
            fit(d,body,(95,685,860,465),48,ink)
        elif kind=='poster':
            fit(d,title,(62,245,935,335),154 if role=='working' else 78,ink,bold=True)
            d.rectangle((54,620,1010,1208),fill='#f7eee1')
            fit(d,body,(92,669,872,480),49,ink)
        else:
            fit(d,title,(112 if kind=='notebook' else 98,246,870,325),154 if role=='working' else 66,ink,face=face,bold=True)
            d.line((112,622,980,622),fill=accent,width=3)
            fit(d,body,(112,676,866,500),49,ink,face=face)
        p=Path(output)/f'{index+1}.png';im.save(p);paths.append(p)
    return paths


def reel_frame(c,plan,t):
    """Distinct compositions around the same verified math animation layer."""
    from social import cinema, storyboard, hooks
    kind=style(c);reveal,worked,recap,end=storyboard.beats(plan)
    phase=0 if t<reveal else 1 if t<worked else 2 if t<recap else 3
    im,d,ink,accent=page(kind,phase,4,(720,1280))
    if kind=='casefile' and t<9:
        brain,reality=joke(c)
        comic_panel(d,'MY BRAIN',brain,(56,175,575,365),False,min(1,t/.4))
        if t>=4:
            comic_panel(d,'THE QUESTION',reality,(56,625,575,440),True,min(1,(t-4)/.35))
        else:
            fit(d,'Confidence: high. Reading: optional.',(70,770,550,155),34,ink,bold=True)
        d.rectangle((48,1189,48+596*t/28,1193),fill=accent)
        return im
    # Shrink brand and move it into the platform-safe top region.
    d.rectangle((0,30,688,140),fill=COLORS[kind][0] if kind!='comparison' else '#202831')
    d.text((50,103),'JE / '+LABELS[kind],font=font(17,'mono'),fill=ink if kind!='comparison' else '#f5eee0')
    title=plan.get('hook') or hooks.opening(c)
    if phase==1:title=c['answer']
    elif phase==2:title='The working' if kind=='notebook' else 'Here is the calculation'
    elif phase==3:title='Only under these conditions'
    face='serif' if kind=='notebook' else 'sans'
    if phase<=1:
        # Render just the authored diagram, without reusing the old title/footer.
        layer=Image.new('RGB',(720,1280),cinema.BG);ld=ImageDraw.Draw(layer)
        cinema.experiment(ld,c,t if phase==0 else t-reveal+3,phase==1,cinema.BLUE,plan['format'])
        diagram=layer.crop((56,375,658,885))
        if kind=='casefile':
            im.paste(diagram.resize((602,510)),(56,170))
            fit(d,title,(80,727,547,222),54,ink,bold=True)
        elif kind=='poster':
            fit(d,title,(48,182,590,245),64,ink,bold=True)
            im.paste(diagram.resize((590,500)),(48,465))
        elif kind=='comparison':
            fit(d,title,(50,181,577,230),58,ink,bold=True)
            im.paste(diagram.resize((578,489)),(50,440))
            d.rectangle((50,939,628,1000),fill='#202831')
            fit(d,'PREDICT' if phase==0 else 'CHECK THE RESULT',(70,950,538,44),23,'#f7eee1',face='mono')
        else:
            fit(d,title,(86,187,546,222),55,ink,face=face,bold=True)
            im.paste(diagram.resize((548,464)),(84,447))
            d.line((84,947,632,947),fill=accent,width=3)
        detail=c['question'] if phase==0 else c.get('why',c['rule'])
        fit(d,detail,(80 if kind=='casefile' else 54,1020,548 if kind=='casefile' else 574,150),28,ink,min_size=22)
    else:
        fit(d,title,(66,193,565,155),49,ink,face=face,bold=True)
        if phase==2:
            fit(d,c['question'],(76,405,552,210),35,ink,min_size=24)
            fill='#292c30' if kind=='casefile' else '#fffaf0'
            d.rectangle((55,665,644,1138),fill=fill)
            fit(d,c['solution'],(80,707,535,365),38,ink,min_size=24)
        else:
            fit(d,c['condition'],(78,422,550,238),39,ink,min_size=24)
            d.line((78,704,628,704),fill=accent,width=4)
            fit(d,'Mistake to avoid: '+c['trap'],(78,751,550,268),37,ink,min_size=24)
    for cue in plan.get('subtitles',[]):
        if cue['start']<=t<cue['end']:
            d.rectangle((42,1030,649,1170),fill='#161719')
            fit(d,cue['text'],(61,1054,566,104),32,'#f7eee1',bold=True,min_size=24)
            break
    d.rectangle((48,1189,644,1193),fill='#777777')
    d.rectangle((48,1189,48+596*min(1,max(0,t/end)),1193),fill=accent)
    return im
