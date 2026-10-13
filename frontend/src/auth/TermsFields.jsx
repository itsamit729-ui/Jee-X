import { Link } from 'react-router-dom'

export const TERMS_VERSION = '2026-10-13'
export const emptyTerms = () => ({ version: TERMS_VERSION, accepted: false })

export default function TermsFields({ value, onChange }) {
  return <fieldset className="signup-terms">
    <legend>Before you join</legend>
    <p>Student profiles and rated-contest history are public. Use a nickname and keep personal contact details out of your profile.</p>
    <p><strong>Under 18?</strong> A parent or legal guardian must review these documents with you and complete the acceptance below before you continue.</p>
    <label className="signup-terms-check"><input type="checkbox" required checked={value.accepted} onChange={e => onChange({ ...value, accepted: e.target.checked })}/><span>I am at least 18 and agree to the <Link to="/terms" target="_blank" rel="noopener noreferrer">Terms & Conditions</Link> and have read the <Link to="/privacy" target="_blank" rel="noopener noreferrer">Privacy Notice</Link>, for myself or as this student’s parent or legal guardian. If accepting for a student under 18, I authorise and will supervise their use of Jee Edge, including its public student profile features.</span></label>
  </fieldset>
}
