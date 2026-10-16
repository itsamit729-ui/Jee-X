import { createRoot } from 'react-dom/client'
import { flushSync } from 'react-dom'
import MathText from '../components/MathText.jsx'
import { optionDisplay } from './questionOptions.js'
import { paperDiagramUrls, fetchPaperDiagram } from './teacherPaperImages.js'

// Loaded only on download: render the same KaTeX maths in the browser, without
// installing a browser or running video/PDF rendering on the small web server.
const STYLE = `.tp-pdf-root{position:absolute;left:-12000px;top:0;width:714px;background:white;color:#111;font:16px/1.65 Arial,sans-serif;z-index:-1}.tp-pdf-root *{box-sizing:border-box}.tp-pdf-root h1{font-size:26px;line-height:1.3;margin:8px 0}.tp-pdf-root h2{font-size:17px;line-height:1.4;margin:0 0 10px}.tp-pdf-root p{margin:6px 0}.tp-pdf-root header{padding-bottom:20px;border-bottom:2px solid #222;margin-bottom:24px}.tp-pdf-root article{padding:4px 0 22px}.tp-pdf-root .pdf-option{display:flex;gap:12px;margin:8px 0}.tp-pdf-root .pdf-option>b{width:24px;flex-shrink:0}.tp-pdf-root figure{margin:12px 0}.tp-pdf-root img{display:block;max-width:100%;max-height:300px;object-fit:contain}.tp-pdf-root .pdf-passage{padding:10px;border:1px solid #ddd;margin-bottom:12px}.tp-pdf-root .math-block{display:block;margin:10px 0}.tp-pdf-root .katex-display{margin:8px 0}.tp-pdf-root .pdf-meta{font-size:13px;color:#444}`
function Assets({assets=[],images}) {return assets.map((a,i)=><figure key={i}><img src={images.get(a.url)} alt={a.alt_text||'Question diagram'}/></figure>)}
function Paper({paper,variant,images}) {
  const questions=variant==='B'?paper.variant_b.map(id=>paper.questions.find(q=>q.question_id===id)):paper.questions
  return <><style>{STYLE}</style><header data-pdf-block><span className="pdf-meta">JEE EDGE · {paper.settings.exam.replaceAll('_',' ').toUpperCase()} · {paper.sets_enabled?`SET ${variant}`:'STANDARD PAPER'}</span><h1>{paper.title}</h1><p>{questions.length} questions · {paper.settings.duration_minutes} minutes · +{paper.settings.marks_correct} / −{paper.settings.marks_wrong}</p><MathText text={paper.settings.instructions}/><p className="pdf-meta">Name: ____________________________ &nbsp; OMR ID: __________________</p></header>{questions.map((q,i)=><article data-pdf-block key={q.question_id}><h2>Question {i+1} <span className="pdf-meta">· {q.subject} · {q.type.replaceAll('_',' ')}</span></h2>{q.passage&&<div className="pdf-passage"><MathText text={q.passage.body}/><Assets assets={q.passage.assets} images={images}/></div>}<div><MathText text={q.stem}/></div><Assets assets={q.assets} images={images}/>{q.type==='numerical'?<p className="pdf-meta">Numerical answer: __________________</p>:q.options.map(o=><div className="pdf-option" key={o.label}><b>({o.label})</b><div><MathText text={optionDisplay(q,o).text}/></div></div>)}</article>)}</>
}
async function imageData(paper,index,url) {
  let blob
  try {blob=await fetchPaperDiagram(paper.id,index,url)}
  catch(error){const qi=paper.questions.findIndex(q=>[...(q.assets||[]),...(q.passage?.assets||[])].some(a=>a.url===url));const q=paper.questions[qi];throw Error(`Question ${qi+1}${q?.ref?` (${q.ref})`:''}: ${error.message}`)}
  return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('A diagram could not be read. Please retry.'));reader.readAsDataURL(blob)})
}
function blankCut(canvas,start,desired) {
  const context=canvas.getContext('2d',{willReadFrequently:true}), lower=Math.max(start+80,desired-140)
  for(let y=desired;y>lower;y-=2){const row=context.getImageData(0,y,canvas.width,1).data;let blank=true;for(let x=0;x<row.length;x+=4){if(row[x]<245||row[x+1]<245||row[x+2]<245){blank=false;break}}if(blank)return y}
  return desired
}
export async function downloadPaperPdf(paper,variant='A',progress=()=>{}) {
  if(!paper.finalized)throw Error('This paper is not ready to download.')
  const [{jsPDF},{default:html2canvas}]=await Promise.all([import('jspdf'),import('html2canvas')])
  const urls=paperDiagramUrls(paper)
  const images=new Map()
  // Bound parallel fetches so large papers do not overwhelm mobile browsers.
  for(let i=0;i<urls.length;i+=4){await Promise.all(urls.slice(i,i+4).map(async (url,j)=>images.set(url,await imageData(paper,i+j,url))))}
  const host=document.createElement('div');host.className='tp-pdf-root';host.setAttribute('aria-hidden','true');document.body.append(host)
  const root=createRoot(host)
  try {
    flushSync(()=>root.render(<Paper paper={paper} variant={variant} images={images}/>))
    await document.fonts.ready
    await Promise.all([...host.querySelectorAll('img')].map(img=>img.decode()))
    const pdf=new jsPDF({unit:'pt',format:'a4',compress:true});pdf.setProperties({title:paper.title,creator:'Jee Edge'})
    const width=pdf.internal.pageSize.getWidth(),height=pdf.internal.pageSize.getHeight(),margin=40,usable=width-margin*2,bottom=height-44
    let y=margin
    const blocks=[...host.querySelectorAll('[data-pdf-block]')]
    for(let i=0;i<blocks.length;i++) {
      progress(`Preparing PDF ${i+1}/${blocks.length}…`)
      const block=blocks[i]
      // Reduce unusually wide display equations to the printable content width.
      for(const math of block.querySelectorAll('.katex-display')){if(math.scrollWidth>714)math.style.fontSize=`${Math.max(9,16*714/math.scrollWidth)}px`}
      const canvas=await html2canvas(block,{scale:1.7,backgroundColor:'#ffffff',logging:false,useCORS:true,allowTaint:false,windowWidth:1000})
      const ratio=usable/canvas.width,total=canvas.height*ratio
      if(total<=bottom-margin&&y+total>bottom){pdf.addPage();y=margin}
      let start=0
      while(start<canvas.height) {
        let available=Math.floor((bottom-y)/ratio)
        if(available<40){pdf.addPage();y=margin;available=Math.floor((bottom-y)/ratio)}
        let end=Math.min(canvas.height,start+available)
        if(end<canvas.height)end=blankCut(canvas,start,end)
        const slice=document.createElement('canvas');slice.width=canvas.width;slice.height=end-start
        slice.getContext('2d').drawImage(canvas,0,start,canvas.width,end-start,0,0,canvas.width,end-start)
        pdf.addImage(slice.toDataURL('image/jpeg',0.94),'JPEG',margin,y,usable,slice.height*ratio)
        y+=slice.height*ratio;start=end;slice.width=slice.height=0
        if(start<canvas.height){pdf.addPage();y=margin}
      }
      canvas.width=canvas.height=0
      await new Promise(resolve=>requestAnimationFrame(resolve))
    }
    const pages=pdf.getNumberOfPages()
    for(let i=1;i<=pages;i++){pdf.setPage(i);pdf.setFontSize(9);pdf.setTextColor(90);pdf.text(`Jee Edge | Paper ${paper.id} | ${paper.sets_enabled?'Set '+variant:'Standard paper'}`,margin,height-22);pdf.text(`${i} / ${pages}`,width-margin,height-22,{align:'right'})}
    pdf.save(`paper-${paper.id}-${paper.sets_enabled?variant:'standard'}.pdf`)
  }finally{root.unmount();host.remove()}
}
