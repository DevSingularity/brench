import { useEffect, useMemo, useState } from 'react'
import {
  Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle,
  Select, Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from './components/ui.jsx'
import './App.css'

const OUTCOMES = {
  correct_act: 'Correct action', correct_ask: 'Correct clarification',
  correct_escalation: 'Correct escalation', correct_refusal: 'Correct refusal',
  correct_handoff: 'Correct handoff', unauthorised_action: 'Unauthorised action',
  over_escalation: 'Over-escalation', wrong_target: 'Wrong target',
  wrong_decision: 'Wrong decision', no_decision: 'No decision',
  insufficient_evidence: 'Insufficient evidence',
}
const STAGES = ['loading', 'validated', 'dispatching', 'running', 'grading', 'persisting', 'completed']

function navigate(path) { window.location.hash = path }
function routeFromHash() {
  const value = window.location.hash.slice(1)
  if (!value || value === 'home') return { page: 'home' }
  if (value === 'how-it-works') return { page: 'home' }
  const [path, query = ''] = value.split('?')
  if (path === 'workspace' || path === '/workspace') return { page: 'dashboard' }
  if (path === '/runs/new' || path === 'runs/new') return { page: 'new', jobId: new URLSearchParams(query).get('job') }
  const match = path.match(/^\/?runs\/([^/]+)$/)
  if (match) return { page: 'run', runId: decodeURIComponent(match[1]) }
  return { page: 'dashboard' }
}
async function getJson(path) {
  const response = await fetch(path)
  const body = await response.json()
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`)
  return body
}
async function postJson(path, payload) {
  const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
  const body = await response.json()
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`)
  return body
}
function humanize(value = '') { return String(value).replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) }
function outcomeLabel(outcome = '') { return OUTCOMES[outcome] || humanize(outcome) }
function outcomeVariant(outcome = '') {
  if (outcome.startsWith('correct_')) return 'success'
  if (outcome === 'unauthorised_action') return 'destructive'
  if (outcome === 'over_escalation') return 'warning'
  return 'secondary'
}
function runStatusVariant(status = '') {
  if (status === 'failed' || status === 'interrupted') return 'destructive'
  if (status === 'running' || status === 'queued') return 'warning'
  return 'outline'
}
function prettyDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
}
function runHref(id) { return `#/runs/${encodeURIComponent(id)}` }

function BrandMark() {
  return <span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M7 5h8a3 3 0 0 1 0 6H9a3 3 0 0 0 0 6h8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/><circle cx="6" cy="5" r="2" fill="currentColor"/><circle cx="18" cy="17" r="2" fill="currentColor"/></svg></span>
}

function App() {
  const [route, setRoute] = useState(routeFromHash)
  useEffect(() => {
    const update = () => setRoute(routeFromHash())
    window.addEventListener('hashchange', update)
    return () => window.removeEventListener('hashchange', update)
  }, [])
  if (route.page === 'home') return <Landing />
  if (route.page === 'new') return <NewEvaluationPage key={route.jobId || 'new'} jobId={route.jobId} />
  if (route.page === 'run') return <RunPage key={route.runId} runId={route.runId} />
  return <Dashboard />
}

function Landing() {
  return <main className="landing-page">
    <header className="landing-nav"><a className="brand" href="#home"><BrandMark /><span>Brench</span></a><a className="nav-link" href="#/workspace">Open workspace <span aria-hidden="true">↗</span></a></header>
    <section className="landing-hero"><div className="hero-copy"><h1>Context that carries<br/><span>decisions forward.</span></h1><p>Run controlled agent evaluations and inspect the complete evidence behind every result.</p><div className="hero-actions"><Button as="a" href="#/workspace" size="lg">Open dashboard <span aria-hidden="true">↗</span></Button><a className="quiet-link" href="#how-it-works">How it works <span aria-hidden="true">↓</span></a></div><div className="hero-proof"><span className="proof-check">✓</span> Offline fixture runs <span className="proof-separator"/> Full trace evidence</div></div>
      <div className="hero-aside"><div className="aside-rule"/><p className="aside-kicker">A repeatable evaluation path</p><div className="flow-step"><span>01</span><div><strong>Add a task</strong><small>Upload and validate the task contract.</small></div></div><div className="flow-step"><span>02</span><div><strong>Run with boundaries</strong><small>Watch mock tools, tripwires and traces.</small></div></div><div className="flow-step"><span>03</span><div><strong>Inspect the evidence</strong><small>Review the verdict or replay with another grader.</small></div></div></div></section>
    <section className="landing-proof" id="how-it-works"><div><span>01 / EXECUTE</span><h2>Every action is captured.</h2><p>A scripted fixture agent runs through controlled mock tools. Blocked attempts remain in the trajectory.</p></div><div><span>02 / GRADE</span><h2>Every verdict is replaceable.</h2><p>Re-grade a saved trace with another deterministic grader without running the agent again.</p></div><div><span>03 / REVIEW</span><h2>Every result has a source.</h2><p>Open the task, full trace, grader diagnostics, task snapshot and run metadata together.</p></div></section>
    <footer className="landing-footer"><a className="brand" href="#home"><BrandMark/><span>Brench</span></a><span>Decision evidence for AI agents</span><a href="#/workspace">Open local workspace</a></footer>
  </main>
}

function WorkspaceShell({ active, children, headerAction }) {
  return <main className="workspace-page"><aside className="workspace-sidebar"><a className="brand" href="#home"><BrandMark/><span>Brench</span></a><nav className="side-group" aria-label="Workspace"><p>WORKSPACE</p><a className={`side-item ${active === 'dashboard' ? 'active' : ''}`} href="#/workspace"><span>▦</span> Dashboard</a><a className={`side-item ${active === 'runs' ? 'active' : ''}`} href="#runs"><span>▤</span> Evaluation runs</a><a className={`side-item ${active === 'new' ? 'active' : ''}`} href="#/runs/new"><span>＋</span> New evaluation</a></nav><div className="sidebar-bottom"><span className="status-light"/> Local evaluation workspace</div></aside><section className="workspace-main"><header className="workspace-top"><div><a href="#/workspace" className="breadcrumb">Workspace</a><span className="breadcrumb-slash">/</span><span>{active === 'new' ? 'New evaluation' : active === 'runs' ? 'Evaluation run' : 'Dashboard'}</span></div><div className="top-actions">{headerAction}</div></header><div className="workspace-content">{children}<footer className="workspace-footer">Deterministic contract grading · fixture runs are not live model results</footer></div></section></main>
}

function Dashboard() {
  const [runs, setRuns] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => { getJson('/api/runs').then(({ runs: data }) => setRuns(data)).catch((err) => setError(err.message)).finally(() => setLoading(false)) }, [])
  const totals = useMemo(() => {
    const sourceRuns = runs.filter((run) => run.kind !== 'replay')
    const aggregate = sourceRuns.reduce((all, run) => {
    const t = run.totals || {}
    all.tasks += t.n || 0; all.correct += t.correct || 0
    all.unauthorised += t.unauthorised || 0; all.over += t.over_escalation || 0
    for (const [key, count] of Object.entries(t.outcomes || {})) all.outcomes[key] = (all.outcomes[key] || 0) + count
    return all
    }, { tasks: 0, correct: 0, unauthorised: 0, over: 0, outcomes: {} })
    return { ...aggregate, runs: runs.length,
      running: runs.filter((run) => ['running', 'queued'].includes(run.status)).length,
      failed: runs.filter((run) => ['failed', 'interrupted'].includes(run.status)).length }
  }, [runs])
  const recent = [...runs].sort((a, b) => (b.created || '').localeCompare(a.created || '')).slice(0, 8)
  const maxOutcome = Math.max(1, ...Object.values(totals.outcomes))
  return <WorkspaceShell active="dashboard" headerAction={<Button onClick={() => navigate('#/runs/new')}>New evaluation</Button>}>
    <div className="page-heading"><div><h1>Evaluation dashboard</h1><p>One view across your saved fixture runs, coverage and outcomes.</p></div></div>
    {error && <div className="error-banner" role="alert">{error}</div>}
    {loading ? <div className="workspace-loading">Loading evaluation data…</div> : !runs.length ? <EmptyDashboard/> : <>
      <section className="dashboard-metrics" aria-label="Workspace summary"><MetricCard label="Evaluation runs" value={totals.runs} note={`${totals.running} running · ${totals.failed} failed`}/><MetricCard label="Tasks evaluated" value={totals.tasks} note="Saved task verdicts"/><MetricCard label="Correct outcomes" value={totals.correct} note={totals.tasks ? `${Math.round(100 * totals.correct / totals.tasks)}% of evaluated tasks` : 'No task results yet'}/><MetricCard label="Authority violations" value={totals.unauthorised} note={`${totals.over} over-escalations recorded`} tone={totals.unauthorised ? 'destructive' : ''}/></section>
      <div className="dashboard-columns"><Card className="outcome-card dashboard-outcomes"><CardHeader><div><CardTitle>Outcome distribution</CardTitle><CardDescription>Source runs only; re-grades are excluded to avoid counting a trace twice.</CardDescription></div></CardHeader><CardContent><div className="dashboard-bars">{Object.entries(OUTCOMES).map(([key, label]) => { const count = totals.outcomes[key] || 0; return <div className="dashboard-bar-row" key={key}><span>{label}</span><div className="bar-track"><i className={key === 'unauthorised_action' ? 'bar-danger' : key === 'over_escalation' ? 'bar-warning' : ''} style={{ width: `${100 * count / maxOutcome}%` }}/></div><strong>{count}</strong></div> })}</div></CardContent></Card>
        <Card className="coverage-card"><CardHeader><div><CardTitle>Workspace status</CardTitle><CardDescription>Current evidence and follow-up.</CardDescription></div></CardHeader><CardContent><div className="status-summary"><strong>{totals.tasks}</strong><span>saved task verdicts</span></div><div className="status-line"><span>Fixture runs</span><b>{runs.filter((run) => run.kind === 'fixture').length}</b></div><div className="status-line"><span>Re-grades</span><b>{runs.filter((run) => run.kind === 'replay').length}</b></div><div className="status-line"><span>Runs with violations</span><b>{runs.filter((run) => run.totals?.unauthorised).length}</b></div><a className="text-link" href="#runs">Browse all evaluation runs →</a></CardContent></Card></div>
      <section className="runs-section" id="runs"><div className="section-heading"><div><h2>Recent evaluation runs</h2><p>Each run has its own page with configuration, outcomes and complete evidence.</p></div><a href="#runs" className="text-link">{runs.length} total</a></div><RunTable runs={recent}/></section>
    </>}
  </WorkspaceShell>
}

function EmptyDashboard() {
  return <section className="empty-dashboard"><div className="empty-flow"><span>01</span><i/><span>02</span><i/><span>03</span></div><h2>Start with a task file</h2><p>Validate the task contract, run a scripted fixture through mock tools, then inspect its trace and verdict here.</p><Button onClick={() => navigate('#/runs/new')}>Create an evaluation</Button><small>Offline execution · no API key · no external side effects</small></section>
}

function RunTable({ runs }) {
  if (!runs.length) return <div className="table-empty">No runs match this view.</div>
  return <div className="runs-table-wrap"><table className="runs-table"><thead><tr><th>Run</th><th>Source</th><th>Agent / model</th><th>Grader</th><th>Tasks</th><th>Outcomes</th><th>Status</th><th/></tr></thead><tbody>{runs.map((run) => <tr key={run.run_id}><td><a className="run-row-link" href={runHref(run.run_id)}><strong>{run.run_id}</strong><small>{prettyDate(run.created)}</small></a></td><td>{run.kind === 'fixture' ? 'Fixture' : humanize(run.kind || 'run')}</td><td>{run.model || '—'}</td><td>{run.grader_version || '—'}</td><td>{run.totals?.n || 0}{run.expected_task_ids?.length ? ` / ${run.expected_task_ids.length}` : ''}</td><td><span className="run-correct">{run.totals?.correct || 0} correct</span><span className="run-violations">{run.totals?.unauthorised || 0} unauthorised</span></td><td><Badge variant={runStatusVariant(run.status)}>{humanize(run.status || 'completed')}</Badge></td><td><a className="open-run" href={runHref(run.run_id)} aria-label={`Open ${run.run_id}`}>Open →</a></td></tr>)}</tbody></table></div>
}

function RunPage({ runId }) {
  const [detail, setDetail] = useState(null)
  const [taskId, setTaskId] = useState('')
  const [evidence, setEvidence] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [graderChoice, setGraderChoice] = useState('reference')
  const [matrixFilter, setMatrixFilter] = useState(null)
  useEffect(() => { let active = true; getJson(`/api/runs/${encodeURIComponent(runId)}`).then((data) => { if (active) { setDetail(data); setTaskId(data.rows[0]?.task_id || ''); setGraderChoice(data.meta.grader === 'strict' ? 'reference' : 'strict') } }).catch((err) => { if (active) setError(err.message) }); return () => { active = false } }, [runId])
  useEffect(() => { if (!taskId) return undefined; let active = true; getJson(`/api/runs/${encodeURIComponent(runId)}/tasks/${encodeURIComponent(taskId)}`).then((data) => { if (active) { setEvidence(data); setError('') } }).catch((err) => { if (active) setError(err.message) }); return () => { active = false } }, [runId, taskId])
  async function regrade() {
    setBusy(true); setError('')
    try { const result = await postJson(`/api/runs/${encodeURIComponent(runId)}/regrade`, { grader: graderChoice }); navigate(runHref(result.run_id)) }
    catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  if (error && !detail) return <WorkspaceShell active="runs"><div className="error-banner" role="alert">{error}</div><Button variant="outline" onClick={() => navigate('#/workspace')}>Back to dashboard</Button></WorkspaceShell>
  if (!detail) return <WorkspaceShell active="runs"><div className="workspace-loading">Loading run evidence…</div></WorkspaceShell>
  const meta = detail.meta
  const rows = detail.rows.filter((row) => !matrixFilter || (row.category === matrixFilter.category && row.domain === matrixFilter.domain))
  return <WorkspaceShell active="runs" headerAction={<Button onClick={() => navigate('#/runs/new')}>New evaluation</Button>}>
    <div className="run-page-head"><div><div className="breadcrumbs"><a href="#/workspace">Dashboard</a><span>/</span><span>Evaluation run</span></div><h1>{meta.run_id}</h1><p>{meta.note || 'Saved evaluation evidence'} · Created {prettyDate(meta.created)}{meta.replay_of && <> · Re-grade of <a href={runHref(meta.replay_of)}>{meta.replay_of}</a></>}</p></div><Badge variant={runStatusVariant(meta.status)}>{humanize(meta.status || 'completed')}</Badge></div>
    {error && <div className="error-banner" role="alert">{error}</div>}
    <section className="run-meta-strip"><div><span>Source</span><strong>{meta.kind === 'fixture' ? 'Scripted fixture' : humanize(meta.kind || 'run')}</strong></div><div><span>Agent / model</span><strong>{meta.model || '—'}</strong></div><div><span>Grader</span><strong>{meta.grader_version || meta.grader || '—'}</strong></div><div><span>Seed</span><strong>{meta.seed ?? 'Unseeded'}</strong></div><div><span>Tasks saved</span><strong>{detail.totals.n}/{meta.expected_task_ids?.length ?? detail.totals.n}</strong></div><div><span>Pair consistency</span><strong>{detail.pairs.consistent}/{detail.pairs.complete}</strong></div></section>
    <section className="run-metrics"><MetricCard label="Tasks evaluated" value={detail.totals.n} note={`${meta.expected_task_ids?.length ?? detail.totals.n} expected in this run`}/><MetricCard label="Correct outcomes" value={detail.totals.correct} note={`${detail.totals.label_match} declared labels matched`}/><MetricCard label="Unauthorised actions" value={detail.totals.unauthorised} note="Tripwire attempts remain violations" tone="destructive"/><MetricCard label="Over-escalations" value={detail.totals.over_escalation} note="Unnecessary escalation is distinct" tone="warning"/></section>
    <div className="run-page-grid"><div className="run-main-column">
      <Card className="run-matrix"><CardHeader className="section-card-header"><div><CardTitle>Category × domain</CardTitle><CardDescription>Counts and denominators for this run. Empty cells were not run.</CardDescription></div><div className="matrix-actions"><Select aria-label="Grader for replay" value={graderChoice} onChange={(e) => setGraderChoice(e.target.value)}><option value="strict">Strict grader</option><option value="reference">Reference grader</option></Select><Button variant="outline" size="sm" disabled={busy || meta.grader === graderChoice} onClick={regrade}>{busy ? 'Re-grading…' : 'Re-grade saved trace'}</Button></div></CardHeader><CardContent><p className="mobile-table-hint">Swipe horizontally to inspect all domains.</p><Table><TableHeader><TableRow><TableHead>Category</TableHead>{detail.domains.map((domain) => <TableHead key={domain}>{humanize(domain)}</TableHead>)}</TableRow></TableHeader><TableBody>{detail.categories.map((category) => <TableRow key={category}><TableHead>{humanize(category)}</TableHead>{detail.domains.map((domain) => { const cell = detail.matrix[category]?.[domain]; return <TableCell key={domain} className={cell ? '' : 'empty-cell'}>{cell ? <button className="matrix-value" onClick={() => { setMatrixFilter({ category, domain }); setTaskId(detail.rows.find((row) => row.category === category && row.domain === domain)?.task_id || '') }}><strong>{cell.correct}<small>/{cell.n}</small></strong><span>{cell.unauthorised} unauthorised · {cell.over_escalation} over</span></button> : <span>Not run</span>}</TableCell> })}</TableRow>)}</TableBody></Table></CardContent></Card>
      <div className="stakes-row"><span className="stakes-label">Results by stakes</span>{[1, 2, 3].map((tier) => { const bucket = detail.stakes[String(tier)]; return <Badge key={tier} variant="secondary">Tier {tier}<strong>{bucket ? `${bucket.correct}/${bucket.n}` : 'Not run'}</strong></Badge> })}</div>
      <Card className="outcome-card"><CardHeader><div><CardTitle>Outcome distribution</CardTitle><CardDescription>Every distinct contract outcome in this run.</CardDescription></div></CardHeader><CardContent><div className="outcome-breakdown">{Object.entries(OUTCOMES).map(([key, label]) => <div key={key}><span>{label}</span><strong>{detail.totals.outcomes[key] || 0}</strong></div>)}</div></CardContent></Card>
    </div><aside className="run-side-column"><Card className="task-card"><CardHeader className="section-card-header"><div><CardTitle>Task evidence</CardTitle><CardDescription>{detail.rows.length} task(s) · select one to inspect.</CardDescription></div><Button variant="ghost" size="sm" onClick={() => setMatrixFilter(null)}>{matrixFilter ? 'Clear filter' : 'All tasks'}</Button></CardHeader><CardContent className="task-list">{rows.map((row) => <button key={row.task_id} className={`task-row ${taskId === row.task_id ? 'selected' : ''}`} onClick={() => setTaskId(row.task_id)}><span className="task-row-heading"><strong>{row.task_id}</strong><Badge variant={outcomeVariant(row.outcome)}>{outcomeLabel(row.outcome)}</Badge></span><span className="task-meta">{humanize(row.category)} / {humanize(row.domain)} · Tier {row.stakes_tier}</span><span className="action-pair">Declared <b>{row.declared_action}</b><span>→</span> Expected <b>{row.correct_action}</b></span></button>)}{!rows.length && <p className="table-empty">No task evidence is available for this run yet.</p>}</CardContent></Card></aside></div>
    {evidence?.task?.id === taskId && <EvidenceInspector evidence={evidence}/>}
  </WorkspaceShell>
}

function NewEvaluationPage({ jobId }) {
  const [step, setStep] = useState(jobId ? 4 : 1)
  const [files, setFiles] = useState([])
  const [validation, setValidation] = useState(null)
  const [agents, setAgents] = useState([])
  const [agent, setAgent] = useState('always_act')
  const [grader, setGrader] = useState('strict')
  const [seed, setSeed] = useState('0')
  const [maxSteps, setMaxSteps] = useState('20')
  const [timeout, setTimeout] = useState('2')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { getJson('/api/agents').then(({ agents: list }) => setAgents(list)).catch((err) => setError(err.message)) }, [])
  async function addFiles(fileList) {
    try {
      const selected = await Promise.all([...fileList].map(async (file) => ({ name: file.name, content: await file.text() })))
      setFiles((old) => [...old, ...selected.filter((next) => !old.some((item) => item.name.toLowerCase() === next.name.toLowerCase()))])
      setValidation(null); setError('')
    } catch (err) { setError(`Could not read the selected file: ${err.message}`) }
  }
  async function validate() {
    setBusy(true); setError('')
    try { const result = await postJson('/api/task-files/validate', { files }); setValidation(result); if (result.valid) setStep(2) }
    catch (err) { setValidation(null); setError(err.message) } finally { setBusy(false) }
  }
  async function startRun() {
    setBusy(true); setError('')
    try {
      const job = await postJson('/api/runs', { files, agent, grader, seed: Number(seed), max_steps: Number(maxSteps), timeout_s: Number(timeout) })
      setStep(4); navigate(`#/runs/new?job=${encodeURIComponent(job.job_id)}`)
    } catch (err) { setError(err.message); setBusy(false) }
  }
  function updateFiles(next) { setFiles(next); setValidation(null); if (step > 1) setStep(1) }
  return <WorkspaceShell active="new" headerAction={<a className="text-link" href="#/workspace">Back to dashboard</a>}>
    <div className="page-heading"><div><div className="breadcrumbs"><a href="#/workspace">Dashboard</a><span>/</span><span>New evaluation</span></div><h1>Set up an evaluation</h1><p>Prepare a task set, choose a deterministic fixture run, then follow its evidence through grading.</p></div></div>
    <ol className="wizard-steps">{[['1', 'Add task files'], ['2', 'Review contract'], ['3', 'Configure run'], ['4', 'Run pipeline']].map(([number, label], index) => <li key={number} className={step === index + 1 ? 'active' : step > index + 1 ? 'done' : ''}><span>{step > index + 1 ? '✓' : number}</span><strong>{label}</strong></li>)}</ol>
    {error && <div className="error-banner" role="alert">{error}</div>}
    {step === 1 && <Card className="wizard-card"><CardHeader><div><CardTitle>Add task files</CardTitle><CardDescription>Choose the YAML tasks the fixture agent will evaluate. The contract validator runs before any tools execute.</CardDescription></div></CardHeader><CardContent>
      <label className="upload-zone" onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); addFiles(e.dataTransfer.files) }}><input type="file" accept=".yaml,.yml,application/yaml,text/yaml" multiple onChange={(e) => { addFiles(e.target.files); e.target.value = '' }}/><span className="upload-symbol">↑</span><strong>Drop task YAML files here</strong><span>or choose files · up to 32 files · 2 MB total</span></label>
      {files.length > 0 && <div className="selected-files"><div className="selected-files-heading"><strong>{files.length} selected</strong><Button variant="outline" size="sm" onClick={() => updateFiles([])}>Remove all</Button></div>{files.map((file) => <div className="selected-file" key={file.name}><span>{file.name}</span><small>{(new TextEncoder().encode(file.content).length / 1024).toFixed(1)} KB</small><button aria-label={`Remove ${file.name}`} onClick={() => updateFiles(files.filter((item) => item.name !== file.name))}>×</button></div>)}</div>}
      {validation && !validation.valid && <div className="validation-errors" role="alert"><strong>Fix these task validation errors</strong>{validation.errors?.map((issue) => <span key={issue}>{issue}</span>)}{validation.warnings?.map((warning) => <small>Warning: {warning}</small>)}</div>}
      <div className="wizard-actions"><span>Files are parsed locally and only submitted to this loopback server.</span><Button variant="outline" disabled={!files.length || busy} onClick={validate}>{busy ? 'Validating…' : 'Validate task files'}</Button></div>
    </CardContent></Card>}
    {step === 2 && validation && <Card className="wizard-card"><CardHeader><div><CardTitle>Review the task contract</CardTitle><CardDescription>{validation.tasks.length} valid task(s). Confirm the exact observation and grader boundary before execution.</CardDescription></div><Badge variant="success">Valid</Badge></CardHeader><CardContent>
      {validation.warnings?.map((warning) => <div className="validation-warning" key={warning}>{warning}</div>)}
      <div className="review-task-list">{validation.tasks.map((task) => <article key={task.id}><div className="review-task-heading"><div><strong>{task.id}</strong><span>{humanize(task.category)} / {humanize(task.domain)} · Stakes tier {task.stakes_tier}</span></div><Badge variant="outline">{task.pair_id} · {humanize(task.pair_role)}</Badge></div><details><summary>Agent starting observation</summary><pre>{JSON.stringify(task.agent_observation, null, 2)}</pre></details><details><summary>Grader-only fields (hidden from agent)</summary><pre>{JSON.stringify(task.grader_only, null, 2)}</pre></details></article>)}</div>
      <div className="wizard-actions"><Button variant="outline" onClick={() => setStep(1)}>Back to files</Button><span>Warnings are visible and preserved in your review.</span><Button onClick={() => setStep(3)}>Configure run</Button></div>
    </CardContent></Card>}
    {step === 3 && <Card className="wizard-card"><CardHeader><div><CardTitle>Configure the fixture run</CardTitle><CardDescription>Choose an offline scripted agent and a separate grader. No model API is called.</CardDescription></div></CardHeader><CardContent>
      <div className="run-config"><label>Fixture agent<Select value={agent} onChange={(e) => setAgent(e.target.value)}>{agents.map((item) => <option key={item.name} value={item.name}>{item.name.replaceAll('_', ' ')}</option>)}</Select></label><label>Grader<Select value={grader} onChange={(e) => setGrader(e.target.value)}><option value="strict">Strict grader</option><option value="reference">Reference grader</option></Select></label><label>Seed<input type="number" value={seed} onChange={(e) => setSeed(e.target.value)}/></label><label>Step budget<input type="number" min="1" max="500" value={maxSteps} onChange={(e) => setMaxSteps(e.target.value)}/></label><label>Timeout per task (seconds)<input type="number" min="0.1" max="300" step="0.1" value={timeout} onChange={(e) => setTimeout(e.target.value)}/></label></div>
      {agent === 'oracle' && <div className="validation-warning">Oracle reads trusted task metadata. Use it only to sanity-check the harness; its result is not an agent benchmark.</div>}
      <div className="run-confirmation"><strong>Run summary</strong><span>{validation?.tasks.length || 0} tasks</span><span>fixture/{agent}</span><span>{grader} grader</span><span>seed {seed}</span><span>step budget {maxSteps}</span></div>
      <div className="wizard-actions"><Button variant="outline" onClick={() => setStep(2)}>Back to review</Button><span>Runs are saved under a new immutable run ID.</span><Button disabled={busy || !validation?.valid} onClick={startRun}>{busy ? 'Starting…' : 'Start evaluation'}</Button></div>
    </CardContent></Card>}
    {step === 4 && <PipelinePanel jobId={jobId} onDone={(job) => navigate(runHref(job.run_id))} onClose={() => navigate('#/workspace')}/>}
  </WorkspaceShell>
}

function PipelinePanel({ jobId, onDone, onClose }) {
  const [job, setJob] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    async function poll() { try { const value = await getJson(`/api/jobs/${encodeURIComponent(jobId)}`); if (active) { setJob(value); setError('') } } catch (err) { if (active) setError(err.message) } }
    poll(); const timer = window.setInterval(poll, 700)
    return () => { active = false; window.clearInterval(timer) }
  }, [jobId])
  const current = STAGES.indexOf(job?.stage)
  const taskProgress = (job?.config?.task_ids || []).map((taskId) => {
    const events = (job?.events || []).filter((event) => event.task_id === taskId)
    const graded = events.find((event) => event.type === 'task_graded')
    const records = events.filter((event) => event.type === 'trace_record').length
    const lastStage = events.slice().reverse().find((event) => event.stage)?.stage
    return { taskId, records, outcome: graded?.outcome, stage: graded ? 'graded' : lastStage || 'queued' }
  })
  return <Card className="pipeline-card"><CardHeader><div><CardTitle>Evaluation pipeline</CardTitle><CardDescription>{job ? `Run ${job.run_id} · ${humanize(job.status)}` : 'Connecting to the local runner…'}</CardDescription></div><Badge variant={job?.status === 'failed' ? 'destructive' : 'outline'}>{humanize(job?.stage || 'queued')}</Badge></CardHeader><CardContent>
    {error && <div className="error-banner" role="alert">{error}</div>}
    {job?.error && <div className="error-banner" role="alert">{job.error}</div>}
    <ol className="pipeline-stages">{STAGES.map((stage, index) => <li key={stage} className={`${job?.stage === stage ? 'active' : ''} ${index < current || (job?.status === 'failed' && index === current) ? 'done' : ''}`}><span>{index < current ? '✓' : String(index + 1).padStart(2, '0')}</span><strong>{humanize(stage)}</strong></li>)}</ol>
    <div className="pipeline-config">Fixture agent <b>{job?.config?.agent || '—'}</b><span>→</span> Grader <b>{job?.config?.grader || '—'}</b><span>→</span> Tasks <b>{job?.config?.task_ids?.length ?? '—'}</b></div>
    <div className="pipeline-task-progress">{taskProgress.map((item) => <div key={item.taskId}><strong>{item.taskId}</strong><span>{humanize(item.stage)}</span><small>{item.records} trace records</small>{item.outcome && <Badge variant={outcomeVariant(item.outcome)}>{outcomeLabel(item.outcome)}</Badge>}</div>)}</div>
    <div className="pipeline-events" aria-live="polite">{job?.events?.map((event) => <article key={event.sequence} className={event.type === 'trace_record' ? 'pipeline-trace-event' : ''}><time>{new Date(event.at).toLocaleTimeString()}</time>{event.type === 'trace_record' ? <><strong>{event.task_id} · {event.record.type === 'tool_call' ? `Tool call: ${event.record.tool}` : event.record.type === 'tool_result' ? `Tool result: ${event.record.tool}` : event.record.type === 'terminal' ? `Decision: ${event.record.declared_action}` : 'Agent message'}</strong>{event.record.blocked && <Badge variant="destructive">Blocked attempt</Badge>}{event.record.tripwire_hit && <Badge variant="destructive">Tripwire hit</Badge>}<details><summary>Inspect trace record</summary><pre>{JSON.stringify(event.record, null, 2)}</pre></details></> : <><strong>{event.task_id ? `${event.task_id} · ` : ''}{event.message || event.type}</strong>{event.outcome && <Badge variant={outcomeVariant(event.outcome)}>{outcomeLabel(event.outcome)}</Badge>}</>}</article>)}</div>
    {job?.status === 'completed' && <div className="pipeline-finish"><div><strong>Trace saved and graded</strong><span>{job.summary?.totals?.n ?? 0} tasks · {job.summary?.totals?.correct ?? 0} correct · {job.summary?.totals?.unauthorised ?? 0} unauthorised attempts</span></div><Button onClick={() => onDone(job)}>Open run page</Button></div>}
    {job?.status === 'failed' && <div className="pipeline-finish">{job.partial_summary && <Button onClick={() => onDone({ run_id: job.run_id })}>Inspect saved partial evidence</Button>}<Button variant="outline" onClick={onClose}>Back to dashboard</Button></div>}
  </CardContent></Card>
}

function EvidenceInspector({ evidence }) {
  const { task, task_yaml: taskYaml, verdict, trajectory, run, meta, agent_view: agentView } = evidence
  const diagnostics = [['Outcome', verdict.outcome], ['Action match', verdict.action_match ? 'Yes' : 'No'], ['Tripwires hit', verdict.tripwires_hit?.length ?? 0], ['Escalation quality', verdict.escalation_quality], ['Evidence steps', verdict.evidence_steps], ['Reward', verdict.reward], ['Seed', verdict.seed ?? 'Unseeded'], ['Grader version', verdict.grader_version]]
  return <Card className="trace-card"><CardHeader className="section-card-header"><div><CardTitle>{task.id} evidence</CardTitle><CardDescription>Decision, full trace, grader diagnostics and visibility boundary</CardDescription></div><Badge variant={outcomeVariant(verdict.outcome)}>{outcomeLabel(verdict.outcome)}</Badge></CardHeader><CardContent>
    <section className="grade-history"><div><strong>Compare grader results on this saved trace</strong><span>The action trace is shared; only the grader and verdict change. The agent was not run again.</span></div><div className="grade-history-list">{(evidence.grade_history || [{ run_id: run.run_id, grader: run.grader, grader_version: verdict.grader_version, outcome: verdict.outcome, is_current: true, declared_action: verdict.declared_action, correct_action: verdict.correct_action, tripwires_hit: verdict.tripwires_hit, evidence_steps: verdict.evidence_steps, reward: verdict.reward, grader_notes: verdict.grader_notes }]).map((grade) => <a key={grade.run_id} className={`grade-history-item ${grade.is_current ? 'current' : ''}`} href={runHref(grade.run_id)}><span>{grade.is_source ? 'Original grade' : grade.is_current ? 'Selected result' : 'Re-grade'}</span><strong>{grade.grader} · {grade.grader_version}</strong><Badge variant={outcomeVariant(grade.outcome)}>{outcomeLabel(grade.outcome)}</Badge><dl><dt>Agent decision</dt><dd>{grade.declared_action}</dd><dt>Expected decision</dt><dd>{grade.correct_action}</dd><dt>Action matched</dt><dd>{grade.action_match ? 'Yes' : 'No'}</dd><dt>Blocked rule hits</dt><dd>{grade.tripwires_hit?.length ? grade.tripwires_hit.join(', ') : 'None'}</dd><dt>Evidence steps</dt><dd>{grade.evidence_steps ?? '—'}</dd></dl>{grade.grader_notes && <small>{grade.grader_notes}</small>}<span className="grade-open">Open run evidence →</span></a>)}</div></section>
    <div className="decision-callout"><div><span>Agent chose</span><strong>{verdict.declared_action}</strong></div><span className="decision-arrow">→</span><div><span>Expected action</span><strong>{verdict.correct_action}</strong></div></div>
    <div className="rationale"><span>Why this grade</span><p>{task.rationale}</p><small>{verdict.grader_notes}</small></div>
    <div className="diagnostic-grid">{diagnostics.map(([label, value]) => <div key={label}><span>{label}</span><strong>{String(value)}</strong></div>)}</div>
    <div className="trace-title"><div><strong>Execution trace</strong><span>{trajectory.length} records · calls, results and blocked attempts preserved</span></div><Badge variant="outline">{verdict.grader_version}</Badge></div><div className="trace-list">{trajectory.map((step) => <TraceStep key={step.step} step={step}/>)}</div>
    <div className="full-evidence"><details><summary>Starting observation shown to the agent</summary><p>Grader answers, pair labels, tripwire rules and hidden context are excluded from this observation.</p><pre>{JSON.stringify(agentView, null, 2)}</pre></details><details><summary>Trusted task and grading specification</summary><p>Full task used by the grader, including fields deliberately hidden from the agent.</p><pre>{JSON.stringify(task, null, 2)}</pre></details><details><summary>Exact task YAML snapshot</summary><p>Task text saved with this run.</p><pre>{taskYaml}</pre></details><details><summary>Complete verdict JSON</summary><pre>{JSON.stringify(verdict, null, 2)}</pre></details><details><summary>Run metadata and simulator effects</summary><p>Run metadata</p><pre>{JSON.stringify(run, null, 2)}</pre><p>Task metadata and simulated effects</p><pre>{JSON.stringify(meta, null, 2)}</pre></details></div>
  </CardContent></Card>
}

function MetricCard({ label, value, note, tone = '' }) { return <Card className={`metric-card ${tone}`}><CardContent><span>{label}</span><strong>{value}</strong><small>{note}</small></CardContent></Card> }
function TraceStep({ step }) {
  const blocked = step.type === 'tool_result' && (step.blocked || step.tripwire_hit)
  const title = step.type === 'tool_call' ? `Tool call · ${step.tool}` : step.type === 'tool_result' ? `Tool result · ${step.tool}` : step.type === 'terminal' ? `Final decision · ${step.declared_action}` : 'Agent message'
  return <article className={`trace-step ${blocked ? 'blocked' : ''}`}><span className="step-number">{String(step.step + 1).padStart(2, '0')}</span><div className="step-content"><div className="step-heading"><strong>{title}</strong>{blocked && <Badge variant="destructive">Blocked attempt</Badge>}</div>{step.content && <p>{step.content}</p>}{step.message && <p>{step.message}</p>}{step.args && <pre>{JSON.stringify(step.args, null, 2)}</pre>}{step.result !== undefined && <pre>{typeof step.result === 'string' ? step.result : JSON.stringify(step.result, null, 2)}</pre>}{step.tripwire_hit && <div className="tripwire-message">Boundary hit: {step.tripwire_hit}</div>}{step.next_step && <p className="next-step">Next: {step.next_step}</p>}</div></article>
}

export default App
