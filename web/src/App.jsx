import { Fragment, useEffect, useState } from 'react'

// One fixed comparison for now. There is no UI for choosing files.
const API_URL =
  'http://localhost:8000/check?left=fixtures/trip-de.html&right=fixtures/trip-en.html'

const API_ORIGIN = new URL(API_URL).origin
const LEFT = new URL(API_URL).searchParams.get('left')
const RIGHT = new URL(API_URL).searchParams.get('right')

const FILTERS = [
  ['all', 'All'],
  ['error', 'Errors only'],
  ['info', 'Info only'],
]

// The server's own message from an error body. FastAPI puts it in "detail":
// a string for our 400 and 404, a list of problems for a 422. A body that is
// not JSON at all is shown exactly as it came.
function serverMessage(body) {
  try {
    const detail = JSON.parse(body).detail
    if (typeof detail === 'string') return detail
    if (detail !== undefined) return JSON.stringify(detail)
  } catch {
    // Not JSON: fall through to the raw text.
  }
  return body
}

// Resolves to the page's next state. It never throws, so every failure ends up
// on screen instead of leaving the page stuck on "Checking…".
async function fetchFindings() {
  let res
  let body
  try {
    res = await fetch(API_URL)
    body = await res.text()
  } catch {
    // The browser raises the same TypeError for "server not running" and
    // "blocked by CORS", so the page cannot tell them apart. It also gets no
    // status to show.
    return {
      status: 'error',
      error: {
        httpStatus: null,
        message: `No response from ${API_ORIGIN}. Is the API running? (A CORS block looks the same to the page.)`,
      },
    }
  }

  if (!res.ok) {
    return {
      status: 'error',
      error: { httpStatus: `${res.status} ${res.statusText}`, message: serverMessage(body) },
    }
  }

  try {
    return { status: 'done', findings: JSON.parse(body) }
  } catch {
    return {
      status: 'error',
      error: { httpStatus: `${res.status} ${res.statusText}`, message: `Response was not JSON: ${body}` },
    }
  }
}

export default function App() {
  const [result, setResult] = useState({ status: 'loading' })

  useEffect(() => {
    // In development, StrictMode runs this effect twice. The cleanup marks the
    // first run as stale so only the second response is stored.
    let ignore = false
    fetchFindings().then((next) => {
      if (!ignore) setResult(next)
    })
    return () => {
      ignore = true
    }
  }, [])

  let content
  if (result.status === 'loading') {
    content = <p>Checking…</p>
  } else if (result.status === 'error') {
    content = (
      <div className="request-error" role="alert">
        <p className="request-error-status">
          {result.error.httpStatus ? `Request failed: ${result.error.httpStatus}` : 'Request failed'}
        </p>
        <p>{result.error.message}</p>
      </div>
    )
  } else if (result.findings.length === 0) {
    content = <p className="agree">The pages agree on everything this checker checks.</p>
  } else {
    content = <Findings findings={result.findings} />
  }

  return (
    <main>
      <h1>page-parity</h1>
      <p className="pair">
        {LEFT} <span className="muted">vs</span> {RIGHT}
      </p>
      {content}
    </main>
  )
}

function Findings({ findings }) {
  const [filter, setFilter] = useState('all')
  // The index, in the unfiltered list, of the finding whose values are shown,
  // or null. The API gives findings no id. The list never changes after the
  // fetch, so the index is a stable identity for both this and the row keys.
  const [openIndex, setOpenIndex] = useState(null)

  const errorCount = findings.filter((f) => f.severity === 'error').length
  const infoCount = findings.filter((f) => f.severity === 'info').length

  const visible = findings
    .map((finding, index) => ({ finding, index }))
    .filter(({ finding }) => filter === 'all' || finding.severity === filter)

  return (
    <>
      <p className="counts">
        {errorCount} {errorCount === 1 ? 'error' : 'errors'}, {infoCount} info
      </p>

      <fieldset className="filter">
        <legend>Show</legend>
        {FILTERS.map(([value, label]) => (
          <label key={value}>
            <input
              type="radio"
              name="filter"
              value={value}
              checked={filter === value}
              onChange={() => setFilter(value)}
            />
            {label}
          </label>
        ))}
      </fieldset>

      {visible.length === 0 ? (
        // Not the same as "the pages agree": there are findings, just hidden.
        <p>
          No {filter} findings. {findings.length} hidden by the filter.
        </p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Field</th>
              <th>Severity</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {visible.map(({ finding, index }) => {
              const isOpen = openIndex === index
              return (
                // Fragment groups the two rows under one key without adding an element.
                <Fragment key={index}>
                  {/* The row's onClick is the only toggle. The button has no
                      handler of its own: a click on it, or Enter/Space while it
                      has focus, bubbles up to the row, so each press toggles once. */}
                  <tr className="finding" onClick={() => setOpenIndex(isOpen ? null : index)}>
                    <td>
                      <button type="button" aria-expanded={isOpen}>
                        {finding.field}
                      </button>
                    </td>
                    <td>
                      <span className={`badge ${finding.severity}`}>{finding.severity}</span>
                    </td>
                    <td>{finding.message}</td>
                  </tr>
                  {isOpen && (
                    <tr className="details">
                      <td colSpan={3}>
                        <div className="sides">
                          <Side label={`Left · ${LEFT}`} value={finding.left} />
                          <Side label={`Right · ${RIGHT}`} value={finding.right} />
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      )}
    </>
  )
}

// null means the value is missing on that side. That is not the same as an
// empty string, so the two are shown differently. `== null` also catches
// undefined (a key absent from the JSON), so a missing value can never render
// as a blank box.
function Side({ label, value }) {
  let shown
  if (value == null) {
    shown = <em className="muted">missing</em>
  } else if (value === '') {
    shown = <em className="muted">empty</em>
  } else {
    shown = value
  }
  return (
    <div className="side">
      <h3>{label}</h3>
      <div className="value">{shown}</div>
    </div>
  )
}
