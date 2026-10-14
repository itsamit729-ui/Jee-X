import { memo } from 'react'
import MathText from '../MathText.jsx'
import './question-options.css'
import { optionDisplay } from '../../lib/questionOptions.js'

function QuestionOptions({ question, answerKey = false }) {
  if (question.type === 'numerical') return <p className="cl-numerical-note">Numerical answer · students enter a number.</p>
  const options = question.options || []
  if (!options.length) return <p className="cl-option-missing" role="status">Answer options are unavailable for this question.</p>
  return <div className="cl-question-options" aria-label="Answer options">{options.map((option, index) => {
    const display = optionDisplay(question, option)
    return <div key={option.id ?? `${option.label}-${index}`} className={`cl-question-option ${display.kind}${answerKey && option.is_correct ? ' is-correct' : ''}`}><span className="cl-choice-letter">{option.label}</span><div>{display.kind === 'text' ? <MathText text={display.text}/> : <span className="cl-choice-note">{display.text}</span>}{answerKey && option.is_correct && <small>Correct answer</small>}</div></div>
  })}</div>
}

export default memo(QuestionOptions)
