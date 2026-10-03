import { useEffect, useState } from 'react'
import { Compass } from 'lucide-react'
import { request } from '../lib/api.js'
import TopicStudyPlan from './TopicStudyPlan.jsx'

export default function GoalJourney({ afterTest = false, attemptId, ...props }) {
  const [data,setData] = useState(null), [error,setError] = useState(''), [retry,setRetry] = useState(0)
  useEffect(() => {
    let active = true
    setError('');setData(null)
    request('/api/roadmap/journey', afterTest || retry ? {cache:false} : {}).then(value => {if(active)setData(value)}).catch(e=>{if(active)setError(e.message)})
    return ()=>{active=false}
  },[attemptId,retry,afterTest])
  if(error)return <div className="journey-loading" role="alert">We couldn’t load your route. Your practice is still available below.<button className="btn btn-secondary" onClick={()=>setRetry(v=>v+1)}>Retry</button></div>
  if(!data)return <div className="journey-loading" role="status"><Compass size={20}/>Finding your next step…</div>
  return <TopicStudyPlan data={data} compact afterTest={afterTest} {...props}/>
}
