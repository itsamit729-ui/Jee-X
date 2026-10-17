// Share expensive rendering across A/B and repeated downloads, only in this tab.
export function paperPdfKey(paper) {
  return JSON.stringify([paper.id,paper.version,paper.title,paper.settings,paper.questions,paper.variant_b,paper.sets_enabled])
}

export function createPaperPdfCache({render,compose,limit=2}) {
  const entries=new Map()
  return async function prepare(paper,variant='A',progress=()=>{}) {
    const key=paperPdfKey(paper)
    let entry=entries.get(key)
    if(!entry) {
      entry={listeners:new Set(),pdfs:new Map(),last:{label:'Loading PDF tools…',percent:2}}
      entries.set(key,entry)
      while(entries.size>limit)entries.delete(entries.keys().next().value)
      const report=value=>{entry.last=value;for(const listener of entry.listeners)listener(value)}
      entry.content=Promise.resolve().then(()=>render(paper,report)).catch(error=>{
        if(entries.get(key)===entry)entries.delete(key)
        throw error
      })
    } else {entries.delete(key);entries.set(key,entry)}
    entry.listeners.add(progress)
    progress(entry.last)
    try {
      if(!entry.pdfs.has(variant)) {
        const job=entry.content.then(content=>compose(paper,variant,content))
          .catch(error=>{entry.pdfs.delete(variant);throw error})
        entry.pdfs.set(variant,job)
      }
      const blob=await entry.pdfs.get(variant)
      progress({label:'PDF ready',percent:100})
      return blob
    } finally {entry.listeners.delete(progress)}
  }
}

export function pdfCaptureBatches(blocks,maxHeight=3000,maxCount=6) {
  const batches=[]
  let batch=[],height=0
  for(const block of blocks) {
    if(batch.length&&(height+block.height>maxHeight||batch.length>=maxCount)) {
      batches.push(batch);batch=[];height=0
    }
    batch.push(block);height+=block.height
  }
  if(batch.length)batches.push(batch)
  return batches
}
