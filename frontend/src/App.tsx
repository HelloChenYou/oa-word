import { useEffect, useMemo, useState } from "react";
import {
  createTask,
  getTaskResult,
  getTaskStatus,
  getTemplateDetail,
  listTemplates,
  uploadTemplate
} from "./api";
import type { TaskResult, TemplateDetail, TemplateItem } from "./types";

function App() {
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateDetail | null>(null);

  const [templateName, setTemplateName] = useState("");
  const [templateDocType, setTemplateDocType] = useState("general");
  const [templateFile, setTemplateFile] = useState<File | null>(null);

  const [text, setText] = useState("请各部门登陆OA系统，并上报员工手机号13800138000。");
  const [mode, setMode] = useState<"review" | "rewrite">("review");
  const [scene, setScene] = useState<"general" | "contract" | "announcement" | "tech_doc">("general");
  const [taskId, setTaskId] = useState("");
  const [taskStatus, setTaskStatus] = useState("");
  const [taskResult, setTaskResult] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const templateOptions = useMemo(() => [{ template_id: "", name: "不使用模板" }, ...templates], [templates]);

  const loadTemplates = async () => {
    const data = await listTemplates();
    setTemplates(data);
  };

  useEffect(() => {
    loadTemplates().catch((err) => setMessage(`加载模板失败: ${String(err)}`));
  }, []);

  useEffect(() => {
    if (!selectedTemplateId) {
      setSelectedTemplate(null);
      return;
    }
    getTemplateDetail(selectedTemplateId)
      .then(setSelectedTemplate)
      .catch((err) => setMessage(`读取模板详情失败: ${String(err)}`));
  }, [selectedTemplateId]);

  const onUploadTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!templateFile || !templateName.trim()) {
      setMessage("请填写模板名称并选择模板文件。");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const resp = await uploadTemplate({ name: templateName.trim(), docType: templateDocType, file: templateFile });
      setMessage(`模板上传成功: ${resp.template_id}`);
      setTemplateName("");
      setTemplateDocType("general");
      setTemplateFile(null);
      await loadTemplates();
    } catch (err) {
      setMessage(`模板上传失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const onCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) {
      setMessage("请输入待校对文本。");
      return;
    }
    setLoading(true);
    setMessage("");
    setTaskResult(null);
    try {
      const payload = {
        text: text.trim(),
        mode,
        scene,
        ...(selectedTemplateId ? { template_id: selectedTemplateId } : {})
      };
      const resp = await createTask(payload);
      setTaskId(resp.task_id);
      setTaskStatus(resp.status);
      setMessage(`任务已创建: ${resp.task_id}`);
    } catch (err) {
      setMessage(`创建任务失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const pollTask = async () => {
    if (!taskId) {
      setMessage("请先创建任务。");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const statusResp = await getTaskStatus(taskId);
      setTaskStatus(statusResp.status);
      if (statusResp.status === "success") {
        const result = await getTaskResult(taskId);
        setTaskResult(result);
      }
    } catch (err) {
      setMessage(`查询任务失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <header>
        <h1>AI 公文助手管理台</h1>
        <p>模板上传（docx/txt/md）+ 校对任务管理</p>
      </header>

      <section className="card">
        <h2>模板管理</h2>
        <form onSubmit={onUploadTemplate} className="grid">
          <label>
            模板名称
            <input value={templateName} onChange={(e) => setTemplateName(e.target.value)} placeholder="例如：通知模板" />
          </label>
          <label>
            模板类型
            <input value={templateDocType} onChange={(e) => setTemplateDocType(e.target.value)} placeholder="general/notice/..." />
          </label>
          <label>
            模板文件
            <input
              type="file"
              accept=".docx,.txt,.md"
              onChange={(e) => setTemplateFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <button type="submit" disabled={loading}>
            上传模板
          </button>
        </form>

        <div className="row">
          <label>
            选择模板
            <select value={selectedTemplateId} onChange={(e) => setSelectedTemplateId(e.target.value)}>
              {templateOptions.map((item) => (
                <option key={item.template_id || "none"} value={item.template_id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <button onClick={loadTemplates} disabled={loading}>
            刷新模板列表
          </button>
        </div>

        {selectedTemplate && (
          <div className="block">
            <h3>模板解析结果</h3>
            <pre>{JSON.stringify(selectedTemplate.parsed, null, 2)}</pre>
          </div>
        )}
      </section>

      <section className="card">
        <h2>校对任务</h2>
        <form onSubmit={onCreateTask} className="grid">
          <label>
            模式
            <select value={mode} onChange={(e) => setMode(e.target.value as "review" | "rewrite")}>
              <option value="review">review</option>
              <option value="rewrite">rewrite</option>
            </select>
          </label>
          <label>
            场景
            <select
              value={scene}
              onChange={(e) => setScene(e.target.value as "general" | "contract" | "announcement" | "tech_doc")}
            >
              <option value="general">general</option>
              <option value="contract">contract</option>
              <option value="announcement">announcement</option>
              <option value="tech_doc">tech_doc</option>
            </select>
          </label>
          <label className="full">
            文本内容
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={7} />
          </label>
          <button type="submit" disabled={loading}>
            创建任务
          </button>
          <button type="button" onClick={pollTask} disabled={loading || !taskId}>
            查询任务状态/结果
          </button>
        </form>

        <div className="block">
          <div>任务ID：{taskId || "-"}</div>
          <div>任务状态：{taskStatus || "-"}</div>
        </div>
      </section>

      <section className="card">
        <h2>结果展示</h2>
        {!taskResult && <p>暂无结果，任务成功后点击“查询任务状态/结果”。</p>}
        {taskResult && (
          <>
            <pre>{JSON.stringify(taskResult.summary, null, 2)}</pre>
            <table>
              <thead>
                <tr>
                  <th>严重级别</th>
                  <th>类别</th>
                  <th>标题</th>
                  <th>原文</th>
                  <th>建议</th>
                  <th>来源</th>
                </tr>
              </thead>
              <tbody>
                {taskResult.issues.map((issue, idx) => (
                  <tr key={`${issue.title}-${idx}`}>
                    <td>{issue.severity}</td>
                    <td>{issue.category}</td>
                    <td>{issue.title}</td>
                    <td>{issue.original_text}</td>
                    <td>{issue.suggested_text}</td>
                    <td>{issue.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </section>

      {message && <div className="toast">{message}</div>}
    </div>
  );
}

export default App;
