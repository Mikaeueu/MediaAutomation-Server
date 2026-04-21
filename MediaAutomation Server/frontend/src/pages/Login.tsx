import React, { useState } from "react";
import useAuth from "../auth/useAuth";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("midiadm");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const nav = useNavigate();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await login(username, password);
      nav("/");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Erro ao autenticar");
    }
  };

  return (
    <div style={{ maxWidth: 420, margin: "2rem auto" }}>
      <h2>Entrar</h2>
      <form onSubmit={onSubmit}>
        <div>
          <label>Usuário</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} />
        </div>
        <div>
          <label>Senha</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <div style={{ color: "red" }}>{error}</div>}
        <button type="submit">Entrar</button>
      </form>
    </div>
  );
}
