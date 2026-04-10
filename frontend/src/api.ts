import type { RuleItem, TaskResult, TemplateDetail, TemplateItem } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

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
    body: form
  });
  return parseJson<{ template_id: string }>(res);
}

export async function listTemplates() {
  const res = await fetch(`${API_BASE}/api/v1/templates`);
  return parseJson<TemplateItem[]>(res);
}

export async function getTemplateDetail(templateId: string) {
  const res = await fetch(`${API_BASE}/api/v1/templates/${templateId}`);
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
  return parseJson<{ task_id: string; status: string }>(res);
}

export async function getTaskStatus(taskId: string) {
  const res = await fetch(`${API_BASE}/api/v1/proofread/tasks/${taskId}`);
  return parseJson<{ task_id: string; status: string }>(res);
}

export async function getTaskResult(taskId: string) {
  const res = await fetch(`${API_BASE}/api/v1/proofread/tasks/${taskId}/result`);
  return parseJson<TaskResult>(res);
}

export async function listRules(input?: { scope?: string; ownerId?: string }) {
  const params = new URLSearchParams();
  if (input?.scope) params.set("scope", input.scope);
  if (input?.ownerId) params.set("owner_id", input.ownerId);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${API_BASE}/api/v1/rules${suffix}`);
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
  return parseJson<RuleItem>(res);
}

export async function deleteRule(ruleId: string, ownerId?: string) {
  const params = new URLSearchParams();
  if (ownerId) params.set("owner_id", ownerId);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${API_BASE}/api/v1/rules/${ruleId}${suffix}`, {
    method: "DELETE"
  });
  return parseJson<{ ok: boolean }>(res);
}
