/** Central API base and paths for the FastAPI backend. */
export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const api = {
  health: `${API_BASE_URL}/health`,
  revenue: `${API_BASE_URL}/api/v1/analytics/revenue`,
  insights: `${API_BASE_URL}/api/v1/analytics/insights`,
  aiIntel: `${API_BASE_URL}/api/v1/analytics/ai-intelligence`,
  timeline: `${API_BASE_URL}/api/v1/interactions/timeline`,
  crmRecords: `${API_BASE_URL}/api/v1/crm/records`,
  crmRecord: (id) => `${API_BASE_URL}/api/v1/crm/records/${id}`,
  ingestAudio: `${API_BASE_URL}/ingest/audio`,
  ingestTranscript: `${API_BASE_URL}/ingest/transcript`,
  hubspotPush: (id) => `${API_BASE_URL}/api/v1/hubspot/push/${id}`,
  agentsChat: `${API_BASE_URL}/api/v1/agents/chat`,
  agentsNext: (id) => `${API_BASE_URL}/api/v1/agents/next-action/${id}`,
  agentsFollowup: (id) => `${API_BASE_URL}/api/v1/agents/followup/${id}`,
  google: {
    status: `${API_BASE_URL}/api/v1/google/status/`,
    auth: `${API_BASE_URL}/api/v1/google/auth/`,
    signout: `${API_BASE_URL}/api/v1/google/auth/signout`,
    gmailGenerate: `${API_BASE_URL}/api/v1/google/gmail/generate`,
    gmailSend: `${API_BASE_URL}/api/v1/google/gmail/send`,
    calendar: `${API_BASE_URL}/api/v1/google/calendar/schedule`,
  },
};

export async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    mode: "cors",
    cache: "no-store",
    ...options,
    headers: {
      ...(options.headers || {}),
    },
  });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    const detail =
      data && typeof data === "object" && typeof data.detail === "string"
        ? data.detail
        : `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return data;
}
