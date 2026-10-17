import { createRoot } from 'react-dom/client'
import { flushSync } from 'react-dom'
import MathText from '../components/MathText.jsx'
import { optionDisplay } from './questionOptions.js'
import { paperDiagramUrls, fetchPaperDiagram } from './teacherPaperImages.js'
import { createPaperPdfCache, pdfCaptureBatches } from './teacherPaperPdfCache.js'
import { composePaperPdf, PDF_PAGE } from './teacherPaperPdfCompose.js'

const STYLE = `.tp-pdf-root{position:absolute;left:-12000px;top:0;width:714px;background:white;color:#111;font:16px/1.65 Arial,sans-serif;z-index:-1}.tp-pdf-root *{box-sizing:border-box}.tp-pdf-root h1{font-size:26px;line-height:1.3;margin:8px 0}.tp-pdf-root p{margin:6px 0}.tp-pdf-root header{padding:0 0 20px;border-bottom:2px solid #222}.tp-pdf-root article{padding:4px 0 18px}.tp-pdf-root .pdf-option{display:flex;gap:12px;margin:8px 0}.tp-pdf-root .pdf-option>b{width:24px;flex-shrink:0}.tp-pdf-root figure{margin:12px 0}.tp-pdf-root img{display:block;max-width:100%;max-height:300px;object-fit:contain}.tp-pdf-root .pdf-passage{padding:10px;border:1px solid #ddd;margin-bottom:12px}.tp-pdf-root .math-block{display:block;margin:10px 0}.tp-pdf-root .katex-display{margin:8px 0}.tp-pdf-root .pdf-meta{font-size:13px;color:#444}`
const PAGE=PDF_PAGE
function Assets({assets=[],images}) {return assets.map((a,i)=><figure key={i}><img src={images.get(a.url)} alt={a.alt_text||'Question diagram'}/></figure>)}
function PaperContent({paper,images}) {
  return <><header data-pdf-block="header"><span className="pdf-meta">{paper.settings.exam.replaceAll('_',' ').toUpperCase()}</span><h1>{paper.title}</h1><p>{paper.questions.length} questions · {paper.settings.duration_minutes} minutes · +{paper.settings.marks_correct} / −{paper.settings.marks_wrong}</p><MathText text={paper.settings.instructions}/><p className="pdf-meta">Name: ____________________________ &nbsp; OMR ID: __________________</p></header>{paper.questions.map(q=><article data-pdf-block={q.question_id} key={q.question_id}>{q.passage&&<div className="pdf-passage"><MathText text={q.passage.body}/><Assets assets={q.passage.assets} images={images}/></div>}<div><MathText text={q.stem}/></div><Assets assets={q.assets} images={images}/>{q.type==='numerical'?<p className="pdf-meta">Numerical answer: __________________</p>:q.options.map(o=><div className="pdf-option" key={o.label}><b>({o.label})</b><div><MathText text={optionDisplay(q,o).text}/></div></div>)}</article>)}</>
}
async function imageData(paper,index,url) {
  let blob
  try {blob=await fetchPaperDiagram(paper.id,index,url)}
  catch(error){const qi=paper.questions.findIndex(q=>[...(q.assets||[]),...(q.passage?.assets||[])].some(a=>a.url===url));const q=paper.questions[qi];throw Error(`Question ${qi+1}${q?.ref?` (${q.ref})`:''}: ${error.message}`)}
  return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('A diagram could not be read. Please retry.'));reader.readAsDataURL(blob)})
}
function blankCut(canvas,start,desired) {
  const context=canvas.getContext('2d',{willReadFrequently:true}),lower=Math.max(start+80,desired-140)
  for(let y=desired-1;y>lower;y-=2){const row=context.getImageData(0,y,canvas.width,1).data;let blank=true;for(let x=0;x<row.length;x+=4){if(row[x]<245||row[x+1]<245||row[x+2]<245){blank=false;break}}if(blank)return y}
  return desired
}
function rasterBlock(canvas,top,height) {
  const width=canvas.width,ratio=(PAGE.width-2*PAGE.margin)/width
  const maxHeight=Math.floor((PAGE.bottom-PAGE.margin-28)/ratio)
  const parts=[]
  let start=top,end=top+height
  while(start<end) {
    let cut=Math.min(end,start+maxHeight)
    if(cut<end)cut=blankCut(canvas,start,cut)
    const slice=document.createElement('canvas');slice.width=width;slice.height=cut-start
    slice.getContext('2d').drawImage(canvas,0,start,width,cut-start,0,0,width,cut-start)
    parts.push({data:slice.toDataURL('image/jpeg',0.94),width,height:slice.height})
    slice.width=slice.height=0;start=cut
  }
  return {parts,height:height*ratio}
}

async function renderContent(paper,progress) {
  const [{jsPDF},{default:html2canvas}]=await Promise.all([import('jspdf'),import('html2canvas')])
  const urls=paperDiagramUrls(paper),images=new Map()
  progress({label:urls.length?'Loading question diagrams…':'Typesetting questions…',percent:8})
  for(let i=0;i<urls.length;i+=4)await Promise.all(urls.slice(i,i+4).map(async(url,j)=>images.set(url,await imageData(paper,i+j,url))))
  const style=document.createElement('style');style.textContent=STYLE;document.head.append(style)
  const host=document.createElement('div');host.className='tp-pdf-root';host.dataset.pdfSource='true';host.setAttribute('aria-hidden','true');document.body.append(host)
  const root=createRoot(host),rendered=new Map()
  try {
    flushSync(()=>root.render(<PaperContent paper={paper} images={images}/>))
    await document.fonts.ready
    await Promise.all([...host.querySelectorAll('img')].map(img=>img.decode()))
    for(const math of host.querySelectorAll('.katex-display'))if(math.scrollWidth>714)math.style.fontSize=`${Math.max(9,16*714/math.scrollWidth)}px`
    const blocks=[...host.querySelectorAll('[data-pdf-block]')].map(node=>({node,height:node.getBoundingClientRect().height}))
    const batches=pdfCaptureBatches(blocks)
    let completed=0
    for(const batch of batches) {
      const capture=document.createElement('div');capture.className='tp-pdf-root';capture.setAttribute('aria-hidden','true')
      batch.forEach(({node})=>capture.append(node.cloneNode(true)))
      document.body.append(capture)
      let canvas
      try {
        const rect=capture.getBoundingClientRect()
        const positions=[...capture.children].map(node=>({id:node.dataset.pdfBlock,top:node.getBoundingClientRect().top-rect.top,height:node.getBoundingClientRect().height}))
        canvas=await html2canvas(capture,{scale:1.7,backgroundColor:'#ffffff',logging:false,useCORS:true,allowTaint:false,windowWidth:1000,
          ignoreElements:node=>node.id==='root'||node.dataset?.pdfSource==='true'})
        const scale=canvas.width/rect.width
        for(const block of positions) {
          const top=Math.round(block.top*scale),end=Math.min(canvas.height,Math.round((block.top+block.height)*scale))
          rendered.set(block.id,rasterBlock(canvas,top,end-top))
        }
      } finally {if(canvas)canvas.width=canvas.height=0;capture.remove()}
      completed+=batch.length
      progress({label:`Preparing questions ${Math.min(completed-1,paper.questions.length)} of ${paper.questions.length}…`,percent:Math.round(20+completed/blocks.length*70)})
      await new Promise(resolve=>setTimeout(resolve,0))
    }
    return {jsPDF,rendered}
  }finally{root.unmount();host.remove();style.remove()}
}

const cachedPdf=createPaperPdfCache({render:renderContent,compose:composePaperPdf})
export function preparePaperPdf(paper,variant='A',progress=()=>{}) {
  if(!paper.finalized)return Promise.reject(Error('This paper is not ready to download.'))
  if(!['A','B'].includes(variant)||(variant==='B'&&!paper.sets_enabled))return Promise.reject(Error('This paper does not have that set.'))
  return cachedPdf(paper,variant,progress)
}
export async function downloadPaperPdf(paper,variant='A',progress=()=>{}) {
  const blob=await preparePaperPdf(paper,variant,value=>progress(value.label))
  const url=URL.createObjectURL(blob),link=document.createElement('a')
  link.href=url;link.download=`paper-${paper.id}-${paper.sets_enabled?variant:'standard'}.pdf`
  document.body.append(link);link.click();link.remove()
  setTimeout(()=>URL.revokeObjectURL(url),60000)
}
