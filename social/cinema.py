"""Visual-first motion design with exact, authored mathematical demonstrations."""
import math
import re
from functools import lru_cache
from PIL import Image, ImageDraw
from social import worker, storyboard

BG='#101115';PANEL='#191c22';WHITE='#f4f0e8';ORANGE='#ff864b';BLUE='#8ecfdf';MUTED='#999da7'


@lru_cache(maxsize=64)
def font(size,bold=False):return worker.font(size,bold)


def ease(t):
    t=max(0,min(1,t));return 1-(1-t)**3


def mix(a,b,t):return a+(b-a)*t


def block(d,text,box,size=44,color=WHITE,bold=True):
    text=re.sub(r"\^([23])(?!\d)",lambda m: {"2":"²","3":"³"}[m[1]],str(text)).replace("->","→").replace("theta","θ")
    x,y,w,h=box
    for pts in range(size,21,-2):
        face=font(pts,bold);lines=worker.wrapped(d,str(text),face,w)
        if len(lines)*(pts+8)<=h and all(d.textlength(line,font=face)<=w for line in lines):
            for j,line in enumerate(lines):d.text((x,y+j*(pts+8)),line,font=face,fill=color)
            return
    raise worker.ServiceError('Cinematic Reel text exceeds the safe area.')


def tag(d,text,x,y,color=ORANGE):
    w=d.textlength(text,font=font(19,True))+28
    d.rounded_rectangle((x,y,x+w,y+36),radius=10,fill=PANEL,outline=color,width=1)
    d.text((x+14,y+6),text,font=font(19,True),fill=color)


def dot(d,x,y,r,color):
    # Concentric rims create depth without expensive per-frame blur.
    d.ellipse((x-r-7,y-r-7,x+r+7,y+r+7),outline=color,width=1)
    d.ellipse((x-r,y-r,x+r,y+r),fill=color)
    d.ellipse((x-r*.5,y-r*.6,x-r*.12,y-r*.22),fill=WHITE)


def arrow(d,x,y,xx,yy,color):
    d.line((x,y,xx,yy),fill=color,width=4);a=math.atan2(yy-y,xx-x)
    d.polygon([(xx,yy),(xx-14*math.cos(a-.45),yy-14*math.sin(a-.45)),
        (xx-14*math.cos(a+.45),yy-14*math.sin(a+.45))],fill=color)


def grid(d):
    for x in range(64,644,48):d.line((x,375,x,825),fill='#24272f')
    for y in range(390,826,48):d.line((64,y,642,y),fill='#24272f')


def nvalue(c):return int(c['lesson_id'].split(':')[1])


def experiment(d,c,t,revealed,accent,format):
    """Keep all geometry in the 64,370..642,840 safe diagram area."""
    topic=c['topic'];n=nvalue(c);p=1 if revealed else (t%5)/5
    grid(d)
    if topic=='Projectile range':
        angle=n+20
        upper=90-angle; total=2*math.sin(math.radians(upper));clock=p*total
        landing=95+540*math.sin(math.radians(2*angle))
        for a,col in [(angle,ORANGE),(upper,accent)]:
            end=2*math.sin(math.radians(a));now=min(clock,end)
            pts=[]
            for j in range(81):
                tt=now*j/80;pts.append((95+540*math.cos(math.radians(a))*tt,
                    795-780*(math.sin(math.radians(a))*tt-tt*tt/2)))
            if len(pts)>1:d.line(pts,fill=col,width=5)
            dot(d,*pts[-1],12,col)
        d.line((85,810,620,810),fill=MUTED,width=2)
        tag(d,f'{angle} degrees',80,415,ORANGE);tag(d,f'{upper} degrees' if revealed else '? degrees',400,415,accent)
        if revealed:
            d.line((landing,760,landing,818),fill=WHITE,width=2)
            tag(d,'SAME RANGE',int(max(260,landing-150)),835)
        return 'Same speed / level ground / no air drag'
    if topic=='Vertical throw':
        clock=p*2;y=800-340*(2*clock-clock*clock)
        d.line((310,445,310,812),fill='#464953',width=2)
        for j in range(12):
            tt=max(0,clock-j*.025);yy=800-340*(2*tt-tt*tt)
            d.ellipse((299,yy-3,305,yy+3),fill=ORANGE)
        dot(d,310,y,21,ORANGE);arrow(d,365,y,365,y+58,accent)
        tag(d,'g stays DOWN',402,575,accent)
        velocity=1-clock
        if abs(velocity)>.04:arrow(d,255,y,255,y-90*velocity,WHITE)
        tag(d,'velocity',100,720,WHITE)
        return 'At the top: v = 0. Acceleration is still g.'
    if topic=='Uniform circular motion':
        cx,cy,r=335,615,142;a=t*1.3
        d.ellipse((cx-r,cy-r,cx+r,cy+r),outline='#454954',width=2)
        for j in range(24):
            aa=a-j*.045;d.ellipse((cx+r*math.cos(aa)-3,cy+r*math.sin(aa)-3,cx+r*math.cos(aa)+3,cy+r*math.sin(aa)+3),fill=ORANGE)
        x,y=cx+r*math.cos(a),cy+r*math.sin(a);dot(d,x,y,17,WHITE)
        arrow(d,x,y,cx,cy,ORANGE);arrow(d,x,y,x-74*math.sin(a),y+74*math.cos(a),accent)
        tag(d,'v: tangent',80,835,accent);tag(d,'a: inward',370,835)
        return 'Fixed radius: double v -> four times a'
    if topic=='Wave speed':
        for j in range(29):
            x=80+j*19;y=610+88*math.sin(j*.4-t*2)
            d.line((x,495,x,735),fill='#2d313a',width=1)
            dot(d,x,y,7,accent if j==14 else ORANGE)
        arrow(d,170,430,500,430,WHITE);tag(d,'wave travels',230,375,WHITE)
        tag(d,'Marked point stays at one x',95,820,accent)
        return 'v = frequency x wavelength'
    if topic=='Kinetic energy scaling':
        for y,v,col in [(505,1,accent),(685,3,ORANGE)]:
            x=95+(t*v*90)%485;d.line((90,y+25,620,y+25),fill=MUTED,width=2)
            d.rounded_rectangle((x-24,y-14,x+24,y+12),radius=8,fill=col)
            for dx in (-13,13):d.ellipse((x+dx-6,y+10,x+dx+6,y+22),fill=WHITE)
            tag(d,'v' if v==1 else '3v',80,y-85,col)
        for j in range(9 if revealed else 1):
            d.rectangle((335+j*31,760,356+j*31,806),fill=ORANGE)
        tag(d,'9K' if revealed else '? K',90,775)
        return 'Same mass. Kinetic energy scales with v squared.'
    if topic=='Dilution':
        p=ease(min(t/6,1));left=235;right=480;bottom=805;level=mix(730,490,p)
        d.rectangle((left,460,right,bottom),outline='#89909d',width=4)
        d.rectangle((left+5,level,right-5,bottom-4),fill='#203944')
        if p<1:
            for i in range(7):
                yy=385+(t*200+i*25)%max(1,level-380)
                d.ellipse((350,yy,358,yy+14),fill=accent)
        for i in range(12):
            x=265+(i%4)*59+4*math.sin(t+i);yy=level+24+(i//4)*(bottom-level-45)/3+3*math.cos(t+i)
            dot(d,x,yy,7,ORANGE)
        tag(d,'12 particles',85,390);tag(d,'still 12',435,835)
        return 'Illustration: solute stays fixed as volume increases.'
    if topic=='First-order half-life':
        # Number of glowing particles follows the exact discrete half-life steps.
        step=min(3,int(t/2.2));count=64//(2**step)
        for i in range(64):
            x=115+(i%8)*64;yy=420+(i//8)*47
            col=ORANGE if i<count else '#333740'
            r=11 if i<count else 5
            if i<count:yy+=3*math.sin(t*2+i*.6)
            d.ellipse((x-r,yy-r,x+r,yy+r),fill=col)
        tag(d,f'{step} half-lives',85,820,accent);tag(d,f'{8*n//(2**step)} g left',365,820)
        return '64 dots represent the sample; mass halves each step.'
    if topic in ('Odd-function integral','Even-function integral','Derivative at a point'):
        odd=topic=='Odd-function integral';derivative=topic=='Derivative at a point'
        cx,cy,sx=345,650,240
        if derivative:
            # Display the actual f(x)=x^2+n*x over 0..4 on a shared scaled axis.
            cx,cy,sx=100,805,125;sy=330/(16+4*n)
            f=lambda x:x*x+n*x
            pts=[(cx+sx*(i/40),cy-sy*f(i/40)) for i in range(161)]
            d.line((90,cy,635,cy),fill=MUTED,width=2)
            d.line(pts,fill=ORANGE,width=5)
            x=2 if revealed else .3+3.4*p;y=f(x);slope=2*x+n
            d.line((cx+sx*(x-.5),cy-sy*(y-.5*slope),cx+sx*(x+.5),cy-sy*(y+.5*slope)),fill=accent,width=5)
            dot(d,cx+sx*x,cy-sy*y,10,WHITE)
            tag(d,f'f(x) = x^2 + {n}x',85,395)
            tag(d,f'slope = {n+4}' if revealed else 'Follow the tangent',180,835,accent)
            return 'Differentiate first. Then substitute x = 2.'
        f=(lambda x:x**3) if odd else (lambda x:x*x)
        sy=170;bound=min(1,t/4)
        for sign,col in [(-1,'#314b54'),(1,'#74452e')]:
            xs=[sign*bound*i/50 for i in range(51)]
            d.polygon([(cx,cy)]+[(cx+sx*x,cy-sy*f(x)) for x in xs]+[(cx+sx*xs[-1],cy)],fill=col)
        pts=[(cx+sx*i/100,cy-sy*f(i/100)) for i in range(-100,101)]
        d.line((75,cy,620,cy),fill=MUTED,width=2);d.line((cx,425,cx,825),fill=MUTED,width=2)
        d.line(pts,fill=ORANGE,width=5)
        tag(d,'NEGATIVE' if odd else 'POSITIVE',75,855,accent);tag(d,'POSITIVE',405,855)
        return 'Opposite signed areas cancel.' if odd else 'Equal positive areas add.'
    if topic=='Difference of squares':
        # Actual a,b dimensions, common scale. L-shaped area becomes (a-b)(a+b).
        a=100+n;b=100-n;gap=a-b;scale=2.4;x=180;y=450;q=1 if revealed else ease(((t%7)-2)/3)
        # Fixed removed b-square and two translated remaining strips (no area distortion).
        if q<1:
            d.rectangle((x,y,x+b*scale,y+b*scale),fill='#242831',outline=MUTED,width=2)
            block(d,'b²',(x+40,y+70,160,70),42,color=MUTED)
        # top strip a by gap, side strip gap by b, rotate side to join horizontally.
        d.rectangle((mix(x,100,q),mix(y+b*scale,640,q),mix(x,100,q)+a*scale,mix(y+b*scale,640,q)+gap*scale),fill=ORANGE)
        cx=mix(x+(b+gap/2)*scale,100+(a+b/2)*scale,q);cy=mix(y+b*scale/2,640+gap*scale/2,q)
        angle=math.pi/2*q
        points=[]
        for xx,yy in [(-gap/2,-b/2),(gap/2,-b/2),(gap/2,b/2),(-gap/2,b/2)]:
            points.append((cx+scale*(xx*math.cos(angle)-yy*math.sin(angle)),cy+scale*(xx*math.sin(angle)+yy*math.cos(angle))))
        d.polygon(points,fill=accent)
        tag(d,f'a = {a}    b = {b}',145,390,WHITE)
        if q>.95:
            tag(d,f'a + b = {a+b}',205,735,WHITE)
            tag(d,f'a - b = {gap}',205,550)
        return 'Same area, rearranged: (a - b)(a + b)'
    if topic=='Limiting reagent':
        # A balanced discrete ratio illustration; units are explicitly molecules here.
        progress=1 if revealed else ease(min((t%7)/5,1))
        for j in range(3):
            xx=155+j*180;yy=480
            if j<2:
                yy=mix(480,685,progress)
            for dx in (-10,10):dot(d,xx+dx,yy,12,accent)
        for j in range(6):
            target=j//3;xx=110+j*92;yy=590
            xx=mix(xx,155+target*180+(-36,0,36)[j%3],progress)
            yy=mix(yy,720+(j%2)*34,progress)
            for dx in (-5,5):d.ellipse((xx+dx-5,yy-5,xx+dx+5,yy+5),fill=ORANGE)
        tag(d,'3 N2',90,395,accent);tag(d,'6 H2',410,395)
        if progress>.95:
            # Replace reactant drawing with explicitly grouped product molecules.
            d.rectangle((70,630,425,825),fill=BG)
            for i in range(4):
                xx=120+(i%2)*180;yy=680+(i//2)*105;dot(d,xx,yy,12,accent)
                for a in (0,2.094,4.189):
                    hx=xx+31*math.cos(a);hy=yy+31*math.sin(a)
                    d.line((xx,yy,hx,hy),fill=MUTED,width=2);d.ellipse((hx-7,hy-7,hx+7,hy+7),fill=ORANGE)
            tag(d,'4 NH3',95,840);tag(d,'1 N2 left',420,540,accent)
        return 'Ratio illustration: N2 + 3H2 -> 2NH3. H2 runs out.'
    # Old saved lessons still render with authored equation/answer reveals.
    block(d,c['answer'] if revealed else '?',(95,475,520,190),80,color=ORANGE)
    return c.get('rule',c['solution'])


@lru_cache(maxsize=1)
def background():
    im=Image.new('RGB',(720,1280),BG);d=ImageDraw.Draw(im)
    for y in range(1280):
        k=int(5*(1-y/1280));d.line((0,y,719,y),fill=(16+k,17+k,21+k))
    return im


def frame(c,plan,t):
    im=background().copy();d=ImageDraw.Draw(im);accent=BLUE if plan['accent']=='blue' else '#d9d0bc'
    reveal,example,recap,end=storyboard.beats(plan)
    phase=0 if t<reveal else 1 if t<example else 2 if t<recap else 3
    d.text((54,96),'JE',font=font(32,True),fill=ORANGE)
    d.text((112,105),'JEEEDGE   /   '+c['subject'],font=font(17,True),fill=MUTED)
    d.text((565,106),f'{phase+1:02d} / 04',font=font(17),fill=MUTED)
    hooks=storyboard.HOOKS.get(c['topic'],(c['topic'],)*3)
    title=hooks[plan['hook_index']]
    if phase==0:
        title=('SPOT THE TRAP' if plan['format']=='spot_trap' else title)
        if plan['format']=='spot_trap':subtitle=c['trap']
        elif plan['format']=='compare':subtitle='Compare what changes. Predict the result.'
        else:subtitle='Make your prediction before the reveal.'
    elif phase==1:
        title={'Projectile range':'SAME RANGE.', 'Vertical throw':'v = 0.  g IS NOT.',
            'Kinetic energy scaling':'ENERGY x9.', 'Dilution':'SAME SOLUTE.',
            'First-order half-life':'HALVE WHAT REMAINS.', 'Odd-function integral':'THEY CANCEL.',
            'Even-function integral':'DOUBLE ONE HALF.', 'Difference of squares':'ONE RECTANGLE.',
            'Limiting reagent':'H2 RUNS OUT.'}.get(c['topic'],'WATCH THE RULE.')
        subtitle=c['rule']
    elif phase==2:
        title='YOUR TURN.';subtitle=c['question']
    else:title='SAVE THE SHORTCUT.';subtitle=c['condition']
    starts=(0,reveal,example,recap);age=t-starts[phase]
    # A restrained slide-in at scene boundaries; diagrams keep their full scale.
    block(d,title,(54,175+int(18*(1-ease(age/.35))),570,165),54)
    if phase<=1:
        sim=t if phase==0 else (t-reveal+3)
        note=experiment(d,c,sim,phase==1,accent,plan['format'])
        if phase==0:
            block(d,subtitle,(54,950,570,105),28,color=WHITE,bold=False)
            remaining=max(1,math.ceil(reveal-t))
            d.arc((555,1050,609,1104),-90,-90+360*(1-t/reveal),fill=ORANGE,width=4)
            d.text((572,1064),str(remaining),font=font(21,True),fill=WHITE)
        else:
            block(d,note,(54,950,570,100),29,color=ORANGE)
            block(d,c['condition'],(54,1060,540,77),22,color=MUTED,bold=False)
    elif phase==2:
        block(d,subtitle,(54,385,570,180),36)
        if age<2:
            for j in range(3):d.ellipse((288+j*44,640,306+j*44,658),fill=ORANGE if age>(j*.5) else '#363a44')
            block(d,'Pause. Try it.',(54,765,540,75),42,color=ORANGE)
        else:
            d.rounded_rectangle((54,610,624,748),radius=22,fill=PANEL,outline=ORANGE,width=2)
            block(d,c['answer'],(80,643,515,88),52,color=ORANGE)
            block(d,c['solution'],(54,800,570,265),32,bold=False)
    else:
        block(d,c['rule'],(54,380,570,210),39)
        tag(d,'ONLY WHEN',54,640,accent)
        block(d,subtitle,(54,700,570,160),29,bold=False)
        block(d,'Watch out: '+c['trap'],(54,895,570,110),26,color=ORANGE,bold=False)
        block(d,'Replay and predict it.' if plan['ending']=='challenge' else 'Save for revision. Follow @jeeedge.',(54,1060,550,70),24,color=WHITE)
    for j in range(4):
        x=54+j*146;d.rounded_rectangle((x,1160,x+134,1164),radius=2,fill='#30343e')
        a=starts[j];b=(reveal,example,recap,28)[j];f=max(0,min(1,(t-a)/(b-a)))
        if f>0:d.rectangle((x,1160,x+134*f,1164),fill=ORANGE)
    return im
