import { useEffect, useState } from "react";
import {
  changePassword,
  createRule,
  createTask,
  createUser,
  deleteKnowledge,
  deleteRule,
  getCurrentUser,
  getKnowledgeDetail,
  getTaskResult,
  getTaskStatus,
  getTemplateDetail,
  listKnowledge,
  listRules,
  listTemplates,
  listUsers,
  login,
  resetUserPassword,
  updateKnowledge,
  updateRule,
  updateUser,
  uploadKnowledge,
  uploadTemplate
} from "./api";
import type { AuthUser, KnowledgeDetail, KnowledgeItem, RuleItem, TaskResult, TemplateDetail, TemplateItem, UserItem } from "./types";

type SectionKey = "users" | "personalRules" | "publicRules" | "templates" | "knowledge" | "tasks";
type RuleScope = "private" | "public";
type UserRole = "admin" | "operator";

const ALL_SECTIONS: SectionKey[] = ["personalRules", "publicRules", "tasks"];
const ADMIN_SECTIONS: SectionKey[] = ["users", "personalRules", "publicRules", "templates", "knowledge", "tasks"];

function getInitialSection(): SectionKey {
  const hash = window.location.hash.replace("#", "");
  return [...ADMIN_SECTIONS, ...ALL_SECTIONS].includes(hash as SectionKey) ? (hash as SectionKey) : "tasks";
}

function App() {
  const [activeSection, setActiveSection] = useState<SectionKey>(getInitialSection);
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const [loginUsername, setLoginUsername] = useState("admin");
  const [loginPassword, setLoginPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const [users, setUsers] = useState<UserItem[]>([]);
  const [userUsername, setUserUsername] = useState("");
  const [userPassword, setUserPassword] = useState("");
  const [userRole, setUserRole] = useState<UserRole>("operator");
  const [userEnabled, setUserEnabled] = useState(true);
  const [userMustChangePassword, setUserMustChangePassword] = useState(true);
  const [editingUsername, setEditingUsername] = useState<string | null>(null);
  const [resetPasswordValue, setResetPasswordValue] = useState("");
  const [userModalOpen, setUserModalOpen] = useState(false);

  const [ownerId, setOwnerId] = useState("demo_user");
  const [rules, setRules] = useState<RuleItem[]>([]);
  const [ruleKeyword, setRuleKeyword] = useState("");
  const [ruleScope, setRuleScope] = useState<RuleScope>("private");
  const [ruleKind, setRuleKind] = useState("term_replace");
  const [ruleTitle, setRuleTitle] = useState("");
  const [ruleSeverity, setRuleSeverity] = useState("P1");
  const [ruleCategory, setRuleCategory] = useState("style");
  const [rulePattern, setRulePattern] = useState("");
  const [ruleReplacement, setRuleReplacement] = useState("");
  const [ruleReason, setRuleReason] = useState("");
  const [ruleEnabled, setRuleEnabled] = useState(true);
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);
  const [ruleModalOpen, setRuleModalOpen] = useState(false);

  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateDetail | null>(null);
  const [templateName, setTemplateName] = useState("");
  const [templateDocType, setTemplateDocType] = useState("general");
  const [templateFile, setTemplateFile] = useState<File | null>(null);

  const [knowledgeItems, setKnowledgeItems] = useState<KnowledgeItem[]>([]);
  const [knowledgeKeyword, setKnowledgeKeyword] = useState("");
  const [knowledgeEnabledFilter, setKnowledgeEnabledFilter] = useState<"all" | "enabled" | "disabled">("all");
  const [selectedKnowledge, setSelectedKnowledge] = useState<KnowledgeDetail | null>(null);
  const [knowledgeName, setKnowledgeName] = useState("");
  const [knowledgeDocType, setKnowledgeDocType] = useState("general");
  const [knowledgeFile, setKnowledgeFile] = useState<File | null>(null);
  const [knowledgeRawText, setKnowledgeRawText] = useState("");
  const [editingKnowledgeId, setEditingKnowledgeId] = useState<string | null>(null);
  const [knowledgeEnabled, setKnowledgeEnabled] = useState(true);
  const [knowledgeModalOpen, setKnowledgeModalOpen] = useState(false);

  const [text, setText] = useState("请各部门登录OA系统，并上报员工手机号13800138000。");
  const [mode, setMode] = useState<"review" | "rewrite">("review");
  const [scene, setScene] = useState<"general" | "contract" | "announcement" | "tech_doc">("general");
  const [taskId, setTaskId] = useState("");
  const [taskStatus, setTaskStatus] = useState("");
  const [taskResult, setTaskResult] = useState<TaskResult | null>(null);

  const isAdmin = currentUser?.role === "admin";
  const mustChangePassword = currentUser?.must_change_password ?? false;
  const canModifyActiveRules = activeSection === "personalRules" || isAdmin;
  const enabledUserCount = users.filter((user) => user.enabled).length;
  const enabledRuleCount = rules.filter((rule) => rule.enabled).length;
  const privateRuleCount = rules.filter((rule) => rule.scope === "private").length;
  const publicRuleCount = rules.filter((rule) => rule.scope === "public").length;
  const resultIssueCount = taskResult?.issues.length ?? 0;
  const resultRagHitCount = taskResult?.rag_hits?.length ?? 0;
  const enabledKnowledgeCount = knowledgeItems.filter((item) => item.enabled).length;
  const knowledgeChunkCount = knowledgeItems.reduce((total, item) => total + item.chunk_count, 0);

  useEffect(() => {
    const onHashChange = () => setActiveSection(getInitialSection());
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
        setOwnerId(user.role === "admin" ? "" : user.username);
      })
      .catch(() => {
        window.localStorage.removeItem("auth_access_token");
      });
  }, []);

  useEffect(() => {
    if (!currentUser) {
      return;
    }
    if (!isAdmin && !ALL_SECTIONS.includes(activeSection)) {
      navigateTo("tasks");
    }
  }, [activeSection, currentUser, isAdmin]);

  useEffect(() => {
    if (!currentUser) {
      return;
    }
    void loadRules();
    if (!isAdmin) {
      return;
    }
    void loadUsers();
    void loadTemplates();
    void loadKnowledge();
  }, [currentUser, isAdmin]);

  useEffect(() => {
    if (!currentUser) {
      return;
    }
    void loadRules();
  }, [activeSection, ownerId, ruleKeyword, currentUser, isAdmin]);

  useEffect(() => {
    if (!selectedTemplateId || !currentUser || !isAdmin) {
      setSelectedTemplate(null);
      return;
    }
    getTemplateDetail(selectedTemplateId)
      .then(setSelectedTemplate)
      .catch((err) => setMessage(`读取模板详情失败: ${String(err)}`));
  }, [selectedTemplateId, currentUser, isAdmin]);

  useEffect(() => {
    if (!currentUser || !isAdmin) {
      return;
    }
    void loadKnowledge();
  }, [knowledgeKeyword, knowledgeEnabledFilter, currentUser, isAdmin]);

  const navigateTo = (section: SectionKey) => {
    if (!isAdmin && !ALL_SECTIONS.includes(section)) {
      return;
    }
    window.location.hash = section;
    setActiveSection(section);
  };

  const resetUserForm = () => {
    setEditingUsername(null);
    setUserUsername("");
    setUserPassword("");
    setUserRole("operator");
    setUserEnabled(true);
    setUserMustChangePassword(true);
    setUserModalOpen(false);
  };

  const fillUserForm = (user: UserItem) => {
    setEditingUsername(user.username);
    setUserUsername(user.username);
    setUserPassword("");
    setUserRole(user.role as UserRole);
    setUserEnabled(user.enabled);
    setUserMustChangePassword(user.must_change_password);
    setUserModalOpen(true);
  };

  const openCreateUserModal = () => {
    resetUserForm();
    setUserModalOpen(true);
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
    setRuleEnabled(true);
    setRuleModalOpen(false);
  };

  const fillRuleForm = (rule: RuleItem) => {
    setEditingRuleId(rule.rule_id);
    if (rule.owner_id) {
      setOwnerId(rule.owner_id);
    }
    setRuleScope(rule.scope === "public" ? "public" : "private");
    setRuleKind(rule.kind);
    setRuleTitle(rule.title);
    setRuleSeverity(rule.severity);
    setRuleCategory(rule.category);
    setRulePattern(rule.pattern);
    setRuleReplacement(rule.replacement);
    setRuleReason(rule.reason);
    setRuleEnabled(rule.enabled);
    setRuleModalOpen(true);
  };

  const openCreateRuleModal = () => {
    resetRuleForm();
    setRuleModalOpen(true);
  };

  const resetKnowledgeForm = () => {
    setEditingKnowledgeId(null);
    setKnowledgeName("");
    setKnowledgeDocType("general");
    setKnowledgeFile(null);
    setKnowledgeRawText("");
    setKnowledgeEnabled(true);
    setKnowledgeModalOpen(false);
  };

  const openCreateKnowledgeModal = () => {
    resetKnowledgeForm();
    setKnowledgeModalOpen(true);
  };

  const fillKnowledgeForm = async (item: KnowledgeItem) => {
    setLoading(true);
    setMessage("");
    try {
      const detail = await getKnowledgeDetail(item.document_id);
      setSelectedKnowledge(detail);
      setEditingKnowledgeId(detail.document_id);
      setKnowledgeName(detail.name);
      setKnowledgeDocType(detail.doc_type);
      setKnowledgeRawText(detail.raw_text);
      setKnowledgeEnabled(detail.enabled);
      setKnowledgeFile(null);
      setKnowledgeModalOpen(true);
    } catch (err) {
      setMessage(`读取知识库详情失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      setUsers(await listUsers());
    } catch (err) {
      setMessage(`加载用户失败: ${String(err)}`);
    }
  };

  const loadRules = async () => {
    try {
      const isPublicPage = activeSection === "publicRules";
      setRules(
        await listRules({
          scope: isPublicPage ? "public" : "private",
          ownerId: isPublicPage ? undefined : isAdmin ? ownerId.trim() || undefined : currentUser?.username,
          keyword: ruleKeyword.trim() || undefined
        })
      );
    } catch (err) {
      setMessage(`加载规则失败: ${String(err)}`);
    }
  };

  const loadTemplates = async () => {
    try {
      setTemplates(await listTemplates());
    } catch (err) {
      setMessage(`加载模板失败: ${String(err)}`);
    }
  };

  const loadKnowledge = async () => {
    try {
      setKnowledgeItems(
        await listKnowledge({
          keyword: knowledgeKeyword.trim() || undefined,
          enabled:
            knowledgeEnabledFilter === "all"
              ? undefined
              : knowledgeEnabledFilter === "enabled"
        })
      );
    } catch (err) {
      setMessage(`加载知识库失败: ${String(err)}`);
    }
  };

  const onLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      const resp = await login({ username: loginUsername.trim(), password: loginPassword });
      window.localStorage.setItem("auth_access_token", resp.access_token);
      setCurrentUser(resp.user);
      setOwnerId(resp.user.role === "admin" ? "" : resp.user.username);
      setCurrentPassword(loginPassword);
      setLoginPassword("");
      setMessage(`登录成功: ${resp.user.username}`);
      navigateTo(resp.user.role === "admin" ? "users" : "tasks");
    } catch (err) {
      setMessage(`登录失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const onPasswordChange = async (event: React.FormEvent) => {
    event.preventDefault();
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
      window.localStorage.setItem("auth_access_token", updated.access_token);
      setCurrentUser(updated.user);
      setCurrentPassword("");
      setNewPassword("");
      setMessage("密码修改成功。");
    } catch (err) {
      setMessage(`密码修改失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const onLogout = () => {
    window.localStorage.removeItem("auth_access_token");
    setCurrentUser(null);
    setUsers([]);
    setRules([]);
    setTemplates([]);
    setKnowledgeItems([]);
    setSelectedTemplate(null);
    setSelectedKnowledge(null);
    setTaskResult(null);
    setTaskId("");
    setTaskStatus("");
    setCurrentPassword("");
    setNewPassword("");
    resetUserForm();
    resetRuleForm();
    resetKnowledgeForm();
    setMessage("已退出登录。");
  };

  const onSubmitUser = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!userUsername.trim()) {
      setMessage("请输入用户名。");
      return;
    }
    if (!editingUsername && userPassword.trim().length < 8) {
      setMessage("新建用户时密码长度至少 8 位。");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      if (editingUsername) {
        await updateUser(editingUsername, {
          role: userRole,
          enabled: userEnabled,
          must_change_password: userMustChangePassword
        });
        setMessage(`用户更新成功: ${editingUsername}`);
      } else {
        await createUser({
          username: userUsername.trim(),
          password: userPassword.trim(),
          role: userRole,
          enabled: userEnabled,
          must_change_password: userMustChangePassword
        });
        setMessage(`用户创建成功: ${userUsername.trim()}`);
      }
      resetUserForm();
      await loadUsers();
    } catch (err) {
      setMessage(`用户保存失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const onToggleUserEnabled = async (user: UserItem) => {
    setLoading(true);
    setMessage("");
    try {
      await updateUser(user.username, { enabled: !user.enabled });
      if (editingUsername === user.username) {
        setUserEnabled(!user.enabled);
      }
      setMessage(`用户状态已更新: ${user.username}`);
      await loadUsers();
    } catch (err) {
      setMessage(`更新用户状态失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const onToggleUserPasswordFlag = async (user: UserItem) => {
    setLoading(true);
    setMessage("");
    try {
      await updateUser(user.username, { must_change_password: !user.must_change_password });
      if (editingUsername === user.username) {
        setUserMustChangePassword(!user.must_change_password);
      }
      setMessage(`强制改密标记已更新: ${user.username}`);
      await loadUsers();
    } catch (err) {
      setMessage(`更新改密标记失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const onResetUserPassword = async (username: string) => {
    if (resetPasswordValue.trim().length < 8) {
      setMessage("重置密码长度至少 8 位。");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      await resetUserPassword(username, {
        new_password: resetPasswordValue.trim(),
        must_change_password: true
      });
      setResetPasswordValue("");
      setMessage(`密码已重置: ${username}`);
      await loadUsers();
    } catch (err) {
      setMessage(`重置密码失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const onUploadTemplate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!templateFile || !templateName.trim()) {
      setMessage("请填写模板名称并选择模板文件。");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const resp = await uploadTemplate({
        name: templateName.trim(),
        docType: templateDocType,
        file: templateFile
      });
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

  const onTemplateFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setTemplateFile(file);
    if (file && !templateName.trim()) {
      const defaultName = file.name.replace(/\.[^/.]+$/, "");
      setTemplateName(defaultName || file.name);
    }
  };

  const onKnowledgeFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setKnowledgeFile(file);
    if (file && !knowledgeName.trim()) {
      const defaultName = file.name.replace(/\.[^/.]+$/, "");
      setKnowledgeName(defaultName || file.name);
    }
  };

  const onSubmitKnowledge = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!knowledgeName.trim()) {
      setMessage("请填写知识库名称。");
      return;
    }
    if (!editingKnowledgeId && !knowledgeFile) {
      setMessage("新增知识库时必须选择文件。");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      if (editingKnowledgeId) {
        const updated = await updateKnowledge(editingKnowledgeId, {
          name: knowledgeName.trim(),
          doc_type: knowledgeDocType.trim(),
          enabled: knowledgeEnabled,
          raw_text: knowledgeRawText.trim()
        });
        setSelectedKnowledge(updated);
        setMessage(`知识库已更新: ${updated.name}`);
      } else if (knowledgeFile) {
        const created = await uploadKnowledge({
          name: knowledgeName.trim(),
          docType: knowledgeDocType.trim(),
          file: knowledgeFile
        });
        setMessage(`知识库上传成功: ${created.document_id}`);
      }
      resetKnowledgeForm();
      await loadKnowledge();
    } catch (err) {
      setMessage(`知识库保存失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const onToggleKnowledge = async (item: KnowledgeItem) => {
    setLoading(true);
    setMessage("");
    try {
      await updateKnowledge(item.document_id, { enabled: !item.enabled });
      setMessage(`知识库状态已更新: ${item.name}`);
      await loadKnowledge();
    } catch (err) {
      setMessage(`更新知识库状态失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const onDeleteKnowledge = async (item: KnowledgeItem) => {
    setLoading(true);
    setMessage("");
    try {
      await deleteKnowledge(item.document_id);
      if (selectedKnowledge?.document_id === item.document_id) {
        setSelectedKnowledge(null);
      }
      setMessage(`知识库已删除: ${item.name}`);
      await loadKnowledge();
    } catch (err) {
      setMessage(`删除知识库失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const onSubmitRule = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!ruleTitle.trim() || !rulePattern.trim() || !ruleReason.trim()) {
      setMessage("请完整填写规则标题、匹配内容和原因。");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const isPublicPage = activeSection === "publicRules";
      const scope = isPublicPage ? "public" : "private";
      const payload = {
        scope,
        kind: ruleKind,
        title: ruleTitle.trim(),
        severity: ruleSeverity,
        category: ruleCategory,
        pattern: rulePattern.trim(),
        replacement: ruleReplacement.trim(),
        reason: ruleReason.trim(),
        enabled: ruleEnabled
      };
      const scopedOwnerId = scope === "private" ? (isAdmin ? ownerId.trim() || undefined : currentUser?.username) : undefined;
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
      await deleteRule(rule.rule_id, rule.scope === "private" ? rule.owner_id || ownerId.trim() || undefined : undefined);
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
      await updateRule(
        rule.rule_id,
        { enabled: !rule.enabled },
        rule.scope === "private" ? rule.owner_id || ownerId.trim() || undefined : undefined
      );
      if (editingRuleId === rule.rule_id) {
        setRuleEnabled(!rule.enabled);
      }
      setMessage(`规则状态已更新: ${rule.rule_id}`);
      await loadRules();
    } catch (err) {
      setMessage(`规则状态更新失败: ${String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const onCreateTask = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!text.trim()) {
      setMessage("请输入待校对文本。");
      return;
    }
    setLoading(true);
    setMessage("");
    setTaskResult(null);
    try {
      const resp = await createTask({
        text: text.trim(),
        mode,
        scene,
        owner_id: isAdmin ? ownerId.trim() || undefined : currentUser?.username,
        template_id: selectedTemplateId || undefined
      });
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
        setTaskResult(await getTaskResult(taskId));
      }
      if (statusResp.status === "failed") {
        setMessage(statusResp.error_msg || "任务执行失败。");
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
              <input value={loginUsername} onChange={(event) => setLoginUsername(event.target.value)} />
            </label>
            <label>
              密码
              <input type="password" value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} />
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
          <h1>首次登录需要修改密码</h1>
          <p>当前账号仍在使用初始密码，继续使用前必须先修改。</p>
          <form onSubmit={onPasswordChange} className="grid">
            <label>
              当前密码
              <input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />
            </label>
            <label>
              新密码
              <input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
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
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">OA</span>
          <div>
            <strong>AI 公文助手</strong>
            <small>Proofread Console</small>
          </div>
        </div>
        <nav className="topnav">
          {isAdmin && (
            <button type="button" className={activeSection === "users" ? "nav-btn active" : "nav-btn"} onClick={() => navigateTo("users")}>
              用户管理
            </button>
          )}
          <button
            type="button"
            className={activeSection === "personalRules" ? "nav-btn active" : "nav-btn"}
            onClick={() => navigateTo("personalRules")}
          >
            个人规则
          </button>
          <button
            type="button"
            className={activeSection === "publicRules" ? "nav-btn active" : "nav-btn"}
            onClick={() => navigateTo("publicRules")}
          >
            公共规则
          </button>
          {isAdmin && (
            <button
              type="button"
              className={activeSection === "templates" ? "nav-btn active" : "nav-btn"}
              onClick={() => navigateTo("templates")}
            >
              模板管理
            </button>
          )}
          {isAdmin && (
            <button
              type="button"
              className={activeSection === "knowledge" ? "nav-btn active" : "nav-btn"}
              onClick={() => navigateTo("knowledge")}
            >
              知识库
            </button>
          )}
          <button type="button" className={activeSection === "tasks" ? "nav-btn active" : "nav-btn"} onClick={() => navigateTo("tasks")}>
            校对任务
          </button>
        </nav>
        <div className="sidebar-foot">
          <span>运行状态</span>
          <strong>Online</strong>
        </div>
      </aside>
      <main className="workspace">
        <header className="topbar">
          <div>
            <h1>AI 公文助手管理台</h1>
            <p>规则、模板、任务与用户的一体化管理面板</p>
          </div>
          <div className="userbar">
            <div className="user-avatar">{currentUser.username.slice(0, 1).toUpperCase()}</div>
            <div className="user-meta">
              <strong>{currentUser.username}</strong>
              <span>{currentUser.role}</span>
            </div>
            <button type="button" onClick={onLogout}>
              退出
            </button>
          </div>
        </header>
      {isAdmin && activeSection === "users" && (
        <section id="users" className="card">
          <h2>用户管理</h2>
          <p className="section-desc">管理后台账号、角色、启停状态和首次登录改密策略。</p>
          <div className="stats">
            <div className="stat-card">
              <span>账号总数</span>
              <strong>{users.length}</strong>
            </div>
            <div className="stat-card">
              <span>启用账号</span>
              <strong>{enabledUserCount}</strong>
            </div>
            <div className="stat-card">
              <span>需改密</span>
              <strong>{users.filter((user) => user.must_change_password).length}</strong>
            </div>
          </div>
          <div className="page-actions">
            <button type="button" onClick={openCreateUserModal} disabled={loading}>
              新增用户
            </button>
          </div>

          <div className="block">
            <h3>用户列表</h3>
            <label className="full">
              重置密码
              <input
                type="password"
                value={resetPasswordValue}
                onChange={(event) => setResetPasswordValue(event.target.value)}
                placeholder="输入新密码后点击某一行的“重置密码”"
              />
            </label>
            {!users.length && <p>暂无用户数据。</p>}
            {!!users.length && (
              <table>
                <thead>
                  <tr>
                    <th>用户名</th>
                    <th>角色</th>
                    <th>状态</th>
                    <th>强制改密</th>
                    <th>创建时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.username}>
                      <td>{user.username}</td>
                      <td>{user.role}</td>
                      <td>{user.enabled ? "启用" : "停用"}</td>
                      <td>{user.must_change_password ? "是" : "否"}</td>
                      <td>{user.created_at}</td>
                      <td className="table-actions">
                        <button type="button" onClick={() => fillUserForm(user)} disabled={loading}>
                          编辑
                        </button>
                        <button type="button" onClick={() => onToggleUserEnabled(user)} disabled={loading}>
                          {user.enabled ? "停用" : "启用"}
                        </button>
                        <button type="button" onClick={() => onToggleUserPasswordFlag(user)} disabled={loading}>
                          {user.must_change_password ? "取消强制改密" : "强制改密"}
                        </button>
                        <button type="button" onClick={() => onResetUserPassword(user.username)} disabled={loading}>
                          重置密码
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

      {(activeSection === "personalRules" || activeSection === "publicRules") && (
        <section id="rules" className="card">
          <h2>{activeSection === "publicRules" ? "公共规则" : "个人规则"}</h2>
          <p className="section-desc">
            {activeSection === "publicRules"
              ? "公共规则对所有用户生效，只有管理员可以维护。"
              : isAdmin
                ? "管理员可以查看和维护所有用户的个人规则，也可以按用户名称过滤。"
                : "个人规则只对当前账号生效，其他用户无法查看或修改。"}
          </p>
          <div className="stats">
            <div className="stat-card">
              <span>当前结果</span>
              <strong>{rules.length}</strong>
            </div>
            <div className="stat-card">
              <span>已启用</span>
              <strong>{enabledRuleCount}</strong>
            </div>
            <div className="stat-card">
              <span>{activeSection === "publicRules" ? "公共规则" : "个人规则"}</span>
              <strong>{activeSection === "publicRules" ? publicRuleCount : privateRuleCount}</strong>
            </div>
          </div>
          <div className="grid">
            {activeSection === "personalRules" && isAdmin && (
              <label>
                用户名称
                <input value={ownerId} onChange={(event) => setOwnerId(event.target.value)} placeholder="留空查看全部用户" />
              </label>
            )}
            <label>
              搜索
              <input value={ruleKeyword} onChange={(event) => setRuleKeyword(event.target.value)} placeholder="按标题、匹配内容、依据搜索" />
            </label>
          </div>
          {canModifyActiveRules && (
            <div className="page-actions">
              <button type="button" onClick={openCreateRuleModal} disabled={loading}>
                新增{activeSection === "publicRules" ? "公共" : "个人"}规则
              </button>
            </div>
          )}

          <div className="block">
            <h3>规则列表</h3>
            {!rules.length && <p>当前条件下暂无规则。</p>}
            {!!rules.length && (
              <table>
                <thead>
                  <tr>
                    <th>rule_id</th>
                    <th>用户名称</th>
                    <th>scope</th>
                    <th>title</th>
                    <th>pattern</th>
                    <th>replacement</th>
                    <th>evidence</th>
                    <th>状态</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => (
                    <tr key={rule.rule_id}>
                      <td>{rule.rule_id}</td>
                      <td>{rule.owner_id || "-"}</td>
                      <td>{rule.scope}</td>
                      <td>{rule.title}</td>
                      <td>{rule.pattern}</td>
                      <td>{rule.replacement || "-"}</td>
                      <td>{rule.evidence}</td>
                      <td>{rule.enabled ? "启用" : "停用"}</td>
                      <td className="table-actions">
                        {(rule.scope === "private" || isAdmin) && (
                          <>
                            <button type="button" onClick={() => fillRuleForm(rule)} disabled={loading}>
                              编辑
                            </button>
                            <button type="button" onClick={() => onToggleRule(rule)} disabled={loading}>
                              {rule.enabled ? "停用" : "启用"}
                            </button>
                            <button type="button" onClick={() => onDeleteRule(rule)} disabled={loading}>
                              删除
                            </button>
                          </>
                        )}
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
          <p className="section-desc">上传并解析文稿模板，模板中的章节结构会参与后续校对。</p>
          <div className="stats">
            <div className="stat-card">
              <span>模板数量</span>
              <strong>{templates.length}</strong>
            </div>
            <div className="stat-card">
              <span>当前选择</span>
              <strong>{selectedTemplateId ? "已选择" : "无模板"}</strong>
            </div>
          </div>
          <form onSubmit={onUploadTemplate} className="grid">
            <label>
              模板名称
              <input value={templateName} onChange={(event) => setTemplateName(event.target.value)} placeholder="例如 通知模板" />
            </label>
            <label>
              模板类型
              <input value={templateDocType} onChange={(event) => setTemplateDocType(event.target.value)} placeholder="general/notice/..." />
            </label>
            <label>
              模板文件
              <input type="file" accept=".docx,.txt,.md" onChange={onTemplateFileChange} />
            </label>
            <div className="actions">
              <button type="submit" disabled={loading}>
                上传模板
              </button>
            </div>
          </form>

          <div className="row">
            <label>
              选择模板
              <select value={selectedTemplateId} onChange={(event) => setSelectedTemplateId(event.target.value)}>
                <option value="">不使用模板</option>
                {templates.map((item) => (
                  <option key={item.template_id} value={item.template_id}>
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

      {isAdmin && activeSection === "knowledge" && (
        <section id="knowledge" className="card">
          <h2>知识库</h2>
          <p className="section-desc">管理 RAG 检索资料，已启用的知识片段会在校对时注入给大模型作为参考依据。</p>
          <div className="stats">
            <div className="stat-card">
              <span>文档数量</span>
              <strong>{knowledgeItems.length}</strong>
            </div>
            <div className="stat-card">
              <span>已启用</span>
              <strong>{enabledKnowledgeCount}</strong>
            </div>
            <div className="stat-card">
              <span>切片数量</span>
              <strong>{knowledgeChunkCount}</strong>
            </div>
          </div>
          <div className="grid">
            <label>
              搜索
              <input
                value={knowledgeKeyword}
                onChange={(event) => setKnowledgeKeyword(event.target.value)}
                placeholder="按名称、类型、正文内容搜索"
              />
            </label>
            <label>
              状态
              <select value={knowledgeEnabledFilter} onChange={(event) => setKnowledgeEnabledFilter(event.target.value as "all" | "enabled" | "disabled")}>
                <option value="all">全部</option>
                <option value="enabled">仅启用</option>
                <option value="disabled">仅停用</option>
              </select>
            </label>
          </div>
          <div className="page-actions">
            <button type="button" onClick={openCreateKnowledgeModal} disabled={loading}>
              上传知识文档
            </button>
          </div>

          <div className="block">
            <h3>知识文档列表</h3>
            {!knowledgeItems.length && <p>当前条件下暂无知识文档。</p>}
            {!!knowledgeItems.length && (
              <table>
                <thead>
                  <tr>
                    <th>document_id</th>
                    <th>名称</th>
                    <th>类型</th>
                    <th>文件</th>
                    <th>切片</th>
                    <th>状态</th>
                    <th>创建时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {knowledgeItems.map((item) => (
                    <tr key={item.document_id}>
                      <td>{item.document_id}</td>
                      <td>{item.name}</td>
                      <td>{item.doc_type}</td>
                      <td>{item.file_type}</td>
                      <td>{item.chunk_count}</td>
                      <td>{item.enabled ? "启用" : "停用"}</td>
                      <td>{item.created_at}</td>
                      <td className="table-actions">
                        <button type="button" onClick={() => fillKnowledgeForm(item)} disabled={loading}>
                          编辑
                        </button>
                        <button type="button" onClick={() => onToggleKnowledge(item)} disabled={loading}>
                          {item.enabled ? "停用" : "启用"}
                        </button>
                        <button type="button" onClick={() => onDeleteKnowledge(item)} disabled={loading}>
                          删除
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {selectedKnowledge && (
            <div className="block">
              <h3>当前预览</h3>
              <pre>{selectedKnowledge.raw_text}</pre>
            </div>
          )}
        </section>
      )}

      {activeSection === "tasks" && (
        <>
          <section id="tasks" className="card">
            <h2>校对任务</h2>
            <p className="section-desc">提交待校对文本并查询异步任务状态，管理员可指定 Owner 和模板。</p>
            <div className="stats">
              <div className="stat-card">
                <span>当前任务</span>
                <strong>{taskId || "-"}</strong>
              </div>
              <div className="stat-card">
                <span>任务状态</span>
                <strong>{taskStatus || "-"}</strong>
              </div>
              <div className="stat-card">
                <span>问题数量</span>
                <strong>{resultIssueCount}</strong>
              </div>
              <div className="stat-card">
                <span>知识命中</span>
                <strong>{resultRagHitCount}</strong>
              </div>
            </div>
            <form onSubmit={onCreateTask} className="grid">
              <label>
                模式
                <select value={mode} onChange={(event) => setMode(event.target.value as "review" | "rewrite")}>
                  <option value="review">review</option>
                  <option value="rewrite">rewrite</option>
                </select>
              </label>
              <label>
                场景
                <select
                  value={scene}
                  onChange={(event) => setScene(event.target.value as "general" | "contract" | "announcement" | "tech_doc")}
                >
                  <option value="general">general</option>
                  <option value="contract">contract</option>
                  <option value="announcement">announcement</option>
                  <option value="tech_doc">tech_doc</option>
                </select>
              </label>
              <label>
                任务 Owner ID
                <input
                  value={isAdmin ? ownerId : currentUser.username}
                  onChange={(event) => setOwnerId(event.target.value)}
                  disabled={!isAdmin}
                />
              </label>
              {isAdmin && (
                <label>
                  任务模板
                  <select value={selectedTemplateId} onChange={(event) => setSelectedTemplateId(event.target.value)}>
                    <option value="">不使用模板</option>
                    {templates.map((item) => (
                      <option key={item.template_id} value={item.template_id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <label className="full">
                文本内容
                <textarea value={text} onChange={(event) => setText(event.target.value)} rows={7} />
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
            <h2>校对结果</h2>
            {!taskResult && <p>暂无结果，任务成功后点击“查询任务状态/结果”。</p>}
            {taskResult && (
              <>
                <pre>{JSON.stringify(taskResult.summary, null, 2)}</pre>
                {!!taskResult.rag_hits?.length && (
                  <div className="block">
                    <h3>RAG 知识命中</h3>
                    <table>
                      <thead>
                        <tr>
                          <th>文本切片</th>
                          <th>知识文档</th>
                          <th>知识切片</th>
                          <th>得分</th>
                          <th>命中内容</th>
                        </tr>
                      </thead>
                      <tbody>
                        {taskResult.rag_hits.map((hit, index) => (
                          <tr key={`${hit.document_id}-${hit.knowledge_chunk_index}-${index}`}>
                            <td>{hit.chunk_index}</td>
                            <td>{hit.document_name}</td>
                            <td>{hit.knowledge_chunk_index}</td>
                            <td>{hit.score.toFixed(4)}</td>
                            <td>{hit.content_preview}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                <table>
                  <thead>
                    <tr>
                      <th>严重级别</th>
                      <th>类别</th>
                      <th>标题</th>
                        <th>原文</th>
                        <th>建议</th>
                        <th>位置</th>
                        <th>来源</th>
                    </tr>
                  </thead>
                  <tbody>
                    {taskResult.issues.map((issue, index) => (
                      <tr key={`${issue.title}-${index}`}>
                        <td>{issue.severity}</td>
                        <td>{issue.category}</td>
                        <td>{issue.title}</td>
                        <td>{issue.original_text}</td>
                        <td>{issue.suggested_text}</td>
                        <td>
                          {issue.position_start == null || issue.position_end == null
                            ? "-"
                            : `${issue.position_start}-${issue.position_end}`}
                        </td>
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

      </main>
      {userModalOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-card" role="dialog" aria-modal="true" aria-label={editingUsername ? "编辑用户" : "新增用户"}>
            <div className="modal-head">
              <div>
                <h2>{editingUsername ? "编辑用户" : "新增用户"}</h2>
                <p>{editingUsername ? "调整账号角色、启停状态和改密策略。" : "创建新的后台账号并设置初始权限。"}</p>
              </div>
              <button type="button" className="icon-btn" onClick={resetUserForm} disabled={loading}>
                关闭
              </button>
            </div>
            <form onSubmit={onSubmitUser} className="grid">
              <label>
                用户名
                <input
                  value={userUsername}
                  onChange={(event) => setUserUsername(event.target.value)}
                  disabled={Boolean(editingUsername)}
                  placeholder="例如 alice"
                />
              </label>
              <label>
                密码
                <input
                  type="password"
                  value={userPassword}
                  onChange={(event) => setUserPassword(event.target.value)}
                  placeholder={editingUsername ? "编辑时无需填写" : "至少 8 位"}
                  disabled={Boolean(editingUsername)}
                />
              </label>
              <label>
                角色
                <select value={userRole} onChange={(event) => setUserRole(event.target.value as UserRole)}>
                  <option value="admin">admin</option>
                  <option value="operator">operator</option>
                </select>
              </label>
              <label className="checkbox">
                <input type="checkbox" checked={userEnabled} onChange={(event) => setUserEnabled(event.target.checked)} />
                账号启用
              </label>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={userMustChangePassword}
                  onChange={(event) => setUserMustChangePassword(event.target.checked)}
                />
                下次登录强制改密
              </label>
              <div className="actions full">
                <button type="submit" disabled={loading}>
                  {editingUsername ? "保存修改" : "创建用户"}
                </button>
                <button type="button" onClick={resetUserForm} disabled={loading}>
                  取消
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      {ruleModalOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-card wide" role="dialog" aria-modal="true" aria-label={editingRuleId ? "编辑规则" : "新增规则"}>
            <div className="modal-head">
              <div>
                <h2>{editingRuleId ? "编辑规则" : `新增${activeSection === "publicRules" ? "公共" : "个人"}规则`}</h2>
                <p>规则用于稳定处理术语、敏感信息和结构类校对项。</p>
              </div>
              <button type="button" className="icon-btn" onClick={resetRuleForm} disabled={loading}>
                关闭
              </button>
            </div>
            <form onSubmit={onSubmitRule} className="grid">
              <label>
                规则类型
                <select value={ruleKind} onChange={(event) => setRuleKind(event.target.value)}>
                  <option value="term_replace">term_replace</option>
                  <option value="regex_mask">regex_mask</option>
                </select>
              </label>
              <label>
                标题
                <input value={ruleTitle} onChange={(event) => setRuleTitle(event.target.value)} placeholder="例如 部门术语统一" />
              </label>
              <label>
                严重级别
                <select value={ruleSeverity} onChange={(event) => setRuleSeverity(event.target.value)}>
                  <option value="P0">P0</option>
                  <option value="P1">P1</option>
                  <option value="P2">P2</option>
                </select>
              </label>
              <label>
                分类
                <select value={ruleCategory} onChange={(event) => setRuleCategory(event.target.value)}>
                  <option value="style">style</option>
                  <option value="terminology">terminology</option>
                  <option value="compliance">compliance</option>
                  <option value="grammar">grammar</option>
                  <option value="structure">structure</option>
                </select>
              </label>
              <label>
                匹配内容
                <input value={rulePattern} onChange={(event) => setRulePattern(event.target.value)} placeholder="例如 登陆" />
              </label>
              <label>
                替换内容
                <input value={ruleReplacement} onChange={(event) => setRuleReplacement(event.target.value)} placeholder="例如 登录" />
              </label>
              <label className="full">
                原因
                <input value={ruleReason} onChange={(event) => setRuleReason(event.target.value)} />
              </label>
              <label className="checkbox">
                <input type="checkbox" checked={ruleEnabled} onChange={(event) => setRuleEnabled(event.target.checked)} />
                规则启用
              </label>
              <div className="actions full">
                <button type="submit" disabled={loading}>
                  {editingRuleId ? "保存修改" : "创建规则"}
                </button>
                <button type="button" onClick={resetRuleForm} disabled={loading}>
                  取消
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      {knowledgeModalOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-card wide" role="dialog" aria-modal="true" aria-label={editingKnowledgeId ? "编辑知识库" : "上传知识库"}>
            <div className="modal-head">
              <div>
                <h2>{editingKnowledgeId ? "编辑知识库" : "上传知识文档"}</h2>
                <p>知识库会被切片并生成向量，用于校对任务中的 RAG 检索。</p>
              </div>
              <button type="button" className="icon-btn" onClick={resetKnowledgeForm} disabled={loading}>
                关闭
              </button>
            </div>
            <form onSubmit={onSubmitKnowledge} className="grid">
              <label>
                名称
                <input value={knowledgeName} onChange={(event) => setKnowledgeName(event.target.value)} placeholder="例如 公文写作规范" />
              </label>
              <label>
                类型
                <input value={knowledgeDocType} onChange={(event) => setKnowledgeDocType(event.target.value)} placeholder="general/policy/style/..." />
              </label>
              {!editingKnowledgeId && (
                <label className="full">
                  文件
                  <input type="file" accept=".docx,.txt,.md" onChange={onKnowledgeFileChange} />
                </label>
              )}
              {editingKnowledgeId && (
                <label className="full">
                  正文
                  <textarea value={knowledgeRawText} onChange={(event) => setKnowledgeRawText(event.target.value)} rows={12} />
                </label>
              )}
              <label className="checkbox">
                <input type="checkbox" checked={knowledgeEnabled} onChange={(event) => setKnowledgeEnabled(event.target.checked)} />
                知识库启用
              </label>
              <div className="actions full">
                <button type="submit" disabled={loading}>
                  {editingKnowledgeId ? "保存修改" : "上传文档"}
                </button>
                <button type="button" onClick={resetKnowledgeForm} disabled={loading}>
                  取消
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      {message && <div className="toast">{message}</div>}
    </div>
  );
}

export default App;
