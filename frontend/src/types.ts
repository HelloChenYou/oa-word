export type TemplateItem = {
  template_id: string;
  name: string;
  doc_type: string;
  file_type: string;
  created_at: string;
};

export type TemplateDetail = TemplateItem & {
  raw_text: string;
  parsed: {
    placeholders?: string[];
    required_sections?: string[];
  };
};

export type KnowledgeItem = {
  document_id: string;
  name: string;
  doc_type: string;
  file_type: string;
  enabled: boolean;
  chunk_count: number;
  created_at: string;
};

export type KnowledgeDetail = KnowledgeItem & {
  raw_text: string;
};

export type Issue = {
  severity: string;
  category: string;
  title: string;
  original_text: string;
  suggested_text: string;
  reason: string;
  evidence: string;
  confidence: number;
  source: string;
  position_start?: number | null;
  position_end?: number | null;
};

export type TaskResult = {
  task_id: string;
  status: string;
  summary: Record<string, number>;
  issues: Issue[];
  rag_hits?: Array<{
    chunk_index: number;
    document_id: string;
    document_name: string;
    knowledge_chunk_index: number;
    score: number;
    content_preview: string;
    created_at: string;
  }>;
};

export type RuleScope = "public" | "private" | "template";

export type RuleItem = {
  rule_id: string;
  owner_id?: string | null;
  scope: RuleScope;
  kind: string;
  title: string;
  severity: string;
  category: string;
  pattern: string;
  replacement: string;
  reason: string;
  evidence: string;
  enabled: boolean;
};

export type AuthUser = {
  username: string;
  role: string;
  must_change_password: boolean;
};

export type UserItem = {
  username: string;
  role: string;
  enabled: boolean;
  must_change_password: boolean;
  created_at: string;
};
