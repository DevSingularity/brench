import { useEffect, useMemo, useState } from 'react'
import {
  Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle,
  Select, Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from './components/ui.jsx'
import './App.css'

const OUTCOME_LABELS = {
  correct_act: 'Correct action', correct_ask: 'Correct clarification',
  correct_escalation: 'Correct escalation', correct_refusal: 'Correct refusal',
  correct_handoff: 'Correct handoff', unauthorised_action: 'Unauthorised action',
  over_escalation: 'Over-escalation', wrong_target: 'Wrong target',
  wrong_decision: 'Wrong decision', no_decision: 'No decision',
  insufficient_evidence: 'Insufficient evidence',
}

async function getJson(path) {
  const response = await fetch(path)
  const body = await response.json()
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`)
  return body
}

function outcomeVariant(outcome = '') {
  if (outcome.startsWith('correct_')) return 'success'
  if (outcome === 'unauthorised_action') return 'destructive'
  if (outcome === 'over_escalation') return 'warning'
  return 'secondary'
}

function outcomeLabel(outcome = '') { return OUTCOME_LABELS[outcome] || outcome.replaceAll('_', ' ') }
function humanize(value = '') { return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) }

function BrandMark() {
  return <span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M7 5h8a3 3 0 0 1 0 6H9a3 3 0 0 0 0 6h8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/><circle cx="6" cy="5" r="2" fill="currentColor"/><circle cx="18" cy="17" r="2" fill="currentColor"/></svg></span>
}

function App() {
  const [workspace, setWorkspace] = useState(window.location.hash !== '' && window.location.hash !== '#home')
  useEffect(() => {
    const update = () => setWorkspace(window.location.hash !== '' && window.location.hash !== '#home')
    window.addEventListener('hashchange', update)
    return () => window.removeEventListener('hashchange', update)
  }, [])

  return workspace ? <Workspace /> : <Landing />
}

function Landing() {
  return <main className="landing-page">
    <header className="landing-nav">
      <a className="brand" href="#home"><BrandMark /><span>Brench</span></a>
      <a className="nav-link" href="#workspace">Open workspace <span aria-hidden="true">↗</span></a>
    </header>
    <section className="landing-hero">
      <div className="hero-copy">
        <Badge variant="outline" className="hero-badge"><span className="badge-dot" /> Agent evaluation workspace</Badge>
        <h1>Context that carries<br /><span>decisions forward.</span></h1>
        <p>Brench makes agent decisions easier to inspect. Follow each action from the task context through the trace to the grade.</p>
        <div className="hero-actions"><Button as="a" href="#workspace" size="lg">Open workspace <span aria-hidden="true">↗</span></Button><a className="quiet-link" href="#how-it-works">How it works <span aria-hidden="true">↓</span></a></div>
        <div className="hero-proof"><span className="proof-check">✓</span> Deterministic grading <span className="proof-separator" /> Local, offline demo</div>
      </div>
      <div className="hero-aside" aria-label="Evaluation flow">
        <div className="aside-rule" />
        <p className="aside-kicker">From raw trace to clear evidence</p>
        <div className="flow-step"><span>01</span><div><strong>Load a task</strong><small>Use a supplied or custom YAML case.</small></div></div>
        <div className="flow-step"><span>02</span><div><strong>Run with boundaries</strong><small>Mock tools record every allowed or blocked call.</small></div></div>
        <div className="flow-step"><span>03</span><div><strong>Review the decision</strong><small>See the grade beside the complete trace.</small></div></div>
      </div>
    </section>

    <section className="preview-section" aria-label="Brench workspace preview">
      <div className="preview-chrome"><div className="chrome-dots"><i /><i /><i /></div><span>brench / evaluation</span><Badge variant="secondary">Workspace preview</Badge></div>
      <div className="preview-app">
        <aside className="preview-sidebar"><a className="brand small-brand" href="#home"><BrandMark /><span>Brench</span></a><p>WORKSPACE</p><div className="side-item active"><span>◫</span> Overview</div><div className="side-item"><span>▤</span> Evaluation runs</div><div className="side-divider"/><p>METHOD</p><div className="side-item"><span>⌘</span> Grading rules</div><div className="side-item"><span>↗</span> Trace evidence</div><div className="sidebar-footer"><span className="status-light"/> Local workspace</div></aside>
        <div className="preview-main"><div className="preview-heading"><div><p>OVERVIEW</p><h2>Good decisions, made visible.</h2></div><Badge variant="outline">Illustrative sample</Badge></div>
          <div className="preview-metrics"><div><span>Tasks reviewed</span><strong>06</strong><small>across three paired cases</small></div><div><span>Correct decisions</span><strong>06</strong><small>based on contract rules</small></div><div><span>Violations</span><strong className="metric-alert">00</strong><small>attempts preserved in trace</small></div></div>
          <div className="preview-table"><div className="preview-table-head"><span>RECENT DECISIONS</span><span>OUTCOME</span></div><div className="preview-row"><span><i className="row-mark green"/> Invoice above authority cap</span><Badge variant="success">Correct escalation</Badge></div><div className="preview-row"><span><i className="row-mark green"/> Refund within discretion</span><Badge variant="success">Correct action</Badge></div><div className="preview-row"><span><i className="row-mark amber"/> Payroll change from personal email</span><Badge variant="warning">Correct escalation</Badge></div></div>
        </div>
      </div>
    </section>

    <section className="how-section" id="how-it-works"><div><p className="section-kicker">A review you can follow</p><h2>Every grade points back<br />to something the agent did.</h2></div><div className="how-copy"><p>Brench compares the agent’s final choice with a task’s authority, checks earlier tool calls for violations, then keeps the trace beside the result.</p><Button as="a" href="#workspace" variant="outline">Explore evaluation runs <span aria-hidden="true">↗</span></Button></div></section>
    <footer className="landing-footer"><a className="brand" href="#home"><BrandMark /><span>Brench</span></a><span>Decision evidence for AI agents</span><a href="#workspace">Open local workspace</a></footer>
  </main>
}

function Workspace() {
  const [runs, setRuns] = useState([])
  const [runId, setRunId] = useState('')
  const [detail, setDetail] = useState(null)
  const [taskId, setTaskId] = useState('')
  const [evidence, setEvidence] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [matrixFilter, setMatrixFilter] = useState(null)

  useEffect(() => {
    getJson('/api/runs').then(({ runs: data }) => { setRuns(data); if (data.length) setRunId(data.at(-1).run_id); setLoading(false) }).catch((err) => { setError(err.message); setLoading(false) })
  }, [])
  useEffect(() => {
    if (!runId) return
    let active = true
    getJson(`/api/runs/${encodeURIComponent(runId)}`).then((data) => {
      if (!active) return
      setDetail(data); setTaskId(data.rows[0]?.task_id || ''); setEvidence(null); setMatrixFilter(null); setError(''); setLoading(false)
    }).catch((err) => { if (active) { setError(err.message); setLoading(false) } })
    return () => { active = false }
  }, [runId])
  useEffect(() => {
    if (!runId || !taskId) return
    let active = true
    getJson(`/api/runs/${encodeURIComponent(runId)}/tasks/${encodeURIComponent(taskId)}`).then((data) => { if (active) setEvidence(data) }).catch((err) => { if (active) setError(err.message) })
    return () => { active = false }
  }, [runId, taskId])

  const selectedRun = useMemo(() => runs.find((run) => run.run_id === runId), [runs, runId])
  if ((loading && !detail) || (runId && detail?.meta?.run_id !== runId)) return <main className="workspace-loading">Loading Brench workspace…</main>
  return <main className="workspace-page">
    <aside className="workspace-sidebar"><a className="brand" href="#home"><BrandMark /><span>Brench</span></a><div className="side-group"><p>WORKSPACE</p><a className="side-item active" href="#workspace"><span>◫</span> Overview</a><a className="side-item" href="#run-evidence"><span>▤</span> Evaluation runs <Badge variant="secondary">{runs.length}</Badge></a><a className="side-item" href="#evidence"><span>⌘</span> Trace evidence</a></div><div className="sidebar-bottom"><span className="status-light"/> Local evaluation workspace</div></aside>
    <section className="workspace-main"><header className="workspace-top"><div><a href="#home" className="breadcrumb">Brench</a><span className="breadcrumb-slash">/</span><span>Overview</span></div><div className="top-actions"><Badge variant="outline">{selectedRun?.kind === 'fixture' ? 'Fixture data' : selectedRun?.kind || 'No run selected'}</Badge><Select aria-label="Evaluation run" value={runId} onChange={(event) => setRunId(event.target.value)}>{runs.map((run) => <option key={run.run_id} value={run.run_id}>{run.run_id}</option>)}</Select></div></header>
      <div className="workspace-content"><div className="workspace-welcome"><div><p className="section-kicker">RUN OVERVIEW</p><h1>Good afternoon.<br /><span>Your evidence is ready.</span></h1><p>Inspect where an agent’s decision held, where it crossed its authority, and what happened along the way.</p></div><Button as="a" href="#evidence" variant="outline">Review trace <span aria-hidden="true">↓</span></Button></div>
        {error && <div className="error-banner" role="alert">{error}</div>}
        {!runs.length && !error && <Card className="empty-card"><CardHeader><CardTitle>No saved runs yet</CardTitle><CardDescription>Run <code>python -m harness demo</code> from the project root to create fixture evidence.</CardDescription></CardHeader></Card>}
        {detail && <>
          <div className="metric-grid"><MetricCard label="Decisions evaluated" value={detail.totals.n} note={`${detail.pairs.complete} complete paired scenarios`} /><MetricCard label="Correct outcomes" value={detail.totals.correct} note={`${detail.totals.label_match} final labels matched`} /><MetricCard label="Unauthorised actions" value={detail.totals.unauthorised} note="Blocked attempts still count" tone="destructive" /><MetricCard label="Over-escalations" value={detail.totals.over_escalation} note="Unnecessary handoffs" tone="warning" /></div>
          <Card className="matrix-card"><CardHeader className="section-card-header"><div><CardTitle>Decision matrix</CardTitle><CardDescription>Correct outcomes over evaluated cases. Select a cell to filter tasks.</CardDescription></div><Badge variant="outline">{selectedRun?.model || 'No model'}</Badge></CardHeader><CardContent><Table><TableHeader><TableRow><TableHead>Task category</TableHead>{detail.domains.map((domain) => <TableHead key={domain}>{humanize(domain)}</TableHead>)}</TableRow></TableHeader><TableBody>{detail.categories.map((category) => <TableRow key={category}><TableHead>{humanize(category)}</TableHead>{detail.domains.map((domain) => { const cell = detail.matrix[category]?.[domain]; return <TableCell key={domain} className={cell ? '' : 'empty-cell'}>{cell ? <button className="matrix-value" onClick={() => { setMatrixFilter({ category, domain }); const first = detail.rows.find((row) => row.category === category && row.domain === domain); if (first) setTaskId(first.task_id) }}><strong>{cell.correct}<small>/{cell.n}</small></strong><span>{cell.unauthorised ? `${cell.unauthorised} unauthorised` : cell.over_escalation ? `${cell.over_escalation} over-escalated` : 'graded'}</span></button> : <span>Not run</span>}</TableCell>})}</TableRow>)}</TableBody></Table></CardContent></Card>
          <div className="stakes-row"><span className="stakes-label">Results by stakes</span>{[1, 2, 3].map((tier) => { const bucket = detail.stakes[String(tier)]; return <Badge key={tier} variant="secondary">Tier {tier} <strong>{bucket ? `${bucket.correct}/${bucket.n}` : 'Not run'}</strong></Badge> })}</div>
          <div className="evidence-grid" id="run-evidence"><Card className="task-card"><CardHeader className="section-card-header"><div><CardTitle>Task decisions</CardTitle><CardDescription>Choose a case to inspect its evidence.</CardDescription></div><Button variant="ghost" size="sm" onClick={() => setMatrixFilter(null)}>{matrixFilter ? 'Clear filter' : `${detail.rows.length} tasks`}</Button></CardHeader><CardContent className="task-list">{detail.rows.filter((row) => !matrixFilter || (row.category === matrixFilter.category && row.domain === matrixFilter.domain)).map((row) => <button key={row.task_id} className={`task-row ${taskId === row.task_id ? 'selected' : ''}`} onClick={() => setTaskId(row.task_id)}><span className="task-row-heading"><strong>{row.task_id}</strong><Badge variant={outcomeVariant(row.outcome)}>{outcomeLabel(row.outcome)}</Badge></span><span className="task-meta">{humanize(row.category)} / {humanize(row.domain)}</span><span className="action-pair">Agent chose <b>{row.declared_action}</b><span>→</span> Expected <b>{row.correct_action}</b></span></button>)}</CardContent></Card>
            {evidence && <Card className="trace-card"><CardHeader className="section-card-header"><div><CardTitle>{evidence.task.id}</CardTitle><CardDescription>Decision and execution trace</CardDescription></div><Badge variant={outcomeVariant(evidence.verdict.outcome)}>{outcomeLabel(evidence.verdict.outcome)}</Badge></CardHeader><CardContent><div className="decision-callout"><div><span>Agent chose</span><strong>{evidence.verdict.declared_action}</strong></div><span className="decision-arrow">→</span><div><span>Expected action</span><strong>{evidence.verdict.correct_action}</strong></div></div><div className="rationale"><span>Why this grade</span><p>{evidence.task.rationale}</p><small>{evidence.verdict.grader_notes}</small></div><div className="trace-title"><div><strong>Execution trace</strong><span>{evidence.trajectory.length} steps · blocked calls are preserved</span></div><Badge variant="outline">{evidence.verdict.grader_version}</Badge></div><div className="trace-list">{evidence.trajectory.map((step) => <TraceStep key={step.step} step={step} />)}</div></CardContent></Card>}
          </div>
        </>}
        <footer className="workspace-footer">Deterministic contract grading · fixture runs are not live model results</footer>
      </div>
    </section>
  </main>
}

function MetricCard({ label, value, note, tone }) { return <Card className={`metric-card ${tone || ''}`}><CardContent><span>{label}</span><strong>{value}</strong><small>{note}</small></CardContent></Card> }

function TraceStep({ step }) {
  const blocked = step.type === 'tool_result' && (step.blocked || step.tripwire_hit)
  const title = step.type === 'tool_call' ? `Tool call · ${step.tool}` : step.type === 'tool_result' ? `Tool result · ${step.tool}` : step.type === 'terminal' ? `Final decision · ${step.declared_action}` : 'Agent message'
  return <article className={`trace-step ${blocked ? 'blocked' : ''}`}><span className="step-number">{String(step.step + 1).padStart(2, '0')}</span><div className="step-content"><div className="step-heading"><strong>{title}</strong>{blocked && <Badge variant="destructive">Blocked attempt</Badge>}</div>{step.content && <p>{step.content}</p>}{step.message && <p>{step.message}</p>}{step.args && <pre>{JSON.stringify(step.args, null, 2)}</pre>}{step.result && <pre>{typeof step.result === 'string' ? step.result : JSON.stringify(step.result, null, 2)}</pre>}{step.tripwire_hit && <div className="tripwire-message">Boundary hit: {step.tripwire_hit}</div>}{step.next_step && <p className="next-step">Next: {step.next_step}</p>}</div></article>
}

export default App
