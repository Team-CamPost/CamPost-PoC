import { useState } from 'react'
import './App.css'

function App() {
  const [loading, setLoading] = useState({ crawl: false, parse: false, smtp: false })
  const [crawlData, setCrawlData] = useState(null)
  const [parseData, setParseData] = useState(null)
  const [smtpData, setSmtpData] = useState(null)
  const [smtpForm, setSmtpForm] = useState({
    smtpServer: 'smtp.gmail.com',
    smtpPort: 587,
    smtpUser: '',
    smtpPassword: '',
    toEmail: '',
    allowExternalRecipient: false,
  })

  const callApi = async (path, payload) => {
    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data?.detail || '요청 실패')
    }
    return data
  }

  const runCrawl = async () => {
    setLoading((prev) => ({ ...prev, crawl: true }))
    try {
      const data = await callApi('/api/crawl', { limit: 10 })
      setCrawlData({ ok: true, data })
    } catch (e) {
      setCrawlData({ ok: false, error: e.message })
    } finally {
      setLoading((prev) => ({ ...prev, crawl: false }))
    }
  }

  const runParse = async () => {
    setLoading((prev) => ({ ...prev, parse: true }))
    try {
      const data = await callApi('/api/parse', {
        hwpPath: 'test.hwp',
        pdfPath: '봉사활동인증서_플로깅.pdf',
      })
      setParseData({ ok: true, data })
    } catch (e) {
      setParseData({ ok: false, error: e.message })
    } finally {
      setLoading((prev) => ({ ...prev, parse: false }))
    }
  }

  const runSmtp = async () => {
    setLoading((prev) => ({ ...prev, smtp: true }))
    try {
      const data = await callApi('/api/smtp-test', smtpForm)
      setSmtpData({ ok: true, data })
    } catch (e) {
      setSmtpData({ ok: false, error: e.message })
    } finally {
      setLoading((prev) => ({ ...prev, smtp: false }))
    }
  }

  const onSmtpChange = (key, value) => {
    setSmtpForm((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <main className="page">
      <header className="hero">
        <p className="eyebrow">Major-Flow Tech Validation</p>
        <h1>PoC Live Console</h1>
        <p className="sub">
          FastAPI 백엔드와 React 프론트를 연결해 크롤링, 문서 파싱, SMTP를 브라우저에서 바로 검증합니다.
        </p>
      </header>

      <section className="grid">
        <article className="card">
          <div className="card-head">
            <h2>1) 학과 공지 크롤링</h2>
            <button onClick={runCrawl} disabled={loading.crawl}>
              {loading.crawl ? '실행 중...' : '크롤링 실행'}
            </button>
          </div>
          {crawlData && crawlData.ok && (
            <ul className="result-list">
              {crawlData.data.items.map((item, idx) => (
                <li key={`${item.title}-${idx}`}>
                  <span className="idx">{idx + 1}</span>
                  <div>
                    <p className="title">{item.title}</p>
                    <p className="meta">날짜: {item.date || 'N/A'}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {crawlData && !crawlData.ok && <p className="error">{crawlData.error}</p>}
        </article>

        <article className="card">
          <div className="card-head">
            <h2>2) HWP/PDF 텍스트 파싱</h2>
            <button onClick={runParse} disabled={loading.parse}>
              {loading.parse ? '실행 중...' : '파싱 실행'}
            </button>
          </div>

          {parseData && parseData.ok && (
            <div className="parse-block">
              <div className="item">
                <h3>HWP</h3>
                {parseData.data.hwp.ok ? (
                  <>
                    <p>길이: {parseData.data.hwp.length}</p>
                    <p>가독성: {parseData.data.hwp.readable ? 'OK' : '주의'}</p>
                    <pre>{parseData.data.hwp.preview}</pre>
                  </>
                ) : (
                  <p className="error">{parseData.data.hwp.error}</p>
                )}
              </div>
              <div className="item">
                <h3>PDF</h3>
                {parseData.data.pdf.ok ? (
                  <>
                    <p>길이: {parseData.data.pdf.length}</p>
                    <p>가독성: {parseData.data.pdf.readable ? 'OK' : '주의'}</p>
                    <pre>{parseData.data.pdf.preview}</pre>
                  </>
                ) : (
                  <p className="error">{parseData.data.pdf.error}</p>
                )}
              </div>
            </div>
          )}
          {parseData && !parseData.ok && <p className="error">{parseData.error}</p>}
        </article>

        <article className="card full">
          <div className="card-head">
            <h2>3) SMTP 테스트</h2>
            <button onClick={runSmtp} disabled={loading.smtp}>
              {loading.smtp ? '전송 중...' : '테스트 메일 전송'}
            </button>
          </div>

          <div className="form-grid">
            <label>
              SMTP Server
              <input
                value={smtpForm.smtpServer}
                onChange={(e) => onSmtpChange('smtpServer', e.target.value)}
              />
            </label>
            <label>
              SMTP Port
              <input
                type="number"
                value={smtpForm.smtpPort}
                onChange={(e) => onSmtpChange('smtpPort', Number(e.target.value))}
              />
            </label>
            <label>
              SMTP User
              <input
                value={smtpForm.smtpUser}
                onChange={(e) => onSmtpChange('smtpUser', e.target.value)}
              />
            </label>
            <label>
              SMTP Password
              <input
                type="password"
                value={smtpForm.smtpPassword}
                onChange={(e) => onSmtpChange('smtpPassword', e.target.value)}
              />
            </label>
            <label className="wide">
              Receiver Email
              <input
                value={smtpForm.toEmail}
                onChange={(e) => onSmtpChange('toEmail', e.target.value)}
              />
            </label>
            <label className="check wide">
              <input
                type="checkbox"
                checked={smtpForm.allowExternalRecipient}
                onChange={(e) => onSmtpChange('allowExternalRecipient', e.target.checked)}
              />
              외부 도메인 수신 허용
            </label>
          </div>

          {smtpData && smtpData.ok && <p className="success">{smtpData.data.message}</p>}
          {smtpData && !smtpData.ok && <p className="error">{smtpData.error}</p>}
        </article>
      </section>
    </main>
  )
}

export default App
