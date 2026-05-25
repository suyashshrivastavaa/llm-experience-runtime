import { useState, useEffect, useRef, useCallback } from 'react'
import './index.css'

const API = '/api/v1'

function useToast() {
  const [toast, setToast] = useState(null)
  const show = useCallback((msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }, [])
  return { toast, show }
}

function UploadModal({ onClose, onUploaded }) {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [over, setOver] = useState(false)
  const inputRef = useRef()

  const handleDrop = (e) => {
    e.preventDefault()
    setOver(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  const submit = async () => {
    if (!file) return
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    try {
      const res = await fetch(`${API}/ingest/`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error((await res.json()).detail)
      const data = await res.json()
      onUploaded(data)
      onClose()
    } catch (e) {
      alert(e.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <h2>Upload document</h2>
        <div
          className={`dropzone${over ? ' over' : ''}`}
          onDragOver={e => { e.preventDefault(); setOver(true) }}
          onDragLeave={() => setOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current.click()}
        >
          <div className="dz-icon">📄</div>
          <input ref={inputRef} type="file" accept=".pdf,.txt,.md" onChange={e => setFile(e.target.files[0])} />
          {file ? null : <><strong>Click or drag a file here</strong><br />PDF, TXT, or MD</>}
        </div>
        {file && (
          <div className="file-selected">
            <span>📎</span>
            <span>{file.name}</span>
            <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: 11 }}>
              {(file.size / 1024).toFixed(1)} KB
            </span>
          </div>
        )}
        {uploading && <div className="progress-bar"><div className="progress-fill" /></div>}
        <div className="modal-actions">
          <button className="btn-ghost" onClick={onClose} disabled={uploading}>Cancel</button>
          <button className="btn-primary" onClick={submit} disabled={!file || uploading}>
            {uploading ? 'Uploading…' : 'Upload & Index'}
          </button>
        </div>
      </div>
    </div>
  )
}

function Message({ msg }) {
  return (
    <div className={`message ${msg.role}`}>
      <div className="bubble">
        {msg.content}
        {msg.streaming && <span className="cursor" />}
      </div>
      {msg.sources?.length > 0 && (
        <div className="sources">Sources: {msg.sources.join(', ')}</div>
      )}
    </div>
  )
}

export default function App() {
  const [indices, setIndices] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const chatRef = useRef()
  const textareaRef = useRef()
  const { toast, show: showToast } = useToast()

  const fetchIndices = useCallback(async () => {
    try {
      const res = await fetch(`${API}/indices/`)
      if (res.ok) setIndices(await res.json())
    } catch {}
  }, [])

  useEffect(() => { fetchIndices() }, [fetchIndices])

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight
  }, [messages])

  const selectDoc = (id) => {
    if (id === activeId) return
    setActiveId(id)
    setMessages([])
  }

  const deleteDoc = async (e, id) => {
    e.stopPropagation()
    if (!confirm('Delete this index?')) return
    await fetch(`${API}/indices/${id}`, { method: 'DELETE' })
    setIndices(prev => prev.filter(i => i.index_id !== id))
    if (activeId === id) { setActiveId(null); setMessages([]) }
    showToast('Index deleted')
  }

  const onUploaded = (data) => {
    showToast(`Indexed ${data.chunks_indexed} chunks from ${data.filename}`)
    fetchIndices()
    setActiveId(data.index_id)
    setMessages([])
  }

  const sendMessage = async () => {
    const q = input.trim()
    if (!q || !activeId || streaming) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: q }])
    setStreaming(true)

    const aiMsg = { role: 'ai', content: '', streaming: true, sources: [] }
    setMessages(prev => [...prev, aiMsg])

    try {
      const res = await fetch(`${API}/query/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, index_id: activeId, stream: true }),
      })

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6)
          if (payload === '[DONE]') break
          if (payload.startsWith('sources=')) {
            const srcs = payload.slice(8).split(',').filter(Boolean)
            setMessages(prev => {
              const next = [...prev]
              next[next.length - 1] = { ...next[next.length - 1], sources: srcs }
              return next
            })
          } else {
            setMessages(prev => {
              const next = [...prev]
              next[next.length - 1] = { ...next[next.length - 1], content: next[next.length - 1].content + payload }
              return next
            })
          }
        }
      }
    } catch (e) {
      setMessages(prev => {
        const next = [...prev]
        next[next.length - 1] = { ...next[next.length - 1], content: 'Error: ' + e.message }
        return next
      })
    } finally {
      setMessages(prev => {
        const next = [...prev]
        next[next.length - 1] = { ...next[next.length - 1], streaming: false }
        return next
      })
      setStreaming(false)
      textareaRef.current?.focus()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const activeDoc = indices.find(i => i.index_id === activeId)

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>⚡ LLM Runtime</h1>
          <p>RAG-powered document Q&A</p>
        </div>
        <button className="upload-btn" onClick={() => setShowUpload(true)}>+ Upload Document</button>
        <div className="doc-list">
          {indices.length === 0 ? (
            <div className="empty-state">No documents yet.<br />Upload one to get started.</div>
          ) : indices.map(idx => (
            <div
              key={idx.index_id}
              className={`doc-item${activeId === idx.index_id ? ' active' : ''}`}
              onClick={() => selectDoc(idx.index_id)}
            >
              <span className="doc-icon">{idx.filename.endsWith('.pdf') ? '📕' : '📝'}</span>
              <div className="doc-info">
                <div className="doc-name">{idx.filename}</div>
                <div className="doc-meta">{idx.chunks} chunks</div>
              </div>
              <button className="doc-delete" onClick={e => deleteDoc(e, idx.index_id)}>✕</button>
            </div>
          ))}
        </div>
      </aside>

      <div className="main">
        <div className="main-header">
          {activeDoc ? (
            <>
              <span>📖</span>
              <h2>{activeDoc.filename}</h2>
              <span className="badge">{activeDoc.chunks} chunks</span>
            </>
          ) : (
            <h2 style={{ color: 'var(--text-muted)' }}>Select a document to start chatting</h2>
          )}
        </div>

        <div className="chat-area" ref={chatRef}>
          {messages.length === 0 && (
            <div className="chat-empty">
              <div className="icon">{activeDoc ? '💬' : '📂'}</div>
              <h3>{activeDoc ? `Ask anything about ${activeDoc.filename}` : 'No document selected'}</h3>
              <p>{activeDoc ? 'Your questions are answered using only the content of this document.' : 'Upload a document or select one from the sidebar.'}</p>
            </div>
          )}
          {messages.map((msg, i) => <Message key={i} msg={msg} />)}
        </div>

        {activeId ? (
          <div className="input-bar">
            <textarea
              ref={textareaRef}
              rows={1}
              placeholder="Ask a question about this document… (Enter to send)"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={streaming}
            />
            <button className="send-btn" onClick={sendMessage} disabled={!input.trim() || streaming}>
              {streaming ? '…' : 'Send'}
            </button>
          </div>
        ) : (
          <div className="no-doc-bar">Upload or select a document to begin</div>
        )}
      </div>

      {showUpload && <UploadModal onClose={() => setShowUpload(false)} onUploaded={onUploaded} />}
      {toast && <div className={`toast ${toast.type}`}>{toast.msg}</div>}
    </div>
  )
}
