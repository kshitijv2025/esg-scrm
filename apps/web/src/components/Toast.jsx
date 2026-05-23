import {
  useState,
  useEffect,
  useCallback,
  createContext,
  useContext,
} from "react";

const ToastContext = createContext(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) return () => {};
  return ctx;
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((toast) => {
    const id = Date.now() + Math.random();
    const duration = toast.severity === "CRITICAL" ? 15000 : 8000;
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, duration);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={addToast}>
      {children}
      <div className="toast-container">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`toast toast-${(t.severity || "info").toLowerCase()}`}
            onClick={() => removeToast(t.id)}
          >
            <span className="toast-severity">{t.severity}</span>
            <span className="toast-message">{t.message}</span>
            <span className="toast-time">
              {new Date(t.timestamp).toLocaleTimeString()}
            </span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
