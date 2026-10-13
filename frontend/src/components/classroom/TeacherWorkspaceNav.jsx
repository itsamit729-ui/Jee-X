import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Users, Files, UserRound, ChartNoAxesCombined, Library, MessageCircle, ShieldCheck } from 'lucide-react'
import { teacherSections, teacherSection, teacherHref } from '../../lib/teacherWorkspace.js'

const icons = { overview: LayoutDashboard, classes: Users, papers: Files, students: UserRound, tests: ChartNoAxesCombined, learning: Library, doubts: MessageCircle }

export default function TeacherWorkspaceNav({ close, compact = false }) {
  const { pathname, search } = useLocation()
  const active = pathname === '/teacher' ? teacherSection(new URLSearchParams(search)) : null
  return <nav className={`tw-navigation${compact ? ' tw-top-navigation' : ''}`} aria-label="Teacher workspace">
    {!compact&&<p className="tw-nav-label">WORKSPACE</p>}
    {teacherSections.filter(section=>!compact||['overview','classes','papers','students','tests'].includes(section.key)).map(section => {
      const Icon = icons[section.key]
      return <Link key={section.key} to={teacherHref(section.key)} onClick={close} aria-current={active === section.key ? 'page' : undefined}><Icon size={18}/><span>{compact?({papers:'Papers',tests:'Reports'})[section.key]||section.label:section.label}</span>{active === section.key && <span className="tw-nav-dot"/>}</Link>
    })}
    {!compact&&<><p className="tw-nav-label tw-nav-account">YOUR ACCOUNT</p>
    <Link to="/teacher/profile" onClick={close} aria-current={pathname === '/teacher/profile' ? 'page' : undefined}><UserRound size={18}/><span>Teacher profile</span></Link>
    <Link to="/teacher/account" onClick={close} aria-current={pathname === '/teacher/account' ? 'page' : undefined}><ShieldCheck size={18}/><span>Account & support</span></Link>
    </>}
  </nav>
}
