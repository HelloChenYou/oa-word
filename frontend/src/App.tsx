import { useEffect, useState } from "react";
import {
  changePassword,
  createRule,
  createTask,
  createUser,
  deleteRule,
  getCurrentUser,
  getTaskResult,
  getTaskStatus,
  getTemplateDetail,
  listRules,
  listTemplates,
  listUsers,
  login,
  resetUserPassword,
  updateRule,
  updateUser,
  uploadTemplate
} from "./api";
import type { AuthUser, RuleItem, TaskResult, TemplateDetail, TemplateItem, UserItem } from "./types";

type SectionKey = "users" | "rules" | "templates" | "tasks";
type RuleScope = "private" | "public";
type UserRole = "admin" | "operator";

const ADMIN_SECTIONS: SectionKey[] = ["users", "rules", "templates", "tasks"];

function getInitialSection(): SectionKey {
  const hash = window.location.hash.replace("#", "");
  return ADMIN_SECTIONS.includes(hash as SectionKey) ? (hash as SectionKey) : "tasks";
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

  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateDetail | null>(null);
  const [templateName, setTemplateName] = useState("");
  const [templateDocType, setTemplateDocType] = useState("general");
  const [templateFile, setTemplateFile] = useState<File | null>(null);

  const [text, setText] = useState("请各部门登录OA系统，并上报员工手机号13800138000。");
  const [mode, setMode] = useState<"review" | "rewrite">("review");
  const [scene, setScene] = useState<"general" | "contract" | "announcement" | "tech_doc">("general");
  const [taskId, setTaskId] = useState("");
  const [taskStatus, setTaskStatus] = useState("");
  const [taskResult, setTaskResult] = useState<TaskResult | null>(null);

  const isAdmin = currentUser?.role === "admin";
  const mustChangePassword = currentUser?.must_change_password ?? false;

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
    if (!isAdmin && activeSection !== "tasks") {
      navigateTo("tasks");
    }
  }, [activeSection, currentUser, isAdmin]);

  useEffect(() => {
    if (!currentUser || !isAdmin) {
      return;
    }
    void loadUsers();
    void loadRules();
    void loadTemplates();
  }, [currentUser, isAdmin]);

  useEffect(() => {
    if (!currentUser || !isAdmin) {
      return;
    }
    void loadRules();
  }, [ownerId, ruleScope, currentUser, isAdmin]);

  useEffect(() => {
    if (!selectedTemplateId || !currentUser || !isAdmin) {
      setSelectedTemplate(null);
      return;
    }
    getTemplateDetail(selectedTemplateId)
      .then(setSelectedTemplate)
      .catch((err) => setMessage(`读取模板详情失败: ${String(err)}`));
  }, [selectedTemplateId, currentUser, isAdmin]);

  const navigateTo = (section: SectionKey) => {
    if (!isAdmin && section !== "tasks") {
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
  };

  const fillUserForm = (user: UserItem) => {
    setEditingUsername(user.username);
    setUserUsername(user.username);
    setUserPassword("");
    setUserRole(user.role as UserRole);
    setUserEnabled(user.enabled);
    setUserMustChangePassword(user.must_change_password);
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

  const loadUsers = async () => {
    try {
      setUsers(await listUsers());
    } catch (err) {
      setMessage(`加载用户失败: ${String(err)}`);
    }
  };

  const loadRules = async () => {
    try {
      setRules(await listRules({ ownerId, scope: ruleScope }));
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

  const onLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      const resp = await login({ username: loginUsername.trim(), password: loginPassword });
      window.localStorage.setItem("auth_access_token", resp.access_token);
      setCurrentUser(resp.user);
      setOwnerId(resp.user.username);
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
    setSelectedTemplate(null);
    setTaskResult(null);
    setTaskId("");
    setTaskStatus("");
    setCurrentPassword("");
    setNewPassword("");
    resetUserForm();
    resetRuleForm();
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

  const onSubmitRule = async (event: React.FormEvent) => {
    event.preventDefault();
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
      const scopedOwnerId = ruleScope === "private" ? ownerId.trim() || undefined : undefined;
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
      await deleteRule(rule.rule_id, rule.scope === "private" ? ownerId.trim() || undefined : undefined);
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
        rule.scope === "private" ? ownerId.trim() || undefined : undefined
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
                <button type="button" className={activeSection === "users" ? "nav-btn active" : "nav-btn"} onClick={() => navigateTo("users")}>
                  用户管理
                </button>
                <button type="button" className={activeSection === "rules" ? "nav-btn active" : "nav-btn"} onClick={() => navigateTo("rules")}>
                  规则管理
                </button>
                <button
                  type="button"
                  className={activeSection === "templates" ? "nav-btn active" : "nav-btn"}
                  onClick={() => navigateTo("templates")}
                >
                  模板管理
                </button>
              </>
            )}
            <button type="button" className={activeSection === "tasks" ? "nav-btn active" : "nav-btn"} onClick={() => navigateTo("tasks")}>
              校对任务
            </button>
          </nav>
          <div className="auth-panel">
            <button type="button" onClick={onLogout}>
              退出登录
            </button>
          </div>
        </div>
      </header>
      {isAdmin && activeSection === "users" && (
        <section id="users" className="card">
          <h2>用户管理</h2>
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
                placeholder={editingUsername ? "留空表示不修改" : "至少 8 位"}
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
                {editingUsername ? "保存修改" : "新增用户"}
              </button>
              <button type="button" onClick={resetUserForm} disabled={loading}>
                {editingUsername ? "取消编辑" : "重置表单"}
              </button>
            </div>
          </form>

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

      {isAdmin && activeSection === "rules" && (
        <section id="rules" className="card">
          <h2>规则管理</h2>
          <form onSubmit={onSubmitRule} className="grid">
            <label>
              Owner ID
              <input value={ownerId} onChange={(event) => setOwnerId(event.target.value)} placeholder="例如 demo_user" />
            </label>
            <label>
              规则作用域
              <select value={ruleScope} onChange={(event) => setRuleScope(event.target.value as RuleScope)}>
                <option value="private">private</option>
                <option value="public">public</option>
              </select>
            </label>
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
            <label className="full">
              依据
              <input value={ruleEvidence} onChange={(event) => setRuleEvidence(event.target.value)} placeholder="例如 private_rule:demo_user:login" />
            </label>
            <label className="checkbox">
              <input type="checkbox" checked={ruleEnabled} onChange={(event) => setRuleEnabled(event.target.checked)} />
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
            <h3>规则列表</h3>
            {!rules.length && <p>当前条件下暂无规则。</p>}
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
              <input value={templateName} onChange={(event) => setTemplateName(event.target.value)} placeholder="例如 通知模板" />
            </label>
            <label>
              模板类型
              <input value={templateDocType} onChange={(event) => setTemplateDocType(event.target.value)} placeholder="general/notice/..." />
            </label>
            <label>
              模板文件
              <input type="file" accept=".docx,.txt,.md" onChange={(event) => setTemplateFile(event.target.files?.[0] ?? null)} />
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

      {activeSection === "tasks" && (
        <>
          <section id="tasks" className="card">
            <h2>校对任务</h2>
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
                    {taskResult.issues.map((issue, index) => (
                      <tr key={`${issue.title}-${index}`}>
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
