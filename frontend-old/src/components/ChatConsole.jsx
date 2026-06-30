import React, { useState, useEffect, useRef } from 'react';
import { sendChatMessage } from '../api';

const ChatConsole = ({ onStateUpdate }) => {
  // Step A: State Setup
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  // Step C: Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Step B: The Message Handler
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userText = input.trim();
    setInput('');

    // 1. Append user's message immediately
    setMessages(prev => [...prev, { role: 'user', content: userText }]);
    
    // 2. Set isTyping to true
    setIsTyping(true);

    try {
      // 3. Call sendChatMessage (wired to Master Orchestrator)
      const response = await sendChatMessage(userText);
      
      // 4. Append AI response and set isTyping to false
      const aiContent = response.reply || response.content || response.message || response.error || "No response received.";
      
      setMessages(prev => [...prev, { role: 'ai', content: aiContent }]);
      
      if (response.raw_state && onStateUpdate) {
        onStateUpdate(response.raw_state);
      }
    } catch (error) {
      setMessages(prev => [...prev, { role: 'ai', content: "Error communicating with Orchestrator." }]);
    } finally {
      setIsTyping(false);
    }
  };

  // Step C: UI Rendering
  return (
    <div className="chat" style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#0B0F19' }}>
      <div className="chat__messages" style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
        {messages.length === 0 ? (
          <div className="chat__welcome" style={{ textAlign: 'center', marginTop: '40px', color: '#9CA3AF' }}>
            <div className="chat__welcome-icon" style={{ fontSize: '48px', marginBottom: '16px' }}>✨</div>
            <h2 style={{ color: 'white', marginBottom: '8px' }}>AI Project Architect</h2>
            <p>Tell me about the software you want to build. I'll ask questions to clarify your requirements and design the architecture.</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`message message--${msg.role}`}
              style={{
                display: 'flex',
                gap: '16px',
                marginBottom: '24px',
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row'
              }}
            >
              <div 
                className="message__avatar"
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  background: msg.role === 'user' ? '#2563EB' : '#10B981',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 'bold',
                  color: 'white',
                  flexShrink: 0,
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                }}
              >
                {msg.role === 'user' ? 'U' : 'AI'}
              </div>
              <div 
                className="message__bubble"
                style={{
                  background: msg.role === 'user' ? '#2563EB' : '#1F2937',
                  color: 'white',
                  padding: '14px 18px',
                  borderRadius: '12px',
                  borderTopRightRadius: msg.role === 'user' ? '4px' : '12px',
                  borderTopLeftRadius: msg.role === 'ai' ? '4px' : '12px',
                  maxWidth: '75%',
                  lineHeight: '1.6',
                  fontSize: '15px',
                  boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'
                }}
              >
                {msg.content}
              </div>
            </div>
          ))
        )}
        
        {isTyping && (
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginTop: '24px', color: '#9CA3AF', fontSize: '14px', fontStyle: 'italic' }}>
             <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                background: '#10B981',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 'bold',
                color: 'white',
                opacity: 0.7
              }}>AI</div>
            <div style={{ background: '#1F2937', padding: '12px 16px', borderRadius: '12px', borderTopLeftRadius: '4px' }}>
                <span className="animate-pulse">AI is thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat__input-area" style={{ padding: '20px', background: '#111827', borderTop: '1px solid #374151' }}>
        <form className="chat__input-wrapper" onSubmit={handleSendMessage} style={{ display: 'flex', gap: '12px', maxWidth: '800px', margin: '0 auto' }}>
          <input
            type="text"
            className="chat__input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Message the Orchestrator..."
            disabled={isTyping}
            style={{
              flex: 1,
              padding: '14px 20px',
              borderRadius: '24px',
              border: '1px solid #4B5563',
              background: '#1F2937',
              color: 'white',
              outline: 'none',
              fontSize: '15px',
              transition: 'border-color 0.2s'
            }}
          />
          <button
            type="submit"
            className="chat__send-btn"
            disabled={!input.trim() || isTyping}
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              background: (!input.trim() || isTyping) ? '#374151' : '#2563EB',
              border: 'none',
              color: 'white',
              cursor: (!input.trim() || isTyping) ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '20px',
              transition: 'background 0.2s',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }}
          >
            ↑
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatConsole;
