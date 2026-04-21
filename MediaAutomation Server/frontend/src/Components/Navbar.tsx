import React from "react";
import { Link, useNavigate } from "react-router-dom";
import useAuth from "@/auth/useAuth";

export default function Navbar() {
  const auth = useAuth();
  const navigate = useNavigate();

  const onLogout = () => {
    auth.logout();
    navigate("/login");
  };

  return (
    <nav>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", maxWidth: 1100, margin: "0 auto" }}>
        <div>
          <Link to="/">OBS</Link>
          <Link to="/stream" style={{ marginLeft: 12 }}>Streaming</Link>
          <Link to="/system" style={{ marginLeft: 12 }}>Sistema</Link>
        </div>
        <div>
          {auth.user ? (
            <>
              <span style={{ marginRight: 12 }}>{auth.user.username}</span>
              <button onClick={onLogout} style={{ padding: "6px 10px", borderRadius: 6, border: "none", cursor: "pointer" }}>
                Sair
              </button>
            </>
          ) : (
            <Link to="/login">Entrar</Link>
          )}
        </div>
      </div>
    </nav>
  );
}
