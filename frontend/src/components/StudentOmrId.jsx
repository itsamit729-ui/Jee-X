import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { formatOmrId } from '../lib/omrIdentity.js'
import './student-omr-id.css'

export default function StudentOmrId({ studentId }) {
  const id = formatOmrId(studentId)
  const [copyState, setCopyState] = useState('')
  if (!id) return null
  async function copy() {
    try {
      await navigator.clipboard.writeText(id)
      setCopyState('copied')
    } catch { setCopyState('failed') }
  }
  return <section className="student-omr-id" aria-label="Your permanent OMR ID">
    <div className="student-omr-id-heading"><span>Your OMR ID</span><span>Permanent student ID</span></div>
    <div className="student-omr-id-value"><strong>{id}</strong><button type="button" className="btn btn-secondary btn-sm" onClick={copy} aria-label="Copy your OMR ID">{copyState === 'copied' ? <Check size={15}/> : <Copy size={15}/>}Copy ID</button></div>
    <p>This ID stays the same across all your classes and tests. Write all 10 digits on your OMR sheet, including the leading zeros.</p>
    {copyState && <p role="status">{copyState === 'copied' ? 'OMR ID copied.' : 'Could not copy. Select the number above and copy it.'}</p>}
  </section>
}
