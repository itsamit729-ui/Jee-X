// One normalized, token-based matcher for navigation, chapters and study plans.
export function searchText(value) {
  return String(value || '').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase()
    .replace(/\b(maths?|math)\b/g,'mathematics').replace(/\bphys\b/g,'physics').replace(/\bchem\b/g,'chemistry')
    .replace(/\b(3[- ]?d|three dimensional)\b/g,'three dimensional')
    .replace(/[^\p{L}\p{N}]+/gu,' ').trim().replace(/\s+/g,' ')
}
export function matchesSearch(value,query) {
  const haystack=searchText(value)
  return searchText(query).split(' ').filter(Boolean).every(token=>haystack.includes(token))
}
export function rankedSearch(items,query,textOf=item=>item.name) {
  const needle=searchText(query)
  return items.filter(item=>matchesSearch(textOf(item),query)).sort((a,b)=>{
    const score=item=>{const text=searchText(textOf(item));return text===needle?0:text.startsWith(needle)?1:2}
    return score(a)-score(b)
  })
}
