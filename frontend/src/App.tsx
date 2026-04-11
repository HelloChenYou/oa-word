import { useEffect, useMemo, useState } from "react";
import {
  changePassword,
  createRule,
  createTask,
  deleteRule,
  getCurrentUser,
  getTaskResult,
  getTaskStatus,
  getTemplateDetail,
  listRules,
  listTemplates,
  login,
  updateRule,
  uploadTemplate
} from "./api";
import type { AuthUser, RuleItem, TaskResult, TemplateDetail, TemplateItem } from "./types";

type SectionKey = "rules" | "templates" | "tasks";
type RuleScope = "private" | "public";

const SECTION_ORDER: SectionKey[] = ["rules", "templates", "tasks"];

function getSectionFromHash(hash: string): SectionKey {
  const key = hash.replace("#", "") as SectionKey;
  return SECTION_ORDER.includes(key) ? key : "tasks";
}

function App() {
  const [activeSection, setActiveSection] = useState<SectionKey>(() => getSectionFromHash(window.location.hash));
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [loginUsername, setLoginUsername] = useState("admin");
  const [loginPassword, setLoginPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateDetail | null>(null);

  const [templateName, setTemplateName] = useState("");
  const [templateDocType, setTemplateDocType] = useState("general");
  const [templateFile, setTemplateFile] = useState<File | null>(null);

  const [ownerId, setOwnerId] = useState("demo_user");
  const [rules, setRules] = useState<RuleItem[]>([]);
  const [ruleScope, setRuleScope] = useState<RuleScope>("private");
  const [ruleKind, setRuleKind] = useState("term_replace");
  const [ruleTitle, setRuleTitle] = useState("");
  const [ruleSeverity, setRuleSeverity] = useState("P1");
  const [ruleCategory, setRuleCategory] = useState("style");
  const [rulePattern, setRulePattern] = useState("");
  const [ruleReplacement, setRuleReplacement] = useState("");
  const [ruleReason, setRuleReason] = useState("");
  const [ruleEvidence, setRuleEvidence] = useState("");
  const [ruleEnabled, setRuleEnabled] = useState(true);
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);

  const [text, setText] = useState("请各部门登录OA系统，并上报员工手机号13800138000。");
  const [mode, setMode] = useState<"review" | "rewrite">("review");
  const [scene, setScene] = useState<"general" | "contract" | "announcement" | "tech_doc">("general");
  const [taskId, setTaskId] = useState("");
  const [taskStatus, setTaskStatus] = useState("");
  const [taskResult, setTaskResult] = useState<TaskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const templateOptions = useMemo(
    () => [{ template_id: "", name: "不使用模板" }, ...templates],
    [templates]
  );

  const isAdmin = currentUser?.role === "admin";
  const mustChangePassword = currentUser?.must_change_password ?? false;

  useEffect(() => {
    const onHashChange = () => setActiveSection(getSectionFromHash(window.location.hash));
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    const token = window.localStorage.getItem("auth_access_token");
    if (!token) {
      return;
    }
    getCurrentUser()
      .then((user) => {
        setCurrentUser(user);
        setOwnerId(user.username);
      })
      .catch(() => {
        window.localStorage.removeItem("auth_access_token");
      });
  }, []);

  useEffect(() => {
    if (!currentUser) {
      return;
    }
    if (!isAdmin) {
      setActiveSection("tasks");
      window.location.hash = "tasks";
    }
  }, [currentUser, isAdmin]);

  const navigateTo = (section: SectionKey) => {
    if (!isAdmin && section !== "tasks") {
      return;
    }
    window.location.hash = section;
    setActiveSection(section);
  };

  const resetRuleForm = () => {
    setEditingRuleId(null);
    setRuleKind("term_replace");
    setRuleTitle("");
    setRuleSeverity("P1");
    setRuleCategory("style");
    setRulePattern("");
    setRuleReplacement("");
    setRuleReason("");
    setRuleEvidence("");
    setRuleEnabled(true);
  };

  const fillRuleForm = (rule: RuleItem) => {
    setEditingRuleId(rule.rule_id);
    setRuleScope(rule.scope === "public" ? "public" : "private");
    setRuleKind(rule.kind);
    setRuleTitle(rule.title);
    setRuleSeverity(rule.severity);
    setRuleCategory(rule.category);
    setRulePattern(rule.pattern);
    setRuleReplacement(rule.replacement);
    setRuleReason(rule.reason);
    setRuleEvidence(rule.evidence);
    setRuleEnabled(rule.enabled);
  };

  const loadTemplates = async () => {
    const data = await listTemplates();
    setTemplates(data);
  };

  const loadRules = async () => {
    const data = await listRules({ ownerId, scope: ruleScope });
    setRules(data);
  };

  useEffect(() => {
    if (!currentUser || !isAdmin) {
      return;
    }
    loadTemplates().catch((err) => setMessage(`加载模板失败: ${String(err)}`));
  }, [currentUser, isAdmin]);

  useEffect(() => {
    if (!currentUser || !isAdmin) {
      return;
    }
    loadRules().catch((err) => setMessage(`加载规则失败: ${String(err)}`));
  }, [currentUser, ownerId, ruleScope, isAdmin]);

  useEffect(() => {
    if (!selectedTemplateId || !currentUser || !isAdmin) {
      setSelectedTemplate(null);
      return;
    }
    getTemplateDetail(selectedTemplateId)
      .then(setSelectedTemplate)
      .catch((err) => setMessage(`读取模板详情失败: ${String(err)}`));
  }, [selectedTemplateId, currentUser, isAdmin]);

  const onLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      const resp = await login({ username: loginUsername.trim(), password: loginPassword });
      window.localStorage.setItem("auth_access_token", resp.access_token);
      setCurrentUser(resp.user);
      setOwnerId(resp.user.username);
      setCurrentPassword(loginPassword);
      setLoginPassword("");
      setMessage(`登录成功：${resp.user.username}`);
    } catch (err) {
      setMessage(`登录失败：${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const onPasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.trim().length < 8) {
      setMessage("新密码长度至少 8 位。");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const updated = await changePassword({
        current_password: currentPassword,
        new_password: newPassword.trim()
      });
      setCurrentUser(updated);
      setCurrentPassword("");
      setNewPassword("");
      setMessage("密码修改成功，请继续使用系统。");
    } catch (err) {
      setMessage(`密码修改失败：${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const onLogout = () => {
    window.localStorage.removeItem("auth_access_token");
    setCurrentUser(null);
    setCurrentPassword("");
    setNewPassword("");
    setTaskResult(null);
    setTaskId("");
    setTaskStatus("");
    setRules([]);
    setTemplates([]);
    setSelectedTemplate(null);
    setMessage("已退出登录。");
  };

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

  const onSubmitRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruleTitle.trim() || !rulePattern.trim() || !ruleReason.trim() || !ruleEvidence.trim()) {
      setMessage("请完整填写规则标题、匹配内容、原因和依据。");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const payload = {
        scope: ruleScope,
        kind: ruleKind,
        title: ruleTitle.trim(),
        severity: ruleSeverity,
        category: ruleCategory,
        pattern: rulePattern.trim(),
        replacement: ruleReplacement.trim(),
        reason: ruleReason.trim(),
        evidence: ruleEvidence.trim(),
        enabled: ruleEnabled
      };
      const scopedOwnerId = ruleScope === "private" ? ownerId : undefined;
      if (editingRuleId) {
        await updateRule(editingRuleId, payload, scopedOwnerId);
        setMessage(`规则更新成功: ${editingRuleId}`);
      } else {
        await createRule({ owner_id: scopedOwnerId, ...payload });
        setMessage("规则创建成功。");
      }
      resetRuleForm();
      await loadRules();
    } catch (err) {
      setMessage(`规则保存失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const onDeleteRule = async (rule: RuleItem) => {
    setLoading(true);
    setMessage("");
    try {
      await deleteRule(rule.rule_id, rule.scope === "private" ? ownerId : undefined);
      if (editingRuleId === rule.rule_id) {
        resetRuleForm();
      }
      setMessage(`规则删除成功: ${rule.rule_id}`);
      await loadRules();
    } catch (err) {
      setMessage(`规则删除失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const onToggleRule = async (rule: RuleItem) => {
    setLoading(true);
    setMessage("");
    try {
      await updateRule(rule.rule_id, { enabled: !rule.enabled }, rule.scope === "private" ? ownerId : undefined);
      if (editingRuleId === rule.rule_id) {
        setRuleEnabled(!rule.enabled);
      }
      setMessage(`规则已${rule.enabled ? "停用" : "启用"}: ${rule.rule_id}`);
      await loadRules();
    } catch (err) {
      setMessage(`切换规则状态失败: ${String(err)}`);
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
        owner_id: ownerId.trim() || undefined,
        ...(selectedTemplateId ? { template_id: selectedTemplateId } : {})
      };
      const resp = await createTask(payload);
      setTaskId(resp.task_id);
      setTaskStatus(resp.status);
      setMessage(`任务已创建: ${resp.task_id}`);
      navigateTo("tasks");
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

  if (!currentUser) {
    return (
      <div className="page">
        <section className="card auth-card">
          <h1>OA 文稿校对平台</h1>
          <p>请先登录后再访问系统。</p>
          <form onSubmit={onLogin} className="grid">
            <label>
              用户名
              <input value={loginUsername} onChange={(e) => setLoginUsername(e.target.value)} />
            </label>
            <label>
              密码
              <input type="password" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} />
            </label>
            <div className="actions full">
              <button type="submit" disabled={loading}>
                登录
              </button>
            </div>
          </form>
          {message && <div className="toast">{message}</div>}
        </section>
      </div>
    );
  }

  if (mustChangePassword) {
    return (
      <div className="page">
        <section className="card auth-card">
          <h1>首次登录请修改密码</h1>
          <p>当前账号使用的是初始化密码，继续使用前必须先修改。</p>
          <form onSubmit={onPasswordChange} className="grid">
            <label>
              当前密码
              <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
            </label>
            <label>
              新密码
              <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            </label>
            <div className="actions full">
              <button type="submit" disabled={loading}>
                修改密码
              </button>
              <button type="button" onClick={onLogout} disabled={loading}>
                退出登录
              </button>
            </div>
          </form>
          {message && <div className="toast">{message}</div>}
        </section>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="hero">
        <div>
          <h1>AI 公文助手管理台</h1>
          <p>
            当前用户：{currentUser.username}，角色：{currentUser.role}
          </p>
        </div>
        <div className="hero-side">
          <nav className="topnav">
            {isAdmin && (
              <>
                <button type="button" className={activeSection === "rules" ? "nav-btn active" : "nav-btn"} onClick={() => navigateTo("rules")}>
                  规则管理
                </button>
                <button type="button" className={activeSection === "templates" ? "nav-btn active" : "nav-btn"} onClick={() => navigateTo("templates")}>
                  模板管理
                </button>
              </>
            )}
            <button type="button" className={activeSection === "tasks" ? "nav-btn active" : "nav-btn"} onClick={() => navigateTo("tasks")}>
              任务管理
            </button>
          </nav>
          <div className="auth-panel">
            <button type="button" onClick={onLogout}>
              退出登录
            </button>
          </div>
        </div>
      </header>

      {isAdmin && activeSection === "rules" && (
        <section id="rules" className="card">
          <h2>规则管理</h2>
          <form onSubmit={onSubmitRule} className="grid">
            <label>
              Owner ID
              <input value={ownerId} onChange={(e) => setOwnerId(e.target.value)} placeholder="例如 demo_user" />
            </label>
            <label>
              规则作用域
              <select value={ruleScope} onChange={(e) => setRuleScope(e.target.value as RuleScope)}>
                <option value="private">private</option>
                <option value="public">public</option>
              </select>
            </label>
            <label>
              规则类型
              <select value={ruleKind} onChange={(e) => setRuleKind(e.target.value)}>
                <option value="term_replace">term_replace</option>
                <option value="regex_mask">regex_mask</option>
              </select>
            </label>
            <label>
              标题
              <input value={ruleTitle} onChange={(e) => setRuleTitle(e.target.value)} placeholder="例如 部门术语统一" />
            </label>
            <label>
              严重级别
              <select value={ruleSeverity} onChange={(e) => setRuleSeverity(e.target.value)}>
                <option value="P0">P0</option>
                <option value="P1">P1</option>
                <option value="P2">P2</option>
              </select>
            </label>
            <label>
              分类
              <select value={ruleCategory} onChange={(e) => setRuleCategory(e.target.value)}>
                <option value="style">style</option>
                <option value="terminology">terminology</option>
                <option value="compliance">compliance</option>
                <option value="grammar">grammar</option>
                <option value="structure">structure</option>
              </select>
            </label>
            <label>
              匹配内容
              <input value={rulePattern} onChange={(e) => setRulePattern(e.target.value)} placeholder="例如 登陆" />
            </label>
            <label>
              替换内容
              <input value={ruleReplacement} onChange={(e) => setRuleReplacement(e.target.value)} placeholder="例如 登录" />
            </label>
            <label className="full">
              原因
              <input value={ruleReason} onChange={(e) => setRuleReason(e.target.value)} placeholder="说明为什么需要提示" />
            </label>
            <label className="full">
              依据
              <input value={ruleEvidence} onChange={(e) => setRuleEvidence(e.target.value)} placeholder="例如 private_rule:demo_user:login" />
            </label>
            <label className="checkbox">
              <input type="checkbox" checked={ruleEnabled} onChange={(e) => setRuleEnabled(e.target.checked)} />
              规则启用
            </label>
            <div className="actions full">
              <button type="submit" disabled={loading}>
                {editingRuleId ? "保存修改" : "新增规则"}
              </button>
              <button type="button" onClick={resetRuleForm} disabled={loading}>
                {editingRuleId ? "取消编辑" : "重置表单"}
              </button>
            </div>
          </form>

          <div className="block">
            <h3>当前规则</h3>
            {!rules.length && <p>当前筛选条件下暂无规则。</p>}
            {!!rules.length && (
              <table>
                <thead>
                  <tr>
                    <th>rule_id</th>
                    <th>scope</th>
                    <th>title</th>
                    <th>pattern</th>
                    <th>replacement</th>
                    <th>状态</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => (
                    <tr key={rule.rule_id}>
                      <td>{rule.rule_id}</td>
                      <td>{rule.scope}</td>
                      <td>{rule.title}</td>
                      <td>{rule.pattern}</td>
                      <td>{rule.replacement || "-"}</td>
                      <td>{rule.enabled ? "启用" : "停用"}</td>
                      <td className="table-actions">
                        <button type="button" onClick={() => fillRuleForm(rule)} disabled={loading}>
                          编辑
                        </button>
                        <button type="button" onClick={() => onToggleRule(rule)} disabled={loading}>
                          {rule.enabled ? "停用" : "启用"}
                        </button>
                        <button type="button" onClick={() => onDeleteRule(rule)} disabled={loading}>
                          删除
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      )}

      {isAdmin && activeSection === "templates" && (
        <section id="templates" className="card">
          <h2>模板管理</h2>
          <form onSubmit={onUploadTemplate} className="grid">
            <label>
              模板名称
              <input value={templateName} onChange={(e) => setTemplateName(e.target.value)} placeholder="例如 通知模板" />
            </label>
            <label>
              模板类型
              <input value={templateDocType} onChange={(e) => setTemplateDocType(e.target.value)} placeholder="general/notice/..." />
            </label>
            <label>
              模板文件
              <input type="file" accept=".docx,.txt,.md" onChange={(e) => setTemplateFile(e.target.files?.[0] ?? null)} />
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
          </div>

          {selectedTemplate && (
            <div className="block">
              <h3>模板解析结果</h3>
              <pre>{JSON.stringify(selectedTemplate.parsed, null, 2)}</pre>
            </div>
          )}
        </section>
      )}

      {activeSection === "tasks" && (
        <>
          <section id="tasks" className="card">
            <h2>任务管理</h2>
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
                <select value={scene} onChange={(e) => setScene(e.target.value as "general" | "contract" | "announcement" | "tech_doc")}>
                  <option value="general">general</option>
                  <option value="contract">contract</option>
                  <option value="announcement">announcement</option>
                  <option value="tech_doc">tech_doc</option>
                </select>
              </label>
              <label>
                任务 Owner ID
                <input value={ownerId} onChange={(e) => setOwnerId(e.target.value)} disabled={!isAdmin} placeholder={currentUser.username} />
              </label>
              <label className="full">
                文本内容
                <textarea value={text} onChange={(e) => setText(e.target.value)} rows={7} />
              </label>
              <div className="actions full">
                <button type="submit" disabled={loading}>
                  创建任务
                </button>
                <button type="button" onClick={pollTask} disabled={loading || !taskId}>
                  查询任务状态/结果
                </button>
              </div>
            </form>

            <div className="block">
              <div>任务 ID: {taskId || "-"}</div>
              <div>任务状态: {taskStatus || "-"}</div>
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
        </>
      )}

      {message && <div className="toast">{message}</div>}
    </div>
  );
}

export default App;
