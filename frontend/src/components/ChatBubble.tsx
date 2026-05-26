import { useState, useEffect, useRef } from 'react';

interface ChatBubbleProps {
  text: string;
  speaker: string;
  type: 'speech' | 'thought';
  typing: boolean;
}

export default function ChatBubble({ text, speaker, type, typing }: ChatBubbleProps) {
  const [displayedLen, setDisplayedLen] = useState(typing ? 0 : text.length);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!typing) {
      setDisplayedLen(text.length);
      return;
    }

    setDisplayedLen(0);
    let idx = 0;
    intervalRef.current = setInterval(() => {
      idx++;
      if (idx >= text.length) {
        if (intervalRef.current) clearInterval(intervalRef.current);
      }
      setDisplayedLen(idx);
    }, 50);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [text, typing]);

  const isThought = type === 'thought';
  const prefix = isThought ? '💭内心OS: ' : '';
  const displayText = prefix + text.slice(0, displayedLen);

  return (
    <div className="chat-bubble">
      <div className="chat-bubble-header">
        <span className="chat-bubble-speaker">{speaker}</span>
        {isThought && (
          <span style={{ fontSize: 10, color: 'var(--text-muted)', opacity: 0.6 }}>
            (内心独白)
          </span>
        )}
      </div>
      <div className={`chat-bubble-body ${type}`}>
        {displayText}
        {displayedLen < text.length && (
          <span className="chat-bubble-cursor" />
        )}
      </div>
    </div>
  );
}
