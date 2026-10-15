import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const pages = JSON.parse(await readFile(resolve(root, 'src/data/seoPages.json'), 'utf8'))
const titles = new Set()
for (const [path, [title]] of Object.entries(pages)) {
  const html = await readFile(resolve(root, 'dist', path === '/' ? 'index.html' : `${path.slice(1)}/index.html`), 'utf8')
  const canonical = [...html.matchAll(/<link rel="canonical" href="([^"]+)"/g)]
  assert.equal(canonical.length, 1, `Exactly one canonical on ${path}`)
  assert.equal(canonical[0][1], `https://jeeedge.in${path}`)
  const actualTitle = html.match(/<title>(.*?)<\/title>/)[1]
  assert.ok(!titles.has(actualTitle), `Duplicate title: ${path}`)
  titles.add(actualTitle)
  assert.ok(actualTitle.includes(title.split(' ')[0]))
  assert.match(html, /<meta name="robots" content="index, follow"/)
  assert.match(html, /<h1[\s>]/, `Missing readable heading on ${path}`)
  assert.doesNotMatch(html, /<div id="root"><\/div>/)
  for (const href of [...html.matchAll(/(?:href|src)="(\/assets\/[^"?]+)"/g)]) {
    await readFile(resolve(root, 'dist', href[1].slice(1)))
  }
}
const home = await readFile(resolve(root, 'dist/index.html'), 'utf8')
assert.match(home, /href="\/mhtcet\/papers"/)
assert.match(home, /href="\/mhtcet-mock-tests"/)
const shell = await readFile(resolve(root, 'dist/spa.html'), 'utf8')
assert.match(shell, /content="noindex, follow"/)
assert.match(shell, /<div id="root"><\/div>/)
assert.doesNotMatch(shell, /rel="canonical"/)
console.log(`Verified ${Object.keys(pages).length} public HTML pages and private application shell`)
