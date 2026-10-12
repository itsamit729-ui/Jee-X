const KEY = 'jee-paper-return'
export function rememberPaperReturn(value, storage = localStorage, now = Date.now()) {
  if (!value?.startsWith('/pyq?') || value.length > 500) return
  try { storage.setItem(KEY, JSON.stringify({ value, expires: now + 30 * 60 * 1000 })) } catch {}
}
export function pendingPaperReturn(storage = localStorage, now = Date.now()) {
  try {
    const entry = JSON.parse(storage.getItem(KEY) || 'null')
    if (entry?.expires > now && typeof entry.value === 'string' && entry.value.startsWith('/pyq?') && entry.value.length <= 500) return entry.value
    storage.removeItem(KEY)
  } catch {}
  return null
}
export function clearPaperReturn(storage = localStorage) {
  try { storage.removeItem(KEY) } catch {}
}
