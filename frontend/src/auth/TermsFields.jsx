import { Link } from 'react-router-dom'

export const TERMS_VERSION = '2026-10-11'
export const emptyTerms = () => ({ version: TERMS_VERSION, age_band: '', accepted: false, guardian_declared: false })

export default function TermsFields({ value, onChange }) {
  return <fieldset className="signup-terms">
    <legend>Before you join</legend>
    <p>Profiles are public. Choose a nickname and keep your address, school details and contact information out of your profile.</p>
    <label htmlFor="signup-age">Age of the person using this account</label>
    <select id="signup-age" required value={value.age_band} onChange={e => onChange({ ...value, age_band: e.target.value, accepted: false, guardian_declared: false })}>
      <option value="">Choose an age group</option><option value="under_18">Under 18</option><option value="18_plus">18 or older</option>
    </select>
    {value.age_band === 'under_18' && <>
      <p><strong>Ask your parent or legal guardian to complete this part.</strong> Read the terms and privacy notice together before continuing.</p>
      <label className="signup-terms-check"><input type="checkbox" required checked={value.guardian_declared} onChange={e => onChange({ ...value, guardian_declared: e.target.checked })}/><span>I am this student’s parent or legal guardian, am at least 18, and permit their use of Jee Edge. I understand that their profile and contest history are public.</span></label>
    </>}
    <label className="signup-terms-check"><input type="checkbox" required checked={value.accepted} onChange={e => onChange({ ...value, accepted: e.target.checked })}/><span>{value.age_band === 'under_18' ? 'As the parent or legal guardian, I' : 'I'} agree to the <Link to="/terms" target="_blank" rel="noopener noreferrer">Terms & Conditions</Link> and have read the <Link to="/privacy" target="_blank" rel="noopener noreferrer">Privacy Notice</Link> (opens in a new tab).</span></label>
  </fieldset>
}
