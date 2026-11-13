import { useState, useRef, useEffect } from 'react'
import { sendMessage, resetSession } from './api'

const QUICK = [
  { label: '🌾 I am a farmer', text: 'I am a farmer' },
  { label: '🎓 I am a student', text: 'I am a student looking for scholarships' },
  { label: '🏪 Start a business', text: 'I want to start a small business' },
]
const STATUS = {
  potentially_eligible: ['You may be eligible', 'ok'],
  more_info_needed: ['More information needed', 'warn'],
  appears_not_eligible: ['Appears not to meet a condition', 'bad'],
}
const ICON = { met: '✅', not_met: '❌', unknown: '❔' }

function SchemeCard({ s }) {
  const [label, cls] = STATUS[s.status]
  return (
    <div className="card">
      <div className="card-head"><b>{s.name}</b><span className={`badge ${cls}`}>{label}</span></div>
      <p>{s.benefit}</p>
      <ul className="conds">{s.conditions.map((c, i) => <li key={i}>{ICON[c.result]} {c.text}</li>)}</ul>
      <details><summary>Documents to keep ready</summary>
        <ul>{s.documents.map((d) => <li key={d}>{d}</li>)}</ul></details>
      <a href={s.link} target="_blank" rel="noreferrer">Official site / apply →</a>
    </div>
  )
}

export default function App() {
  const [sid, setSid] = useState(null)
  const [msgs, setMsgs] = useState([])
  const [profile, setProfile] = useState({})
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const end = useRef(null)
  useEffect(() => end.current?.scrollIntoView({ behavior: 'smooth' }), [msgs, busy])

  async function send(text) {
    if (!text.trim() || busy) return
    setMsgs((m) => [...m, { role: 'user', text }])
    setInput(''); setBusy(true)
    try {
      const r = await sendMessage(sid, text)
      setSid(r.session_id); setProfile(r.profile || {})
      setMsgs((m) => [...m, { role: 'bot', text: r.message, schemes: r.schemes, sources: r.sources, asOf: r.data_as_of }])
    } catch (e) {
      setMsgs((m) => [...m, { role: 'bot', text: 'Could not reach the server. It may be waking up, so please try again in a minute.' }])
    } finally { setBusy(false) }
  }
  async function reset() { await resetSession(sid); setSid(null); setMsgs([]); setProfile({}) }

  return (
    <div className="app">
      <header>
        <h1>JanSahayak</h1><span>Find government schemes in plain words</span>
        <button onClick={reset}>New chat</button>
      </header>
      {Object.keys(profile).length > 0 && (
        <div className="profile">Your details (this session only): {Object.entries(profile).map(([k, v]) =>
          <span key={k} className="chip">{k.replace('_', ' ')}: {String(v)}</span>)}</div>
      )}
      <main>
        {msgs.length === 0 && (
          <div className="welcome">
            <h2>How can JanSahayak help you today?</h2>
            <p>Tell me about yourself, e.g. “I am a farmer in Uttar Pradesh with 2 acres”.</p>
            <div className="quick">{QUICK.map((q) => <button key={q.label} onClick={() => send(q.text)}>{q.label}</button>)}</div>
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="bubble">{m.text}</div>
            {m.schemes?.map((s) => <SchemeCard key={s.scheme_id} s={s} />)}
            {m.sources?.length > 0 && (
              <div className="sources">Sources: {m.sources.map((s) =>
                <a key={s.id} href={s.url} target="_blank" rel="noreferrer">[{s.id}] {s.title}{s.page ? ` p.${s.page}` : ''}</a>)}
                <div className="asof">Data as of {m.asOf}. Please confirm on the official site or at your nearest CSC.</div>
              </div>
            )}
          </div>
        ))}
        {busy && <div className="msg bot"><div className="bubble typing">Thinking…</div></div>}
        <div ref={end} />
      </main>
      <form onSubmit={(e) => { e.preventDefault(); send(input) }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type your message…" />
        <button disabled={busy}>Send</button>
      </form>
      <footer>We never ask for Aadhaar, bank or phone numbers. Results are guidance, not an official decision.</footer>
    </div>
  )
}
