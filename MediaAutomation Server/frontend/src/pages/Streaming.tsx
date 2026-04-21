import React, { useState } from "react";
import api from "../api/api";
import type { GenerateResponse, KeysPayload } from "../types/types";
import useAuth from "../auth/useAuth";

export default function Streaming() {
  const [gen, setGen] = useState<GenerateResponse | null>(null);
  const [youtubeKey, setYoutubeKey] = useState("");
  const [facebookKey, setFacebookKey] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const { token } = useAuth();

  const generate = async () => {
    setMsg(null);
    try {
      const resp = await api.post<GenerateResponse>("/stream/generate");
      setGen(resp.data);
    } catch (err: any) {
      setMsg(err?.response?.data?.detail || "Erro ao gerar");
    }
  };

  const saveKeys = async () => {
    const payload: KeysPayload = { youtube_key: youtubeKey || undefined, facebook_key: facebookKey || undefined };
    try {
      await api.post("/stream/keys", payload);
      setMsg("Chaves salvas");
    } catch (err: any) {
      setMsg(err?.response?.data?.detail || "Erro ao salvar");
    }
  };

  const startYoutubeAuth = async () => {
    // redirect_uri should match config.json youtube.oauth_redirect_uri
    const redirectUri = encodeURIComponent(import.meta.env.VITE_YT_REDIRECT || "http://0.0.0.0:8000/stream/youtube/callback");
    const resp = await api.get(`/stream/youtube/auth?redirect_uri=${redirectUri}`);
    const url = resp.data.authorization_url;
    window.open(url, "_blank");
  };

  const revoke = async () => {
    try {
      await api.post("/stream/youtube/revoke");
      setMsg("Revogado");
    } catch (err: any) {
      setMsg(err?.response?.data?.detail || "Erro ao revogar");
    }
  };

  return (
    <div>
      <h3>Streaming</h3>
      <div>
        <button onClick={generate}>Gerar título/descrição</button>
        {gen && (
          <div>
            <p><strong>Título:</strong> {gen.title}</p>
            <p><strong>Descrição:</strong> {gen.description}</p>
            <p><strong>Facebook key:</strong> {gen.facebook_key || "Nenhuma"}</p>
            <p><strong>YouTube key:</strong> {gen.youtube_key || "Nenhuma"}</p>
          </div>
        )}
      </div>

      <hr />

      <div>
        <h4>Registrar chaves</h4>
        <input placeholder="YouTube key" value={youtubeKey} onChange={(e) => setYoutubeKey(e.target.value)} />
        <input placeholder="Facebook key" value={facebookKey} onChange={(e) => setFacebookKey(e.target.value)} />
        <button onClick={saveKeys}>Salvar</button>
      </div>

      <hr />

      <div>
        <h4>YouTube OAuth</h4>
        <button onClick={startYoutubeAuth}>Autorizar YouTube (abrir consent screen)</button>
        <button onClick={revoke}>Revogar tokens</button>
      </div>

      {msg && <div style={{ marginTop: 12 }}>{msg}</div>}
    </div>
  );
}
