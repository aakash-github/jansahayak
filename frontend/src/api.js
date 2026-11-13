const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export async function sendMessage(session_id, message) {
  const r = await fetch(`${API}/api/chat`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id, message }),
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
