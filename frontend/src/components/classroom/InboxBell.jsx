import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Bell } from 'lucide-react'
import { request } from '../../lib/api.js'

export default function InboxBell({ onTeacher }) {
  const [count, setCount] = useState(0)
  useEffect(() => {
    let active = true, pending = false
    const refresh = async () => {
      if (document.hidden || pending) return
      pending = true
      try {
        const data = await request('/api/notifications', { cache: false })
        if (active) { setCount(data.unread_count); onTeacher(data.teacher) }
      } catch { /* Keep navigation usable during a temporary outage. */ }
      finally { pending = false }
    }
    refresh()
    const interval = setInterval(refresh, 60000)
    window.addEventListener('focus', refresh)
    window.addEventListener('jee-inbox-changed', refresh)
    document.addEventListener('visibilitychange', refresh)
    return () => { active = false; clearInterval(interval); window.removeEventListener('focus', refresh); window.removeEventListener('jee-inbox-changed', refresh); document.removeEventListener('visibilitychange', refresh) }
  }, [onTeacher])
  return <NavLink to="/notifications" className="jee-nav__bell" aria-label={`Notifications${count ? `, ${count} unread` : ''}`}><Bell size={19}/>{count > 0 && <span>{count > 99 ? '99+' : count}</span>}</NavLink>
}
