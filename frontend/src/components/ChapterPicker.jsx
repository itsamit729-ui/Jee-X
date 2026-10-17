import {useId,useState,useRef} from 'react'
import {rankedSearch} from '../lib/search.js'
import SearchField from './SearchField.jsx'
import './chapter-picker.css'
export default function ChapterPicker({chapters,value,onChange,loading=false}) {
 const trigger=useRef(null)
 const id=useId(),[open,setOpen]=useState(false),[query,setQuery]=useState('')
 const selected=chapters.find(c=>String(c.id)===String(value))
 const rows=rankedSearch(chapters,query)
 function choose(value){onChange(value);setOpen(false);setQuery('');trigger.current?.focus()}
 return <div className="chapter-picker" onBlur={event=>{if(!event.currentTarget.contains(event.relatedTarget))setOpen(false)}} onKeyDown={event=>{if(event.key==='Escape'){setOpen(false);event.currentTarget.querySelector('button')?.focus()}}}>
   <button ref={trigger} type="button" aria-label="Choose chapter" className="input chapter-picker-trigger" disabled={loading} aria-expanded={open} aria-controls={id} onClick={()=>setOpen(v=>!v)}>{loading?'Loading chapters…':selected?.name||'All available chapters'}<span aria-hidden="true">⌄</span></button>
   {open&&<div className="chapter-picker-panel" id={id}><SearchField label="Search chapters" placeholder="Search chapters…" value={query} onChange={e=>setQuery(e.target.value)} autoFocus/>
   <div className="chapter-picker-results" role="group" aria-label="Choose a chapter"><button type="button" aria-pressed={!value} onClick={()=>choose('')}>All available chapters</button>{rows.map(c=><button type="button" key={c.id} aria-pressed={String(value)===String(c.id)} onClick={()=>choose(String(c.id))}><span>{c.name}</span><small>{c.published_question_count??c.count??''} questions</small></button>)}{!rows.length&&<p role="status">No matching chapters. Try fewer words.</p>}</div></div>}
 </div>
}
