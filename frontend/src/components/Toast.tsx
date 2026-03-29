'use client';

import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react';

// ── Types ──

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  dismissing?: boolean;
}

interface ToastContextValue {
  toast: {
    success: (message: string) => void;
    error: (message: string) => void;
    warning: (message: string) => void;
    info: (message: string) => void;
  };
}

// ── Context ──

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within a ToastProvider');
  return ctx;
}

// ── Config ──

const typeConfig: Record<ToastType, { icon: React.ReactNode; bg: string; border: string; text: string }> = {
  success: {
    icon: <CheckCircle size={14} />,
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/20',
    text: 'text-emerald-400',
  },
  error: {
    icon: <AlertCircle size={14} />,
    bg: 'bg-red-500/10',
    border: 'border-red-500/20',
    text: 'text-red-400',
  },
  warning: {
    icon: <AlertTriangle size={14} />,
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/20',
    text: 'text-amber-400',
  },
  info: {
    icon: <Info size={14} />,
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/20',
    text: 'text-blue-400',
  },
};

// ── Single Toast ──

function ToastNotification({
  item,
  onDismiss,
}: {
  item: ToastItem;
  onDismiss: (id: string) => void;
}) {
  const config = typeConfig[item.type];
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    timerRef.current = setTimeout(() => onDismiss(item.id), 4000);
    return () => clearTimeout(timerRef.current);
  }, [item.id, onDismiss]);

  return (
    <div
      className={`flex items-start gap-2.5 px-3.5 py-2.5 rounded-lg border shadow-lg backdrop-blur-sm ${config.bg} ${config.border} ${
        item.dismissing ? 'toast-out' : 'toast-in'
      }`}
      role="alert"
    >
      <span className={`shrink-0 mt-0.5 ${config.text}`}>{config.icon}</span>
      <p className="flex-1 text-xs text-syn-text leading-snug">{item.message}</p>
      <button
        onClick={() => onDismiss(item.id)}
        className="shrink-0 text-syn-muted hover:text-syn-text transition-colors"
      >
        <X size={12} />
      </button>
    </div>
  );
}

// ── Provider ──

let idCounter = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = `toast-${++idCounter}-${Date.now()}`;
    setToasts((prev) => {
      const next = [...prev, { id, type, message }];
      return next.slice(-5); // max 5
    });
  }, []);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) =>
      prev.map((t) => (t.id === id ? { ...t, dismissing: true } : t))
    );
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 200);
  }, []);

  const toast = {
    success: (msg: string) => addToast('success', msg),
    error: (msg: string) => addToast('error', msg),
    warning: (msg: string) => addToast('warning', msg),
    info: (msg: string) => addToast('info', msg),
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-4 right-4 z-[200] flex flex-col gap-2 w-80 pointer-events-none">
        {toasts.map((item) => (
          <div key={item.id} className="pointer-events-auto">
            <ToastNotification item={item} onDismiss={dismiss} />
          </div>
        ))}
      </div>
      <style jsx>{`
        @keyframes toast-slide-in {
          from { opacity: 0; transform: translateX(100%) translateY(8px); }
          to { opacity: 1; transform: translateX(0) translateY(0); }
        }
        @keyframes toast-slide-out {
          from { opacity: 1; transform: translateX(0); }
          to { opacity: 0; transform: translateX(100%); }
        }
        .toast-in { animation: toast-slide-in 0.25s ease-out; }
        .toast-out { animation: toast-slide-out 0.2s ease-in forwards; }
      `}</style>
    </ToastContext.Provider>
  );
}
