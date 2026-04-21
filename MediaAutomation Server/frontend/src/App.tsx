import React from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { AuthProvider } from "./auth/AuthProvider";
import Login from "./pages/Login";
import OBSControl from "./pages/OBSControl";
import Streaming from "./pages/Streaming";
import SystemControl from "./pages/SystemControl";
import { ProtectedRoute } from "./components/ProtectedRoute";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <nav style={{ padding: 12 }}>
          <Link to="/">OBS</Link> | <Link to="/stream">Streaming</Link> | <Link to="/system">Sistema</Link>
        </nav>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <OBSControl />
              </ProtectedRoute>
            }
          />
          <Route
            path="/stream"
            element={
              <ProtectedRoute>
                <Streaming />
              </ProtectedRoute>
            }
          />
          <Route
            path="/system"
            element={
              <ProtectedRoute>
                <SystemControl />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
