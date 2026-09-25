import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { ExternalLink, FileText, ArrowLeft } from 'lucide-react'
import { Logo } from '../components/Brand.jsx'
import AppHeader from '../components/AppHeader.jsx'
import syllabus from '../data/officialSyllabi.json'

export default function Syllabus() {
  const { isAuthenticated } = useAuth()
  return <>
    {isAuthenticated ? <AppHeader/> : <header className="appbar"><div className="wrap appbar-row"><Logo to="/"/><Link to="/" className="btn btn-quiet btn-sm"><ArrowLeft size={15}/> Home</Link></div></header>}
    <main className="wrap-narrow page">
      <div className="page-head"><p className="muted" style={{fontSize:12,letterSpacing:1}}>OFFICIAL EXAM RESOURCES · 2026</p><h1 className="page-title">Know what to prepare.</h1><p className="muted">Full syllabi published by the examination authorities, with quick links to each subject.</p></div>
      {syllabus.exams.map(exam => <section className="panel" key={exam.id} style={{marginBottom:24}} aria-labelledby={`${exam.id}-title`}>
        <div style={{display:'flex',alignItems:'center',gap:14,marginBottom:16}}><FileText size={28} color="#b66a36"/><div><h2 id={`${exam.id}-title`} style={{margin:0,fontSize:22}}>{exam.title} {exam.year}</h2><p className="muted" style={{fontSize:12,marginTop:6}}>{exam.publisher}</p></div></div>
        <p style={{fontSize:14,lineHeight:1.8,marginBottom:18}}>{exam.scope}</p>
        <div style={{display:'flex',gap:10,flexWrap:'wrap',marginBottom:22}}>
          <a className="btn btn-primary" href={exam.pdf_url} target="_blank" rel="noopener noreferrer">Open official syllabus PDF <ExternalLink size={15}/></a>
          <a className="btn btn-secondary" href={exam.official_site} target="_blank" rel="noopener noreferrer">Exam website <ExternalLink size={15}/></a>
        </div>
        <p className="muted" style={{fontSize:12,marginBottom:10}}>Jump to a subject in the official PDF</p>
        <div style={{display:'flex',gap:10,flexWrap:'wrap'}}>{exam.subjects.map(subject => <a key={subject.code} className="btn btn-secondary btn-sm" href={`${exam.pdf_url}#page=${subject.start_page}`} target="_blank" rel="noopener noreferrer">{subject.name} · p. {subject.start_page}<ExternalLink size={12}/></a>)}</div>
        <p className="muted" style={{fontSize:11,marginTop:18}}>{exam.pdf_pages} pages · English · Opens on the official publisher’s site</p>
      </section>)}
      <div className="panel"><h2 style={{fontSize:17,marginBottom:10}}>Preparing for 2027?</h2><p className="muted" style={{fontSize:14,lineHeight:1.8}}>These links were checked on 20 September 2026 and refer to the 2026 editions. Confirm your examination year’s syllabus and subsequent notices on the official websites.</p><p className="muted" style={{fontSize:12,marginTop:12}}>Subject links use PDF page numbers. If your viewer opens at the beginning, enter the indicated page number manually.</p></div>
    </main>
  </>
}
