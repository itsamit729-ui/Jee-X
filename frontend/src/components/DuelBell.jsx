import {useEffect,useState} from 'react'
import {Link} from 'react-router-dom'
import {Swords} from 'lucide-react'
import {request} from '../lib/api.js'
export default function DuelBell(){
 const [count,setCount]=useState(0)
 useEffect(()=>{let alive=true;const load=()=>{if(document.visibilityState==='hidden')return;request('/api/duels/invitations/count',{cache:false}).then(d=>{if(alive)setCount(d.count)}).catch(()=>{})};load();const timer=setInterval(load,30000);window.addEventListener('focus',load);return()=>{alive=false;clearInterval(timer);window.removeEventListener('focus',load)}},[])
 return <Link className="studio-more" to="/duels" aria-label={`1v1 challenges${count?`, ${count} incoming`:''}`} title="1v1 challenges"><Swords size={18}/>{count>0&&<strong>{count}</strong>}</Link>
}
