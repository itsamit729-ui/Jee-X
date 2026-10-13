"""Versioned mixed answer sheets. Geometry is shared by printing and detection."""
import io
import re
from decimal import Decimal
import cv2
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing

DIGITS=8

def needs_mixed(questions):
    return any(q['type']!='single_correct' or len(q.get('options',[]))!=4 for q in questions or [])

def pages_for(questions,order):
    lookup={q['question_id']:q for q in questions}
    pages=[];page=[];column=0;y=332
    for number,qid in enumerate(order,1):
        q=lookup[qid];height=160 if q['type']=='numerical' else 46
        if y+height>790:
            column+=1;y=332
            if column==2:pages.append(page);page=[];column=0
        page.append({'number':number,'question_id':qid,'type':q['type'],'labels':[o['label'] for o in q.get('options',[])],'x':42+270*column,'y':y})
        y+=height
    if page:pages.append(page)
    return pages

def choices(item):
    return [(item['x']+24+46*k,item['y']+28) for k,_ in enumerate(item['labels'])]

def number_cells(item):
    x,y=item['x'],item['y']
    return {'sign':[(x+158,y+9),(x+202,y+9)],'decimal':[(x+28+22*k,y+39) for k in range(9)],
        'digits':[[(x+38+23*c,y+61+8*d) for d in range(10)] for c in range(DIGITS)],'box':(x+31,y+140,210,9)}

def pdf(paper,sheet,name):
    from app.services.teacher_omr import WIDTH,HEIGHT,MARKERS,id_cells
    pages=pages_for(paper.questions,sheet.question_order)
    out=io.BytesIO();c=canvas.Canvas(out,pagesize=(WIDTH,HEIGHT));c.setTitle('Jee Edge mixed answer sheet - '+paper.title)
    for page_index,items in enumerate(pages):
        for x,y in MARKERS:c.rect(float(x)-5,HEIGHT-float(y)-5,10,10,fill=1,stroke=0)
        c.setFont('Helvetica-Bold',15);c.drawString(42,HEIGHT-58,'Jee Edge | Mixed answer sheet')
        c.setFont('Helvetica',9)
        variant=f'Set {sheet.variant}' if paper.settings.get('sets_enabled',True) else 'Standard paper - no sets'
        lines=[(79,paper.title[:66]),(97,'Name: '+(name[:45] if name else '______________________________________')),
            (115,f'Paper {paper.id} | {variant} | Page {page_index+1} of {len(pages)}'),(133,'Keep every page. A score is saved only after all pages are reviewed.')]
        for y,text in lines:
            while c.stringWidth(text,'Helvetica',9)>400:text=text[:-1]
            c.drawString(42,HEIGHT-y,text)
        code=QrCodeWidget(f'JEEOMR3:{sheet.id}:{page_index}');x1,y1,x2,y2=code.getBounds()
        d=Drawing(78,78,transform=[78/(x2-x1),0,0,78/(y2-y1),0,0]);d.add(code);renderPDF.draw(d,c,WIDTH-125,HEIGHT-140)
        c.setFont('Helvetica-Bold',8);c.drawString(42,HEIGHT-149,'STUDENT OMR ID - use the same ID on every page')
        for col in range(10):
            x=54+20*col;c.rect(x-8,HEIGHT-178,16,18)
            for x,y in id_cells(col):c.circle(x,HEIGHT-y,3.5,stroke=1,fill=0)
        c.setFont('Helvetica',8)
        for digit in range(10):c.drawRightString(40,HEIGHT-(190+12*digit)-3,str(digit))
        instructions=['Print A4 at 100%. Keep all four corner squares.', 'Single: shade one. Multiple: shade every correct choice.', 'Numeric: shade + or -, all 8 digits and decimal places.', 'Example -12.5: minus, 00000125, 1 decimal place.', 'Include leading zeros. 0 decimal places = integer.', 'Also write the answer in the small box below the grid.', 'Longer values: write the full answer for teacher entry.', 'Personalised QR copies do not need the ID bubbles.']
        for i,text in enumerate(instructions):c.drawString(280,HEIGHT-(190+15*i),text)
        for item in items:
            x,y=item['x'],item['y'];c.setFont('Helvetica-Bold',9)
            if item['type']!='numerical':
                c.drawString(x,HEIGHT-y,f"Q{item['number']} | {'Multiple correct' if item['type']=='multi_correct' else 'Single correct'}")
                c.setFont('Helvetica',9)
                for label,(cx,cy) in zip(item['labels'],choices(item)):
                    c.circle(cx,HEIGHT-cy,4,stroke=1,fill=0);c.drawString(cx+9,HEIGHT-cy-3,label)
            else:
                c.drawString(x,HEIGHT-y,f"Q{item['number']} | Numerical")
                pts=number_cells(item);c.setFont('Helvetica',8)
                for label,(cx,cy) in zip(['+','-'],pts['sign']):c.circle(cx,HEIGHT-cy,3,stroke=1,fill=0);c.drawString(cx+6,HEIGHT-cy-2,label)
                c.drawString(x,HEIGHT-(y+24),'Decimal places:')
                for digit,(cx,cy) in enumerate(pts['decimal']):
                    c.circle(cx,HEIGHT-cy,3,stroke=1,fill=0);c.drawCentredString(cx,HEIGHT-cy+6,str(digit))
                for col in pts['digits']:
                    for cx,cy in col:c.circle(cx,HEIGHT-cy,2.7,stroke=1,fill=0)
                c.setFont('Helvetica',6)
                for digit in range(10):c.drawRightString(x+27,HEIGHT-(y+61+8*digit)-2,str(digit))
                bx,by,bw,bh=pts['box'];c.rect(bx,HEIGHT-by-bh,bw,bh)
                c.drawString(x,HEIGHT-by-7,'Write:')
        c.setFont('Helvetica',8);c.drawString(42,HEIGHT-805,f'Page {page_index+1}/{len(pages)} | Review all detections before scoring. Unclear handwriting is entered by the teacher.')
        c.showPage()
    c.save();return out.getvalue()

def scan(aligned,items):
    gray=cv2.cvtColor(aligned,cv2.COLOR_BGR2GRAY)
    dark=cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)
    overlay=aligned.copy()
    def strengths(points,r=3):
        out=[]
        for x,y in points:
            cx,cy=round(x*2),round(y*2);crop=dark[cy-r:cy+r+1,cx-r:cx+r+1]
            yy,xx=np.ogrid[-r:r+1,-r:r+1];mask=xx*xx+yy*yy<=r*r
            strength=float(np.mean(crop[mask]>0));out.append(strength)
            if strength>.25:cv2.circle(overlay,(cx,cy),8,(0,100,255),1)
        return out
    def pick(points):
        values=strengths(points);marked=[i for i,v in enumerate(values) if v>=.70]
        uncertain=any(.25<v<.70 for v in values)
        return marked,uncertain,any(v>.25 for v in values)
    results=[]
    for item in items:
        answer='';status='blank'
        if item['type']=='numerical':
            pts=number_cells(item);groups=[pick(pts['sign']),pick(pts['decimal'])]+[pick(c) for c in pts['digits']]
            if all(len(marked)==1 and not unsure for marked,unsure,_ in groups):
                sign='-' if groups[0][0][0]==1 else '';decimals=groups[1][0][0]
                digits=''.join(str(g[0][0]) for g in groups[2:])
                answer=str(Decimal(sign+digits).scaleb(-decimals));status='marked'
            elif any(marked or any_ for marked,_,any_ in groups):status='uncertain';answer=None
            else:
                x,y,w,h=pts['box'];crop=dark[round((y+2)*2):round((y+h-2)*2),round((x+2)*2):round((x+w-2)*2)]
                if crop.size and float(np.mean(crop>0))>.012:status='written';answer=None
        else:
            marked,unsure,_=pick(choices(item));answer=''.join(item['labels'][i] for i in marked)
            if unsure:status='uncertain';answer=None
            elif len(marked)>1 and item['type']=='single_correct':status='multiple';answer=None
            elif marked:status='marked'
        results.append({'number':item['number'],'question_id':item['question_id'],'type':item['type'],'labels':item['labels'],'status':status,'answer':answer})
    ok,encoded=cv2.imencode('.jpg',overlay,[cv2.IMWRITE_JPEG_QUALITY,75])
    if not ok:raise ValueError('Could not create the review preview.')
    return results,encoded.tobytes()

def parse_code(code):
    match=re.fullmatch(r'JEEOMR3:([0-9a-f]{32}):(\d{1,3})',code)
    return f'v3:{match[1]}:{int(match[2])}' if match else None
