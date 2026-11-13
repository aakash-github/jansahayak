const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
// `set` = values from a tapped answer button, e.g. {category: 'sc'} (stored directly, no AI call)
// `scheme_id` = the question is about one scheme (card button or "Which scheme?" pick)
export async function sendMessage(session_id, message, set = null, scheme_id = null) {
  const r = await fetch(`${API}/api/chat`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id, message, set, scheme_id }),
  })
  if (!r.ok) throw new Error(`Server error ${r.status}`)
  return r.json()
}
export async function resetSession(session_id) {
  await fetch(`${API}/api/reset`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id, message: '' }),
  }).catch(() => {})
}
