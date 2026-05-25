import { BrowserRouter, Navigate, Route, Routes, NavLink, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "./api";
import type { User } from "./types";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import ReviewPage from "./pages/ReviewPage";
import UploadPage from "./pages/UploadPage";
import BatchesPage from "./pages/BatchesPage";

function Shell({ user, onLogout }: { user: User; onLogout: () => void }) {
  const navigate = useNavigate();
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>Breathe ESG — Data Review</h1>
          <span className="org">{user.organization?.name}</span>
        </div>
        <nav className="nav">
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/review">Review queue</NavLink>
          <NavLink to="/upload">Upload</NavLink>
          <NavLink to="/batches">Batches</NavLink>
          <button className="btn btn-secondary" onClick={() => { onLogout(); navigate("/login"); }}>
            Sign out
          </button>
        </nav>
      </header>
      <main className="main">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/review" element={<ReviewPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/batches" element={<BatchesPage />} />
        </Routes>
      </main>
    </div>
  );
}

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("token");
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(!!localStorage.getItem("token"));

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setLoading(false);
      return;
    }
    api<User>("/auth/me/")
      .then(setUser)
      .catch(() => localStorage.removeItem("token"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="login-page">Loading…</div>;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            user ? (
              <Navigate to="/" replace />
            ) : (
              <LoginPage onLogin={(u) => setUser(u)} />
            )
          }
        />
        <Route
          path="/*"
          element={
            <PrivateRoute>
              {user ? (
                <Shell
                  user={user}
                  onLogout={() => {
                    localStorage.removeItem("token");
                    setUser(null);
                  }}
                />
              ) : (
                <Navigate to="/login" replace />
              )}
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
