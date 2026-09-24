import { useState } from 'react'
import AppHeader from '../components/AppHeader.jsx'
import MathText from '../components/MathText.jsx'
import QuestionAssets from '../components/QuestionAssets.jsx'
import bank from '../../../generated/questions/physics/current-electricity-images.json'

export default function ImageQuestions() {
  const [answers, setAnswers] = useState({})
  const [revealed, setRevealed] = useState({})
  return <div className="crackjee-root"><AppHeader /><main className="test-shell">
    <div className="page-head"><div><h1 className="page-title">Practice with diagrams</h1>
      <p className="page-sub">Three circuit questions. Choose an answer, expand a diagram, then check the solution.</p>
      <p className="faint">Adapted practice · No rating or progress is recorded here.</p></div></div>
    {bank.questions.map((q, i) => <section className="qcard" key={q.ref} style={{ marginBottom: 28 }}>
      <div className="qmeta"><span className="tag">Physics · Current Electricity</span><span className="tag">Question {i + 1} / 3</span></div>
      <div className="qtext"><MathText text={q.stem} /></div>
      <QuestionAssets assets={[{ url: q.image.url, alt_text: q.image.alt }]} />
      <div className="options" role="radiogroup" aria-label={`Question ${i + 1} options`}>
        {q.options.map(o => <button type="button" role="radio" aria-checked={answers[q.ref] === o.label} key={o.label}
          className={`option ${answers[q.ref] === o.label ? 'is-selected' : ''}`}
          onClick={() => { setAnswers(a => ({ ...a, [q.ref]: o.label })); setRevealed(a => ({ ...a, [q.ref]: false })) }}>
          <span className="option-key">{o.label}</span><span className="option-body"><MathText text={o.content} /></span>
        </button>)}
      </div>
      <button type="button" className="btn btn-primary" style={{ marginTop: 20 }} disabled={!answers[q.ref]} onClick={() => setRevealed(a => ({ ...a, [q.ref]: true }))}>Check answer</button>
      {revealed[q.ref] && <div className="solution" role="status"><p><strong>{q.options.find(o => o.label === answers[q.ref])?.is_correct ? 'Correct!' : `Correct answer: ${q.options.find(o => o.is_correct).label}`}</strong></p><MathText text={q.solution} /></div>}
      <p className="faint" style={{ marginTop: 20, fontSize: 12 }}>Adapted from <a href={q.source.url} target="_blank" rel="noreferrer">{q.source.title}</a> by OpenStax, <a href={q.source.license_url} target="_blank" rel="noreferrer">CC BY 4.0</a>. Wording adapted; diagrams redrawn.</p>
    </section>)}
  </main></div>
}
