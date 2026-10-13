"""Fixed-layout OMR. No OCR guesses: ambiguous bubbles require teacher review."""
import io
import os
import tempfile
from pathlib import Path
from threading import Semaphore
import numpy as np
import cv2
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing

WIDTH, HEIGHT = 595, 842
MARKERS = np.float32([[24,24],[571,24],[571,818],[24,818]])
WORK = Path(os.getenv('TEACHER_SCAN_DIR', tempfile.gettempdir()+'/jeeedge-omr'))
GATE = Semaphore(1)
cv2.setNumThreads(1)

def path(identity, suffix='png'):
    if len(identity)!=32 or any(c not in '0123456789abcdef' for c in identity): raise ValueError('Invalid scan identity')
    WORK.mkdir(parents=True,exist_ok=True)
    return WORK / (identity+'.'+suffix)

def cells(index,id_grid=False):
    col,row=divmod(index,50)
    return [(42+138*col+32+20*k,(330+8.5*row if id_grid else 210+11*row)) for k in range(4)]

def id_cells(column):
    return [(54+20*column,190+12*digit) for digit in range(10)]


def sheet_pdf(paper,sheet,name):
    from app.services import mixed_omr
    if mixed_omr.needs_mixed(getattr(paper,'questions',[])): return mixed_omr.pdf(paper,sheet,name)
    id_grid=name is None
    out=io.BytesIO(); c=canvas.Canvas(out,pagesize=(WIDTH,HEIGHT))
    c.setTitle('Jee Edge OMR - '+paper.title)
    for x,y in MARKERS:
        c.rect(float(x)-5,HEIGHT-float(y)-5,10,10,fill=1,stroke=0)
    c.setFont('Helvetica-Bold',16);c.drawString(42,HEIGHT-62,'Jee Edge | Answer sheet')
    c.setFont('Helvetica',10)
    # Reusable copies identify only the paper/set; the teacher assigns the student.
    set_label=f'Set {sheet.variant}' if (getattr(paper,'settings',None) or {}).get('sets_enabled',True) else 'Standard paper - no sets'
    student_line='Name: ________________________________________' if name is None else 'Student: '+name[:50]
    for y,text in [(86,paper.title[:65]),(106,student_line),(126,f'Paper {paper.id} | Version {paper.version} | {set_label}'),(151,'Fill one bubble completely with a dark pen. Do not fold the sheet.'),(167,'Print at 100% on A4. Keep all four corner squares visible in your photo.')]:
        if id_grid and y>=140: continue
        while c.stringWidth(text,'Helvetica',10)>(400 if y<140 else 510): text=text[:-1]
        c.drawString(42,HEIGHT-y,text)
    qr=QrCodeWidget('JEEOMR:'+sheet.id);x1,y1,x2,y2=qr.getBounds();d=Drawing(78,78,transform=[78/(x2-x1),0,0,78/(y2-y1),0,0]);d.add(qr)
    renderPDF.draw(d,c,WIDTH-125,HEIGHT-140)
    if id_grid:
        c.setFont('Helvetica-Bold',9);c.drawString(42,HEIGHT-149,'STUDENT OMR ID - write and shade all 10 digits')
        for column in range(10):
            x=54+20*column;c.rect(x-8,HEIGHT-178,16,18)
            for x,y in id_cells(column): c.circle(x,HEIGHT-y,3.5,stroke=1,fill=0)
        c.setFont('Helvetica',8)
        for digit in range(10): c.drawRightString(40,HEIGHT-(190+12*digit)-3,str(digit))
        for y,text in [(193,'Use the OMR ID shown in My classroom.'),(209,'Include every leading zero.'),(225,'Write one digit in each box.'),(241,'Shade that digit below the same box.'),(257,'Fill exactly one bubble per column.'),(281,'Fill answers in dark ink. Print A4 at 100%.'),(297,'Keep all four corner squares visible.')]:
            c.drawString(285,HEIGHT-y,text)
    for col in range((len(sheet.question_order)+49)//50):
        c.setFont('Helvetica-Bold',8)
        for k,(x,y) in enumerate(cells(col*50,id_grid)): c.drawCentredString(x,HEIGHT-(318 if id_grid else 197),'ABCD'[k])
    for i,_ in enumerate(sheet.question_order):
        pts=cells(i,id_grid);c.setFont('Helvetica',8);c.drawRightString(pts[0][0]-12,HEIGHT-pts[0][1]-3,str(i+1))
        for k,(x,y) in enumerate(pts):
            c.circle(x,HEIGHT-y,3.4 if id_grid else 4,stroke=1,fill=0)
    c.setFont('Helvetica',8);c.drawString(42,40,'Use only with its matching question paper. Review scan results before publishing scores.')
    c.showPage();c.save();return out.getvalue()

def decode_image(data):
    with Image.open(io.BytesIO(data)) as image:
        if image.width*image.height>25_000_000: raise ValueError('Image is too large. Use a photo below 25 megapixels.')
        image=ImageOps.exif_transpose(image).convert('RGB');image.thumbnail((2200,2200))
        return cv2.cvtColor(np.asarray(image),cv2.COLOR_RGB2BGR)

def read_qr(aligned):
    detector=cv2.QRCodeDetector()
    code,points,_=detector.detectAndDecode(aligned)
    if code:return code,points
    # Dense numerical grids can distract the full-page QR locator. The QR has
    # fixed geometry; try isolated upright and upside-down corners as well.
    for x1,y1,x2,y2 in [(880,70,1160,320),(30,1364,310,1614)]:
        crop=aligned[y1:y2,x1:x2]
        code,points,_=detector.detectAndDecode(cv2.resize(crop,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC))
        if code:
            if points is not None:points=points/2+np.float32([x1,y1])
            return code,points
    return '',None

def detect(data):
    image=decode_image(data); gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    _,binary=cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    contours,_=cv2.findContours(binary,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    h,w=gray.shape;squares=[]
    for contour in contours:
        area=cv2.contourArea(contour)
        x,y,cw,ch=cv2.boundingRect(contour)
        if 25<area<w*h*.008 and .65<cw/max(ch,1)<1.5 and area/(cw*ch)>.7:
            squares.append((x+cw/2,y+ch/2))
    corners=[]
    for tx,ty in [(0,0),(w,0),(w,h),(0,h)]:
        choices=[p for p in squares if abs(p[0]-tx)<w*.3 and abs(p[1]-ty)<h*.25]
        if not choices: raise ValueError('All four corner squares must be visible. Rescan the complete sheet on a plain background.')
        corners.append(min(choices,key=lambda p:(p[0]-tx)**2+(p[1]-ty)**2))
    if len(set(corners))!=4: raise ValueError('Could not align the page. Upload an upright A4 scan.')
    matrix=cv2.getPerspectiveTransform(np.float32(corners),MARKERS*2)
    aligned=cv2.warpPerspective(image,matrix,(WIDTH*2,HEIGHT*2),borderValue=(255,255,255))
    code,points=read_qr(aligned)
    if points is not None and points[0,:,1].mean()>HEIGHT:
        aligned=cv2.rotate(aligned,cv2.ROTATE_180)
        code,points=read_qr(aligned)
    if points is not None and not (points[0,:,0].mean()>WIDTH and points[0,:,1].mean()<HEIGHT*.45):
        raise ValueError('Sheet orientation could not be confirmed. Upload the page upright.')
    from app.services.mixed_omr import parse_code
    mixed=parse_code(code)
    if mixed:return mixed,aligned
    if not code.startswith('JEEOMR:') or len(code)!=39: raise ValueError('Matching Jee Edge QR code was not readable. Upload the correct sheet upright with a sharper QR code.')
    return code[7:],aligned

def bubbles(aligned,count,id_grid=False):
    gray=cv2.cvtColor(aligned,cv2.COLOR_BGR2GRAY)
    # Inner disk excludes the printed ring; option labels sit above the columns.
    dark=cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)
    results=[]
    overlay=aligned.copy()
    for i in range(count):
        scores=[]
        for x,y in cells(i,id_grid):
            cx,cy=int(x*2),int(y*2);r=4 if id_grid else 5
            crop=dark[cy-r:cy+r+1,cx-r:cx+r+1]
            yy,xx=np.ogrid[-r:r+1,-r:r+1];mask=xx*xx+yy*yy<=r*r
            scores.append(float(np.mean(crop[mask]>0)))
        marked=[k for k,v in enumerate(scores) if v>=.65]
        uncertain=any(.3<v<.65 for v in scores)
        status='multiple' if len(marked)>1 else 'uncertain' if uncertain else 'marked' if marked else 'blank'
        answer='ABCD'[marked[0]] if status=='marked' else ''
        results.append({'number':i+1,'status':status,'answer':answer,'strength':[round(v,3) for v in scores]})
        color=(0,130,0) if status in ('marked','blank') else (0,100,255)
        for k,(x,y) in enumerate(cells(i,id_grid)):
            if scores[k]>.3: cv2.circle(overlay,(int(x*2),int(y*2)),12,color,2)
    ok,encoded=cv2.imencode('.jpg',overlay,[cv2.IMWRITE_JPEG_QUALITY,75])
    if not ok: raise ValueError('Preview generation failed.')
    return results,encoded.tobytes()


def read_student_id(aligned):
    """Decode shaded digits only. Never guess from handwriting or roster proximity."""
    gray=cv2.cvtColor(aligned,cv2.COLOR_BGR2GRAY)
    dark=cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)
    digits=[];columns=[]
    for column in range(10):
        strengths=[]
        for x,y in id_cells(column):
            cx,cy=int(x*2),int(y*2);r=4
            crop=dark[cy-r:cy+r+1,cx-r:cx+r+1]
            yy,xx=np.ogrid[-r:r+1,-r:r+1];mask=xx*xx+yy*yy<=r*r
            strengths.append(float(np.mean(crop[mask]>0)))
        marked=[i for i,v in enumerate(strengths) if v>=.75]
        uncertain=any(.2<v<.75 for v in strengths)
        valid=len(marked)==1 and not uncertain
        digits.append(str(marked[0]) if valid else '?')
        columns.append({'column':column+1,'status':'clear' if valid else 'ambiguous','strength':[round(v,3) for v in strengths]})
    code=''.join(digits)
    return {'digits':code,'status':'clear' if '?' not in code else 'ambiguous','columns':columns}
