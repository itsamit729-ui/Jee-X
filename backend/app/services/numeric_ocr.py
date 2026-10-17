"""Local, conservative recognition of one handwritten character per answer box.

Digits use the bundled ONNX MNIST CNN through OpenCV (no remote calls). Signs
and decimal points use geometry. Disagreement and malformed numbers require review; the answer key is never used to influence recognition.
"""
import hashlib
import re
from functools import lru_cache
from pathlib import Path
from threading import Lock
import cv2
import numpy as np

MODEL=Path(__file__).resolve().parents[1]/'data/numeric_ocr/mnist-12.onnx'
MODEL_SHA='5c688690f8bacf667d4c2074af5ad0646ca328d7ab03eccf944a65b320171bdd'
LOCK=Lock()
MIN_CONFIDENCE=.999


@lru_cache(maxsize=1)
def model():
    if hashlib.sha256(MODEL.read_bytes()).hexdigest()!=MODEL_SHA:
        raise ValueError('Number recognizer checksum failed.')
    return cv2.dnn.readNetFromONNX(str(MODEL))


def digit(image):
    ys,xs=np.nonzero(image)
    if len(xs)<8:return None,0.0
    x,y,w,h=cv2.boundingRect(np.column_stack((xs,ys)).astype(np.int32))
    glyph=image[y:y+h,x:x+w]
    scale=20/max(w,h)
    resized=cv2.resize(glyph,(max(1,round(w*scale)),max(1,round(h*scale))),interpolation=cv2.INTER_AREA)
    canvas=np.zeros((28,28),np.float32);rh,rw=resized.shape
    canvas[(28-rh)//2:(28-rh)//2+rh,(28-rw)//2:(28-rw)//2+rw]=resized.astype(np.float32)/255
    moments=cv2.moments(canvas)
    canvas=cv2.warpAffine(canvas,np.float32([[1,0,13.5-moments['m10']/moments['m00']],[0,1,13.5-moments['m01']/moments['m00']]]),(28,28))
    votes=[];scores=[]
    with LOCK:
        net=model()
        for dx,dy in [(0,0),(-.5,0),(.5,0),(0,.5)]:
            view=cv2.warpAffine(canvas,np.float32([[1,0,dx],[0,1,dy]]),(28,28))
            net.setInput(view.reshape(1,1,28,28));logits=net.forward().reshape(-1)
            probabilities=np.exp(logits-np.max(logits));probabilities/=probabilities.sum()
            best=int(np.argmax(probabilities));votes.append(best);scores.append(float(probabilities[best]))
    confidence=min(scores)
    if len(set(votes))!=1 or confidence<MIN_CONFIDENCE:return None,confidence
    return str(votes[0]),confidence


def read_number(gray,boxes):
    chars=[];confidences=[];ended=False
    for x,y,w,h in boxes:
        # Geometry is in PDF points; the detector aligns all scans to 2x A4.
        cell=gray[round((y+3)*2):round((y+h-3)*2),round((x+3)*2):round((x+w-3)*2)]
        if not cell.size:return {'answer':None,'status':'uncertain','confidence':0.0}
        _,ink=cv2.threshold(cell,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
        count,labels,stats,_=cv2.connectedComponentsWithStats(ink)
        clean=np.zeros_like(ink)
        for label in range(1,count):
            if stats[label,cv2.CC_STAT_AREA]>=3:clean[labels==label]=255
        ys,xs=np.nonzero(clean)
        if len(xs)<3:
            if chars:ended=True
            continue
        if ended:return {'answer':None,'status':'uncertain','confidence':0.0}
        left,top,width,height=cv2.boundingRect(np.column_stack((xs,ys)).astype(np.int32))
        if left==0 or top==0 or left+width>=cell.shape[1] or top+height>=cell.shape[0]:
            return {'answer':None,'status':'uncertain','confidence':0.0}
        if height<=max(4,cell.shape[0]*.15) and width>=height*3 and width>=8:
            char,confidence='-',1.0
        elif width<=cell.shape[1]*.3 and height<=cell.shape[0]*.22 and top>=cell.shape[0]*.55:
            char,confidence='.',1.0
        else:
            try:char,confidence=digit(clean)
            except (OSError,ValueError,cv2.error):char,confidence=None,0.0
        if char is None:return {'answer':None,'status':'uncertain','confidence':round(confidence,4)}
        chars.append(char);confidences.append(confidence)
    if not chars:return {'answer':'','status':'blank','confidence':1.0}
    answer=''.join(chars)
    if not re.fullmatch(r'-?(?:\d+(?:\.\d*)?|\.\d+)',answer):
        return {'answer':None,'status':'uncertain','confidence':0.0}
    return {'answer':answer,'status':'marked','confidence':round(min(confidences),4)}
