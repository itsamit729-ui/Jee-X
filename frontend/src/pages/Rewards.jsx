import { useEffect, useState } from 'react'
import { Coins, Gift } from 'lucide-react'
import { rewardsService } from '../lib/rewards.js'
import AppHeader from '../components/AppHeader.jsx'
import { Loader } from '../components/Brand.jsx'

const SHIPPING_FIELDS = [
  ['name', 'Full name', 'text'],
  ['line1', 'Address line 1', 'text'],
  ['line2', 'Address line 2 (optional)', 'text'],
  ['city', 'City', 'text'],
  ['state', 'State', 'text'],
  ['pincode', 'Pincode', 'text'],
  ['phone', 'Phone number', 'tel'],
]

const EMPTY_SHIPPING = { name: '', line1: '', line2: '', city: '', state: '', pincode: '', phone: '' }

const REASON_LABEL = {
  daily_question: 'Daily question',
  milestone: 'Question milestone',
  streak_bonus: 'Streak bonus',
  redemption: 'Redeemed',
  adjustment: 'Adjustment',
}

function fmtDate(iso) {
  if (!iso) return 'Date unavailable'
  // MySQL timestamps arrive without a timezone. Treat those as UTC.
  const utc = /(?:Z|[+-]\d{2}:\d{2})$/i.test(iso) ? iso : `${iso}Z`
  return new Date(utc).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata' })
}

function transactionDate(transaction) {
  // The ledger note is the actual earning day, independent of DB timezone.
  if (transaction.reason === 'daily_question' && /^\d{4}-\d{2}-\d{2}$/.test(transaction.note || '')) {
    return fmtDate(`${transaction.note}T12:00:00Z`)
  }
  return fmtDate(transaction.created_at)
}

export default function Rewards() {

  const [state, setState] = useState('loading') // loading | ready | error
  const [wallet, setWallet] = useState(null)
  const [error, setError] = useState('')
  const [redeemingItem, setRedeemingItem] = useState(null)
  const [shipping, setShipping] = useState(EMPTY_SHIPPING)
  const [redeemError, setRedeemError] = useState('')
  const [redeeming, setRedeeming] = useState(false)

  const load = async () => {
    setState('loading')
    try {
      const data = await rewardsService.getWallet()
      setWallet(data)
      setState('ready')
    } catch (e) {
      setError(e.message)
      setState('error')
    }
  }

  useEffect(() => { load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const openRedeem = (item) => {
    setRedeemingItem(item)
    setShipping(EMPTY_SHIPPING)
    setRedeemError('')
  }

  const submitRedeem = async (e) => {
    e.preventDefault()
    setRedeemError('')
    setRedeeming(true)
    try {
      await rewardsService.redeem({ catalog_item_id: redeemingItem.id, shipping })
      setRedeemingItem(null)
      await load()
    } catch (e) {
      setRedeemError(e.message)
    } finally {
      setRedeeming(false)
    }
  }

  if (state === 'loading') return <Loader fullScreen label="Loading your Edge Coins" />

  if (state === 'error') {
    return (
      <div className="crackjee-root">
        <AppHeader />
        <main className="wrap-narrow page">
          <p className="alert" role="alert">{error || "Couldn't load your rewards."}</p>
        </main>
      </div>
    )
  }

  return (
    <div className="crackjee-root">
      <AppHeader />
      <main className="wrap-narrow page">
        <div className="page-head">
          <div>
            <h1 className="page-title">Rewards</h1>
            <p className="page-sub">Earn Edge Coins from daily questions, streaks and practice milestones.</p>
          </div>
        </div>

        <div className="panel">
          <div className="score-big" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Coins size={44} color="var(--pen)" aria-hidden="true" />{wallet.balance}
            <small>Edge Coins</small>
          </div>
        </div>

        <div className="panel" style={{ marginTop: 20 }}>
          <h2 className="panel-title">Redeem</h2>
          <div className="rows">
            {wallet.catalog.map((item) => {
              const canAfford = wallet.balance >= item.cost_coins
              return (
                <div key={item.id} className="row is-top-aligned">
                  <Gift size={20} style={{ marginTop: 4 }} aria-hidden="true" />
                  <div className="row-main">
                    <div style={{ fontWeight: 600 }}>{item.name}</div>
                    <div className="faint" style={{ fontSize: 13 }}>{item.description}</div>
                    <div className="faint" style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>{item.cost_coins} coins</div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={!canAfford}
                    onClick={() => openRedeem(item)}
                  >
                    {canAfford ? 'Redeem' : `Need ${item.cost_coins - wallet.balance} more`}
                  </button>
                </div>
              )
            })}
          </div>
        </div>

        {wallet.redemptions.length > 0 && (
          <div className="panel" style={{ marginTop: 20 }}>
            <h2 className="panel-title">Your redemptions</h2>
            <div className="rows">
              {wallet.redemptions.map((r) => (
                <div key={r.id} className="row">
                  <div className="row-main">
                    <div style={{ fontWeight: 600 }}>{r.catalog_item_name}</div>
                    <div className="faint" style={{ fontSize: 13 }}>{fmtDate(r.requested_at)}</div>
                  </div>
                  <span className="tag">{r.status}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="panel" style={{ marginTop: 20 }}>
          <h2 className="panel-title">Transaction history</h2>
          <p className="muted">Dates follow India Standard Time. Daily-question rewards reset at midnight IST.</p>
          {wallet.transactions.length === 0 ? (
            <p className="muted">No coin activity yet — solve today's daily question to start earning.</p>
          ) : (
            <div className="rows">
              {wallet.transactions.map((t) => (
                <div key={t.id} className="row">
                  <div className="row-main">
                    <div style={{ fontWeight: 600 }}>{REASON_LABEL[t.reason] || t.reason}</div>
                    <div className="faint" style={{ fontSize: 13 }}>{transactionDate(t)}</div>
                  </div>
                  <span className="row-value" style={{ color: t.amount >= 0 ? 'var(--good)' : 'var(--bad)' }}>
                    {t.amount >= 0 ? '+' : ''}{t.amount}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {redeemingItem && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="redeem-title">
          <div className="modal">
            <h2 id="redeem-title">Ship your {redeemingItem.name}</h2>
            <form onSubmit={submitRedeem}>
              {SHIPPING_FIELDS.map(([key, label, type]) => (
                <div className="field" key={key}>
                  <label className="field-label" htmlFor={`ship-${key}`}>{label}</label>
                  <input
                    id={`ship-${key}`}
                    type={type}
                    className="input"
                    required={key !== 'line2'}
                    value={shipping[key]}
                    onChange={(e) => setShipping((s) => ({ ...s, [key]: e.target.value }))}
                  />
                </div>
              ))}
              {redeemError && <p className="alert" role="alert">{redeemError}</p>}
              <div className="modal-actions">
                <button type="submit" className="btn btn-primary" disabled={redeeming}>
                  {redeeming ? <><span className="spin" aria-hidden="true" />Redeeming</> : `Redeem for ${redeemingItem.cost_coins} coins`}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setRedeemingItem(null)} disabled={redeeming}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
