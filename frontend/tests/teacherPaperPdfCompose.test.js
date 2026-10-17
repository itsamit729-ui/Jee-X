import test from 'node:test'
import assert from 'node:assert/strict'
import {jsPDF} from 'jspdf'
import {composePaperPdf,PDF_PAGE} from '../src/lib/teacherPaperPdfCompose.js'

const pixel='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGP8//8/AwMDEwMDAwMDAwAkBgMB/DXemwAAAABJRU5ErkJggg=='
function raster(height){return {height,parts:[{data:pixel,width:500,height:height*500/(PDF_PAGE.width-80)}]}}
function fixture(count=30){return {id:1,title:'Physics',sets_enabled:true,variant_b:Array.from({length:count},(_,i)=>count-i),questions:Array.from({length:count},(_,i)=>({question_id:i+1,subject:i%2?'CHEM':'PHY',type:'single_correct'}))}}
function observe(){const images=[],texts=[],pdfs=[];function Factory(options){const pdf=new jsPDF(options),image=pdf.addImage,text=pdf.text;pdf.addImage=function(...args){images.push({y:args[3],height:args[5]});return image.apply(pdf,args)};pdf.text=function(value,...args){texts.push(value);return text.call(pdf,value,...args)};pdfs.push(pdf);return pdf}return {Factory,images,texts,pdfs}}

test('real PDFs retain A/B question order, numbering and page bounds when question rasters are reused',async()=>{
  const paper=fixture(),rendered=new Map([['header',raster(140)],...paper.questions.map(q=>[String(q.question_id),raster(q.question_id===9?600:140)])])
  for(const variant of ['A','B']) {
    const {Factory,images,texts,pdfs}=observe()
    const blob=composePaperPdf(paper,variant,{jsPDF:Factory,rendered})
    assert.equal(blob.type,'application/pdf')
    assert.match(new TextDecoder().decode(await blob.arrayBuffer()),/^%PDF/)
    assert.deepEqual(texts.filter(t=>/^Question \d+$/.test(t)),Array.from({length:30},(_,i)=>`Question ${i+1}`))
    const ids=variant==='B'?paper.variant_b:paper.questions.map(q=>q.question_id)
    assert.deepEqual(texts.filter(t=>t.endsWith('| single correct')),ids.map(id=>`${paper.questions[id-1].subject} | single correct`))
    assert.ok(images.every(image=>image.y>=PDF_PAGE.margin&&image.y+image.height<=PDF_PAGE.bottom+.01))
    assert.ok(pdfs[0].getNumberOfPages()>1)
    assert.equal(texts.filter(t=>t.includes(`| Set ${variant}`)).length,pdfs[0].getNumberOfPages())
  }
})

test('multi-page questions retain every segment and invalid variant orders fail visibly',()=>{
  const paper=fixture(2),rendered=new Map([['header',raster(140)],['1',{height:1200,parts:[...raster(700).parts,...raster(500).parts]}],['2',raster(100)]])
  const {Factory,images}=observe()
  composePaperPdf(paper,'A',{jsPDF:Factory,rendered})
  assert.equal(images.length,4)
  assert.ok(images.every(image=>image.y+image.height<=PDF_PAGE.bottom+.01))
  assert.throws(()=>composePaperPdf({...paper,variant_b:[1,1]},'B',{jsPDF:Factory,rendered}),/question order is incomplete/)
})
