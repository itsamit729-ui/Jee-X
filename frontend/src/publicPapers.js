import renderMathInElement from 'katex/contrib/auto-render'
import 'katex/dist/katex.min.css'

for (const node of document.querySelectorAll('.math')) {
  renderMathInElement(node, { throwOnError: false, trust: false, delimiters: [
    { left: '$$', right: '$$', display: true }, { left: '\\[', right: '\\]', display: true },
    { left: '\\(', right: '\\)', display: false }, { left: '$', right: '$', display: false },
  ] })
}
const allowed = ['google', 'youtube', 'instagram', 'whatsapp', 'telegram', 'teacher', 'direct']
const requested = new URLSearchParams(location.search).get('utm_source') || (['instagram', 'youtube'].includes(document.body.dataset.source) ? document.body.dataset.source : null)
let referrer = ''
try { referrer = new URL(document.referrer).hostname } catch {}
const referred = /(^|\.)google\.[a-z.]+$/.test(referrer) ? 'google' : /(^|\.)youtube\.com$/.test(referrer) ? 'youtube' : referrer && referrer !== location.hostname ? 'other' : 'direct'
const source = allowed.includes(requested) ? requested : requested ? 'other' : referred
const paper = document.body.dataset.paper
function track(event) {
  fetch('/api/public-papers/events', { method: 'POST', keepalive: true, headers: { 'Content-Type': 'application/json', 'X-Jee-Request': '1' }, body: JSON.stringify({ paper, source, event }) }).catch(() => {})
}
track('view')
for (const link of document.querySelectorAll('a[href]')) {
  const url = new URL(link.href)
  if (url.origin !== location.origin) continue
  if (url.pathname.startsWith('/mhtcet/papers')) {
    url.searchParams.set('utm_source', source)
    link.href = url.href
  }
  if (link.hasAttribute('data-start')) {
    url.searchParams.set('source', source)
    link.href = url.href
    link.addEventListener('click', () => track('start_click'))
  }
}
