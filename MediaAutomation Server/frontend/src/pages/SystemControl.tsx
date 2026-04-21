import React, { useState } from "react";
import api from "../api/api";
import type { ShutdownSchedulePayload, CancelPayload, OpenProgramPayload } from "../types/types";

export default function SystemControl() {
  const [delay, setDelay] = useState<number>(60);
  const [jobId, setJobId] = useState<string>("");
  const [programId, setProgramId] = useState<string>("obs_studio");
  const [msg, setMsg] = useState<string | null>(null);

  const schedule = async () => {
    const payload: ShutdownSchedulePayload = { delay_seconds: delay };
    try {
      const resp = await api.post("/system/shutdown/schedule", payload);
      setMsg(`Agendado: ${resp.data.job_id}`);
    } catch (err: any) {
      setMsg(err?.response?.data?.detail || "Erro ao agendar");
    }
  };

  const cancel = async () => {
    const payload: CancelPayload = { job_id: jobId };
    try {
      await api.post("/system/shutdown/cancel", payload);
      setMsg("Cancelado");
    } catch (err: any) {
      setMsg(err?.response?.data?.detail || "Erro ao cancelar");
    }
  };

  const openProgram = async () => {
    const payload: OpenProgramPayload = { program_id: programId };
    try {
      await api.post("/system/open", payload);
      setMsg("Programa aberto");
    } catch (err: any) {
      setMsg(err?.response?.data?.detail || "Erro ao abrir");
    }
  };

  return (
    <div>
      <h3>Controle do Sistema</h3>
      <div>
        <label>Delay (segundos)</label>
        <input type="number" value={delay} onChange={(e) => setDelay(Number(e.target.value))} />
        <button onClick={schedule}>Agendar desligamento</button>
      </div>
      <div>
        <label>Job ID</label>
        <input value={jobId} onChange={(e) => setJobId(e.target.value)} />
        <button onClick={cancel}>Cancelar job</button>
      </div>
      <div>
        <label>Program ID</label>
        <input value={programId} onChange={(e) => setProgramId(e.target.value)} />
        <button onClick={openProgram}>Abrir programa</button>
      </div>
      {msg && <div style={{ marginTop: 12 }}>{msg}</div>}
    </div>
  );
}
