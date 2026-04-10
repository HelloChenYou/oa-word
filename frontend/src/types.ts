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
};

export type TaskResult = {
  task_id: string;
  status: string;
  summary: Record<string, number>;
  issues: Issue[];
};
