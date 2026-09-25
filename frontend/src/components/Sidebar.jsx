import { NavLink } from 'react-router-dom'
import { useAuth0 } from '@auth0/auth0-react'
import { LayoutGrid, FileText, BarChart3, BookOpen, User, LogOut, Trophy, Timer } from 'lucide-react'

const linkClass = ({ isActive }) => 'dash-link' + (isActive ? ' active' : '')

export default function Sidebar() {
  const { logout } = useAuth0()

  return (
    <aside className="dash-sidebar">
      <span className="brand">Jee <span className="brand-x">Edge</span></span>
      <nav className="dash-nav">
        <NavLink to="/dashboard" end className={linkClass}>
          <LayoutGrid size={17} strokeWidth={2} />
          Overview
        </NavLink>
        <button className="dash-link disabled" type="button" title="Coming soon">
          <FileText size={17} strokeWidth={2} />
          Mock tests
          <span className="soon">Soon</span>
        </button>
        <button className="dash-link disabled" type="button" title="Coming soon">
          <BarChart3 size={17} strokeWidth={2} />
          Analysis
          <span className="soon">Soon</span>
        </button>
        <NavLink to="/subject-test" className={linkClass}>
          <BookOpen size={17} strokeWidth={2} />
          Subject tests
        </NavLink>
        <NavLink to="/scenarios" className={linkClass}><Timer size={17} />Exam situations</NavLink>
        <NavLink to="/ranking" className={linkClass}><Trophy size={17} />Rankings</NavLink>
        <NavLink to="/profile" className={linkClass}>
          <User size={17} strokeWidth={2} />
          Profile
        </NavLink>
      </nav>

      <button
        className="dash-link logout"
        type="button"
        onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
      >
        <LogOut size={17} strokeWidth={2} />
        Log out
      </button>
    </aside>
  )
}
