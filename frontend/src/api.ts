import type { AuthUser, RuleItem, TaskResult, TemplateDetail, TemplateItem } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const DEFAULT_ADMIN_TOKEN = import.meta.env.VITE_ADMIN_TOKEN ?? "";

function getAuthHeaders(): HeadersInit {
  const authToken = window.localStorage.getItem("auth_access_token");
  if (authToken) {
    return {
      Authorization: `Bearer ${authToken}`
    };
  }
  const adminToken = window.localStorage.getItem("admin_api_token") || DEFAULT_ADMIN_TOKEN;
  if (adminToken) {
    return {
      Authorization: `Bearer ${adminToken}`,
      "X-Admin-Token": adminToken
    };
  }
  return {};
}

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    try {
      const parsed = JSON.parse(text) as { detail?: string };
      throw new Error(parsed.detail || `HTTP ${res.status}`);
    } catch {
      throw new Error(text || `HTTP ${res.status}`);
    }
  }
  return (await res.json()) as T;
}

export async function uploadTemplate(input: {
  name: string;
  docType: string;
  file: File;
}) {
  const form = new FormData();
  form.append("name", input.name);
  form.append("doc_type", input.docType);
  form.append("file", input.file);

  const res = await fetch(`${API_BASE}/api/v1/templates`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: form
  });
  return parseJson<{ template_id: string }>(res);
}

export async function listTemplates() {
  const res = await fetch(`${API_BASE}/api/v1/templates`, {
    headers: getAuthHeaders()
  });
  return parseJson<TemplateItem[]>(res);
}

export async function getTemplateDetail(templateId: string) {
  const res = await fetch(`${API_BASE}/api/v1/templates/${templateId}`, {
    headers: getAuthHeaders()
  });
  return parseJson<TemplateDetail>(res);
}

export async function createTask(input: {
  text: string;
  mode: "review" | "rewrite";
  scene: "general" | "contract" | "announcement" | "tech_doc";
  template_id?: string;
  owner_id?: string;
}) {
  const res = await fetch(`${API_BASE}/api/v1/proofread/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(input)
  });
  return parseJson<{ task_id: string; status: string }>(res);
}

export async function getTaskStatus(taskId: string) {
  const res = await fetch(`${API_BASE}/api/v1/proofread/tasks/${taskId}`, {
    headers: getAuthHeaders()
  });
  return parseJson<{ task_id: string; status: string }>(res);
}

export async function getTaskResult(taskId: string) {
  const res = await fetch(`${API_BASE}/api/v1/proofread/tasks/${taskId}/result`, {
    headers: getAuthHeaders()
  });
  return parseJson<TaskResult>(res);
}

export async function listRules(input?: { scope?: string; ownerId?: string }) {
  const params = new URLSearchParams();
  if (input?.scope) params.set("scope", input.scope);
  if (input?.ownerId) params.set("owner_id", input.ownerId);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${API_BASE}/api/v1/rules${suffix}`, {
    headers: getAuthHeaders()
  });
  return parseJson<RuleItem[]>(res);
}

export async function createRule(input: {
  owner_id?: string;
  scope: string;
  kind: string;
  title: string;
  severity: string;
  category: string;
  pattern: string;
  replacement: string;
  reason: string;
  evidence: string;
  enabled: boolean;
}) {
  const res = await fetch(`${API_BASE}/api/v1/rules`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(input)
  });
  return parseJson<RuleItem>(res);
}

export async function updateRule(
  ruleId: string,
  input: {
    scope?: string;
    kind?: string;
    title?: string;
    severity?: string;
    category?: string;
    pattern?: string;
    replacement?: string;
    reason?: string;
    evidence?: string;
    enabled?: boolean;
  },
  ownerId?: string
) {
  const params = new URLSearchParams();
  if (ownerId) params.set("owner_id", ownerId);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${API_BASE}/api/v1/rules/${ruleId}${suffix}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(input)
  });
  return parseJson<RuleItem>(res);
}

export async function deleteRule(ruleId: string, ownerId?: string) {
  const params = new URLSearchParams();
  if (ownerId) params.set("owner_id", ownerId);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${API_BASE}/api/v1/rules/${ruleId}${suffix}`, {
    method: "DELETE",
    headers: getAuthHeaders()
  });
  return parseJson<{ ok: boolean }>(res);
}

export async function login(input: { username: string; password: string }) {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
  return parseJson<{ access_token: string; token_type: string; expires_in: number; user: AuthUser }>(res);
}

export async function getCurrentUser() {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: getAuthHeaders()
  });
  return parseJson<AuthUser>(res);
}

export async function changePassword(input: { current_password: string; new_password: string }) {
  const res = await fetch(`${API_BASE}/api/v1/auth/change-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(input)
  });
  return parseJson<AuthUser>(res);
}
