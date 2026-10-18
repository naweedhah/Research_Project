import { useEffect, useRef, useState } from 'react';
import { Bot, Eraser, Send, X } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { useComponent4Selection } from '../../context/Component4SelectionContext';
import { sendAiChat } from '../../services/component4/aiApi';

const WELCOME_MESSAGE =
  "Hello! I'm the FedNutri-XAI Health Assistant. Ask me about malnutrition indicators, district risk levels, Triposha planning or how the AI model reached a prediction.";

const suggestedQuestions = [
  'What is SAM?',
  'What does H1, H3 and H6 mean?',
  'Why is this district high risk?',
  'What factors increased the forecast?',
  'What factors decreased the forecast?',
  'Why is this district critical?',
  'What does DMBI mean?',
  'What does SHAP mean?',
  'How much Triposha is needed?',
  'What is the current warning?',
  'What does forecast uncertainty mean?',
  'Summarize the selected district forecast',
];

export default function AIHealthAssistant() {
  const { assistantOpen, setAssistantOpen } = useApp();
  const { district, year, month, hasSelection } = useComponent4Selection();
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: WELCOME_MESSAGE,
    },
  ]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, typing, assistantOpen]);

  if (!assistantOpen) return null;

  const send = async (text) => {
    const q = (text || input).trim();
    if (!q || typing) return;

    setInput('');
    setMessages((m) => [...m, { role: 'user', text: q }]);
    setTyping(true);

    try {
      const payload = { message: q };
      if (hasSelection) {
        payload.district = district;
        payload.year = year;
        payload.month = month;
      }

      const response = await sendAiChat(payload);
      const answer =
        typeof response?.answer === 'string' && response.answer.trim()
          ? response.answer
          : 'Sorry, I could not get a response. Please try again.';

      setMessages((m) => [...m, { role: 'assistant', text: answer }]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          text: 'Sorry, I could not get a response. Please try again.',
        },
      ]);
    } finally {
      setTyping(false);
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-[60] flex h-[540px] w-[min(100vw-2rem,380px)] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl animate-fade-in">
      <div className="flex items-center justify-between bg-gradient-to-r from-[#4C1D95] to-secondary px-4 py-3 text-white">
        <div className="flex items-center gap-2">
          <Bot size={20} />
          <div>
            <p className="text-sm font-bold">AI Health Assistant</p>
            <p className="text-[10px] text-white/70">Nutrition knowledge engine · prototype</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            title="Clear chat"
            onClick={() =>
              setMessages([
                {
                  role: 'assistant',
                  text: WELCOME_MESSAGE,
                },
              ])
            }
            className="rounded-lg p-1.5 hover:bg-white/15"
          >
            <Eraser size={16} />
          </button>
          <button
            type="button"
            onClick={() => setAssistantOpen(false)}
            className="rounded-lg p-1.5 hover:bg-white/15"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto bg-white p-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {m.role === 'assistant' && (
              <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-secondary/15 text-secondary">
                <Bot size={14} />
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                m.role === 'user'
                  ? 'bg-secondary text-white'
                  : 'border border-slate-200 bg-white text-slate-700'
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {typing && (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Bot size={14} className="text-secondary" />
            <span>Thinking...</span>
            <span className="typing-dot">●</span>
            <span className="typing-dot" style={{ animationDelay: '0.2s' }}>
              ●
            </span>
            <span className="typing-dot" style={{ animationDelay: '0.4s' }}>
              ●
            </span>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="border-t border-slate-100 p-3">
        <div className="mb-2 flex flex-nowrap gap-2 overflow-x-auto whitespace-nowrap pb-1 [scrollbar-width:thin] [&::-webkit-scrollbar]:h-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-slate-300">
          {suggestedQuestions.map((q) => (
            <button
              key={q}
              type="button"
              disabled={typing}
              onClick={() => send(q)}
              className="shrink-0 whitespace-nowrap rounded-full border border-slate-200 px-3 py-1 text-[11px] text-slate-600 hover:border-secondary hover:text-secondary disabled:cursor-not-allowed disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                send();
              }
            }}
            disabled={typing}
            placeholder="Ask about nutrition data..."
            className="flex-1 rounded-full border border-slate-200 bg-surface px-4 py-2.5 text-sm outline-none focus:border-secondary disabled:opacity-60"
          />
          <button
            type="button"
            onClick={() => send()}
            disabled={typing || !input.trim()}
            className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary text-white shadow-md shadow-secondary/30 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
