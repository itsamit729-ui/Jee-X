import { Link } from 'react-router-dom'
import { ArrowRight, BookOpenCheck, Clock3, Layers3 } from 'lucide-react'
import { Logo } from '../components/Brand.jsx'

const features = [
  { Icon: Layers3, title: 'Choose the paper', text: 'Select an MHT-CET exam year and shift to practise a specific paper.' },
  { Icon: Clock3, title: 'Practise with a timer', text: 'Work through the two timed sections and get used to managing your pace.' },
  { Icon: BookOpenCheck, title: 'Review your attempt', text: 'After a mock, review your performance and use the college predictor to explore possible colleges.' },
]

export default function MHTCETLanding() {
  return <div className="crackjee-root">
    <header className="appbar"><div className="wrap appbar-row"><Logo to="/"/><Link to="/" className="btn btn-quiet btn-sm">Jee Edge home</Link></div></header>
    <main className="wrap-narrow page">
      <section className="page-head">
        <p className="muted" style={{fontSize:12,letterSpacing:1}}>MHT-CET PRACTICE</p>
        <h1 className="page-title">MHT-CET mocks by year and shift</h1>
        <p className="muted">Rehearse an MHT-CET paper in a timed mock, choose a year and shift, then review your attempt and explore your college outlook.</p>
        <Link className="btn btn-primary" to="/pyq?exam=mht_cet">Browse MHT-CET papers <ArrowRight size={16}/></Link>
      </section>
      <section aria-label="How MHT-CET mock practice works" style={{display:'grid',gap:16,margin:'28px 0'}}>
        {features.map(({Icon,title,text}, index) => <article className="panel" key={title} style={{display:'flex',gap:16,alignItems:'flex-start'}}>
          <Icon size={22} color="#b66a36" aria-hidden="true"/><div><h2 style={{fontSize:18,margin:'0 0 8px'}}>{index + 1}. {title}</h2><p className="muted" style={{margin:0,lineHeight:1.7}}>{text}</p></div>
        </article>)}
      </section>
      <section className="panel" style={{marginBottom:24}}>
        <h2 style={{fontSize:20}}>How to start</h2>
        <p className="muted" style={{lineHeight:1.7}}>Open the MHT-CET question archive, select the available paper by year and shift, and start your mock. You’ll need to sign in to access the archive and save your result. Paper availability can vary as the archive is updated.</p>
        <Link className="btn btn-secondary" to="/pyq?exam=mht_cet">Go to the MHT-CET archive <ArrowRight size={16}/></Link>
      </section>
      <p className="muted" style={{fontSize:12,lineHeight:1.6}}>Jee Edge is an independent exam practice platform and is not affiliated with the MHT-CET examination authority.</p>
    </main>
  </div>
}
