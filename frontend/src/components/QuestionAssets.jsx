import { useRef, useState } from 'react'
import './question-assets.css'

function QuestionImage({ asset }) {
  const dialog = useRef(null)
  const [failed, setFailed] = useState(false)
  // Keep untrusted URLs out of navigation and image sources.
  const url = asset.url?.trim()
  if (!url || !(/^(https?:\/\/|\/(?!\/))/i.test(url))) return null
  const alt = asset.alt_text || asset.alt || 'Question diagram'
  return <figure className="question-figure">
    {failed ? <div className="question-image-error" role="status">
      Diagram could not load. {alt}
      <button type="button" onClick={() => setFailed(false)}>Retry image</button>
    </div> : <button type="button" className="question-image-button" onClick={() => dialog.current?.showModal()} aria-label="Expand question diagram">
      <img src={url} alt={alt} onError={() => setFailed(true)} />
      <span>Expand diagram ↗</span>
    </button>}
    <dialog ref={dialog} className="question-image-dialog" onClick={e => { if (e.target === e.currentTarget) dialog.current.close() }}>
      <button type="button" className="btn btn-secondary" autoFocus onClick={() => dialog.current.close()}>Close diagram</button>
      <img src={url} alt={alt} />
    </dialog>
  </figure>
}

export default function QuestionAssets({ assets = [] }) {
  return assets.map((asset, i) => <QuestionImage key={`${asset.url}-${i}`} asset={asset} />)
}
