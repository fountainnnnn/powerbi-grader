import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useRubric } from './hooks/useRubric';
import { useChat } from './hooks/useChat';
import { API_URL, apiClient } from './services/api';
import { Dashboard, ChatMessage } from './types/api';
import './styles/App.css';

interface ChatSession {
  id: string;
  name: string;
  messages: ChatMessage[];
  createdAt: Date;
}

export function App() {
  const rubric = useRubric();
  const chat = useChat();

  const [isAuthenticated, setIsAuthenticated] = useState(apiClient.isAuthenticated());
  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [attachedFile, setAttachedFile] = useState<Dashboard | null>(null);
  const [attachedPbixFile, setAttachedPbixFile] = useState<Dashboard | null>(null);
  const [inputValue, setInputValue] = useState('');
  const [studentName, setStudentName] = useState('');
  const [detectedStudents, setDetectedStudents] = useState<string[]>([]);
  const [isRenaming, setIsRenaming] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const apiBaseUrl = API_URL;
  const getFileName = (filePath?: string | null) => filePath?.split('\\').pop()?.split('/').pop() || '';
  const getUploadUrl = (filePath?: string | null) => (
    filePath?.startsWith('blob:') ? filePath : `${apiBaseUrl}/uploads/${getFileName(filePath)}`
  );
  const isImagePath = (filePath?: string | null) => /\.(png|jpe?g|gif|webp|bmp)$/i.test(filePath || '');
  const isPbixName = (name?: string | null) => /\.pbix$/i.test(name || '');
  const formatMarkdownText = (value: unknown) => {
    const text = typeof value === 'string' ? value : JSON.stringify(value);
    return text
      .replace(/\s+(\*\*(?:Score\/Grade|Observation|Feedback|Rubric|Visual dashboard evidence|PBIX technical insights|Limitations):\*\*)/g, '\n\n$1')
      .replace(/\s+(- \*\*[^:]+:\*\*)/g, '\n$1')
      .replace(/([^\n])\n(#{2,3}\s)/g, '$1\n\n$2');
  };
  const renderAttachmentPreview = (filename?: string | null, filePath?: string | null, label = 'Attachment') => {
    const displayName = filename || label;
    if (filePath && isImagePath(filePath)) {
      return (
        <div className="msg-attachment-preview">
          <img
            src={getUploadUrl(filePath)}
            alt={displayName}
            className="attachment-thumbnail"
          />
        </div>
      );
    }

    return <div className="msg-attachment">{label}: {displayName}</div>;
  };

  // Load initial data
  useEffect(() => {
    if (!isAuthenticated) return;
    rubric.loadRubric();
    chat.loadHistory();
  }, [isAuthenticated]);

  // After backend history is loaded, sync with sessions
  useEffect(() => {
    if (!isAuthenticated) return;
    const stored = localStorage.getItem('chatSessions');

    if (stored) {
      const sessions: ChatSession[] = JSON.parse(stored).map((s: any) => ({
        ...s,
        createdAt: new Date(s.createdAt),
      }));

      // Merge backend messages into the "All Chats" session
      const updatedSessions = sessions.map(s =>
        s.id === 'all-chats'
          ? { ...s, messages: chat.messages }
          : s
      );

      setChatSessions(updatedSessions);
      if (updatedSessions.length > 0 && !currentSessionId) {
        setCurrentSessionId(updatedSessions[0].id);
      }
    } else if (chat.messages.length > 0) {
      // No saved sessions, create one from backend history
      const defaultSession: ChatSession = {
        id: 'all-chats',
        name: 'All Chats',
        messages: chat.messages,
        createdAt: new Date(),
      };
      setChatSessions([defaultSession]);
      setCurrentSessionId('all-chats');
    } else if (chatSessions.length === 0) {
      // No backend messages and no saved sessions, create default
      const newSession: ChatSession = {
        id: Date.now().toString(),
        name: `Chat 1`,
        messages: [],
        createdAt: new Date(),
      };
      setChatSessions([newSession]);
      setCurrentSessionId(newSession.id);
    }
  }, [chat.messages, isAuthenticated]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat.messages, chat.isLoading]);


  const saveSessions = (sessions: ChatSession[]) => {
    localStorage.setItem('chatSessions', JSON.stringify(sessions));
    setChatSessions(sessions);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);
    setIsLoggingIn(true);
    try {
      await apiClient.login(loginUsername.trim(), loginPassword);
      setIsAuthenticated(true);
      setLoginPassword('');
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleLogout = () => {
    apiClient.logout();
    setIsAuthenticated(false);
    setChatSessions([]);
    setCurrentSessionId(null);
    setAttachedFile(null);
    setAttachedPbixFile(null);
    setDetectedStudents([]);
    setStudentName('');
    chat.clearChat();
  };

  const createNewChat = () => {
    const newSession: ChatSession = {
      id: Date.now().toString(),
      name: `Chat ${chatSessions.length + 1}`,
      messages: [],
      createdAt: new Date(),
    };
    const updated = [newSession, ...chatSessions];
    saveSessions(updated);
    setCurrentSessionId(newSession.id);
    chat.clearChat();
    setAttachedFile(null);
    setAttachedPbixFile(null);
    setDetectedStudents([]);
    setStudentName('');
  };

  const deleteChat = (sessionId: string) => {
    const updated = chatSessions.filter(s => s.id !== sessionId);
    saveSessions(updated);
    if (currentSessionId === sessionId) {
      if (updated.length > 0) {
        setCurrentSessionId(updated[0].id);
      } else {
        createNewChat();
      }
    }
  };

  const renameChat = (sessionId: string, newName: string) => {
    const updated = chatSessions.map(s =>
      s.id === sessionId ? { ...s, name: newName } : s
    );
    saveSessions(updated);
    setIsRenaming(null);
  };

  const switchSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
  };

  const exportChat = () => {
    if (!currentSessionId) return;
    const session = chatSessions.find(s => s.id === currentSessionId);
    if (!session) return;

    let text = `Chat: ${session.name}\nCreated: ${session.createdAt.toLocaleString()}\n\n`;
    session.messages.forEach((msg, i) => {
      text += `Q${i + 1}: ${msg.user_message}\n`;
      text += `A${i + 1}: ${msg.ai_response.text || JSON.stringify(msg.ai_response)}\n\n`;
    });

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-${session.name}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleRubricUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      try {
        await rubric.uploadRubric(file);
      } catch (err) {
        // Error handled
      } finally {
        e.target.value = '';
      }
    }
  };

  const handleFileAttach = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      try {
        const uploaded = await Promise.all(files.map(file => apiClient.uploadDashboard(file)));
        for (const dashboard of uploaded) {
          if (isPbixName(dashboard.filename)) {
            setAttachedPbixFile(dashboard);
            // Auto-detect student names from PBIX
            try {
              const names = await apiClient.getStudents(dashboard.id);
              setDetectedStudents(names);
              setStudentName(''); // Default: grade all students
            } catch {
              // Ignore — user can type name manually
            }
          } else {
            setAttachedFile(dashboard);
          }
        }
      } catch (err) {
        // Error handled
      } finally {
        e.target.value = '';
      }
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const message = inputValue.trim();
    // Allow sending if there's a message OR an attached file
    if (!message && !attachedFile && !attachedPbixFile) return;

    setInputValue('');

    try {
      const visualAttachment = attachedFile;
      const pbixAttachment = attachedPbixFile;
      // Create optimistic message immediately
      const tempId = `temp_${Date.now()}`;
      const optimisticMessage: ChatMessage = {
        id: tempId,
        dashboard_id: visualAttachment?.id || null,
        pbix_id: pbixAttachment?.id || null,
        user_message: message || '',
        ai_response: { text: '', model: '', finish_reason: 'thinking', usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 } },
        created_at: new Date().toISOString(),
        dashboard_filename: visualAttachment?.filename || null,
        dashboard_file_path: visualAttachment?.file_path || null,
        pbix_filename: pbixAttachment?.filename || null,
        pbix_file_path: pbixAttachment?.file_path || null,
      };

      // Show user message and thinking indicator immediately
      const sessionWithOptimistic = chatSessions.map(s => {
        if (s.id === currentSessionId) {
          return {
            ...s,
            messages: [...s.messages, optimisticMessage],
          };
        }
        return s;
      });
      saveSessions(sessionWithOptimistic);
      setAttachedFile(null);
      setAttachedPbixFile(null);

      // Fetch actual response
      const response = await chat.sendMessage(message, visualAttachment?.id, pbixAttachment?.id, studentName.trim() || undefined);

      // Replace optimistic message with actual response
      const updated = sessionWithOptimistic.map(s => {
        if (s.id === currentSessionId) {
          return {
            ...s,
            messages: s.messages.map(m => m.id === tempId ? response : m),
          };
        }
        return s;
      });
      saveSessions(updated);
    } catch (err) {
      // Error handled
    }
  };

  const currentSession = chatSessions.find(s => s.id === currentSessionId);
  const currentMessages = currentSession?.messages || [];

  if (!isAuthenticated) {
    return (
      <div className="login-shell">
        <form className="login-panel" onSubmit={handleLogin}>
          <div className="login-brand">
            <div className="brand-mark">PG</div>
            <div>
              <div className="brand-name">Power BI Grader</div>
              <div className="brand-meta">Assessment review console</div>
            </div>
          </div>
          <h1>Sign in</h1>
          <label>
            <span>Username</span>
            <input
              type="text"
              value={loginUsername}
              onChange={(e) => setLoginUsername(e.target.value)}
              autoComplete="username"
              autoFocus
            />
          </label>
          <label>
            <span>Password</span>
            <input
              type="password"
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
              autoComplete="current-password"
            />
          </label>
          {loginError && <div className="login-error">{loginError}</div>}
          <button
            type="submit"
            className="login-submit"
            disabled={isLoggingIn || !loginUsername.trim() || !loginPassword}
          >
            {isLoggingIn ? 'Checking...' : 'Enter'}
          </button>
        </form>
      </div>
    );
  }

  if (!currentSessionId && chatSessions.length === 0) {
    setTimeout(createNewChat, 0);
    return <div />;
  }

  return (
    <div className="app-container">
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-lockup">
            <div className="brand-mark">PG</div>
            <div>
              <div className="brand-name">Power BI Grader</div>
              <div className="brand-meta">Grader Console</div>
            </div>
          </div>
        </div>

        <button onClick={createNewChat} className="new-chat-btn">
          <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 1v14M1 8h14" stroke="currentColor" strokeWidth="2"/>
          </svg>
          New Chat
        </button>

        {/* CHATS */}
        <div className="sidebar-section">
          <div className="section-label">Chats</div>
          <div className="chats-list">
            {chatSessions.map(session => (
              <div
                key={session.id}
                className={`chat-item ${currentSessionId === session.id ? 'active' : ''}`}
              >
                {isRenaming === session.id ? (
                  <input
                    type="text"
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onBlur={() => renameChat(session.id, renameValue || session.name)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') renameChat(session.id, renameValue || session.name);
                    }}
                    autoFocus
                    className="chat-rename-input"
                  />
                ) : (
                  <div
                    className="chat-name-wrapper"
                    onClick={() => switchSession(session.id)}
                    onDoubleClick={() => {
                      setIsRenaming(session.id);
                      setRenameValue(session.name);
                    }}
                  >
                    <span className="chat-name">{session.name}</span>
                  </div>
                )}
                <div className="chat-actions">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setIsRenaming(session.id);
                      setRenameValue(session.name);
                    }}
                    className="icon-btn edit"
                    title="Rename"
                  >
                    <svg width="18" height="18" viewBox="0 0 16 16" fill="none">
                      <path d="M11.5 2.5L13.5 4.5M2 14h2.5l9-9L11 5l-9 9V14Z" stroke="currentColor" strokeWidth="1.2"/>
                    </svg>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteChat(session.id);
                    }}
                    className="icon-btn delete"
                    title="Delete"
                  >
                    <svg width="18" height="18" viewBox="0 0 16 16" fill="none">
                      <path d="M2 4h12M6 7v5M10 7v5M3 4l1 10a2 2 0 002 2h4a2 2 0 002-2l1-10M6 4V3a1 1 0 011-1h2a1 1 0 011 1v1" stroke="currentColor" strokeWidth="1.2"/>
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* TOOLS */}
        <div className="sidebar-section">
          <div className="section-label">Tools</div>
          <div className="tools-list">
            <button onClick={() => exportChat()} className="tool-item">
              <svg width="20" height="20" viewBox="0 0 16 16" fill="none">
                <path d="M8 2v10M4 9l4 4 4-4M2 14h12" stroke="currentColor" strokeWidth="1.2"/>
              </svg>
              <span>Export</span>
            </button>
            <button onClick={() => {
              if (confirm('Clear all chats?')) {
                setChatSessions([]);
                localStorage.removeItem('chatSessions');
                createNewChat();
              }
            }} className="tool-item">
              <svg width="20" height="20" viewBox="0 0 16 16" fill="none">
                <path d="M2 4h12M6 7v5M10 7v5M3 4l1 10a2 2 0 002 2h4a2 2 0 002-2l1-10M6 4V3a1 1 0 011-1h2a1 1 0 011 1v1" stroke="currentColor" strokeWidth="1.2"/>
              </svg>
              <span>Clear All</span>
            </button>
          </div>
        </div>

        {/* RUBRIC CARD */}
        <div className="rubric-card">
          <div className="card-header">Rubric</div>
          {rubric.rubric ? (
            <div className="card-content">
              <div className="rubric-file">{rubric.rubric.filename}</div>
              <button onClick={() => rubric.deleteRubric()} className="card-btn">
                Remove
              </button>
            </div>
          ) : (
            <label className="card-upload">
              <input
                type="file"
                accept=".pdf,.docx,.doc,image/*"
                onChange={handleRubricUpload}
              />
              <div className="upload-placeholder">
                <svg width="28" height="28" viewBox="0 0 16 16" fill="none">
                  <path d="M8 1v10M3 7l5 5 5-5M2 14h12" stroke="currentColor" strokeWidth="1.2"/>
                </svg>
                <div>Upload Rubric</div>
              </div>
            </label>
          )}
        </div>
      </aside>

      {/* MAIN */}
      <main className="main-area">
        {/* TOP NAV */}
        <nav className="top-nav">
          <h1 className="nav-title">{currentSession?.name || 'Chat'}</h1>
          <div className="nav-actions">
            <button onClick={handleLogout} className="nav-btn text-btn" title="Sign out">
              Sign out
            </button>
            <button onClick={() => exportChat()} className="nav-btn" title="Export">
              <svg width="22" height="22" viewBox="0 0 16 16" fill="none">
                <path d="M8 2v10M4 9l4 4 4-4M2 14h12" stroke="currentColor" strokeWidth="1.2"/>
              </svg>
            </button>
            <button onClick={() => {
              if (confirm('Clear this chat?')) {
                const updated = chatSessions.map(s =>
                  s.id === currentSessionId ? { ...s, messages: [] } : s
                );
                saveSessions(updated);
                chat.clearChat();
                setAttachedFile(null);
                setAttachedPbixFile(null);
                setDetectedStudents([]);
                setStudentName('');
              }
            }} className="nav-btn" title="Clear">
              <svg width="22" height="22" viewBox="0 0 16 16" fill="none">
                <path d="M2 4h12M6 7v5M10 7v5M3 4l1 10a2 2 0 002 2h4a2 2 0 002-2l1-10M6 4V3a1 1 0 011-1h2a1 1 0 011 1v1" stroke="currentColor" strokeWidth="1.2"/>
              </svg>
            </button>
          </div>
        </nav>

        {/* CHAT */}
        <div className="chat-area">
          <div className="messages-wrapper">
            {currentMessages.length === 0 ? (
              <div className="welcome-state">
                <div className="welcome-title">Start a conversation</div>
                <div className="welcome-subtitle">Upload the assessment brief, attach dashboard evidence, then run a strict marking pass.</div>
              </div>
            ) : (
              <div className="messages-list">
                {currentMessages.map((msg) => (
                  <div key={msg.id} className="message-pair">
                    {msg.user_message && (
                      <div className="message user-msg">
                        <p>{msg.user_message}</p>
                        {msg.dashboard_id && renderAttachmentPreview(msg.dashboard_filename, msg.dashboard_file_path, 'Visual file')}
                        {msg.pbix_id && renderAttachmentPreview(msg.pbix_filename, msg.pbix_file_path, 'PBIX insight file')}
                      </div>
                    )}
                    {!msg.user_message && (msg.dashboard_id || msg.pbix_id) && (
                      <div className="message user-msg">
                        <p className="msg-label">Grading Analysis</p>
                        {msg.dashboard_id && renderAttachmentPreview(msg.dashboard_filename, msg.dashboard_file_path, 'Visual file')}
                        {msg.pbix_id && renderAttachmentPreview(msg.pbix_filename, msg.pbix_file_path, 'PBIX insight file')}
                      </div>
                    )}
                    {msg.ai_response.finish_reason === 'thinking' ? (
                      <div className="message ai-msg loading">
                        <div className="thinking-indicator">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                        <p>Model is thinking...</p>
                      </div>
                    ) : (
                      <div className="message ai-msg markdown-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {formatMarkdownText(msg.ai_response.text)}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* INPUT */}
          <footer className="chat-input-area">
            {chat.error && <div className="error-msg">{chat.error}</div>}

            {(attachedFile || attachedPbixFile) && (
              <div className="file-preview-list">
                {attachedFile && (
                  <div className="file-preview">
                    {isImagePath(attachedFile.file_path) && (
                      <div className="file-preview-image">
                        <img
                          src={getUploadUrl(attachedFile.file_path)}
                          alt={attachedFile.filename}
                          className="preview-thumbnail"
                        />
                      </div>
                    )}
                    <div className="file-preview-info">
                      <span className="file-preview-name">Visual: {attachedFile.filename}</span>
                      <button onClick={() => setAttachedFile(null)} className="remove-file" title="Remove attachment">
                        x
                      </button>
                    </div>
                  </div>
                )}
                {attachedPbixFile && (
                  <div className="file-preview">
                    <div className="file-preview-info">
                      <span className="file-preview-name">PBIX: {attachedPbixFile.filename}</span>
                      <button onClick={() => { setAttachedPbixFile(null); setDetectedStudents([]); setStudentName(''); }} className="remove-file" title="Remove PBIX attachment">
                        x
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="student-name-row">
              {detectedStudents.length > 0 ? (
                <select
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  className="student-name-input"
                  disabled={chat.isLoading}
                >
                  <option value="">All Students</option>
                  {detectedStudents.map(name => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  placeholder="Student name, or leave blank for all students"
                  className="student-name-input"
                  disabled={chat.isLoading}
                />
              )}
            </div>

            <form onSubmit={handleSendMessage} className="input-form">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.doc,.pbix,image/*"
                multiple
                onChange={handleFileAttach}
                style={{ display: 'none' }}
              />

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={chat.isLoading}
                className="input-icon-btn"
                title="Attach visual file and PBIX file"
              >
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
              </button>

              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Ask for marking, feedback, or evidence checks..."
                disabled={chat.isLoading}
                className="message-input"
                autoFocus
              />

              <button
                type="submit"
                disabled={chat.isLoading || (!inputValue.trim() && !attachedFile && !attachedPbixFile)}
                className="send-btn"
              >
                <svg width="28" height="28" viewBox="0 0 16 16" fill="none">
                  <path d="M8 2v10M4 7l4-5 4 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            </form>
          </footer>
        </div>
      </main>
    </div>
  );
}

export default App;
