import { useEffect, useMemo, useState } from 'react'
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

function outcomeClass(outcome = '') {
  if (outcome.startsWith('correct_')) return 'good'
  if (outcome === 'unauthorised_action') return 'critical'
  if (outcome === 'over_escalation') return 'caution'
  return 'bad'
}

function App() {
  const [runs, setRuns] = useState([])
  const [runId, setRunId] = useState('')
  const [detail, setDetail] = useState(null)
  const [taskId, setTaskId] = useState('')
  const [evidence, setEvidence] = useState(null)
  const [matrixFilter, setMatrixFilter] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getJson('/api/runs').then(({ runs: data }) => {
      setRuns(data)
      if (data.length) setRunId(data.at(-1).run_id)
      setLoading(false)
    }).catch((err) => { setError(err.message); setLoading(false) })
  }, [])

  useEffect(() => {
    if (!runId) { setDetail(null); return }
    setLoading(true)
    getJson(`/api/runs/${encodeURIComponent(runId)}`).then((data) => {
      setDetail(data)
      setTaskId(data.rows[0]?.task_id || '')
      setEvidence(null)
      setMatrixFilter(null)
      setError('')
      setLoading(false)
    }).catch((err) => { setError(err.message); setLoading(false) })
  }, [runId])

  useEffect(() => {
    if (!runId || !taskId) { setEvidence(null); return }
    getJson(`/api/runs/${encodeURIComponent(runId)}/tasks/${encodeURIComponent(taskId)}`)
      .then(setEvidence).catch((err) => setError(err.message))
  }, [runId, taskId])

  const categories = detail?.categories || []
  const domains = detail?.domains || []
  const selectedRun = useMemo(() => runs.find((run) => run.run_id === runId), [runs, runId])

  if (loading && !detail) return <main className="loading">Loading saved evaluations…</main>
  return (
    <main className="workspace">
      <header className="topbar">
        <a className="wordmark" href="#overview" aria-label="Decision Bench home"><span className="mark">D</span> decision bench</a>
        <div className="top-meta"><span className="live-dot" /> Local evaluation workspace</div>
      </header>

      <section className="intro" id="overview">
        <div>
          <p className="eyebrow">Agent decision evaluation</p>
          <h1>Every decision,<br /><em>with its evidence.</em></h1>
          <p className="lede">Review what an agent chose, where it crossed a boundary, and the trace that explains the grade.</p>
        </div>
        <div className="run-picker">
          <label htmlFor="run-select">Evaluation run</label>
          <select id="run-select" value={runId} onChange={(event) => setRunId(event.target.value)}>
            {runs.map((run) => <option key={run.run_id} value={run.run_id}>{run.run_id}</option>)}
          </select>
          <span>{selectedRun ? `${selectedRun.model} · ${selectedRun.kind || 'imported'}` : 'Run the harness to create evidence'}</span>
        </div>
      </section>

      {error && <div className="notice" role="alert">{error}</div>}
      {!runs.length && !error && <section className="empty-state"><h2>No saved runs yet</h2><p>Run <code>python -m harness demo</code> from the project root to create fixture evidence.</p></section>}

      {detail && <>
        <section className="summary-grid" aria-label="Run summary">
          <article className="summary-main"><span>Decisions evaluated</span><strong>{detail.totals.n}</strong><small>across {detail.pairs.complete} complete paired scenarios</small></article>
          <Summary label="Correct outcomes" value={detail.totals.correct} detail={`${detail.totals.label_match} final labels matched`} tone="good" />
          <Summary label="Unauthorised actions" value={detail.totals.unauthorised} detail="blocked attempts still count" tone="critical" />
          <Summary label="Over-escalations" value={detail.totals.over_escalation} detail="unnecessary handoffs" tone="caution" />
        </section>

        <section className="matrix-section">
          <div className="section-heading"><div><p className="eyebrow">Performance map</p><h2>Where decisions break down</h2></div><p>Each cell shows correct outcomes over evaluated cases.</p></div>
          <div className="matrix-wrap"><table className="matrix"><thead><tr><th>Task category</th>{domains.map((domain) => <th key={domain}>{humanize(domain)}</th>)}</tr></thead>
            <tbody>{categories.map((category) => <tr key={category}><th>{humanize(category)}</th>{domains.map((domain) => {
              const cell = detail.matrix[category]?.[domain]
              return <td key={domain} className={cell ? 'filled' : 'unrun'}>{cell ? <button className="matrix-cell" onClick={() => { setMatrixFilter({ category, domain }); const first = detail.rows.find((row) => row.category === category && row.domain === domain); if (first) setTaskId(first.task_id) }}><strong>{cell.correct}<small>/{cell.n}</small></strong><span>{cell.unauthorised ? `${cell.unauthorised} unauthorised` : cell.over_escalation ? `${cell.over_escalation} over-escalated` : 'cases graded'}</span></button> : <span>Not run</span>}</td>
            })}</tr>)}</tbody></table></div>
        </section>

        <section className="stakes-strip" aria-label="Results by stakes tier"><strong>By stakes</strong>{[1, 2, 3].map((tier) => { const bucket = detail.stakes[String(tier)]; return <div key={tier}><span>Tier {tier}</span><b>{bucket ? `${bucket.correct}/${bucket.n}` : 'Not run'}</b></div> })}</section>

        <section className="evidence-layout">
          <div className="task-panel">
            <div className="section-heading compact"><div><p className="eyebrow">Run evidence</p><h2>Task decisions</h2></div><button className="count-chip clear-filter" onClick={() => setMatrixFilter(null)}>{matrixFilter ? `${humanize(matrixFilter.category)} · ${humanize(matrixFilter.domain)} ×` : `${detail.rows.length} tasks`}</button></div>
            <div className="task-list">{detail.rows.filter((row) => !matrixFilter || (row.category === matrixFilter.category && row.domain === matrixFilter.domain)).map((row) => <button key={row.task_id} className={`task-row ${taskId === row.task_id ? 'selected' : ''}`} onClick={() => setTaskId(row.task_id)}>
              <span className="task-row-top"><strong>{row.task_id}</strong><span className={`status-dot ${outcomeClass(row.outcome)}`} /></span>
              <span>{humanize(row.category)} · {humanize(row.domain)}</span>
              <span className="task-row-bottom"><span>{row.declared_action} <b>→</b> {row.correct_action}</span><span className={`outcome ${outcomeClass(row.outcome)}`}>{OUTCOME_LABELS[row.outcome] || row.outcome}</span></span>
            </button>)}</div>
          </div>

          {evidence && <div className="detail-panel">
            <div className="detail-heading"><div><p className="eyebrow">Decision record</p><h2>{evidence.task.id}</h2></div><span className={`outcome pill ${outcomeClass(evidence.verdict.outcome)}`}>{OUTCOME_LABELS[evidence.verdict.outcome] || evidence.verdict.outcome}</span></div>
            <div className="decision-compare"><div><span>Agent chose</span><strong>{evidence.verdict.declared_action}</strong></div><b aria-hidden="true">→</b><div><span>Expected</span><strong>{evidence.verdict.correct_action}</strong></div></div>
            <div className="why-box"><span>Why this grade</span><p>{evidence.task.rationale}</p>{evidence.verdict.grader_notes && <small>{evidence.verdict.grader_notes}</small>}</div>
            <div className="trace-header"><div><h3>Execution trace</h3><span>{evidence.trajectory.length} recorded steps · blocked actions are preserved</span></div><span className="grader-tag">{evidence.verdict.grader_version}</span></div>
            <div className="trace-list">{evidence.trajectory.map((step) => <TraceStep key={step.step} step={step} />)}</div>
          </div>}
        </section>
        <footer className="footnote">Grades come from deterministic contract rules. Fixture runs are controlled examples, not live model results.</footer>
      </>}
    </main>
  )
}

function Summary({ label, value, detail, tone }) {
  return <article className={`summary-card ${tone}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>
}

function TraceStep({ step }) {
  const blocked = step.type === 'tool_result' && (step.blocked || step.tripwire_hit)
  return <article className={`trace-step ${blocked ? 'blocked' : ''}`}>
    <div className="step-index">{String(step.step + 1).padStart(2, '0')}</div>
    <div className="step-body"><div className="step-title"><strong>{step.type === 'tool_call' ? `Tool call · ${step.tool}` : step.type === 'tool_result' ? `Tool result · ${step.tool}` : step.type === 'terminal' ? `Final decision · ${step.declared_action}` : 'Agent message'}</strong>{blocked && <span className="blocked-tag">Blocked attempt</span>}</div>
      {step.content && <p>{step.content}</p>}{step.message && <p>{step.message}</p>}
      {step.args && <pre>{JSON.stringify(step.args, null, 2)}</pre>}
      {step.result && <pre>{typeof step.result === 'string' ? step.result : JSON.stringify(step.result, null, 2)}</pre>}
      {step.tripwire_hit && <div className="tripwire">Boundary hit: {step.tripwire_hit}</div>}
      {step.next_step && <p className="next-step">Next: {step.next_step}</p>}
    </div>
  </article>
}

function humanize(value = '') { return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) }

export default App
