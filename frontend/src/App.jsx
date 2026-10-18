import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AppProvider, useApp } from './context/AppContext';
import { Component4SelectionProvider } from './context/Component4SelectionContext';
import MainLayout from './components/layout/MainLayout';
import LoadingSpinner from './components/common/LoadingSpinner';
import Login from './pages/Login';
import ResearchHome from './pages/ResearchHome';
import TrustworthyXAI from './pages/TrustworthyXAI';
import PersonalizedNutrition from './pages/PersonalizedNutrition';
import PrivacyRecalibration from './pages/PrivacyRecalibration';
import Settings from './pages/Settings';
import Profile from './pages/Profile';
import Component4Routes from './routes/Component4Routes';

function ProtectedRoute({ children }) {
  const { isAuthenticated, authLoading } = useApp();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface p-6">
        <LoadingSpinner message="Verifying your session..." />
      </div>
    );
  }
  return children;
}

function AppRoutes() {
  const { isAuthenticated } = useApp();

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/research-home" replace /> : <Login />}
      />

      <Route
        path="/research-home"
        element={
          <ProtectedRoute>
            <ResearchHome />
          </ProtectedRoute>
        }
      />
      <Route
        path="/component/trustworthy-xai"
        element={
          <ProtectedRoute>
            <TrustworthyXAI />
          </ProtectedRoute>
        }
      />
      <Route
        path="/component/personalized-nutrition"
        element={
          <ProtectedRoute>
            <PersonalizedNutrition />
          </ProtectedRoute>
        }
      />
      <Route
        path="/component/privacy-recalibration"
        element={
          <ProtectedRoute>
            <PrivacyRecalibration />
          </ProtectedRoute>
        }
      />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/research-home" replace />} />
        {Component4Routes()}
        <Route path="settings" element={<Settings />} />
        <Route path="profile" element={<Profile />} />
      </Route>

      <Route
        path="*"
        element={<Navigate to={isAuthenticated ? '/research-home' : '/login'} replace />}
      />
    </Routes>
  );
}

export default function App() {
  return (
    <AppProvider>
      <Component4SelectionProvider>
        <BrowserRouter>
          <AppRoutes />
          <Toaster
            position="top-right"
            toastOptions={{
              style: {
                borderRadius: '12px',
                background: '#0B1F4D',
                color: '#fff',
                fontSize: '15px',
              },
            }}
          />
        </BrowserRouter>
      </Component4SelectionProvider>
    </AppProvider>
  );
}
