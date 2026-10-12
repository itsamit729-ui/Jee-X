"""Additional original concept drawings; no stock footage or generative media."""
import math
from social.cinema import tag, arrow, dot, grid, ORANGE, WHITE, BLUE, MUTED
TOPICS = ('Parallel resistance','Spring combination','Capacitor combination','Mole fraction',
          'Ideal gas ratios','Arithmetic progression','Repeated percentage change','Impulse',
          'Lens displacement','SN1 rate law','AM-GM minimum')

def draw(d,c,t,revealed):
    topic=c['topic']
    if topic not in TOPICS:return False
    n=int(c['lesson_id'].split(':')[1]) if topic not in ('Lens displacement','SN1 rate law','AM-GM minimum') else None
    grid(d)
    if topic=='Mole fraction':
        for i in range(4*n):
            x=105+(i%8)*64;y=495+(i//8)*45+4*math.sin(t*2+i)
            dot(d,x,y,10,ORANGE if i<n else BLUE)
        tag(d,f'{n} mol A',80,395);tag(d,f'{3*n} mol B',365,395,BLUE)
        tag(d,'x(A) = 1/4' if revealed else 'A / ALL particles',160,827)
    elif topic=='Parallel resistance':
        d.line((85,630,160,630,160,510,500,510,500,630,610,630),fill=WHITE,width=4)
        d.line((160,630,160,750,500,750,500,630),fill=WHITE,width=4)
        for y,value in ((510,n),(750,2*n)):
            d.rectangle((275,y-20,400,y+20),fill='#344145',outline=ORANGE,width=3)
            tag(d,f'{value} ohm',275,y-80)
            x=170+(t*95)%320;dot(d,x,y,6,BLUE)
        tag(d,'Same voltage / two current paths',79,827,BLUE)
    elif topic=='Spring combination':
        extension=(1+math.sin(t*1.3))*.5*40
        y=410;d.line((180,y,480,y),fill=WHITE,width=5)
        for j in range(2):
            start=y+20+j*(150+extension);end=start+145+extension
            pts=[(330,start)]+[(330+(-1)**i*35,start+15+i*(end-start-30)/10) for i in range(11)]+[(330,end)]
            d.line(pts,fill=ORANGE if j==0 else BLUE,width=5)
            tag(d,f'{10*n} N/m',440,start+25,ORANGE if j==0 else BLUE)
        arrow(d,565,695,565,787,WHITE)
        tag(d,'Same force / extensions add',83,838)
    elif topic=='Capacitor combination':
        d.line((85,630,260,630),fill=WHITE,width=4);d.line((280,630,445,630),fill=WHITE,width=4);d.line((465,630,615,630),fill=WHITE,width=4)
        for x in (260,445):
            for dx in (0,20):d.line((x+dx,555,x+dx,705),fill=ORANGE,width=6)
            tag(d,f'{2*n} uF',x-42,475)
            for j in range(4):dot(d,x-15,576+j*33,4,BLUE)
        tag(d,'Equal charge / voltages add',82,812,BLUE)
    elif topic=='Ideal gas ratios':
        ratio=min(1,t/4);height=145+145*ratio
        d.rectangle((218,415,487,815),outline=WHITE,width=4)
        d.rectangle((224,815-height,481,810),fill='#294951')
        d.line((214,815-height,491,815-height),fill=ORANGE,width=9)
        for i in range(14):dot(d,240+(i%5)*52+6*math.sin(t*3+i),800-(i//5+.5)*(height-20)/3,5,BLUE)
        tag(d,'T and amount stay fixed',97,845,BLUE)
        tag(d,f'{n} L -> {2*n} L',165,385)
    elif topic=='Arithmetic progression':
        tag(d,f'1 + 2 + ... + {2*n}',90,405)
        total=2*n+1
        for j in range(min(4,n)):
            y=515+j*71
            tag(d,f'{j+1}',90,y);tag(d,f'{2*n-j}',480,y,BLUE)
            progress=min(1,max(0,(t-j*.45)/1.2))
            d.line((155,y+18,155+285*progress,y+18),fill=WHITE,width=3)
            if progress==1:tag(d,f'= {total}',245,y)
        tag(d,'Every pair has the same sum',84,839,BLUE)
    elif topic=='Repeated percentage change':
        start=100;high=100+n;end=100*(1+n/100)*(1-n/100)
        values=(start,high,end)
        for i,v in enumerate(values):
            x=100+i*182;height=v*2.8*min(1,max(0,t-i*.7))
            d.rectangle((x,800-height,x+105,800),fill=ORANGE if i!=1 else BLUE)
            tag(d,('100',f'+{n}%',f'-{n}%')[i],x-8,420)
        tag(d,'Successive changes / different bases',77,846,BLUE)
    elif topic=='Impulse':
        # +3 / -2 velocity ratio: two seconds in, three seconds out.
        progress=t%5;direction=1 if progress<2 else -1
        x=150+progress*207 if direction==1 else 564-(progress-2)*138
        dot(d,x,640,26,ORANGE);d.line((590,480,590,800),fill=WHITE,width=6)
        arrow(d,x,570,x+direction*70,570,BLUE)
        tag(d,'+3 m/s' if direction==1 else '-2 m/s',130,419,BLUE)
        tag(d,'Change velocity WITH its sign',88,820)
    elif topic=='Lens displacement':
        # Authored example: D=100 cm, d=60 cm, so (u,v)=(20,80) or (80,20).
        u,v=(20,80) if t%6<3 else (80,20)
        obj,screen,axis=105,555,650;lens=obj+4.5*u
        tip=axis-38;image_tip=axis+38*v/u
        d.line((80,axis,600,axis),fill=MUTED,width=2)
        arrow(d,obj,axis,obj,tip,ORANGE)
        d.line((screen,452,screen,815),fill=WHITE,width=4)
        for position in (195,465):
            d.ellipse((position-10,552,position+10,742),outline=BLUE if position==lens else MUTED,width=3)
        arrow(d,screen,axis,screen,image_tip,ORANGE)
        rays=[((obj,tip),(lens,tip),(screen,image_tip)),((obj,tip),(lens,axis),(screen,image_tip))]
        progress=min(1,(t%3)/1.4)
        for points in rays:
            start,bend,stop=points
            if progress<.5:
                d.line((start,(start[0]+(bend[0]-start[0])*progress*2,start[1]+(bend[1]-start[1])*progress*2)),fill=ORANGE,width=3)
            else:
                d.line((start,bend,(bend[0]+(stop[0]-bend[0])*(progress*2-1),bend[1]+(stop[1]-bend[1])*(progress*2-1))),fill=ORANGE,width=3)
        tag(d,'object',76,485);tag(d,'screen',487,395,BLUE)
        tag(d,f'u={u} cm  /  v={v} cm',135,817,BLUE)
        tag(d,'Same f = 16 cm',195,430)
    elif topic=='SN1 rate law':
        # Changes from the stored example; bar heights encode concentration factors.
        fraction=min(1,t/2.5)
        tag(d,'Concentration factors',89,395,BLUE)
        for x,factor,label in ((132,2,'substrate'),(408,3,'nucleophile')):
            d.rectangle((x,735-68,x+105,735),outline=MUTED,width=2)
            height=68*(1+(factor-1)*fraction)
            d.rectangle((x,735-height,x+105,735),fill=ORANGE if factor==2 else BLUE)
            tag(d,f'x{factor}',x+19,450,ORANGE if factor==2 else BLUE)
            tag(d,label,x-34,761,WHITE)
        tag(d,'rate = k[substrate]  ->  x2',92,839)
    elif topic=='AM-GM minimum':
        # Plot the actual x+9/x example on x>0, never a decorative parabola.
        def point(x):return (105+x*68,807-(x+9/x-4)*25)
        d.line((105,432,105,807,600,807),fill=MUTED,width=3)
        tag(d,'y = x + 9/x  (x > 0)',80,395,BLUE)
        tag(d,'x',595,819,WHITE)
        cutoff=.8+6.2*min(1,t/3)
        points=[point(.8+j*6.2/140) for j in range(141) if .8+j*6.2/140<=cutoff]
        if len(points)>1:d.line(points,fill=ORANGE,width=4)
        px,py=point(3)
        if revealed or t>1.4:
            d.line((105,py,px,py,px,807),fill=BLUE,width=2)
            dot(d,px,py,9,BLUE)
            tag(d,'6',68,py-15,BLUE);tag(d,'3',px-10,819,BLUE)
            tag(d,'minimum (3, 6)',300,624,BLUE)
    return True
