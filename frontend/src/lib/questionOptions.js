export function embeddedChoices(question) {
  const stem = question?.stem || ''
  const matches = [...stem.matchAll(/^[ \t]*\(([A-D])\)[ \t]+/gm)]
  const labels = (question?.options || []).map(option => option.label)
  if (!matches.length || matches.map(match => match[1]).join('') !== labels.join('')) return {}
  const choices = Object.fromEntries(matches.map((match, i) => [match[1], stem.slice(match.index + match[0].length, matches[i + 1]?.index ?? stem.length).trim()]))
  return Object.values(choices).every(Boolean) ? choices : {}
}

export function optionDisplay(question, option) {
  const content = option?.content == null ? '' : String(option.content).trim()
  const label = String(option?.label || '')
  const placeholder = !content || content.toUpperCase().replace(/[().:\s]/g, '') === label.toUpperCase()
  const embedded = placeholder ? embeddedChoices(question)[label] : null
  if (embedded) return { kind: 'text', text: embedded }
  if (!content) return { kind: 'missing', text: `Option ${label} text is unavailable.` }
  const diagrams = (question?.assets || []).filter(asset => /^(https?:\/\/|\/(?!\/))/i.test(asset?.url?.trim() || ''))
  if (content && (!diagrams.length || content.toUpperCase().replace(/[().:\s]/g, '') !== label.toUpperCase())) return { kind: 'text', text: content }
  if (diagrams.length) return { kind: 'diagram', text: `Option ${label} is shown in the question image.` }
  return { kind: 'missing', text: `Option ${label} text is unavailable.` }
}

export function missingOptions(questions) {
  return questions.flatMap((question, index) => question.type === 'numerical' ? [] : !(question.options || []).length ? [{ number: index + 1, question_id: question.question_id, label: '?' }] : (question.options || []).filter(option => optionDisplay(question, option).kind === 'missing').map(option => ({ number: index + 1, question_id: question.question_id, label: option.label })))
}
