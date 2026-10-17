import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, CartesianGrid } from 'recharts'
import Palette from './Palette.jsx'
import MathText from './MathText.jsx'
import QuestionAssets from './QuestionAssets.jsx'
import DeferredDetails from './DeferredDetails.jsx'
import { INK_2, LINE, PEN, GOOD, BAD, IDLE, SUBJECT_COLOR, axisProps, gridProps, tooltipProps, fontBody } from '../crackjee/ui.js'
import { OUTCOME_SQUARE, OUTCOME_WORD, QUESTION_FILTERS, filterQuestions, yourAnswer, correctAnswer, splitChapters, chartChapters,
  correctRate, practiceChapterPath, changeSincePrevious, MIN_CHAPTER_QUESTIONS, isSlow, isRushed, minutes } from '../lib/attemptAnalysis.js'
import './attempt-report.css'

const TABS = [['overview', 'Overview'], ['subjects', 'Subjects'], ['chapters', 'Chapters'], ['questions', 'Questions']]
const shortName = (name) => (name.length > 14 ? name.slice(0, 13) + '…' : name)

// Full analysis of one stored attempt. Purely presentational: `data` is the
// GET /api/test-attempts/{id}/analysis payload with detail_available = true.
export default function AttemptReport({ data }) {
  // The open tab lives in the URL (?tab=questions), so Back and shared links land on the same view.
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = TABS.some(([key]) => key === searchParams.get('tab')) ? searchParams.get('tab') : 'overview'
  const setTab = (key) => setSearchParams((params) => { const next = new URLSearchParams(params); if (key === 'overview') next.delete('tab'); else next.set('tab', key); return next }, { replace: true })
  const [filter, setFilter] = useState('all')
  const { summary, subjects, chapters, questions, meta } = data
  const pieData = [
    { name: 'Correct', value: summary.correct, color: GOOD },
    { name: 'Wrong', value: summary.wrong, color: BAD },
    { name: 'Skipped', value: summary.skipped, color: IDLE },
  ]
  const radarData = chartChapters(chapters).map((c) => ({ ch: shortName(c.name), v: Math.round(correctRate(c) * 100) }))
  const { weak, strong, tooFew } = splitChapters(chapters)
  const change = changeSincePrevious(meta, summary)
  const signed = (n) => (n > 0 ? `+${n}` : String(n))
  const shown = filterQuestions(questions, filter)

  return <div className="attempt-report">
    <section className="panel result-panel" aria-label="Score">
      <div>
        <div className="score-big">{summary.score}<small>/ {summary.max_score}</small></div>
        <p className="result-line" style={{ marginTop: 12 }}>{summary.correct} correct, {summary.wrong} wrong, {summary.skipped} skipped</p>
      </div>
      <div className="result-squares">
        {subjects.length > 1 ? subjects.map((s) => (
          <div key={s.code} className="result-sub">
            <span className="result-sub-name"><span className="dot" style={{ background: SUBJECT_COLOR[s.code] || PEN }} />{s.name}</span>
            <Palette size="sm" states={questions.filter((q) => q.subject_code === s.code).map((q) => OUTCOME_SQUARE[q.outcome] || 'skipped')} label={s.name} />
          </div>
        )) : <Palette size="sm" states={questions.map((q) => OUTCOME_SQUARE[q.outcome] || 'skipped')} label="Your answers" />}
      </div>
    </section>

    <div className="stats" style={{ marginTop: 16 }}>
      <div className="stat"><div className="stat-value">{summary.accuracy}%</div><div className="stat-label">Accuracy on attempted</div></div>
      <div className="stat"><div className="stat-value">{minutes(summary.time_sec)} min</div><div className="stat-label">{meta.duration_sec ? `Time used of ${minutes(meta.duration_sec)}` : 'Time spent'}</div></div>
      <div className="stat"><div className="stat-value">{questions.filter(isSlow).length}</div><div className="stat-label">Slow questions</div></div>
      {summary.marks_lost > 0 && <div className="stat"><div className="stat-value">{summary.marks_lost}</div><div className="stat-label">Marks lost to wrong answers</div></div>}
      {change && <div className="stat"><div className="stat-value">{signed(change.score)}</div><div className="stat-label">Marks vs your last attempt ({signed(change.accuracy)}% accuracy)</div></div>}
    </div>

    <div className="seg tabs" role="group" aria-label="Result view">
      {TABS.map(([key, text]) => <button key={key} type="button" aria-pressed={tab === key} onClick={() => setTab(key)}>{text}</button>)}
    </div>

    {tab === 'overview' && <div className="stack">
      <div className="grid-2">
        <div className="panel">
          <h2 className="panel-title">Answers</h2>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={58} outerRadius={84} paddingAngle={2} dataKey="value" stroke="none">
                {pieData.map((e) => <Cell key={e.name} fill={e.color} />)}
              </Pie>
              <Tooltip {...tooltipProps} />
            </PieChart>
          </ResponsiveContainer>
          <div className="chart-legend">
            {pieData.map((d) => <span key={d.name}><i className="dot" style={{ background: d.color }} />{d.name} <b>{d.value}</b></span>)}
          </div>
        </div>
        <div className="panel">
          <h2 className="panel-title">By subject</h2>
          <ResponsiveContainer width="100%" height={236}>
            <BarChart data={subjects} barSize={36}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="name" {...axisProps} />
              <YAxis {...axisProps} width={28} allowDecimals={false} />
              <Tooltip {...tooltipProps} />
              <Bar dataKey="correct" name="Correct" fill={GOOD} stackId="a" />
              <Bar dataKey="wrong" name="Wrong" fill={BAD} stackId="a" />
              <Bar dataKey="skipped" name="Skipped" fill={IDLE} stackId="a" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      {radarData.length >= 3 && <div className="panel">
        <h2 className="panel-title">Questions correct by chapter</h2>
        <p className="muted attempt-report-note">The {radarData.length} chapters with the most questions in this paper; skipped questions count as not correct.</p>
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={radarData} outerRadius="66%">
            <PolarGrid stroke={LINE} />
            <PolarAngleAxis dataKey="ch" tick={{ fill: INK_2, fontSize: 12, fontFamily: fontBody }} />
            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
            <Radar dataKey="v" name="Correct %" stroke={PEN} fill={PEN} fillOpacity={0.18} strokeWidth={2} />
            <Tooltip {...tooltipProps} />
          </RadarChart>
        </ResponsiveContainer>
      </div>}
    </div>}

    {tab === 'subjects' && <div className="stack">
      {subjects.map((s) => (
        <div key={s.code} className="panel">
          <div className="panel-head">
            <h2 className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: 10 }}><span className="dot" style={{ background: SUBJECT_COLOR[s.code] || PEN }} />{s.name}</h2>
            <span className="row-value" style={{ fontSize: 22 }}>{s.marks}<span className="faint" style={{ fontSize: 15 }}> / {s.max_marks}</span></span>
          </div>
          <div className="bar" aria-hidden="true">
            <span style={{ width: `${(s.correct / s.total) * 100}%`, background: GOOD }} />
            <span style={{ width: `${(s.wrong / s.total) * 100}%`, background: BAD }} />
          </div>
          <p className="muted" style={{ marginTop: 12, fontSize: 14.5 }}>
            {s.correct} correct, {s.wrong} wrong, {s.skipped} skipped · {s.accuracy}% accuracy on attempted · {minutes(s.time_sec)} min spent
          </p>
        </div>
      ))}
    </div>}

    {tab === 'chapters' && <div className="stack">
      <p className="muted attempt-report-note">Questions correct out of those in each chapter (skipped ones count as not correct). Chapters need at least {MIN_CHAPTER_QUESTIONS} questions in the paper to be judged.</p>
      <div className="grid-2">
        {[['Needs work', weak, BAD, 'No chapter is below 50%.'], ['Strong', strong, GOOD, 'No chapter is at 50% or above yet.']].map(([title, list, color, empty]) => (
          <div key={title} className="panel">
            <h2 className="panel-title">{title}</h2>
            {list.length === 0 ? <p className="muted">{empty}</p> : <div className="rows">
              {list.map((c) => <div key={c.chapter_id} className="row">
                <span className="row-main">{c.name}<small className="faint attempt-report-time"> · {minutes(c.time_sec)} min</small>
                  {color === BAD && <Link className="attempt-report-practice" to={practiceChapterPath(c,meta)}>{['mht_cet','bitsat'].includes(meta.pattern)?'Practice this subject’s PYQs':'Practice this chapter'}</Link>}</span>
                <span className="row-value" style={{ color }}>{c.correct}/{c.total}</span>
              </div>)}
            </div>}
          </div>
        ))}
      </div>
      {tooFew.length > 0 && <p className="muted attempt-report-note">Too few questions to judge: {tooFew.map((c) => `${c.name} (${c.correct}/${c.total})`).join(', ')}.</p>}
    </div>}

    {tab === 'questions' && <div className="stack">
      <div className="seg attempt-report-filters" role="group" aria-label="Show questions">
        {QUESTION_FILTERS.map(([key, text]) => <button key={key} type="button" aria-pressed={filter === key} onClick={() => setFilter(key)}>
          {text} <span className="faint">{filterQuestions(questions, key).length}</span>
        </button>)}
      </div>
      {shown.length === 0 ? <p className="muted">No questions match this filter.</p> : <div className="panel attempt-report-questions">
        {shown.map((q) => <DeferredDetails key={q.question_id} className="solution attempt-report-question" summary={<span className="solution-head">
          <span className="sq" data-s={OUTCOME_SQUARE[q.outcome] || 'skipped'} />
          Question {q.position}
          <span className="faint attempt-report-chapter">{q.chapter}</span>
          <span className="faint">{OUTCOME_WORD[q.outcome]} · yours {yourAnswer(q)} · answer {correctAnswer(q)} · {q.time_taken_sec}s{isSlow(q) ? ' (slow)' : isRushed(q) ? ' (rushed)' : ''}</span>
          <span className="marks" style={{ color: q.marks_awarded > 0 ? GOOD : q.marks_awarded < 0 ? BAD : undefined }}>{q.marks_awarded > 0 ? '+' : ''}{q.marks_awarded}</span>
        </span>}>
          {q.passage && <div className="passage"><MathText text={q.passage} /></div>}
          <div className="qtext"><MathText text={q.stem} /></div>
          <QuestionAssets assets={q.assets} />
          {q.type !== 'numerical' && <ul className="attempt-report-options">
            {q.options.map((o) => {
              const correct = q.correct_option_ids.includes(o.id)
              const chosen = q.selected_option_ids.includes(o.id)
              return <li key={o.id} className={`${correct ? 'is-correct' : ''} ${chosen && !correct ? 'is-wrong' : ''}`}>
                <span className="option-key">{o.label}</span><MathText text={o.content} />
                {(correct || chosen) && <span className="attempt-report-tag">{correct && chosen ? 'Your answer · correct' : correct ? 'Correct answer' : 'Your answer'}</span>}
              </li>
            })}
          </ul>}
          <p className="muted">Time: {q.time_taken_sec}s (expected about {q.expected_time_sec}s)</p>
          <p><MathText text={q.solution || 'Worked solution is not available yet.'} /></p>
        </DeferredDetails>)}
      </div>}
    </div>}
  </div>
}
