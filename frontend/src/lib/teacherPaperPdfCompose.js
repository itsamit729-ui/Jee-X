export const PDF_PAGE={width:595.28,height:841.89,margin:40,bottom:797.89}
const PAGE=PDF_PAGE
export function composePaperPdf(paper,variant,{jsPDF,rendered}) {
  const byId=new Map(paper.questions.map(q=>[q.question_id,q]))
  const order=variant==='B'?paper.variant_b:paper.questions.map(q=>q.question_id)
  if(!Array.isArray(order)||order.length!==paper.questions.length||new Set(order).size!==order.length||order.some(id=>!byId.has(id)||!rendered.has(String(id))))throw Error('The saved question order is incomplete. Reopen the saved paper and try again.')
  const pdf=new jsPDF({unit:'pt',format:'a4',compress:true});pdf.setProperties({title:paper.title,creator:'Jee Edge'})
  const usable=PAGE.width-PAGE.margin*2
  let y=PAGE.margin
  pdf.setFontSize(10);pdf.setTextColor(80);pdf.text(`JEE EDGE  |  ${paper.sets_enabled?'SET '+variant:'STANDARD PAPER'}`,PAGE.margin,y);y+=18
  function add(block) {
    for(const part of block.parts) {
      const height=part.height*usable/part.width
      if(y+height>PAGE.bottom){pdf.addPage();y=PAGE.margin}
      pdf.addImage(part.data,'JPEG',PAGE.margin,y,usable,height,undefined,'FAST')
      y+=height
    }
  }
  add(rendered.get('header'));y+=20
  order.forEach((id,i)=>{
    const q=byId.get(id),block=rendered.get(String(id))
    if(y+22+Math.min(block.height,PAGE.bottom-PAGE.margin-28)>PAGE.bottom){pdf.addPage();y=PAGE.margin}
    pdf.setFont('helvetica','bold');pdf.setFontSize(12);pdf.setTextColor(20)
    pdf.text(`Question ${i+1}`,PAGE.margin,y+12)
    pdf.setFont('helvetica','normal');pdf.setFontSize(9);pdf.setTextColor(90)
    pdf.text(`${q.subject} | ${q.type.replaceAll('_',' ')}`,PAGE.margin+90,y+12)
    y+=22;add(block);y+=10
  })
  const pages=pdf.getNumberOfPages()
  for(let i=1;i<=pages;i++){pdf.setPage(i);pdf.setFontSize(9);pdf.setTextColor(90);pdf.text(`Jee Edge | Paper ${paper.id} | ${paper.sets_enabled?'Set '+variant:'Standard paper'}`,PAGE.margin,PAGE.height-22);pdf.text(`${i} / ${pages}`,PAGE.width-PAGE.margin,PAGE.height-22,{align:'right'})}
  return pdf.output('blob')
}
