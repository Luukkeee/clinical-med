'use client'

import { useState, useEffect, useRef } from 'react'

const API = 'http://localhost:8000'

/* ── Types ────────────────────────────────────────────────── */
interface Citation   { source: string; section: string; category: string; relevance_score: number }
interface SafetyReport {
  grounding_score: number; grounded_sentences: number; total_sentences: number
  ungrounded_sentences: string[]; numeric_validation: string; numeric_mismatches: any[]
  dangerous_content: boolean; danger_flags: string[]; safety_passed: boolean
}
interface QueryResponse {
  query: string; response: string; confidence_score: number; risk_level: string
  citations: Citation[]; safety_report: SafetyReport; confidence_reasoning: string
  query_analysis: { expanded_query: string; medical_concepts: string[]; query_type: string; urgency: string }
  retrieval_stats: { total_retrieved: number; evidence_used: number }
  performance: { total_time_seconds: number; agent_timings: { agent: string; time_seconds: number }[] }
}
interface WebScrapeResult {
  id: string; text: string; document: string; section: string; source_url: string
  pmid: string; journal: string; year: string; authors: string; mesh_terms: string[]
}
interface WebScrapeData {
  scrape_results: { query: string; source: string; results: WebScrapeResult[]; total_found: number; scrape_time_seconds: number }
  synthesized_response: QueryResponse | null
}
interface HealthData  { status: string; mode: string; vector_store_ready: boolean; total_chunks: number; documents_loaded: number }
interface AnalyticsData { total_queries: number; avg_confidence: number; risk_distribution: Record<string,number>; avg_response_time: number; queries: any[] }

/* ── Icons (inline SVG) ──────────────────────────────────── */
const Icon = {
  Search: () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"/></svg>,
  Sparkle: () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z"/></svg>,
  Shield: () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"/></svg>,
  Chart: () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"/></svg>,
  Globe: () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5a17.92 17.92 0 01-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418"/></svg>,
  Check: () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>,
  X: () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>,
  Warn: () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/></svg>,
  Arrow: () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12h15m0 0l-6.75-6.75M19.5 12l-6.75 6.75"/></svg>,
  Book: () => <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"/></svg>,
  Ext: () => <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"/></svg>,
}

const SAMPLES = [
  'What is the first-line treatment for Stage 2 hypertension?',
  'How do you manage acute STEMI?',
  'What are the diagnostic criteria for Type 2 Diabetes?',
  'Describe the management of acute anaphylaxis.',
  'What is the hour-1 bundle for sepsis?',
  'How do you manage atrial fibrillation?',
  'What are the KDIGO staging criteria for AKI?',
  'Describe stepwise asthma treatment.',
]

const AGENTS = ['Query Analyst', 'Retriever', 'Appraiser', 'Synthesizer', 'Safety Officer', 'Confidence']

/* ── Helpers ──────────────────────────────────────────────── */
const riskStyle = (r: string) => {
  if (r === 'low')      return 'bg-emerald-50 text-emerald-700 border-emerald-200'
  if (r === 'moderate') return 'bg-amber-50 text-amber-700 border-amber-200'
  if (r === 'high')     return 'bg-rose-50 text-rose-700 border-rose-200'
  return 'bg-surface-100 text-ink-500 border-surface-200'
}
const confColor = (s: number) => s >= 0.85 ? 'text-emerald-600' : s >= 0.65 ? 'text-amber-600' : 'text-rose-600'
const confBar   = (s: number) => s >= 0.85 ? 'bg-emerald-500'  : s >= 0.65 ? 'bg-amber-500'  : 'bg-rose-500'

/* ══════════════════════════════════════════════════════════ */
export default function Home() {
  const [query, setQuery]           = useState('')
  const [loading, setLoading]       = useState(false)
  const [result, setResult]         = useState<QueryResponse | null>(null)
  const [error, setError]           = useState('')
  const [health, setHealth]         = useState<HealthData | null>(null)
  const [analytics, setAnalytics]   = useState<AnalyticsData | null>(null)
  const [tab, setTab]               = useState<'query'|'analytics'>('query')
  const [webSearch, setWebSearch]    = useState(false)
  const [webData, setWebData]       = useState<WebScrapeData | null>(null)
  const [scraping, setScraping]     = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    fetch(`${API}/api/health`).then(r=>r.json()).then(setHealth).catch(()=>setHealth(null))
  }, [])

  const handleQuery = async () => {
    if (!query.trim()) return
    setLoading(true); setError(''); setResult(null); setWebData(null)
    try {
      if (webSearch) {
        setScraping(true)
        const r = await fetch(`${API}/api/webscrape`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ query: query.trim(), enable_web_search: true }) })
        if (!r.ok) throw new Error(`Server error: ${r.status}`)
        const d: WebScrapeData = await r.json()
        setWebData(d); if (d.synthesized_response) setResult(d.synthesized_response)
        setScraping(false)
      } else {
        const r = await fetch(`${API}/api/query`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ query: query.trim(), enable_web_search: false }) })
        if (!r.ok) throw new Error(`Server error: ${r.status}`)
        setResult(await r.json())
      }
      fetch(`${API}/api/analytics`).then(r=>r.json()).then(setAnalytics).catch(()=>{})
    } catch (e: any) { setError(e.message || 'Connection failed.') }
    finally { setLoading(false) }
  }

  /* ── Render helpers ── */
  const renderMarkdown = (text: string) =>
    text.split('\n').map((line, i) => {
      if (line.startsWith('**') && line.endsWith('**'))
        return <h4 key={i} className="md-heading">{line.replace(/\*\*/g, '')}</h4>
      if (line.startsWith('- '))
        return <li key={i} className="list-disc">{line.slice(2)}</li>
      if (/^\d+\./.test(line))
        return <li key={i} className="list-decimal">{line.replace(/^\d+\.\s*/, '')}</li>
      if (line.startsWith('---'))
        return <hr key={i} />
      if (!line.trim()) return <div key={i} className="h-2" />
      return <p key={i}>{line}</p>
    })

  /* ══════════════════ JSX ══════════════════════════════════ */
  return (
    <div className="min-h-screen flex flex-col">

      {/* ─── Navbar ─────────────────────────────────────── */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-surface-200">
        <div className="max-w-5xl mx-auto flex items-center justify-between px-6 h-14">
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-500 to-accent-700 flex items-center justify-center shadow-sm">
              <span className="text-white text-sm font-bold">M</span>
            </div>
            <div className="leading-tight">
              <span className="text-[15px] font-bold text-ink-900 tracking-tight">MedRAG</span>
              <span className="hidden sm:inline text-[11px] ml-2 text-ink-400 font-medium">Clinical Decision Support</span>
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-3">
            {health && (
              <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-ink-400 mr-2">
                <span className={`w-1.5 h-1.5 rounded-full ${health.status === 'healthy' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                {health.mode}&nbsp;·&nbsp;{health.total_chunks} chunks
              </div>
            )}
            <div className="flex p-0.5 bg-surface-100 rounded-lg">
              <button onClick={() => setTab('query')}
                className={`px-3 py-1 text-[13px] font-medium rounded-md transition-all duration-150
                  ${tab === 'query' ? 'bg-white shadow-sm text-ink-900' : 'text-ink-500 hover:text-ink-700'}`}>
                Query
              </button>
              <button onClick={() => { setTab('analytics'); fetch(`${API}/api/analytics`).then(r=>r.json()).then(setAnalytics).catch(()=>{}) }}
                className={`px-3 py-1 text-[13px] font-medium rounded-md transition-all duration-150
                  ${tab === 'analytics' ? 'bg-white shadow-sm text-ink-900' : 'text-ink-500 hover:text-ink-700'}`}>
                Analytics
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ─── Main ───────────────────────────────────────── */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-8">
        {tab === 'query' ? (
          <div className="space-y-6">

            {/* ── Hero / Search ── */}
            <section className="text-center pt-4 pb-2">
              <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-ink-900">
                Ask a clinical question
              </h1>
              <p className="mt-2 text-[15px] text-ink-400 max-w-lg mx-auto">
                Evidence-based answers powered by a 6-agent safety pipeline &amp; FAISS retrieval.
              </p>
            </section>

            {/* ── Query Card ── */}
            <div className="card p-5 animate-fade-in">
              <div className="relative">
                <textarea
                  ref={inputRef}
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleQuery() } }}
                  placeholder="e.g. What is the first-line treatment for Stage 2 hypertension?"
                  className="input-field pr-28 resize-none min-h-[56px]"
                  rows={2}
                />
                <button
                  onClick={handleQuery}
                  disabled={loading || !query.trim()}
                  className="btn-primary absolute right-2 top-2 !py-2 !px-4 !text-[13px]"
                >
                  {loading
                    ? <span className="flex items-center gap-1.5"><svg className="animate-spin w-3.5 h-3.5" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>Running…</span>
                    : <span className="flex items-center gap-1.5"><Icon.Sparkle />Analyze</span>}
                </button>
              </div>

              {/* Controls row */}
              <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap gap-1.5">
                  {SAMPLES.slice(0, 4).map((s, i) => (
                    <button key={i} onClick={() => { setQuery(s); inputRef.current?.focus() }}
                      className="text-[11px] px-2.5 py-1 rounded-full border border-surface-200 text-ink-500 hover:border-accent-300 hover:text-accent-600 transition-colors duration-150">
                      {s.length > 45 ? s.slice(0,45)+'…' : s}
                    </button>
                  ))}
                </div>
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <button
                    role="switch" aria-checked={webSearch}
                    onClick={() => setWebSearch(!webSearch)}
                    className={`relative w-9 h-5 rounded-full transition-colors duration-200 ${webSearch ? 'bg-accent-500' : 'bg-surface-300'}`}>
                    <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200 ${webSearch ? 'translate-x-4' : ''}`}/>
                  </button>
                  <span className="text-[12px] font-medium text-ink-500 flex items-center gap-1">
                    <Icon.Globe /> PubMed
                  </span>
                </label>
              </div>
            </div>

            {/* ── Loading State ── */}
            {loading && (
              <div className="card p-8 text-center animate-fade-in">
                <div className="flex items-center justify-center gap-3 mb-5">
                  <svg className="animate-spin w-5 h-5 text-accent-500" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  <span className="text-[14px] font-medium text-ink-700">
                    {scraping ? 'Scraping PubMed & synthesizing…' : 'Running 6-agent pipeline…'}
                  </span>
                </div>
                <div className="flex justify-center gap-2">
                  {AGENTS.map((a, i) => (
                    <span key={i}
                      className="text-[11px] px-2.5 py-1 rounded-full bg-accent-50 text-accent-600 font-medium animate-pulse-dot"
                      style={{ animationDelay: `${i * 0.25}s` }}>
                      {a}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* ── Error ── */}
            {error && (
              <div className="card border-rose-200 bg-rose-50 p-4 flex items-start gap-3 animate-fade-in">
                <span className="text-rose-500 mt-0.5"><Icon.Warn /></span>
                <p className="text-[13px] text-rose-700">{error}</p>
              </div>
            )}

            {/* ═══════ Results ═══════ */}
            {result && (
              <div className="space-y-5 animate-slide-up">

                {/* ── Score Strip ── */}
                <div className="card p-4 flex flex-col sm:flex-row items-start sm:items-center gap-4">
                  <div className="flex-1 w-full">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[12px] font-semibold uppercase tracking-wider text-ink-400">Confidence</span>
                      <span className={`text-lg font-bold tabular-nums ${confColor(result.confidence_score)}`}>
                        {(result.confidence_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-surface-200 overflow-hidden">
                      <div className={`h-full rounded-full transition-all duration-700 ease-out ${confBar(result.confidence_score)}`}
                        style={{ width: `${result.confidence_score * 100}%` }} />
                    </div>
                  </div>
                  <div className="flex items-center gap-2.5 shrink-0">
                    <span className={`pill ${riskStyle(result.risk_level)}`}>
                      {result.risk_level === 'low' && <Icon.Check />}
                      {result.risk_level === 'high' && <Icon.Warn />}
                      <span className="ml-1 capitalize">{result.risk_level} risk</span>
                    </span>
                    <span className="text-[11px] text-ink-400 tabular-nums">
                      {result.performance.total_time_seconds.toFixed(2)}s
                    </span>
                  </div>
                </div>

                {/* ── Clinical Response ── */}
                <div className="card p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <Icon.Sparkle />
                    <h2 className="text-[16px] font-bold text-ink-900">Clinical Response</h2>
                  </div>
                  <div className="md-response">
                    {renderMarkdown(result.response)}
                  </div>
                </div>

                {/* ── Safety Report ── */}
                <div className="card p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <Icon.Shield />
                    <h2 className="text-[16px] font-bold text-ink-900">Safety Report</h2>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {[
                      { label: 'Grounding', value: `${(result.safety_report.grounding_score*100).toFixed(0)}%`, ok: result.safety_report.grounding_score >= 0.7 },
                      { label: 'Numerics', value: result.safety_report.numeric_validation === 'passed' ? 'Passed' : 'Warning', ok: result.safety_report.numeric_validation === 'passed' },
                      { label: 'Safety', value: result.safety_report.safety_passed ? 'Passed' : 'Failed', ok: result.safety_report.safety_passed },
                      { label: 'Dangerous', value: result.safety_report.dangerous_content ? 'Detected' : 'None', ok: !result.safety_report.dangerous_content },
                    ].map((m, i) => (
                      <div key={i} className={`rounded-xl p-3.5 text-center border ${m.ok ? 'bg-emerald-50/60 border-emerald-100' : 'bg-rose-50/60 border-rose-100'}`}>
                        <p className={`text-xl font-bold tabular-nums ${m.ok ? 'text-emerald-600' : 'text-rose-600'}`}>{m.value}</p>
                        <p className="text-[11px] font-medium text-ink-400 mt-0.5">{m.label}</p>
                      </div>
                    ))}
                  </div>
                  {result.safety_report.danger_flags.length > 0 && (
                    <div className="mt-4 p-3 rounded-xl bg-rose-50 border border-rose-200">
                      {result.safety_report.danger_flags.map((f,i) => (
                        <p key={i} className="text-[13px] text-rose-700 flex items-center gap-1.5"><Icon.Warn />{f}</p>
                      ))}
                    </div>
                  )}
                </div>

                {/* ── Citations ── */}
                {result.citations.length > 0 && (
                  <div className="card p-6">
                    <div className="flex items-center gap-2 mb-4">
                      <Icon.Book />
                      <h2 className="text-[16px] font-bold text-ink-900">Evidence Sources</h2>
                      <span className="pill bg-surface-100 text-ink-500 border-surface-200 ml-1">{result.citations.length}</span>
                    </div>
                    <div className="space-y-2">
                      {result.citations.map((c, i) => (
                        <div key={i}
                          className="flex items-center justify-between p-3 rounded-xl bg-surface-50 hover:bg-surface-100 transition-colors duration-150 group">
                          <div className="min-w-0">
                            <p className="text-[13px] font-medium text-ink-900 truncate">{c.source}</p>
                            <p className="text-[11px] text-ink-400">{c.section} · {c.category}</p>
                          </div>
                          <span className="pill bg-accent-50 text-accent-600 border-accent-100 shrink-0 ml-3 tabular-nums">
                            {(c.relevance_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* ── PubMed Articles ── */}
                {webData && webData.scrape_results.results.length > 0 && (
                  <div className="card p-6">
                    <div className="flex items-center gap-2 mb-1">
                      <Icon.Globe />
                      <h2 className="text-[16px] font-bold text-ink-900">PubMed Research</h2>
                      <span className="pill bg-violet-50 text-violet-600 border-violet-100 ml-1">{webData.scrape_results.total_found} articles</span>
                    </div>
                    <p className="text-[11px] text-ink-400 mb-4">
                      Scraped from {webData.scrape_results.source} in {webData.scrape_results.scrape_time_seconds}s
                    </p>
                    <div className="space-y-2">
                      {webData.scrape_results.results.map((art, i) => (
                        <details key={i} className="group rounded-xl border border-surface-200 overflow-hidden">
                          <summary className="flex items-start gap-3 p-3.5 cursor-pointer hover:bg-surface-50 transition-colors duration-150">
                            <div className="flex-1 min-w-0">
                              <p className="text-[13px] font-medium text-ink-900 leading-snug">{art.document}</p>
                              <p className="text-[11px] text-ink-400 mt-0.5">
                                {art.authors}{art.year ? ` (${art.year})` : ''} — <span className="italic">{art.journal}</span>
                              </p>
                            </div>
                            <a href={art.source_url} target="_blank" rel="noopener noreferrer"
                              onClick={e => e.stopPropagation()}
                              className="pill bg-accent-50 text-accent-600 border-accent-100 hover:bg-accent-100 transition-colors shrink-0 gap-1">
                              <Icon.Ext />PMID:{art.pmid}
                            </a>
                          </summary>
                          <div className="px-3.5 pb-3.5 pt-2 border-t border-surface-200 text-[13px] text-ink-700 leading-relaxed">
                            {art.text}
                            {art.mesh_terms?.length > 0 && (
                              <div className="mt-2.5 flex flex-wrap gap-1">
                                {art.mesh_terms.map((t,j) => (
                                  <span key={j} className="text-[10px] px-1.5 py-0.5 rounded-md bg-violet-50 text-violet-600 font-medium">{t}</span>
                                ))}
                              </div>
                            )}
                          </div>
                        </details>
                      ))}
                    </div>
                  </div>
                )}

                {/* ── Pipeline Details ── */}
                <div className="card p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <Icon.Chart />
                    <h2 className="text-[16px] font-bold text-ink-900">Pipeline Details</h2>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-[13px]">
                    <div>
                      <p className="text-ink-400 text-[11px] font-medium mb-0.5">Query Type</p>
                      <p className="font-semibold text-ink-900 capitalize">{result.query_analysis.query_type.replace('_',' ')}</p>
                    </div>
                    <div>
                      <p className="text-ink-400 text-[11px] font-medium mb-0.5">Urgency</p>
                      <p className="font-semibold text-ink-900 capitalize">{result.query_analysis.urgency}</p>
                    </div>
                    <div>
                      <p className="text-ink-400 text-[11px] font-medium mb-0.5">Evidence</p>
                      <p className="font-semibold text-ink-900">{result.retrieval_stats.total_retrieved} → {result.retrieval_stats.evidence_used} used</p>
                    </div>
                    <div>
                      <p className="text-ink-400 text-[11px] font-medium mb-0.5">Concepts</p>
                      <div className="flex flex-wrap gap-1 mt-0.5">
                        {result.query_analysis.medical_concepts.slice(0,4).map((c,i) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.5 rounded-md bg-violet-50 text-violet-600 font-medium">{c}</span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Agent timings */}
                  <div className="mt-5">
                    <p className="section-title mb-2">Agent Timing</p>
                    <div className="flex gap-1.5">
                      {result.performance.agent_timings.map((t, i) => (
                        <div key={i} className="flex-1 text-center group">
                          <div className="bg-accent-50 group-hover:bg-accent-100 transition-colors rounded-t-lg py-2 px-1">
                            <span className="text-[11px] font-semibold text-accent-700 tabular-nums">{t.time_seconds.toFixed(2)}s</span>
                          </div>
                          <div className="bg-surface-50 rounded-b-lg py-1.5 px-1 border-x border-b border-surface-200">
                            <span className="text-[10px] font-medium text-ink-400">{t.agent.split(' ').pop()}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* ═══════ Analytics Tab ═══════ */
          <div className="space-y-6 animate-fade-in">
            <section className="pt-4 pb-2">
              <h1 className="text-2xl font-bold text-ink-900">Analytics</h1>
              <p className="text-[14px] text-ink-400 mt-1">Performance overview of your clinical queries.</p>
            </section>

            {analytics ? (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: 'Total Queries', value: analytics.total_queries, color: 'text-accent-600 bg-accent-50 border-accent-100' },
                    { label: 'Avg Confidence', value: `${(analytics.avg_confidence*100).toFixed(0)}%`, color: 'text-emerald-600 bg-emerald-50 border-emerald-100' },
                    { label: 'Avg Time', value: `${analytics.avg_response_time.toFixed(2)}s`, color: 'text-violet-600 bg-violet-50 border-violet-100' },
                    { label: 'Low Risk', value: analytics.risk_distribution['low'] || 0, color: 'text-emerald-600 bg-emerald-50 border-emerald-100' },
                  ].map((s,i) => (
                    <div key={i} className={`rounded-2xl border p-5 text-center ${s.color}`}>
                      <p className="text-3xl font-bold tabular-nums">{s.value}</p>
                      <p className="text-[12px] font-medium mt-1 opacity-70">{s.label}</p>
                    </div>
                  ))}
                </div>

                {/* Risk dist */}
                <div className="card p-6">
                  <h3 className="text-[14px] font-semibold text-ink-900 mb-3">Risk Distribution</h3>
                  <div className="flex gap-3">
                    {Object.entries(analytics.risk_distribution).map(([r, c]) => (
                      <div key={r} className={`flex-1 rounded-xl border text-center py-4 ${riskStyle(r)}`}>
                        <p className="text-2xl font-bold">{c as number}</p>
                        <p className="text-[11px] font-medium capitalize mt-0.5 opacity-70">{r}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Recent queries */}
                {analytics.queries.length > 0 && (
                  <div className="card p-6">
                    <h3 className="text-[14px] font-semibold text-ink-900 mb-3">Recent Queries</h3>
                    <div className="space-y-1.5">
                      {analytics.queries.slice(-10).reverse().map((q: any, i: number) => (
                        <div key={i} className="flex items-center justify-between p-3 rounded-xl hover:bg-surface-50 transition-colors duration-150">
                          <span className="text-[13px] text-ink-700 truncate flex-1">{q.query}</span>
                          <div className="flex items-center gap-2 ml-4 shrink-0">
                            <span className={`text-[13px] font-semibold tabular-nums ${confColor(q.confidence)}`}>
                              {(q.confidence*100).toFixed(0)}%
                            </span>
                            <span className={`pill text-[11px] ${riskStyle(q.risk_level)}`}>{q.risk_level}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="card p-12 text-center">
                <p className="text-ink-400 text-[14px]">No analytics data yet. Submit some queries first.</p>
              </div>
            )}
          </div>
        )}
      </main>

      {/* ─── Footer ─────────────────────────────────────── */}
      <footer className="border-t border-surface-200 mt-auto">
        <div className="max-w-5xl mx-auto px-6 py-4 text-center text-[11px] text-ink-400">
          MedRAG is a research prototype — not a certified medical device. Always consult qualified healthcare providers.
        </div>
      </footer>
    </div>
  )
}
