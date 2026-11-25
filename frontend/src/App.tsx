import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppLayout } from './components/Layout';
import { LoadingState } from './components/UI';

import { AmbientBackground } from './components/AmbientBackground';
import { InteractiveEffects } from './components/InteractiveEffects';

const LandingPage = lazy(() =>
  import('./pages/LandingPage').then((page) => ({ default: page.LandingPage }))
);
const LoginPage = lazy(() =>
  import('./pages/LoginPage').then((page) => ({ default: page.LoginPage }))
);
const RegisterPage = lazy(() =>
  import('./pages/RegisterPage').then((page) => ({ default: page.RegisterPage }))
);
const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((page) => ({ default: page.DashboardPage }))
);
const MyDocumentsPage = lazy(() =>
  import('./pages/MyDocumentsPage').then((page) => ({ default: page.MyDocumentsPage }))
);
const UploadPage = lazy(() =>
  import('./pages/UploadPage').then((page) => ({ default: page.UploadPage }))
);
const DocumentProcessingPage = lazy(() =>
  import('./pages/DocumentProcessingPage').then((page) => ({ default: page.DocumentProcessingPage }))
);
const DocumentAnalysisPage = lazy(() =>
  import('./pages/DocumentAnalysisPage').then((page) => ({ default: page.DocumentAnalysisPage }))
);
const AssistantPage = lazy(() =>
  import('./pages/AssistantPage').then((page) => ({ default: page.AssistantPage }))
);
const AnomalyDetectionPage = lazy(() =>
  import('./pages/AnomalyDetectionPage').then((page) => ({ default: page.AnomalyDetectionPage }))
);
const VisualizationsPage = lazy(() =>
  import('./pages/VisualizationsPage').then((page) => ({ default: page.VisualizationsPage }))
);
const CompareDocumentsPage = lazy(() =>
  import('./pages/CompareDocumentsPage').then((page) => ({ default: page.CompareDocumentsPage }))
);
const ReportsPage = lazy(() =>
  import('./pages/ReportsPage').then((page) => ({ default: page.ReportsPage }))
);
const SettingsPage = lazy(() =>
  import('./pages/SettingsPage').then((page) => ({ default: page.SettingsPage }))
);

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="dark-app min-h-screen flex items-center justify-center bg-slate-50">
        <LoadingState message="Authenticating workspace..." />
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <AppLayout>{children}</AppLayout>;
}

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AmbientBackground />
        <InteractiveEffects />
        <Suspense
          fallback={
            <div className="dark-app min-h-screen flex items-center justify-center bg-slate-50">
              <LoadingState message="Opening your workspace..." />
            </div>
          }
        >
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/documents"
              element={
                <ProtectedRoute>
                  <MyDocumentsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/upload"
              element={
                <ProtectedRoute>
                  <UploadPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/documents/:id/processing"
              element={
                <ProtectedRoute>
                  <DocumentProcessingPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/analysis"
              element={
                <ProtectedRoute>
                  <DocumentAnalysisPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/analysis/:id"
              element={
                <ProtectedRoute>
                  <DocumentAnalysisPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/assistant"
              element={
                <ProtectedRoute>
                  <AssistantPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/assistant/:id"
              element={
                <ProtectedRoute>
                  <AssistantPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/anomalies"
              element={
                <ProtectedRoute>
                  <AnomalyDetectionPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/visualizations"
              element={
                <ProtectedRoute>
                  <VisualizationsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/compare"
              element={
                <ProtectedRoute>
                  <CompareDocumentsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/reports"
              element={
                <ProtectedRoute>
                  <ReportsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <SettingsPage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
