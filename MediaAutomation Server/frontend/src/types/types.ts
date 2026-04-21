export interface User {
  username: string;
  full_name?: string | null;
  disabled?: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface ActionResponse {
  status: string;
  detail?: string | null;
}

export interface GenerateResponse {
  youtube_key?: string | null;
  facebook_key?: string | null;
  title: string;
  description: string;
}

export interface KeysPayload {
  youtube_key?: string | null;
  facebook_key?: string | null;
}

export interface ShutdownSchedulePayload {
  at?: string | null; // ISO string
  delay_seconds?: number | null;
}

export interface CancelPayload {
  job_id: string;
}

export interface OpenProgramPayload {
  program_id: string;
}
