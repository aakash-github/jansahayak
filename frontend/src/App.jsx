import { useState, useRef, useEffect } from 'react'
import { sendMessage, resetSession } from './api'
import { useListener, speak, stopSpeaking, canListen, canSpeak } from './speech'

const GROUPS = [
  { key: 'farmer', icon: '🌾', title: 'Farmer', desc: 'Income, insurance, loans', text: 'I am a farmer', tone: 'green' },
  { key: 'student', icon: '🎓', title: 'Student', desc: 'Scholarships & fees', text: 'I am a student looking for scholarships', tone: 'blue' },
  { key: 'entrepreneur', icon: '🏪', title: 'Business', desc: 'Loans & subsidies', text: 'I want to start a small business', tone: 'saffron' },
]
// Complete one-liners: telling everything at once usually means no follow-up questions at all
const EXAMPLES = [
  'Farmer in UP, 2 acres, age 35',
  'B.Tech girl, OBC, income 3 lakh',
  'मैं बिहार का किसान हूँ, 1 एकड़',
]
// Questions about the schemes on screen. With several cards we first ask "Which scheme?" (on the phone, no server call).
const FOLLOWUPS = { en: ['How do I apply?', 'What documents do I need?', 'Explain the benefits simply'],
  hi: ['आवेदन कैसे करें?', 'कौन से दस्तावेज़ चाहिए?', 'लाभ आसान भाषा में समझाइए'] }
// What the per-card buttons send, e.g. "How do I apply for PM-KISAN?"
const CARD_ASK = {
  en: { apply: (n) => `How do I apply for ${n}?`, docs: (n) => `What documents do I need for ${n}?` },
  hi: { apply: (n) => `${n} के लिए आवेदन कैसे करें?`, docs: (n) => `${n} के लिए कौन से दस्तावेज़ चाहिए?` },
}
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
// on phones the 🎤 button sits right next to the text box, so the placeholder skips the emoji
const isMobile = typeof window !== 'undefined' && window.matchMedia('(max-width: 640px)').matches
const fmt = (k, v) => k === 'annual_income' ? `₹${Number(v).toLocaleString('en-IN')}`
  : typeof v === 'boolean' ? (v ? 'Yes' : 'No')
  : k === 'category' ? String(v).toUpperCase()
  : k === 'occupation' ? ({ farmer: 'Farmer', student: 'Student', entrepreneur: 'Business' }[v] || v)
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
  // [S1] -> citation pill, **text** -> bold, links (plain or [text](url)) -> clickable
  const clean = text.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '$2')
  const parts = clean.split(/(\[S\d+\]|\*\*[^*]+\*\*|https?:\/\/[^\s)]+)/g)
  return (
    <div className="bubble">
      {parts.map((p, i) => /^\[S\d+\]$/.test(p) ? <sup key={i} className="cite">{p.slice(1, -1)}</sup>
        : /^\*\*[^*]+\*\*$/.test(p) ? <b key={i}>{p.slice(2, -2)}</b>
        : /^https?:\/\//.test(p) ? <a key={i} href={p.replace(/[.,]$/, '')} target="_blank" rel="noreferrer">{p}</a> : p)}
    </div>
  )
}

const isHindi = (t) => /[ऀ-ॿ]/.test(t || '')

/** One smart follow-up question with tap-to-answer buttons (or a dropdown for long lists like states). */
function FollowUp({ f, blocking, onPick, onSkip }) {
  const hi = isHindi(f.question)
  const names = f.helps_names?.length ? f.helps_names.join(', ') + (f.helps > f.helps_names.length ? ` +${f.helps - f.helps_names.length}` : '') : ''
  return (
    <div className={`followup ${blocking ? 'blocking' : ''}`}>
      {!blocking && (
        <p>💡 {f.why && <span>{f.why} </span>}<b>{f.question}</b>
          {names && <small className="helps">{hi ? 'इनकी जाँच होगी: ' : 'Helps check: '}{names}</small>}</p>
      )}
      {f.options.length > 8 ? (
        <select defaultValue="" onChange={(e) => e.target.value !== '' && onPick(f.options[e.target.value])}>
          <option value="" disabled>{hi ? 'चुनें…' : 'Choose…'}</option>
          {f.options.map((o, i) => <option key={o.label} value={i}>{o.label}</option>)}
        </select>
      ) : (
        <div className="chips">{f.options.map((o) => <button key={o.label} className="chip opt" onClick={() => onPick(o)}>{o.label}</button>)}</div>
      )}
      <div className="fu-foot">
        {f.input && <small>{hi ? (f.options.length ? 'या नीचे लिखें' : 'नीचे लिखें') : (f.options.length ? 'or type it below' : 'Type it in the box below')}</small>}
        {!blocking && <button className="skip" onClick={onSkip}>{hi ? 'छोड़ें' : 'Skip'}</button>}
      </div>
    </div>
  )
}

function SchemeCard({ s, onAsk, hi }) {
  const st = STATUS[s.status]
  const ask = CARD_ASK[hi ? 'hi' : 'en']
  const name = s.short_name || s.name
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
      <div className="card-actions">
        {onAsk && <button className="act" onClick={() => onAsk(ask.apply(name), s.scheme_id)}>📝 {hi ? 'आवेदन कैसे करें' : 'How to apply'}</button>}
        {onAsk && <button className="act" onClick={() => onAsk(ask.docs(name), s.scheme_id)}>📄 {hi ? 'दस्तावेज़' : 'Documents'}</button>}
        <a className="apply" href={s.link} target="_blank" rel="noreferrer">{hi ? 'आधिकारिक साइट' : 'Official site'} →</a>
      </div>
    </article>
  )
}

export default function App() {
  const [sid, setSid] = useState(null)
  const [msgs, setMsgs] = useState([])
  const [profile, setProfile] = useState({})
  const [labels, setLabels] = useState({}) // button text for tapped answers, e.g. "Up to ₹2.5 lakh"
  const [skipped, setSkipped] = useState(-1) // index of the bot message whose follow-up was skipped
  const [chooser, setChooser] = useState(null) // generic question waiting for "Which scheme?" pick
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [slow, setSlow] = useState(false)
  const [lang, setLang] = useState('en-IN')
  const [speaking, setSpeaking] = useState(null) // index of message being read aloud
  const viaVoice = useRef(false)
  const end = useRef(null)
  const inputRef = useRef(null)
  const mic = useListener({ lang, onFinal: (t) => { viaVoice.current = true; send(t) } })

  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])

  function readAloud(i, text) {
    if (!canSpeak) return
    if (speaking === i) { stopSpeaking(); setSpeaking(null); return }
    setSpeaking(i)
    const hindi = isHindi(text) // Devanagari -> Hindi voice
    speak(text, { lang: hindi ? 'hi-IN' : 'en-IN', onEnd: () => setSpeaking((s) => (s === i ? null : s)) })
  }

  // `set` comes from a tapped answer button: the backend stores it directly (faster, no AI guess)
  async function send(text, set = null, schemeId = null) {
    if (!text.trim() || busy) return
    setChooser(null)
    const voice = viaVoice.current
    viaVoice.current = false
    stopSpeaking(); setSpeaking(null)
    const botIndex = msgs.length + 1 // user message goes at msgs.length, reply right after
    setMsgs((m) => [...m, { role: 'user', text, voice }])
    setInput(''); setBusy(true); setSlow(false)
    const timer = setTimeout(() => setSlow(true), 8000)
    try {
      const r = await sendMessage(sid, text, set, schemeId)
      setSid(r.session_id); setProfile(r.profile || {}); setLabels(r.profile_labels || {})
      const bot = { role: 'bot', text: r.message, schemes: r.schemes, sources: r.sources, asOf: r.data_as_of, followup: r.followup, blocking: r.needs_followup }
      setMsgs((m) => [...m, bot])
      if (voice) readAloud(botIndex, spoken(bot)) // asked by voice -> answer by voice
      if (r.followup?.input && !r.followup.options.length) setTimeout(() => inputRef.current?.focus(), 50)
    } catch {
      setMsgs((m) => [...m, { role: 'bot', text: 'I could not reach the server. It may be waking up, so please try again in a minute.' }])
    } finally { clearTimeout(timer); setBusy(false) }
  }
  async function reset() { stopSpeaking(); setSpeaking(null); await resetSession(sid); setSid(null); setMsgs([]); setProfile({}); setLabels({}) }
  // read the follow-up question aloud too (unless the reply already is that question)
  const spoken = (m) => (m.followup && !m.blocking ? `${m.text} ${m.followup.question}` : m.text)
  const last = msgs[msgs.length - 1]
  const lastIdx = msgs.length - 1
  const activeFollowup = !busy && last?.role === 'bot' && last.followup && skipped !== lastIdx ? last.followup : null
  const chatHi = isHindi([...msgs].reverse().find((m) => m.role === 'bot')?.text)
  // generic question ("How do I apply?"): one card -> ask about it; several -> "Which scheme?" buttons first
  function askGeneric(q) {
    const cards = last?.schemes || []
    if (cards.length === 1) return send(q, null, cards[0].scheme_id)
    setChooser({
      q, field: 'scheme', question: chatHi ? 'किस योजना के बारे में?' : 'Which scheme do you mean?', helps: 0, helps_names: [],
      options: cards.map((s) => ({ label: s.short_name || s.name, scheme_id: s.scheme_id })),
    })
  }

  return (
    <div className="page">
      <header className="top">
        <div className="brand" onClick={reset} role="button">
          <span className="logo">ज</span>
          <div><b>JanSahayak</b><small>जन सहायक · Your scheme guide</small></div>
        </div>
        {msgs.length > 0 && <button className="ghost" onClick={reset}>↺ New chat</button>}
      </header>

      <div className={`layout ${msgs.length === 0 ? 'home' : ''}`}>
        <main className="chat">
          {msgs.length === 0 ? (
            <section className="welcome">
              <div className="hero">
                <div>
                  <span className="tag">🏛️ 28 schemes · Hindi &amp; English</span>
                  <h1>Find government schemes meant for you</h1>
                  <p>Tap who you are. We check the official rules and show what you can apply for.</p>
                </div>
                <Hero />
              </div>
              <h2>I am a…</h2>
              <div className="groups">
                {GROUPS.map((g) => (
                  <button key={g.key} className={`group ${g.tone}`} onClick={() => send(g.text, { occupation: g.key })}>
                    <span className="gicon">{g.icon}</span>
                    <span className="gtext"><b>{g.title}</b><small>{g.desc}</small></span>
                    <span className="garrow" aria-hidden="true">→</span>
                  </button>
                ))}
              </div>
              <div className="try">
                <span>Or just say it:</span>
                {EXAMPLES.map((e) => <button key={e} className="chip" onClick={() => send(e)}>{e}</button>)}
              </div>
              <div className="trust">
                <span>🛡️ No Aadhaar or bank details</span>
                <span>📚 Official sources</span>
                {canListen && <span>🎤 Speak Hindi or English</span>}
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
                      <button className={`listen ${speaking === i ? 'on' : ''}`} onClick={() => readAloud(i, spoken(m))}>
                        {speaking === i ? '⏹ Stop' : '🔊 Listen'}
                      </button>
                    )}
                    {m.schemes?.length > 0 && <div className="schemes">{m.schemes.map((s) => <SchemeCard key={s.scheme_id} s={s} hi={isHindi(m.text)} onAsk={busy ? null : (q, id) => send(q, null, id)} />)}</div>}
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
              {chooser && !busy ? (
                <div className="follow">
                  <FollowUp f={chooser} onSkip={() => setChooser(null)}
                    onPick={(o) => send(`${chooser.q} (${o.label})`, null, o.scheme_id)} />
                </div>
              ) : activeFollowup && (
                <div className="follow">
                  <FollowUp f={activeFollowup} blocking={last.blocking} onSkip={() => setSkipped(lastIdx)}
                    onPick={(o) => send(o.label, o.set && Object.keys(o.set).length ? o.set : null, o.scheme_id || null)} />
                </div>
              )}
              {!busy && !chooser && last?.role === 'bot' && last.schemes?.length > 0 && (
                <div className="chips follow">{FOLLOWUPS[chatHi ? 'hi' : 'en'].map((f) => <button key={f} className="chip" onClick={() => askGeneric(f)}>{f}</button>)}</div>
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
              ref={inputRef}
              value={mic.listening ? mic.interim : input}
              onChange={(e) => setInput(e.target.value)}
              readOnly={mic.listening}
              className={mic.listening ? 'listening' : ''}
              placeholder={mic.listening ? (lang === 'hi-IN' ? 'बोलिए… सुन रहा हूँ' : 'Listening… speak now')
                : !canListen ? 'Type your question'
                : isMobile ? 'Type or tap to speak' : 'Type or tap 🎤 to speak'}
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

        {msgs.length > 0 && <aside className="side">
          <div className="panel">
            <h4>👤 Your details</h4>
            {Object.keys(profile).length === 0
              ? <p className="muted">Nothing yet. As you chat, the details we understand appear here.</p>
              : <dl>{Object.entries(profile).map(([k, v]) => <div key={k}><dt>{LABELS[k] || k.replace('_', ' ')}</dt><dd>{(k !== 'occupation' && labels[k]) || fmt(k, v)}</dd></div>)}</dl>}
            <p className="muted small">Kept only for this session. “New chat” clears it.</p>
          </div>
          <div className="panel">
            <h4>🧭 How it works</h4>
            <ol className="steps"><li>Pick who you are, or type / 🎤 speak</li><li>See matching schemes straight away</li><li>Tap an answer to sharpen the results</li><li>Open documents &amp; official links</li></ol>
          </div>
          <div className="panel note">Results are guidance, not an official decision. Need help applying? Visit your nearest <b>CSC</b>.</div>
        </aside>}
      </div>
    </div>
  )
}
