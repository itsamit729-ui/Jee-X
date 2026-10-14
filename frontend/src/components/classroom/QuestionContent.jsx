import { memo } from 'react'
import MathText from '../MathText.jsx'
import QuestionAssets from '../QuestionAssets.jsx'
import QuestionOptions from './QuestionOptions.jsx'

function QuestionContent({ question: q, solution = false, options = false }) {
  return <><div className="cl-question-meta">{q.subject} · {q.chapter} · {q.ref}</div>{q.passage && <div className="cl-passage"><MathText text={q.passage.body}/><QuestionAssets assets={q.passage.assets}/></div>}<div className="cl-question-stem"><MathText text={q.stem}/></div><QuestionAssets assets={q.assets}/>{(options || solution) && <QuestionOptions question={q} answerKey={solution}/>} {solution && <div className="cl-solution"><strong>Answer & explanation</strong><p>{q.type === 'numerical' ? `${q.answer_min} to ${q.answer_max}` : q.options.filter(o => o.is_correct).map(o => o.label).join(', ')}</p><MathText text={q.solution || 'No written explanation is available for this question.'}/></div>}</>
}

export default memo(QuestionContent)
