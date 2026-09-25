import { NavLink } from 'react-router-dom'
import { useAuth0 } from '@auth0/auth0-react'
import { LayoutDashboard, BookOpen, Flame, Coins, MessageCircle, UserRound, LogOut, Trophy, Library, Timer } from 'lucide-react'
import { Logo } from './Brand.jsx'

const LINKS = [
  ['/dashboard', 'Overview', LayoutDashboard],
  ['/subject-test', 'Practice', BookOpen],
  ['/scenarios', 'Situations', Timer],
  ['/daily', 'Daily', Flame],
  ['/syllabus', 'Syllabus', Library],
  ['/ranking', 'Rankings', Trophy],
  ['/rewards', 'Rewards', Coins],
  ['/buddy', 'Study assistant', MessageCircle],
  ['/profile', 'Profile', UserRound],
]
export default function AppHeader() {
  const { logout } = useAuth0()
  return <header className="appbar"><div className="wrap appbar-row"><Logo to="/dashboard"/><nav className="appnav" aria-label="Main">{LINKS.map(([to, text, Icon]) => <NavLink key={to} to={to} className={({isActive}) => 'navlink' + (isActive ? ' active' : '')}><Icon size={16}/>{text}</NavLink>)}</nav><button type="button" className="btn btn-quiet btn-sm" onClick={() => logout({logoutParams:{returnTo:window.location.origin}})}><LogOut size={15}/><span className="hide-sm">Log out</span></button></div></header>
}
