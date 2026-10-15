import { createServer } from 'vite'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { resolve, dirname } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const dist = resolve(root, 'dist')
const pages = JSON.parse(await readFile(resolve(root, 'src/data/seoPages.json'), 'utf8'))
const template = await readFile(resolve(dist, 'index.html'), 'utf8')
const manifest = JSON.parse(await readFile(resolve(dist, '.vite/manifest.json'), 'utf8'))
const escape = text => text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;')
function metadata(html, title, description, url) {
  for (const [pattern, value] of [
    [/<title>[^<]*<\/title>/, `<title>${escape(title)}</title>`],
    [/<meta name="description" content="[^"]*"\s*\/>/, `<meta name="description" content="${escape(description)}" />`],
    [/<link rel="canonical" href="[^"]*"\s*\/>/, `<link rel="canonical" href="${url}" />`],
    [/<meta property="og:title" content="[^"]*"\s*\/>/, `<meta property="og:title" content="${escape(title)}" />`],
    [/<meta property="og:description" content="[^"]*"\s*\/>/, `<meta property="og:description" content="${escape(description)}" />`],
    [/<meta property="og:url" content="[^"]*"\s*\/>/, `<meta property="og:url" content="${url}" />`],
  ]) {
    if (!pattern.test(html)) throw new Error(`Missing SEO template field: ${pattern}`)
    html = html.replace(pattern, () => value)
  }
  return html.replace('</head>', `<meta name="twitter:title" content="${escape(title)}" /><meta name="twitter:description" content="${escape(description)}" /></head>`)
}
// Authenticated screens must never inherit a public homepage body/canonical.
const shell = template.replace(/<title>[^<]*<\/title>/, '<title>Your account · Jee Edge</title>')
  .replace('content="index, follow"', 'content="noindex, follow"')
  .replace(/<link rel="canonical"[^>]*>/, '')
  .replace(/<script type="application\/ld\+json">[\s\S]*?<\/script>/, '')
await writeFile(resolve(dist, 'spa.html'), shell)
const server = await createServer({ root, server: { middlewareMode: true, watch: null }, appType: 'custom' })
try {
  const { render } = await server.ssrLoadModule('/src/entry-seo.jsx')
  for (const [path, [name, description]] of Object.entries(pages)) {
    const url = `https://jeeedge.in${path}`
    const body = render(path)
    if (!body.includes('<h1')) throw new Error(`No public heading rendered: ${path}`)
    let html = metadata(template, `${name} · Jee Edge`, description, url)
      .replace('<div id="root"></div>', () => `<div id="root">${body}</div>`)
    const css = new Set(), seen = new Set()
    function collect(key) {
      if (seen.has(key)) return
      seen.add(key)
      const entry = manifest[key] || {}
      for (const file of entry.css || []) css.add(file)
      for (const dependency of entry.imports || []) collect(dependency)
    }
    const component = path === '/' ? 'Home' : { '/syllabus': 'Syllabus', '/pricing': 'Pricing', '/free-test': 'FreeTest', '/image-questions': 'ImageQuestions', '/mhtcet-mock-tests': 'MHTCETLanding' }[path]
    collect(`src/pages/${component}.jsx`)
    const styles = [...css].filter(file => !html.includes(`href="/${file}"`)).map(file => `<link rel="stylesheet" href="/${file}">`).join('')
    html = html.replace('</head>', `${styles}</head>`)
    const output = resolve(dist, path === '/' ? 'index.html' : `${path.slice(1)}/index.html`)
    await mkdir(dirname(output), { recursive: true })
    await writeFile(output, html)
    console.log(`Prerendered ${path}`)
  }
} finally { await server.close() }
