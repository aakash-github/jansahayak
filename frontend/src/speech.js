// Voice in/out using the browser's built-in Web Speech API (no backend, no cost).
// Speech-to-text works in Chrome, Edge and Safari (not Firefox). Text-to-speech works almost everywhere.
import { useEffect, useRef, useState } from 'react'

const SR = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)
export const canListen = !!SR
export const canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window

const ERRORS = {
  'not-allowed': 'Microphone access is blocked. Allow it from the 🔒 icon in the address bar.',
  'service-not-allowed': 'Microphone access is blocked. Allow it from the 🔒 icon in the address bar.',
  'no-speech': "I didn't hear anything. Tap the mic and try again.",
  'audio-capture': 'No microphone found on this device.',
  network: 'Voice input needs an internet connection.',
}

/** Speech-to-text. Calls onFinal(text) when the user stops talking. */
export function useListener({ lang, onFinal }) {
  const [listening, setListening] = useState(false)
  const [interim, setInterim] = useState('')
  const [error, setError] = useState('')
  const rec = useRef(null)
  const cb = useRef(onFinal)
  cb.current = onFinal

  useEffect(() => () => rec.current?.abort(), [])

  function start() {
    if (!SR || listening) return
    stopSpeaking()
    const r = new SR()
    r.lang = lang
    r.interimResults = true // show words live while speaking
    r.continuous = false // stop automatically after a pause
    let finalText = ''
    r.onresult = (e) => {
      const text = Array.from(e.results).map((x) => x[0].transcript).join('')
      setInterim(text)
      if (e.results[e.results.length - 1].isFinal) finalText = text
    }
    r.onerror = (e) => { if (e.error !== 'aborted') setError(ERRORS[e.error] || `Voice input failed (${e.error}).`) }
    r.onend = () => {
      setListening(false)
      setInterim('')
      if (finalText.trim()) cb.current(finalText.trim())
    }
    setError('')
    setListening(true)
    r.start()
    rec.current = r
  }

  const stop = () => rec.current?.stop() // stop() still delivers the final text
  return { listening, interim, error, start, stop, clearError: () => setError('') }
}

/** Text-to-speech. Splits into sentences because Chrome cuts off long utterances. */
export function speak(text, { lang = 'en-IN', onEnd } = {}) {
  if (!canSpeak) return
  window.speechSynthesis.cancel()
  const clean = text
    .replace(/\[S\d+\]/g, '') // citations
    .replace(/\p{Extended_Pictographic}/gu, '') // emoji
    .replace(/[*#_`]/g, '')
    .replace(/\bRs\.?\s?/g, 'rupees ')
  const sentences = clean.split(/(?<=[.!?।])\s+/).filter((s) => s.trim())
  const voices = window.speechSynthesis.getVoices()
  const voice = voices.find((v) => v.lang === lang) || voices.find((v) => v.lang.startsWith(lang.slice(0, 2)))
  sentences.forEach((s, i) => {
    const u = new SpeechSynthesisUtterance(s)
    u.lang = lang
    u.rate = 0.95
    if (voice) u.voice = voice
    if (i === sentences.length - 1) { u.onend = onEnd; u.onerror = onEnd }
    window.speechSynthesis.speak(u)
  })
}

export function stopSpeaking() {
  if (canSpeak) window.speechSynthesis.cancel()
}
