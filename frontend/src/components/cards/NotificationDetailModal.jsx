import { X, AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function NotificationDetailModal() {
  const { selectedNotification, setSelectedNotification } = useApp();
  if (!selectedNotification) return null;

  const Icon =
    selectedNotification.type === 'critical'
      ? AlertTriangle
      : selectedNotification.type === 'success'
        ? CheckCircle2
        : Info;

  const color =
    selectedNotification.type === 'critical'
      ? 'text-danger bg-danger/10'
      : selectedNotification.type === 'success'
        ? 'text-success bg-success/10'
        : 'text-secondary bg-secondary/10';

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-primary/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg animate-fade-in rounded-2xl bg-white p-6 shadow-2xl">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className={`rounded-xl p-2.5 ${color}`}>
              <Icon size={20} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-primary">{selectedNotification.title}</h3>
              <p className="text-xs text-slate-400">{selectedNotification.time}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setSelectedNotification(null)}
            className="rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-primary"
          >
            <X size={18} />
          </button>
        </div>
        <p className="mb-2 text-sm font-medium text-slate-600">{selectedNotification.preview}</p>
        <div className="rounded-2xl bg-surface p-4 text-sm leading-relaxed text-slate-700">
          {selectedNotification.message}
        </div>
        <button
          type="button"
          onClick={() => setSelectedNotification(null)}
          className="mt-5 w-full rounded-full bg-secondary py-2.5 text-sm font-semibold text-white"
        >
          Close
        </button>
      </div>
    </div>
  );
}
