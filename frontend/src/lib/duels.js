import {request} from './api.js'
export const formats = [{count:5,minutes:5,label:'Sprint'},{count:10,minutes:15,label:'Duel'},{count:15,minutes:25,label:'Endurance'}]
export const examNames = {jee_main:'JEE Main',mht_cet:'MHT-CET',bitsat:'BITSAT'}
export const duelService = {
  list:()=>request('/api/duels',{cache:false}),
  create:body=>request('/api/duels',{method:'POST',body}),
  get:(id,paper=true)=>request(`/api/duels/${encodeURIComponent(id)}?paper=${paper}`,{cache:false}),
  action:(id,action)=>request(`/api/duels/${encodeURIComponent(id)}/${action}`,{method:'POST'}),
  save:(id,q,body)=>request(`/api/duels/${encodeURIComponent(id)}/answers/${encodeURIComponent(q)}`,{method:'PUT',body}),
}
export function secondsUntil(timestamp,now,offset=0){return Math.max(0,Math.ceil((Date.parse(timestamp)-now-offset)/1000))}
export function resultTitle(match,userId){return match.winner_id==null?'A draw. Well played.':match.winner_id===userId?'You won this round.':'A rematch awaits.'}
