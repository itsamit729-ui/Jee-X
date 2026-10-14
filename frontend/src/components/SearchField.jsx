import { Search } from 'lucide-react'
import './search-field.css'

// Icon and input occupy separate columns; input padding cannot cover the icon.
export default function SearchField({ label, className = '', ...props }) {
  return <div className={`workspace-search ${className}`}>
    <Search size={18} aria-hidden="true"/>
    <input {...props} type="search" aria-label={label}/>
  </div>
}
