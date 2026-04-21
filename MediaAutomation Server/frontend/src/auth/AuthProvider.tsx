import React, { createContext, useState, useEffect } from "react";
import api, { setAuthToken } from "../api/api";
import type { User, TokenResponse } from "../types/types";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("token"));
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    setAuthToken(token);
    if (!token) {
      setUser(null);
    } else {
      // Optionally decode token or call a /me endpoint if available
      setUser({ username: "midiadm" });
    }
  }, [token]);

  const login = async (username: string, password: string) => {
    const form = new URLSearchParams();
    form.append("username", username);
    form.append("password", password);
    const resp = await api.post<TokenResponse>("/auth/login", form.toString(), {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    const t = resp.data.access_token;
    localStorage.setItem("token", t);
    setToken(t);
    setAuthToken(t);
    setUser({ username });
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setAuthToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
