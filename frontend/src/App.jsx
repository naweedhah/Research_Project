import { Fragment } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AppProvider, useApp } from './context/AppContext';
import AppShell from './layout/AppShell';
import Login from './pages/auth/Login';
import Overview from './pages/home/Overview';
import { COMPONENT_ROUTES } from './routes';
import { Loading } from './ui';

function Protected({ children }) {
  const { isAuthenticated, authLoading } = useApp();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (authLoading) return <div className="p-8"><Loading label="Verifying your session…" /></div>;
  return children;
}

function AppRoutes() {
  const { isAuthenticated } = useApp();
  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <Login />} />
      <Route element={<Protected><AppShell /></Protected>}>
        <Route index element={<Overview />} />
        {COMPONENT_ROUTES.map((routes, i) => <Fragment key={i}>{routes}</Fragment>)}
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <AppRoutes />
        <Toaster position="top-right" toastOptions={{ style: { borderRadius: '10px', background: '#0f2a3d', color: '#fff', fontSize: '14px' } }} />
      </BrowserRouter>
    </AppProvider>
  );
}
