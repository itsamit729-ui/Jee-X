import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, GraduationCap } from 'lucide-react'
import CollegeInfo from './CollegeInfo.jsx'

const rank = value => Number(value).toLocaleString('en-IN')
function CollegeCard({ scenario, target, settings, baseline }) {
  const [list, setList] = useState('')
  const rows = scenario?.colleges || []
  const lists = [...new Set(rows.map(c => c.rank_list).filter(Boolean))]
  const selectedList = lists.includes(list) ? list : lists.includes(settings.admission.category) ? settings.admission.category : lists[0]
  const choices = rows.filter(c => c.rank_list === selectedList)
  const preferred = choices.filter(c => settings.choices?.some(p => p.institute === c.institute && p.program === c.program))
  const pool = preferred.length ? preferred : choices
  const college = pool.find(c => c.meets_conservative_estimate) || pool[0]
  const benchmark = target && scenario?.basis === 'college_cutoff'
  const score = target ? settings.target_marks : baseline.score
  const enteredRank = !target && scenario?.basis === 'entered_crl' ? scenario.rank_low : null
  const pendingChoice = target ? settings.choices?.[0] : null
  return <article className={target ? 'college-future college-destination' : 'college-future'}>
    <header><span className="topic-plan-label">{target ? 'AT YOUR GOAL' : 'WITH YOUR CURRENT PERFORMANCE'}</span><GraduationCap size={22} aria-hidden="true"/></header>
    <div className="college-score">{enteredRank != null ? <><strong>{rank(enteredRank)}</strong><span>CRL · entered rank</span></> : score != null ? <><strong>{score}</strong><span>/ 300 marks{target ? ' target' : ' · baseline'}</span></> : <strong>{target ? 'Your college goal' : scenario?.basis === 'entered_crl' ? 'Your entered rank' : 'Find your starting point'}</strong>}</div>
    {lists.length > 1 && <label className="college-rank-select">Compare rank list <select aria-label={target ? 'Target rank list' : 'Current rank list'} value={selectedList} onChange={e => setList(e.target.value)}>{lists.map(value => <option key={value}>{value}</option>)}</select></label>}
    {college ? <>
      <span className="college-match-label">{benchmark ? 'YOUR CHOSEN DESTINATION' : preferred.length ? 'MATCH FROM YOUR PREFERENCES' : 'FEATURED COLLEGE MATCH'}</span>
      <h3>{college.institute}<CollegeInfo institute={college.institute} program={college.program}/></h3><p className="college-branch">{college.program}</p>
      <div className="college-cutoff"><span>{college.rank_list} closing rank</span><strong>{rank(college.closing_rank)}</strong></div>
      <small>{college.reference_year} · Round {college.reference_round} · {college.quota} · {college.seat_type}</small>
      <p className="college-match-note">{benchmark ? 'Historical benchmark for this choice. Demonstrate the required rank in its own rank list.' : college.meets_conservative_estimate ? 'Within the full compared rank range against this historical cutoff.' : 'A stretch option: overlaps only the optimistic end of the rank estimate.'}</p>
      {choices.length > 1 && <details><summary>Explore other matching branches & colleges</summary><ul>{choices.filter(c => c !== college).map((c, i) => <li key={i}><strong>{c.institute}<CollegeInfo institute={c.institute} program={c.program}/></strong><span>{c.program}</span><small>{c.rank_list} {rank(c.closing_rank)} · {c.reference_year} · {c.quota} · {c.seat_type} · {c.meets_conservative_estimate ? 'Within compared range' : 'Stretch option'}</small></li>)}</ul></details>}
    </> : <div className="college-no-match"><h3>{pendingChoice ? <>{pendingChoice.institute}<CollegeInfo institute={pendingChoice.institute} program={pendingChoice.program}/></> : target ? 'Your destination starts here' : 'Your first college match is ahead'}</h3>{pendingChoice && <p>{pendingChoice.program}</p>}<p>{!target && !Object.keys(scenario?.rank_inputs || {}).length ? 'Take a balanced assessment or add your JEE rank to see colleges matching your current level.' : !settings.admission.state ? 'Add your Class XII state in goal settings to include eligible NIT quotas.' : 'No matching programs in the available cutoff data for this scenario. Explore a different target, or add your category rank in goal settings.'}</p>{!target && baseline.score == null && <Link className="btn btn-secondary" to="/practice?assessment=1">Find my starting point <ArrowUpRight size={15}/></Link>}</div>}
  </article>
}
export default function CollegeHorizon({ outlook }) {
  if (!outlook) return null
  return <section className="college-horizon" id="college-outlook" aria-label="Current and target college opportunities">
    <div className="college-horizon-heading"><div><span className="topic-plan-label">SEE WHAT YOU’RE WORKING TOWARDS</span><h2>Today’s position. Tomorrow’s possibilities.</h2></div><span>{outlook.settings.admission.category}{outlook.settings.admission.state ? ' · ' + outlook.settings.admission.state : ' · Add state in goal settings'}</span></div>
    <div className="college-horizon-grid"><CollegeCard scenario={outlook.current} baseline={outlook.baseline} settings={outlook.settings}/><CollegeCard scenario={outlook.target} baseline={outlook.baseline} settings={outlook.settings} target/></div>
    <p className="college-horizon-note">Matches use available historical cutoffs and your eligibility details. Your preferences are prioritised; featured matches are not a college quality ranking. Marks estimates compare OPEN seats using CRL. Category seats require the corresponding category rank.</p>
  </section>
}
