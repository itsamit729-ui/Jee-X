"""A visual problem unfolds in short cuts, with exact authored working and a follow-up."""
import math
from fractions import Fraction
from PIL import Image, ImageDraw
from social import art_direction as art, retention

INK='#f5efe5'; MUTED='#b0aaa1'; ORANGE='#ff9156'; PANEL='#282522'; BG='#191816'

def text(draw,value,box,size=38,color=INK,bold=False,minimum=23):
    return art.fit(draw,value,box,size,color,bold=bold,min_size=minimum)


def arrow(draw,a,b,color=ORANGE,width=4):
    draw.line((*a,*b),fill=color,width=width)
    angle=math.atan2(b[1]-a[1],b[0]-a[0])
    points=[b,(b[0]-13*math.cos(angle-.45),b[1]-13*math.sin(angle-.45)),(b[0]-13*math.cos(angle+.45),b[1]-13*math.sin(angle+.45))]
    draw.polygon(points,fill=color)


def plot(draw,b,t,index):
    kind=b['visual'];phase=(t%4)/4
    if kind=='capacitors' and index<2:
        for x,title,voltage,signs in ((220,'C','V',('+','-')),(490,'2C','V/2',('-','+'))):
            draw.line((x-27,470,x-27,565),fill=INK,width=5);draw.line((x+27,470,x+27,565),fill=INK,width=5)
            text(draw,title,(x-40,411,120,43),30,ORANGE,True)
            text(draw,voltage,(x-36,589,120,43),29,ORANGE,True)
            for sign,dx in zip(signs,(-68,47)):text(draw,sign,(x+dx,497,37,42),29,MUTED,True)
        if index>=0:
            draw.line((193,470,193,395,463,395,463,470),fill=ORANGE,width=2)
            draw.line((247,565,247,655,517,655,517,565),fill=ORANGE,width=2)
        if index==1:text(draw,'Q = 0 → V final = 0',(150,670,440,44),29,ORANGE,True)
        return
    if kind=='rolling' and index<2:
        u=phase;q=2*u-u*u;x=150+390*q-12;y=630-210*q-23;r=26
        draw.line((135,638,550,414),fill=MUTED,width=4)
        draw.ellipse((x-r,y-r,x+r,y+r),outline=ORANGE,width=4)
        angle=math.hypot(390,210)/r*q
        draw.line((x,y,x+r*math.cos(angle),y+r*math.sin(angle)),fill=INK,width=3)
        text(draw,'pure rolling',(90,401,280,43),29,ORANGE,True)
        text(draw,'translation + rotation',(160,673,440,38),25,MUTED)
        return
    if kind in ('rolling','capacitors'):kind='bars'
    if kind=='bars':
        values=b['initial'] if index<0 and b.get('initial') else b['data']; maximum=max(abs(v) for _,v in values) or 1
        baseline=559;draw.line((78,baseline,612,baseline),fill='#61564b',width=2)
        gap=530/len(values);growth=min(1,(t%7+.2)/.7)
        for i,(label,value) in enumerate(values):
            x=88+i*gap;h=value/maximum*135*growth
            color=ORANGE if i==index%len(values) else '#92877c'
            if h:draw.rounded_rectangle((x,min(baseline,baseline-h),x+gap-19,max(baseline,baseline-h)),radius=5,fill=color)
            number=str(Fraction(value).limit_denominator(24)) if abs(value)<2 else f'{value:g}'
            text(draw,number,(x,min(baseline,baseline-h)-41,gap-18,42),26,color,True,19)
            text(draw,label,(x,baseline+max(0,-h)+7,gap-16,58),20,MUTED,False,14)
        draw.text((85,687),b.get('units','Exact values · common linear scale'),font=art.font(16,'sans'),fill=MUTED)
        return
    if kind=='algebra':
        for i,line in enumerate(b['data']):
            y=417+i*72;active=i==index%3
            draw.rounded_rectangle((78,y,610,y+60),radius=10,fill='#413226' if active else PANEL)
            text(draw,line,(94,y+13,500,39),30,ORANGE if active else MUTED,True,19)
        return
    if kind=='wedge':
        recoil=-25*phase;slide=65*phase
        pts=[(170+recoil,650),(410+recoil,650),(410+recoil,410)]
        draw.polygon(pts,fill=PANEL,outline=MUTED)
        x=355+recoil-slide;y=438+slide
        draw.polygon([(x,y-27),(x+27,y),(x,y+27),(x-27,y)],fill=ORANGE)
        arrow(draw,(290+recoil,575),(200+recoil,575));text(draw,'A = g/3',(170,630,230,42),29,ORANGE,True)
        text(draw,'m',(345,557,45,40),28);text(draw,'m',(x-8,y-17,40,40),24,BG,True)
        text(draw,'45°',(345,608,100,40),25,MUTED)
    elif kind=='rod':
        hinge=(215,420);angle=min(math.pi/2,phase*math.pi*1.1);end=(hinge[0]+235*math.cos(angle),hinge[1]+235*math.sin(angle))
        draw.line((*hinge,*end),fill=MUTED,width=12);draw.ellipse((203,408,227,432),fill=ORANGE)
        if angle>=math.pi/2-.01:
            arrow(draw,(510,585),(510,445));text(draw,'At bottom: H = 5mg/2',(280,663,330,40),25,ORANGE,True)
        else:text(draw,'release → bottom',(310,635,300,42),27,ORANGE,True)
        arrow(draw,(hinge[0]+(end[0]-hinge[0])/2,hinge[1]+(end[1]-hinge[1])/2),(hinge[0]+(end[0]-hinge[0])/2,hinge[1]+(end[1]-hinge[1])/2+65),INK)
    elif kind=='springs':
        x1=240+25*math.sin(t*3);x2=455-25*math.sin(t*3)
        for start,end in ((80,x1-22),(x1+22,x2-22),(x2+22,610)):
            points=[(start,510)]+[(start+(end-start)*i/16,510+(11 if i%2 else -11)) for i in range(1,16)]+[(end,510)]
            draw.line(points,fill=MUTED,width=3)
        for x in (x1,x2):draw.rounded_rectangle((x-22,482,x+22,538),radius=7,fill=ORANGE)
        text(draw,'x2 = -x1',(220,572,280,43),34,ORANGE,True)
        text(draw,'Opposite-phase mode',(166,630,390,36),25,MUTED)
    elif kind=='hoop':
        cx,cy,r=345,510,105;draw.ellipse((cx-r,cy-r,cx+r,cy+r),outline=MUTED,width=4)
        draw.line((cx,cy-r-15,cx,cy+r+15),fill='#51483f',width=2)
        for sign in (-1,1):
            theta=sign*math.pi/3;x=cx+r*math.sin(theta);y=cy+r*math.cos(theta)
            draw.line((cx,cy,x,y),fill=ORANGE,width=2);draw.ellipse((x-9,y-9,x+9,y+9),fill=ORANGE)
            pulse=13+2*math.sin(t*5);draw.ellipse((x-pulse,y-pulse,x+pulse,y+pulse),outline=ORANGE,width=2)
        text(draw,'60° on either side',(152,638,430,40),30,ORANGE,True)
        text(draw,'bottom: unstable',(230,386,280,42),20,MUTED)
    elif kind=='speed':
        left,right,top,bottom=99,599,419,601
        draw.line((left,top,left,bottom,right,bottom),fill=MUTED,width=2)
        points=[(left+(right-left)*i/100,bottom-78*math.sqrt(2*(1-math.cos(2*math.pi*i/100)))) for i in range(101)]
        draw.line(points,fill=ORANGE,width=4)
        i=int(phase*100);x,y=points[i];draw.ellipse((x-7,y-7,x+7,y+7),fill=INK)
        text(draw,'v / (E/B)',(100,380,230,42),24,MUTED)
        for label,x in (('0',left),('pi',(left+right)/2),('2pi',right-25)):text(draw,label,(x,611,70,35),22,MUTED)
        text(draw,'maximum = 2E/B',(208,651,360,36),28,ORANGE,True)
    elif kind=='tunnel':
        cx,cy,r=345,515,109;draw.ellipse((cx-r,cy-r,cx+r,cy+r),outline=MUTED,width=4)
        draw.line((cx,cy-r,cx,cy+r),fill='#51483f',width=2)
        y=cy-r*math.cos(phase*math.pi/2);draw.ellipse((cx-10,y-10,cx+10,y+10),fill=ORANGE)
        text(draw,'surface → centre',(166,636,440,40),29,ORANGE,True)
        text(draw,'t = T/4',(101,474,190,42),32)
    elif kind=='discriminant':
        left,right,y0=108,598,427
        points=[(left+(right-left)*i/100,y0-160*4*(i/100)*(i/100-1)) for i in range(101)]
        draw.polygon([(left,y0)]+points+[(right,y0)],fill='#513327')
        draw.line((left,y0,right,y0),fill=MUTED,width=2);draw.line(points,fill=ORANGE,width=4)
        text(draw,'0',(left,380,50,44),25,MUTED);text(draw,'1',(right-20,380,50,44),25,MUTED)
        text(draw,'D = 4a(a-1) < 0',(170,632,430,44),32,ORANGE,True)
    elif kind=='circle':
        cx,cy,r=320,520,100
        draw.line((90,cy,610,cy),fill='#61564b',width=2);draw.line((445,410,445,640),fill='#61564b',width=2)
        draw.ellipse((cx-r,cy-r,cx+r,cy+r),outline=ORANGE,width=4)
        x=cx+r*math.cos(t);y=cy+r*math.sin(t)
        for fx in (370,520):draw.line((x,y,fx,cy),fill=MUTED,width=2);draw.ellipse((fx-4,cy-4,fx+4,cy+4),fill=INK)
        draw.ellipse((x-7,y-7,x+7,y+7),fill=ORANGE)
        text(draw,'-1',(357,cy+13,70,42),21,MUTED);text(draw,'+1',(507,cy+13,70,42),21,MUTED)
        text(draw,'one distance = twice the other',(105,650,520,36),25,ORANGE,True)


def frame(c,p,t):
    b=retention.brief(c);kind=p['format'];im=Image.new('RGB',(720,1280),BG);d=ImageDraw.Draw(im)
    # Text and equations stay out of the right-hand platform rail and lower controls.
    d.text((54,150),'JEE EDGE',font=art.font(19,'sans',True),fill=INK)
    d.text((445,154),c['subject'],font=art.font(13,'mono'),fill=MUTED)
    series={'challenge':'MAKE A PREDICTION','answer_first':'RESULT → REASON','mistake_check':'FIND THE BROKEN STEP','visual_proof':'FOLLOW THE MODEL'}[kind]
    d.text((54,201),series,font=art.font(17,'mono',True),fill=ORANGE)
    if t<8:
        title=(c['answer'] if kind=='answer_first' else c['trap'] if kind=='mistake_check' and t>=3 else p.get('hook') or b['hook'])
        text(d,title,(54,245,566,145),56,INK,True,29)
        plot(d,b,t,-1)
        text(d,b['setup'],(54,753,566,130),32,INK,False,25)
        label='CHECK THIS ASSUMPTION' if kind=='mistake_check' else 'Your method first. Then the proof.'
        text(d,label,(54,902,565,35),21,ORANGE,False,19)
    elif t<30:
        step=0 if t<15 else 1 if t<22 else 2
        text(d,b['setup'],(54,249,566,116),33,INK,False,25)
        plot(d,b,t,step)
        d.rounded_rectangle((54,715,628,887),radius=14,fill=PANEL)
        d.text((72,729),f'0{step+1}',font=art.font(17,'mono',True),fill=ORANGE)
        text(d,c['worked_steps'][step],(114,735,494,152),33,INK,True,25)
        text(d,('MODEL','SUBSTITUTE','DEDUCE')[step],(54,901,560,37),22,ORANGE,True)
    elif t<36:
        text(d,'Now change one condition.',(54,253,566,125),48,INK,True,31)
        text(d,c['transfer_question'],(54,429,566,181),37,INK,False,27)
        if t>=33:
            d.rounded_rectangle((54,665,628,893),radius=16,fill=PANEL)
            text(d,c['transfer_answer'],(76,689,530,177),34,ORANGE,True,25)
        else:
            # The moving underline gives a short thinking beat, not a long empty countdown.
            d.line((54,684,54+574*(t-30)/3,684),fill=ORANGE,width=4)
    else:
        text(d,c['condition'],(54,249,566,170),32,INK,False,23)
        text(d,c['transfer_question'],(54,429,566,181),37,INK,False,27)
        d.rounded_rectangle((54,665,628,893),radius=16,fill=PANEL)
        text(d,c['transfer_answer'],(76,689,530,177),34,ORANGE,True,25)
        text(d,'Chapter practice · jeeedge.in',(54,910,566,39),24,MUTED,False,21)
    cues=p.get('subtitles',[])
    for cue in cues:
        if cue['start']<=t<cue['end']:
            d.rounded_rectangle((44,959,639,1077),radius=12,fill='#090b09')
            text(d,cue['text'],(63,976,558,88),31,INK,True,25);break
    # Persistent chapter marks make the working navigable on rewatch.
    for i,(a,z) in enumerate(zip(retention.CUTS,retention.CUTS[1:])):
        x=54+574*a/40;end=54+574*z/40-4
        d.line((x,1120,end,1120),fill=ORANGE if t>=a else '#494138',width=4)
    return im
