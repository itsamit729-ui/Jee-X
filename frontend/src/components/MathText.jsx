import { memo, useMemo, useEffect, useRef } from 'react'
import katex from 'katex'
import 'katex/dist/katex.min.css'

// Question content from the bank mixes plain text with $inline$ and
// $$block$$ LaTeX (e.g. "Let $S = \\sum_{r=1}^{10} ...$. Then ..."). This
// renders both, and preserves \n line breaks in the surrounding text.
const MATH_RE = /\$\$([\s\S]+?)\$\$|\$([^$\n]+?)\$/g

function renderMath(tex, displayMode) {
  try {
    return katex.renderToString(tex, { throwOnError: false, displayMode })
  } catch {
    return tex.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))
  }
}

function textWithLineBreaks(text, keyPrefix) {
  const lines = text.split('\n')
  return lines.map((line, i) => (
    <span key={`${keyPrefix}-${i}`}>
      {line}
      {i < lines.length - 1 && <br />}
    </span>
  ))
}

function MathText({ text, style }) {
  const host=useRef(null)
  // Timers and form edits must not typeset an unchanged question again.
  const content = useMemo(() => {
    if (!text) return null
    const parts = []
    let last = 0
    let match
    MATH_RE.lastIndex = 0
    while ((match = MATH_RE.exec(text))) {
      if (match.index > last) parts.push({ type: 'text', content: text.slice(last, match.index) })
      if (match[1] !== undefined) parts.push({ type: 'block', content: match[1] })
      else parts.push({ type: 'inline', content: match[2] })
      last = match.index + match[0].length
    }
    if (last < text.length) parts.push({ type: 'text', content: text.slice(last) })

    return parts.map((p, i) =>
      p.type === 'text' ? (
        textWithLineBreaks(p.content, i)
      ) : (
        <span key={i} className={`math-fragment math-${p.type}`}
          dangerouslySetInnerHTML={{ __html: renderMath(p.content, p.type === 'block') }} />
      )
    )
  }, [text])
  useEffect(()=>{
    const element=host.current
    if(!element)return
    const parent=element.parentElement
    function fit(){
      if(!parent?.clientWidth)return
      for(const fragment of element.querySelectorAll('.math-fragment')){
        fragment.style.fontSize=''
        const available=Math.min(parent.clientWidth,element.clientWidth||parent.clientWidth)
        const html=fragment.querySelector('.katex-html')
        const width=Math.max(html?.scrollWidth||0,html?.getBoundingClientRect().width||0,fragment.scrollWidth)
        if(width>available)fragment.style.fontSize=`${available/width*.98}em`
      }
    }
    fit()
    const observer=typeof ResizeObserver==='undefined'?null:new ResizeObserver(fit)
    if(parent)observer?.observe(parent)
    document.fonts?.ready.then(()=>{if(element.isConnected)fit()})
    return()=>observer?.disconnect()
  },[content])
  return content ? <span ref={host} className="math-text" style={style}>{content}</span> : null
}

export default memo(MathText)
