import React, { useState } from "react";
import api from "../api/api";
import type { ActionResponse } from "../types/types";

export default function OBSControl() {
  const [status, setStatus] = useState<string | null>(null);
  const [scene, setScene] = useState("");
  const [loading, setLoading] = useState(false);

  const call = async (path: string, method = "post", data?: any) => {
    setLoading(true);
    try {
      const resp = await (api as any)[method]<ActionResponse>(`/obs${path}`, data);
      setStatus(resp.data.status || JSON.stringify(resp.data));
    } catch (err: any) {
      setStatus(err?.response?.data?.detail || "Erro");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h3>Controle OBS</h3>
      <div>
        <button onClick={() => call("/start")}>Iniciar Stream</button>
        <button onClick={() => call("/stop")}>Parar Stream</button>
        <button onClick={() => call("/status", "get")}>Status</button>
      </div>
      <div style={{ marginTop: 12 }}>
        <input placeholder="Nome da cena" value={scene} onChange={(e) => setScene(e.target.value)} />
        <button onClick={() => call("/scene", "post", { scene_name: scene })}>Mudar Cena</button>
      </div>
      <div style={{ marginTop: 12 }}>{loading ? "Carregando..." : status}</div>
    </div>
  );
}
