import { useState, useRef, useEffect } from 'react'
import { sendMessage, resetSession } from './api'
import { useListener, speak, stopSpeaking, canListen, canSpeak } from './speech'

const GROUPS = [
  { key: 'farmer', icon: '🌾', title: 'Farmer', desc: 'Income support, crop insurance, farm credit', text: 'I am a farmer', tone: 'green' },
  { key: 'student', icon: '🎓', title: 'Student', desc: 'Scholarships & education support', text: 'I am a student looking for scholarships', tone: 'blue' },
  { key: 'entrepreneur', icon: '🏪', title: 'Business', desc: 'Loans, subsidies, MSME support', text: 'I want to start a small business', tone: 'saffron' },
]
const EXAMPLES = [
  'I am a farmer in Uttar Pradesh with 2 acres of land',
  'B.Tech student, girl, family income 3 lakh',
  'I want to start a tailoring business, age 28',
]
const FOLLOWUPS = ['What documents do I need?', 'How do I apply?', 'Explain the benefits simply']
const STATUS = {
  potentially_eligible: { label: 'May be eligible', cls: 'ok', icon: '✓' },
  more_info_needed: { label: 'Need more info', cls: 'warn', icon: '?' },
  appears_not_eligible: { label: 'Condition not met', cls: 'bad', icon: '✕' },
}
const COND = { met: ['✓', 'ok'], not_met: ['✕', 'bad'], unknown: ['?', 'warn'] }
const LABELS = {
  occupation: 'Occupation', state: 'State', age: 'Age', annual_income: 'Family income', gender: 'Gender',
  category: 'Category', disability: 'Disability', land_acres: 'Land (acres)', course: 'Course', business_type: 'Business',
  shg_member: 'Women SHG member', class12_top20: 'Top 20% in Class 12', class12_top1: 'Top 1% in Class 12',
  top_institution: 'Top institute', school_student: 'School student', swanath_category: 'Swanath category', dpiit_recognised: 'DPIIT startup',
}
const fmt = (k, v) => k === 'annual_income' ? `₹${Number(v).toLocaleString('en-IN')}`
  : typeof v === 'boolean' ? (v ? 'Yes' : 'No')
  : k === 'category' ? String(v).toUpperCase()
  : String(v).charAt(0).toUpperCase() + String(v).slice(1)

function Hero() {
  return (
    <svg className="hero-art" viewBox="0 0 200 160" aria-hidden="true">
      <circle cx="150" cy="40" r="22" fill="#ffd8a8" />
      <path d="M0 120 Q50 90 100 115 T200 105 V160 H0Z" fill="rgba(255,255,255,.18)" />
      <path d="M0 135 Q60 110 120 132 T200 125 V160 H0Z" fill="rgba(255,255,255,.28)" />
      <g transform="translate(40 60)">
        <rect x="0" y="20" width="56" height="44" rx="4" fill="#fff" opacity=".95" />
        <path d="M-6 22 L28 -2 L62 22Z" fill="#fff" opacity=".95" />
        <rect x="22" y="40" width="12" height="24" fill="#e8590c" />
        <circle cx="28" cy="10" r="5" fill="#2f9e44" />
      </g>
      <g fill="#fff" opacity=".9">
        <rect x="118" y="88" width="4" height="30" /><circle cx="120" cy="84" r="9" />
        <rect x="140" y="94" width="4" height="24" /><circle cx="142" cy="90" r="7" />
      </g>
    </svg>
  )
}

function Bubble({ text }) {
  // turn [S1] into small citation pills and **text** into bold
  const parts = text.split(/(\[S\d+\]|\*\*[^*]+\*\*)/g)
  return (
    <div className="bubble">
      {parts.map((p, i) => /^\[S\d+\]$/.test(p) ? <sup key={i} className="cite">{p.slice(1, -1)}</sup>
        : /^\*\*[^*]+\*\*$/.test(p) ? <b key={i}>{p.slice(2, -2)}</b> : p)}
    </div>
  )
}

function SchemeCard({ s }) {
  const st = STATUS[s.status]
  return (
    <article className={`scheme ${st.cls}`}>
      <header>
        <h3>{s.name}</h3>
        <span className={`pill ${st.cls}`}>{st.icon} {st.label}</span>
      </header>
      <p className="benefit">💰 {s.benefit}</p>
      <ul className="conds">
        {s.conditions.map((c, i) => <li key={i}><span className={`dot ${COND[c.result][1]}`}>{COND[c.result][0]}</span>{c.text}</li>)}
      </ul>
      <details>
        <summary>📄 Documents to keep ready ({s.documents.length})</summary>
        <ul className="docs">{s.documents.map((d) => <li key={d}>{d}</li>)}</ul>
      </details>
      <a className="apply" href={s.link} target="_blank" rel="noreferrer">Visit official site →</a>
    </article>
  )
}

export default function App() {
  const [sid, setSid] = useState(null)
  const [msgs, setMsgs] = useState([])
  const [profile, setProfile] = useState({})
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [slow, setSlow] = useState(false)
  const [lang, setLang] = useState('en-IN')
  const [speaking, setSpeaking] = useState(null) // index of message being read aloud
  const viaVoice = useRef(false)
  const end = useRef(null)
  const mic = useListener({ lang, onFinal: (t) => { viaVoice.current = true; send(t) } })

  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])

  function readAloud(i, text) {
    if (!canSpeak) return
    if (speaking === i) { stopSpeaking(); setSpeaking(null); return }
    setSpeaking(i)
    const hindi = /[ऀ-ॿ]/.test(text) // Devanagari -> Hindi voice
    speak(text, { lang: hindi ? 'hi-IN' : 'en-IN', onEnd: () => setSpeaking((s) => (s === i ? null : s)) })
  }

  async function send(text) {
    if (!text.trim() || busy) return
    const voice = viaVoice.current
    viaVoice.current = false
    stopSpeaking(); setSpeaking(null)
    const botIndex = msgs.length + 1 // user message goes at msgs.length, reply right after
    setMsgs((m) => [...m, { role: 'user', text, voice }])
    setInput(''); setBusy(true); setSlow(false)
    const timer = setTimeout(() => setSlow(true), 8000)
    try {
      const r = await sendMessage(sid, text)
      setSid(r.session_id); setProfile(r.profile || {})
      setMsgs((m) => [...m, { role: 'bot', text: r.message, schemes: r.schemes, sources: r.sources, asOf: r.data_as_of, followup: r.needs_followup }])
      if (voice) readAloud(botIndex, r.message) // asked by voice -> answer by voice
    } catch {
      setMsgs((m) => [...m, { role: 'bot', text: 'I could not reach the server. It may be waking up, so please try again in a minute.' }])
    } finally { clearTimeout(timer); setBusy(false) }
  }
  async function reset() { stopSpeaking(); setSpeaking(null); await resetSession(sid); setSid(null); setMsgs([]); setProfile({}) }
  const last = msgs[msgs.length - 1]

  return (
    <div className="page">
      <header className="top">
        <div className="brand" onClick={reset} role="button">
          <span className="logo">ज</span>
          <div><b>JanSahayak</b><small>जन सहायक · Your scheme guide</small></div>
        </div>
        {msgs.length > 0 && <button className="ghost" onClick={reset}>↺ New chat</button>}
      </header>

      <div className="layout">
        <main className="chat">
          {msgs.length === 0 ? (
            <section className="welcome">
              <div className="hero">
                <div>
                  <span className="tag">🇮🇳 Government schemes, made simple</span>
                  <h1>Find the schemes meant for you, in plain words.</h1>
                  <p>Tell us about yourself. JanSahayak checks the official eligibility rules, lists the documents you need and links you to the official site.</p>
                </div>
                <Hero />
              </div>
              <h2>Who are you looking for support as?</h2>
              <div className="groups">
                {GROUPS.map((g) => (
                  <button key={g.key} className={`group ${g.tone}`} onClick={() => send(g.text)}>
                    <span className="gicon">{g.icon}</span><b>{g.title}</b><small>{g.desc}</small>
                  </button>
                ))}
              </div>
              <h2>Or try an example</h2>
              <div className="chips">{EXAMPLES.map((e) => <button key={e} className="chip" onClick={() => send(e)}>“{e}”</button>)}</div>
              <div className="trust">
                {canListen && <span>🎤 Speak in English or Hindi</span>}
                <span>🛡️ No Aadhaar, bank or phone numbers asked</span>
                <span>📚 Answers cite official sources</span>
                <span>⚖️ Rules decide eligibility, not AI guesses</span>
              </div>
            </section>
          ) : (
            <section className="thread">
              {msgs.map((m, i) => (
                <div key={i} className={`msg ${m.role}`}>
                  {m.role === 'bot' && <span className="avatar">ज</span>}
                  <div className="col">
                    <Bubble text={m.text} />
                    {m.role === 'user' && m.voice && <small className="via">🎤 spoken</small>}
                    {m.role === 'bot' && canSpeak && (
                      <button className={`listen ${speaking === i ? 'on' : ''}`} onClick={() => readAloud(i, m.text)}>
                        {speaking === i ? '⏹ Stop' : '🔊 Listen'}
                      </button>
                    )}
                    {m.schemes?.length > 0 && <div className="schemes">{m.schemes.map((s) => <SchemeCard key={s.scheme_id} s={s} />)}</div>}
                    {m.sources?.length > 0 && (
                      <div className="sources">
                        <b>Sources</b>
                        {m.sources.map((s) => <a key={s.id} href={s.url} target="_blank" rel="noreferrer"><sup className="cite">{s.id}</sup>{s.title}{s.page ? `, p.${s.page}` : ''}</a>)}
                        <small>Data as of {m.asOf}. Always confirm on the official site or at your nearest Common Service Centre (CSC).</small>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {busy && (
                <div className="msg bot"><span className="avatar">ज</span>
                  <div className="bubble typing"><i /><i /><i />{slow && <small>Waking up the server, this can take up to a minute…</small>}</div>
                </div>
              )}
              {!busy && last?.role === 'bot' && last.schemes?.length > 0 && (
                <div className="chips follow">{FOLLOWUPS.map((f) => <button key={f} className="chip" onClick={() => send(f)}>{f}</button>)}</div>
              )}
              <div ref={end} />
            </section>
          )}

          {mic.error && <div className="mic-error" onClick={mic.clearError}>{mic.error} ✕</div>}
          <form className="composer" onSubmit={(e) => { e.preventDefault(); send(input) }}>
            {canListen && (
              <button type="button" className="lang" onClick={() => setLang(lang === 'en-IN' ? 'hi-IN' : 'en-IN')}
                title="Language you will speak in" disabled={mic.listening}>
                {lang === 'en-IN' ? 'EN' : 'हिं'}
              </button>
            )}
            <input
              value={mic.listening ? mic.interim : input}
              onChange={(e) => setInput(e.target.value)}
              readOnly={mic.listening}
              className={mic.listening ? 'listening' : ''}
              placeholder={mic.listening ? (lang === 'hi-IN' ? 'बोलिए… सुन रहा हूँ' : 'Listening… speak now') : 'Type or tap 🎤 to speak'}
            />
            {canListen && (
              <button type="button" className={`mic ${mic.listening ? 'on' : ''}`} disabled={busy}
                onClick={mic.listening ? mic.stop : mic.start} aria-label={mic.listening ? 'Stop listening' : 'Speak'}
                title={mic.listening ? 'Stop' : 'Tap and speak'}>
                {mic.listening ? '■' : '🎤'}
              </button>
            )}
            <button disabled={busy || mic.listening || !input.trim()} aria-label="Send">➤</button>
          </form>
        </main>

        <aside className="side">
          <div className="panel">
            <h4>👤 Your details</h4>
            {Object.keys(profile).length === 0
              ? <p className="muted">Nothing yet. As you chat, the details we understand appear here.</p>
              : <dl>{Object.entries(profile).map(([k, v]) => <div key={k}><dt>{LABELS[k] || k.replace('_', ' ')}</dt><dd>{fmt(k, v)}</dd></div>)}</dl>}
            <p className="muted small">Kept only for this session. “New chat” clears it.</p>
          </div>
          <div className="panel">
            <h4>🧭 How it works</h4>
            <ol className="steps"><li>Type, or tap 🎤 and speak</li><li>Tell us about yourself</li><li>We check official rules</li><li>See schemes, documents &amp; links</li></ol>
          </div>
          <div className="panel note">Results are guidance, not an official decision. Need help applying? Visit your nearest <b>CSC</b>.</div>
        </aside>
      </div>
    </div>
  )
}
