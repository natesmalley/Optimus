import React, { useState, useEffect } from 'react';
import './App.css';

interface AgendaItem {
  id: string;
  type: 'event' | 'task';
  title: string;
  time?: string;
  priority?: number;
  energy?: number;
}

function App() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const [agenda, setAgenda] = useState<AgendaItem[]>([]);
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  // Check online status
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Load today's agenda
  useEffect(() => {
    loadAgenda();
  }, []);

  const loadAgenda = async () => {
    try {
      const response = await fetch('http://localhost:8003/api/mobile/today');
      const data = await response.json();
      setAgenda(data.items || []);
    } catch (error) {
      console.error('Failed to load agenda:', error);
      // Load from local storage if offline
      const cached = localStorage.getItem('cached_agenda');
      if (cached) {
        setAgenda(JSON.parse(cached));
      }
    }
  };

  const startListening = () => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      alert('Speech recognition not supported on this browser');
      return;
    }

    const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
      setTranscript('Listening...');
      // Haptic feedback if available
      if ('vibrate' in navigator) {
        navigator.vibrate(50);
      }
    };

    recognition.onresult = (event: any) => {
      const current = event.resultIndex;
      const transcript = event.results[current][0].transcript;
      setTranscript(transcript);
      
      if (event.results[current].isFinal) {
        processCommand(transcript);
      }
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      setIsListening(false);
      setTranscript('Error: ' + event.error);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
  };

  const processCommand = async (command: string) => {
    setResponse('Processing...');
    
    try {
      const apiResponse = await fetch('http://localhost:8003/api/assistant/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: command,
          mode: 'MOBILE',
          context: { 
            device: 'ios',
            location: 'mobile'
          }
        })
      });
      
      const data = await apiResponse.json();
      setResponse(data.answer || 'No response');
      
      // Speak response if API available
      if (data.audio_url) {
        const audio = new Audio(data.audio_url);
        audio.play();
      } else if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(data.answer);
        utterance.pitch = 0.8;
        utterance.rate = 0.9;
        speechSynthesis.speak(utterance);
      }
      
    } catch (error) {
      console.error('Failed to process command:', error);
      setResponse('Failed to process command. Please try again.');
    }
  };

  const quickActions = [
    { icon: '📅', label: 'Today', action: () => processCommand("What's my schedule today?") },
    { icon: '✅', label: 'Add Task', action: () => processCommand("Add a new task") },
    { icon: '📧', label: 'Emails', action: () => processCommand("Check important emails") },
    { icon: '🎯', label: 'Focus', action: () => processCommand("Start focus time") },
  ];

  return (
    <div className="App">
      <header className="App-header">
        <div className="status-bar">
          <h1>🤖 Optimus</h1>
          <span className={`online-status ${isOnline ? 'online' : 'offline'}`}>
            {isOnline ? '🟢' : '🔴'}
          </span>
        </div>
      </header>

      <main className="App-main">
        {/* Today's Agenda */}
        <section className="agenda-section">
          <h2>Today's Agenda</h2>
          <div className="agenda-list">
            {agenda.length > 0 ? (
              agenda.map(item => (
                <div key={item.id} className={`agenda-item ${item.type}`}>
                  <span className="agenda-time">{item.time || 'All day'}</span>
                  <span className="agenda-title">{item.title}</span>
                  {item.priority && (
                    <span className="agenda-priority">P{item.priority}</span>
                  )}
                </div>
              ))
            ) : (
              <p className="no-items">No items scheduled</p>
            )}
          </div>
        </section>

        {/* Voice Interface */}
        <section className="voice-section">
          <button 
            className={`voice-button ${isListening ? 'listening' : ''}`}
            onTouchStart={startListening}
            onClick={startListening}
            disabled={isListening}
          >
            <span className="voice-icon">{isListening ? '🎤' : '🎙️'}</span>
            <span className="voice-label">
              {isListening ? 'Listening...' : 'Tap to speak'}
            </span>
          </button>
          
          {transcript && (
            <div className="transcript">
              <strong>You:</strong> {transcript}
            </div>
          )}
          
          {response && (
            <div className="response">
              <strong>Optimus:</strong> {response}
            </div>
          )}
        </section>

        {/* Quick Actions */}
        <section className="quick-actions">
          <h3>Quick Actions</h3>
          <div className="action-grid">
            {quickActions.map((action, idx) => (
              <button 
                key={idx}
                className="action-button"
                onClick={action.action}
              >
                <span className="action-icon">{action.icon}</span>
                <span className="action-label">{action.label}</span>
              </button>
            ))}
          </div>
        </section>
      </main>

      {/* Bottom Navigation */}
      <nav className="bottom-nav">
        <button className="nav-item active">
          <span>🏠</span>
          <span>Home</span>
        </button>
        <button className="nav-item">
          <span>📊</span>
          <span>Stats</span>
        </button>
        <button className="nav-item">
          <span>🎯</span>
          <span>Goals</span>
        </button>
        <button className="nav-item">
          <span>⚙️</span>
          <span>Settings</span>
        </button>
      </nav>
    </div>
  );
}

export default App;