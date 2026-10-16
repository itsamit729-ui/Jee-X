// Retry the database import only after checking its transactional server cursor.
export const IMPORT_COUNTERS=['added','updated','unchanged','skipped','conflicts']
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms))
const retryable=error=>error.retryable!==false&&(!error.status||[408,409,429,500,502,503,504].includes(error.status))

function checked(state,preview) {
  if(state.digest!==preview.digest||state.total!==preview.eligible||!Number.isInteger(state.offset)||state.offset<0||state.offset>state.total) {
    throw Object.assign(new Error('The saved import does not match this preview. Review the dataset again.'),{retryable:false})
  }
  return state
}

export async function runPipelineImport({request,token,preview,onProgress=()=>{},onRetry=()=>{},isActive=()=>true,wait=pause}) {
  const path=`/api/admin/pipeline-questions/${preview.year}`
  const read=async()=>checked(await request(`${path}/progress`,{token,cache:false,timeoutMs:30_000}),preview)
  let state=await read(),failures=0
  onProgress(state)
  while(isActive()&&!state.finished) {
    try {
      const result=await request(`${path}/publish`,{token,method:'POST',timeoutMs:45_000,
        body:{expected_digest:preview.digest,offset:state.offset,limit:25}})
      const next=checked(result.progress,preview)
      if(next.offset<=state.offset&&!next.finished)throw Object.assign(new Error('The server did not confirm import progress.'),{retryable:false})
      state=next;failures=0;onRetry('');onProgress(state)
    } catch(error) {
      if(!isActive())break
      if(!retryable(error)||failures>=3)throw error
      failures+=1
      onRetry(`Connection interrupted. Checking saved progress before retry ${failures}/3…`)
      await wait(1000*failures)
      if(!isActive())break
      // If the POST committed despite a lost response, this cursor advances.
      // If the read fails, another bounded retry checks it before any POST.
      try {
        const saved=await read();state=saved;onProgress(state)
      } catch(readError) {
        if(!retryable(readError)||failures>=3)throw readError
        // Do not send a POST with unconfirmed state after a failed status check.
        let confirmed=false
        while(isActive()&&failures<3&&!confirmed) {
          failures+=1;await wait(1000*failures)
          try {state=await read();onProgress(state);confirmed=true}
          catch(nextError){if(!retryable(nextError)||failures>=3)throw nextError}
        }
        if(!confirmed&&isActive())throw readError
      }
    }
  }
  if(state.finished)onRetry('')
  return state
}
