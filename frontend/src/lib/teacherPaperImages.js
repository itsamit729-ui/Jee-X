import { API_URL } from './api.js'

export function paperDiagramUrls(paper) {
  return [...new Set(paper.questions.flatMap(q=>[...(q.assets||[]),...(q.passage?.assets||[])]).map(a=>a.url))]
}

export async function fetchPaperDiagram(paperId,index,url,{fetchImpl=fetch,apiBase=API_URL}={}) {
  if(typeof url!=='string'||!(/^(https?:\/\/|\/(?!\/))/i.test(url)))throw Error('Invalid diagram URL. Open the saved paper to inspect this question.')
  const path=new URL(url,'https://paper.invalid').pathname
  // Resolve local bank assets through the saved snapshot, including URLs that
  // still point to an old website hostname. The server never fetches arbitrary URLs.
  const local=path.startsWith('/question-images/')
  const backendUrl=`${apiBase}/api/teacher/papers/${paperId}/diagrams/${index}`
  const candidates=local?(url.startsWith('/')?[url,backendUrl]:[backendUrl,url]):[url]
  let last
  for(const candidate of [...new Set(candidates)]) {
    for(let attempt=0;attempt<2;attempt++) {
      try {
        const response=await fetchImpl(candidate,{credentials:candidate===backendUrl?'include':'same-origin',headers:candidate===backendUrl?{'X-Jee-Request':'1'}:{},signal:AbortSignal.timeout(15000)})
        if(response.status===401||response.status===403) {
          // Session problems must remain visible; do not disguise them as a missing figure.
          const error=Error('Sign in again, then reopen this saved paper.');error.auth=true;throw error
        }
        if(!response.ok){const error=Error(`Image request returned HTTP ${response.status}. Retry the download; the saved paper is intact.`);error.retry=response.status===429||response.status>=500;throw error}
        const blob=await response.blob()
        if(!blob.type.startsWith('image/'))throw Error('The image request returned a page instead of a diagram. Open the saved paper to inspect this question.')
        if(!blob.size||blob.size>10000000)throw Error('The diagram file is empty or too large to download.')
        return blob
      }catch(error){
        if(error.auth)throw error
        last=error
        if(attempt||!(error.retry||error.name==='TimeoutError'||error.name==='AbortError'||error instanceof TypeError))break
        await new Promise(resolve=>setTimeout(resolve,350))
      }
    }
  }
  throw last||Error('The diagram could not be loaded. Retry the download.')
}
