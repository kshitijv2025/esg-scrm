import React, { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../api/client";
import { useAuth } from "../contexts/AuthContext";

// ---------------------------------------------------------------------------
// Shared sub-components
// ---------------------------------------------------------------------------

function SectionHeader({ title, subtitle }) {
  return (
    <div style={{ marginBottom: "20px" }}>
      <h3
        style={{
          fontSize: "0.95rem",
          fontWeight: 700,
          color: "var(--text)",
          margin: "0 0 4px",
        }}
      >
        {title}
      </h3>
      {subtitle && (
        <p style={{ fontSize: "0.78rem", color: "var(--text-dim)", margin: 0 }}>
          {subtitle}
        </p>
      )}
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    active: { label: "Active", cls: "tier-a" },
    inactive: { label: "Inactive", cls: "tier-c" },
    pending: { label: "Pending", cls: "tier-b" },
  };
  const s = map[status] || map.inactive;
  return <span className={`risk-tier ${s.cls}`}>{s.label}</span>;
}

function RoleBadge({ role }) {
  const cls = role === "admin" ? "tier-a" : role === "editor" ? "tier-b" : "";
  return <span className={`risk-tier ${cls}`}>{role}</span>;
}

function InlineMsg({ msg }) {
  if (!msg) return null;
  return (
    <div
      style={{
        marginTop: "10px",
        padding: "8px 12px",
        borderRadius: "6px",
        fontSize: "0.82rem",
        background: msg.ok ? "var(--green-dim)" : "var(--red-dim)",
        color: msg.ok ? "var(--green)" : "var(--red)",
      }}
    >
      {msg.message}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 1 — User Management
// ---------------------------------------------------------------------------

function UserManagementTab() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Invite form
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState("viewer");
  const [inviting, setInviting] = useState(false);
  const [inviteMsg, setInviteMsg] = useState(null);

  // Role change
  const [changingRoleFor, setChangingRoleFor] = useState(null);
  const [newRole, setNewRole] = useState("");
  const [roleMsg, setRoleMsg] = useState(null);

  const loadUsers = useCallback(() => {
    setLoading(true);
    setError(null);
    apiFetch("/admin/users")
      .then((r) => r.json())
      .then((d) => {
        setUsers(d.users || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  async function handleInvite(e) {
    e.preventDefault();
    if (!inviteEmail.trim() || !inviteName.trim()) return;
    setInviting(true);
    setInviteMsg(null);
    try {
      const res = await apiFetch("/auth/invite", {
        method: "POST",
        body: JSON.stringify({
          email: inviteEmail,
          full_name: inviteName,
          role: inviteRole,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setInviteMsg({ ok: false, message: data.detail || "Invite failed" });
      } else {
        setInviteMsg({
          ok: true,
          message: `Invitation sent to ${inviteEmail}`,
        });
        setInviteEmail("");
        setInviteName("");
        setInviteRole("viewer");
        loadUsers();
      }
    } catch (err) {
      setInviteMsg({ ok: false, message: err.message });
    } finally {
      setInviting(false);
    }
  }

  async function handleChangeRole(userId, currentRole) {
    const role = newRole || currentRole;
    try {
      const res = await apiFetch(`/admin/users/${userId}/role`, {
        method: "PUT",
        body: JSON.stringify({ role }),
      });
      const data = await res.json();
      if (!res.ok) {
        setRoleMsg({
          ok: false,
          message: data.detail || "Failed to update role",
        });
      } else {
        setChangingRoleFor(null);
        setNewRole("");
        setRoleMsg({ ok: true, message: "Role updated" });
        loadUsers();
      }
    } catch (err) {
      setRoleMsg({ ok: false, message: err.message });
    }
  }

  async function handleDeactivate(userId) {
    if (
      !window.confirm(
        "Deactivate this user? They will lose access immediately.",
      )
    )
      return;
    try {
      const res = await apiFetch(`/admin/users/${userId}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const data = await res.json();
        setRoleMsg({
          ok: false,
          message: data.detail || "Failed to deactivate user",
        });
      } else {
        loadUsers();
        setRoleMsg({ ok: true, message: "User deactivated" });
      }
    } catch (err) {
      setRoleMsg({ ok: false, message: err.message });
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Invite form */}
      <div className="panel" style={{ padding: "20px" }}>
        <SectionHeader
          title="Invite New User"
          subtitle="Invite a team member to your organization. They'll receive an email to set their password."
        />
        <form
          onSubmit={handleInvite}
          style={{
            display: "flex",
            gap: "10px",
            flexWrap: "wrap",
            alignItems: "flex-end",
          }}
        >
          <div className="field-row" style={{ flex: "2", minWidth: "180px" }}>
            <label>Email</label>
            <input
              type="email"
              className="input"
              placeholder="colleague@company.com"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              required
            />
          </div>
          <div className="field-row" style={{ flex: "2", minWidth: "160px" }}>
            <label>Full Name</label>
            <input
              type="text"
              className="input"
              placeholder="Jane Smith"
              value={inviteName}
              onChange={(e) => setInviteName(e.target.value)}
              required
            />
          </div>
          <div className="field-row" style={{ flex: "1", minWidth: "120px" }}>
            <label>Role</label>
            <select
              className="input select"
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
            >
              <option value="viewer">Viewer</option>
              <option value="editor">Editor</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button type="submit" className="btn btn-primary" disabled={inviting}>
            {inviting ? "Sending..." : "Send Invite"}
          </button>
        </form>
        <InlineMsg msg={inviteMsg} />
      </div>

      {/* User list */}
      <div className="panel" style={{ padding: "20px" }}>
        <SectionHeader
          title="Team Members"
          subtitle={`${users.length} user${users.length !== 1 ? "s" : ""} in your organization`}
        />
        <InlineMsg msg={roleMsg} />
        {loading ? (
          <div className="panel-loading">Loading users...</div>
        ) : error ? (
          <div style={{ color: "var(--red)", fontSize: "0.85rem" }}>
            {error}
          </div>
        ) : (
          <table className="supplier-table" style={{ marginTop: "12px" }}>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Last Login</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr>
                  <td
                    colSpan="6"
                    style={{
                      textAlign: "center",
                      color: "var(--text-muted)",
                      padding: "32px",
                    }}
                  >
                    No users found
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id}>
                    <td style={{ fontWeight: 600 }}>{u.full_name}</td>
                    <td style={{ color: "var(--text-dim)" }}>{u.email}</td>
                    <td>
                      {changingRoleFor === u.id ? (
                        <div
                          style={{
                            display: "flex",
                            gap: "6px",
                            alignItems: "center",
                          }}
                        >
                          <select
                            className="input select"
                            style={{
                              width: "auto",
                              padding: "4px 8px",
                              fontSize: "0.8rem",
                            }}
                            value={newRole || u.role}
                            onChange={(e) => setNewRole(e.target.value)}
                          >
                            <option value="viewer">Viewer</option>
                            <option value="editor">Editor</option>
                            <option value="admin">Admin</option>
                          </select>
                          <button
                            className="btn btn-sm"
                            onClick={() => handleChangeRole(u.id, u.role)}
                          >
                            Save
                          </button>
                          <button
                            className="btn btn-sm"
                            style={{ color: "var(--text-muted)" }}
                            onClick={() => {
                              setChangingRoleFor(null);
                              setNewRole("");
                            }}
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <RoleBadge role={u.role} />
                      )}
                    </td>
                    <td>
                      <StatusBadge
                        status={u.is_active ? "active" : "inactive"}
                      />
                    </td>
                    <td
                      style={{ color: "var(--text-dim)", fontSize: "0.82rem" }}
                    >
                      {u.last_login
                        ? new Date(u.last_login).toLocaleDateString()
                        : "—"}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "6px" }}>
                        <button
                          className="btn btn-sm"
                          onClick={() => {
                            setChangingRoleFor(u.id);
                            setNewRole(u.role);
                          }}
                        >
                          Change Role
                        </button>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => handleDeactivate(u.id)}
                        >
                          Deactivate
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 2 — Organization Settings
// ---------------------------------------------------------------------------

function OrgSettingsTab() {
  const { user } = useAuth();
  const [org, setOrg] = useState({ name: "", industry: "", country: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);

  useEffect(() => {
    apiFetch("/auth/me")
      .then((r) => r.json())
      .then((d) => {
        if (d.org)
          setOrg({
            name: d.org.name || "",
            industry: d.org.industry || "",
            country: d.org.country || "",
          });
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  function update(field, value) {
    setOrg((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setSaveMsg(null);
    try {
      const res = await apiFetch("/admin/org", {
        method: "PUT",
        body: JSON.stringify(org),
      });
      const data = await res.json();
      if (!res.ok)
        setSaveMsg({ ok: false, message: data.detail || "Save failed" });
      else setSaveMsg({ ok: true, message: "Organization settings saved" });
    } catch (err) {
      setSaveMsg({ ok: false, message: err.message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="panel" style={{ padding: "24px", maxWidth: "600px" }}>
      <SectionHeader
        title="Organization Settings"
        subtitle="Update your organization profile. These details appear on reports and exports."
      />
      {loading ? (
        <div className="panel-loading">Loading...</div>
      ) : (
        <form
          onSubmit={handleSave}
          style={{ display: "flex", flexDirection: "column", gap: "16px" }}
        >
          <div className="field-row">
            <label>Organization Name</label>
            <input
              type="text"
              className="input"
              value={org.name}
              onChange={(e) => update("name", e.target.value)}
              placeholder="Acme Corporation"
              required
            />
          </div>
          <div className="field-row">
            <label>Industry</label>
            <input
              type="text"
              className="input"
              value={org.industry}
              onChange={(e) => update("industry", e.target.value)}
              placeholder="Manufacturing, Technology, Finance..."
            />
          </div>
          <div className="field-row">
            <label>Country</label>
            <input
              type="text"
              className="input"
              value={org.country}
              onChange={(e) => update("country", e.target.value)}
              placeholder="United States"
            />
          </div>
          <InlineMsg msg={saveMsg} />
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </form>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 3 — API Keys
// ---------------------------------------------------------------------------

function ApiKeysTab() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [newKey, setNewKey] = useState(null);
  const [revoking, setRevoking] = useState(null);
  const [msg, setMsg] = useState(null);

  function loadKeys() {
    setLoading(true);
    apiFetch("/admin/api-keys")
      .then((r) => r.json())
      .then((d) => {
        setKeys(d.keys || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }

  useEffect(() => {
    loadKeys();
  }, []);

  async function handleGenerate() {
    setGenerating(true);
    setNewKey(null);
    setMsg(null);
    try {
      const res = await apiFetch("/admin/api-keys", { method: "POST" });
      const data = await res.json();
      if (!res.ok)
        setMsg({ ok: false, message: data.detail || "Failed to generate key" });
      else {
        setNewKey(data.key);
        loadKeys();
        setMsg({ ok: true, message: "New API key generated" });
      }
    } catch (err) {
      setMsg({ ok: false, message: err.message });
    } finally {
      setGenerating(false);
    }
  }

  async function handleRevoke(keyId) {
    if (
      !window.confirm(
        "Revoke this API key? Any integrations using it will stop working.",
      )
    )
      return;
    setRevoking(keyId);
    setMsg(null);
    try {
      const res = await apiFetch(`/admin/api-keys/${keyId}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const data = await res.json();
        setMsg({ ok: false, message: data.detail || "Failed to revoke key" });
      } else {
        loadKeys();
        setMsg({ ok: true, message: "API key revoked" });
      }
    } catch (err) {
      setMsg({ ok: false, message: err.message });
    } finally {
      setRevoking(null);
    }
  }

  function maskKey(key) {
    if (!key || key.length < 8) return "••••••••";
    return "••••••••" + key.slice(-4);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {newKey && (
        <div
          style={{
            background: "rgba(34, 197, 94, 0.08)",
            border: "1px solid var(--green)",
            borderRadius: "10px",
            padding: "16px 20px",
          }}
        >
          <div
            style={{
              fontWeight: 700,
              color: "var(--green)",
              marginBottom: "8px",
              fontSize: "0.85rem",
            }}
          >
            New API Key — Copy it now, it won't be shown again
          </div>
          <div
            style={{
              fontFamily: "monospace",
              fontSize: "0.88rem",
              color: "var(--text)",
              background: "var(--surface2)",
              padding: "8px 12px",
              borderRadius: "6px",
              wordBreak: "break-all",
              marginBottom: "10px",
            }}
          >
            {newKey}
          </div>
          <button
            className="btn btn-sm"
            onClick={() => navigator.clipboard.writeText(newKey)}
          >
            Copy to Clipboard
          </button>
          <button
            className="btn btn-sm"
            style={{ marginLeft: "8px", color: "var(--text-muted)" }}
            onClick={() => setNewKey(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      <InlineMsg msg={msg} />

      <div className="panel" style={{ padding: "20px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginBottom: "16px",
          }}
        >
          <SectionHeader
            title="API Keys"
            subtitle="Use API keys to authenticate programmatic access to the ESG SCRM API."
          />
          <button
            className="btn btn-primary"
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? "Generating..." : "+ Generate Key"}
          </button>
        </div>

        {loading ? (
          <div className="panel-loading">Loading...</div>
        ) : (
          <table className="supplier-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Key</th>
                <th>Created</th>
                <th>Last Used</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {keys.length === 0 ? (
                <tr>
                  <td
                    colSpan="5"
                    style={{
                      textAlign: "center",
                      color: "var(--text-muted)",
                      padding: "32px",
                    }}
                  >
                    No API keys yet. Generate one to get started.
                  </td>
                </tr>
              ) : (
                keys.map((k) => (
                  <tr key={k.id}>
                    <td style={{ fontWeight: 600 }}>
                      {k.name || "Unnamed key"}
                    </td>
                    <td
                      style={{
                        fontFamily: "monospace",
                        fontSize: "0.82rem",
                        color: "var(--text-dim)",
                      }}
                    >
                      {maskKey(k.key)}
                    </td>
                    <td
                      style={{ color: "var(--text-dim)", fontSize: "0.82rem" }}
                    >
                      {new Date(k.created_at).toLocaleDateString()}
                    </td>
                    <td
                      style={{ color: "var(--text-dim)", fontSize: "0.82rem" }}
                    >
                      {k.last_used_at
                        ? new Date(k.last_used_at).toLocaleDateString()
                        : "—"}
                    </td>
                    <td>
                      <button
                        className="btn btn-sm btn-danger"
                        disabled={revoking === k.id}
                        onClick={() => handleRevoke(k.id)}
                      >
                        {revoking === k.id ? "Revoking..." : "Revoke"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 4 — Alert Thresholds
// ---------------------------------------------------------------------------

const CLUSTERS = [
  "energy",
  "emissions",
  "water",
  "diesel",
  "scope3_coverage",
  "supplier_risk",
  "evidence_chain",
];

const OPERATORS = [
  { value: "gt", label: "Greater than (>)" },
  { value: "gte", label: "Greater than or equal (>=)" },
  { value: "lt", label: "Less than (<)" },
  { value: "lte", label: "Less than or equal (<=)" },
  { value: "eq", label: "Equal (=)" },
];

const SEVERITY_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

function SeverityBadge({ severity }) {
  const cls =
    severity === "critical"
      ? "tier-a"
      : severity === "high"
        ? "tier-b"
        : severity === "medium"
          ? "tier-c"
          : "";
  return <span className={`risk-tier ${cls}`}>{severity || "—"}</span>;
}

function ThresholdConfigTab() {
  const [thresholds, setThresholds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Editing state per threshold id
  const [editing, setEditing] = useState({});
  // Draft values while editing
  const [drafts, setDrafts] = useState({});
  // Save / delete / add in-progress ids
  const [saving, setSaving] = useState({});
  const [deleting, setDeleting] = useState(null);
  const [msg, setMsg] = useState(null);

  // Add-new form state
  const [newCluster, setNewCluster] = useState(CLUSTERS[0]);
  const [newMetric, setNewMetric] = useState("");
  const [newOperator, setNewOperator] = useState("gt");
  const [newValue, setNewValue] = useState("");
  const [newSeverity, setNewSeverity] = useState("medium");
  const [adding, setAdding] = useState(false);

  function loadThresholds() {
    setLoading(true);
    setError(null);
    apiFetch("/alerts/thresholds")
      .then((r) => r.json())
      .then((d) => {
        setThresholds(d.thresholds || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }

  useEffect(() => {
    loadThresholds();
  }, []);

  function startEdit(t) {
    setEditing((prev) => ({ ...prev, [t.id]: true }));
    setDrafts((prev) => ({
      ...prev,
      [t.id]: {
        threshold_value: t.threshold_value,
        operator: t.operator,
        severity: t.severity,
        is_active: t.is_active,
      },
    }));
  }

  function cancelEdit(id) {
    setEditing((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    setDrafts((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }

  function setDraft(id, field, value) {
    setDrafts((prev) => ({
      ...prev,
      [id]: { ...prev[id], [field]: value },
    }));
  }

  async function saveThreshold(t) {
    setSaving((prev) => ({ ...prev, [t.id]: true }));
    setMsg(null);
    const body = drafts[t.id];
    try {
      const res = await apiFetch(`/alerts/thresholds/${t.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        setMsg({ ok: false, message: data.detail || "Update failed" });
      } else {
        setThresholds((prev) =>
          prev.map((x) => (x.id === t.id ? { ...x, ...body } : x)),
        );
        cancelEdit(t.id);
        setMsg({ ok: true, message: "Threshold updated" });
      }
    } catch (err) {
      setMsg({ ok: false, message: err.message });
    } finally {
      setSaving((prev) => {
        const next = { ...prev };
        delete next[t.id];
        return next;
      });
    }
  }

  async function deleteThreshold(t) {
    if (
      !window.confirm(
        `Delete threshold for "${t.metric_cluster}"? This cannot be undone.`,
      )
    )
      return;
    setDeleting(t.id);
    setMsg(null);
    try {
      const res = await apiFetch(`/alerts/thresholds/${t.id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const data = await res.json();
        setMsg({ ok: false, message: data.detail || "Delete failed" });
      } else {
        setThresholds((prev) => prev.filter((x) => x.id !== t.id));
        setMsg({ ok: true, message: "Threshold deleted" });
      }
    } catch (err) {
      setMsg({ ok: false, message: err.message });
    } finally {
      setDeleting(null);
    }
  }

  async function addThreshold(e) {
    e.preventDefault();
    if (!newMetric.trim()) return;
    setAdding(true);
    setMsg(null);
    try {
      const res = await apiFetch("/alerts/thresholds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cluster: newCluster,
          metric_cluster: newMetric.trim(),
          operator: newOperator,
          threshold_value: parseFloat(newValue) || 0,
          severity: newSeverity,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setMsg({ ok: false, message: data.detail || "Create failed" });
      } else {
        setNewMetric("");
        setNewValue("");
        setNewOperator("gt");
        setNewSeverity("medium");
        loadThresholds();
        setMsg({ ok: true, message: "Threshold added" });
      }
    } catch (err) {
      setMsg({ ok: false, message: err.message });
    } finally {
      setAdding(false);
    }
  }

  // Group thresholds by cluster
  const grouped = {};
  for (const c of CLUSTERS) grouped[c] = [];
  for (const t of thresholds) {
    const c = t.cluster || t.metric_cluster;
    if (Array.isArray(grouped[c])) grouped[c].push(t);
    else grouped[c].push(t); // fall back to metric_cluster key
  }

  const operatorLabel = (op) =>
    OPERATORS.find((o) => o.value === op)?.label || op;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <InlineMsg msg={msg} />

      {loading ? (
        <div className="panel" style={{ padding: "20px" }}>
          <div className="panel-loading">Loading thresholds...</div>
        </div>
      ) : error ? (
        <div className="panel" style={{ padding: "20px" }}>
          <div style={{ color: "var(--red)", fontSize: "0.85rem" }}>
            {error}
          </div>
        </div>
      ) : (
        CLUSTERS.map((cluster) =>
          grouped[cluster]?.length === 0 ? null : (
            <div key={cluster} className="panel" style={{ padding: "20px" }}>
              <SectionHeader
                title={cluster
                  .replace(/_/g, " ")
                  .replace(/\b\w/g, (c) => c.toUpperCase())}
                subtitle={`${grouped[cluster].length} threshold${grouped[cluster].length !== 1 ? "s" : ""}`}
              />
              <table className="supplier-table" style={{ marginTop: "12px" }}>
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Operator</th>
                    <th>Threshold</th>
                    <th>Severity</th>
                    <th>Active</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {grouped[cluster].map((t) => {
                    const isEditing = editing[t.id];
                    const draft = drafts[t.id] || {};
                    return (
                      <tr key={t.id}>
                        <td style={{ fontWeight: 600 }}>{t.metric_cluster}</td>
                        <td>
                          {isEditing ? (
                            <select
                              className="input select"
                              style={{
                                width: "auto",
                                padding: "4px 8px",
                                fontSize: "0.8rem",
                              }}
                              value={draft.operator ?? t.operator}
                              onChange={(e) =>
                                setDraft(t.id, "operator", e.target.value)
                              }
                            >
                              {OPERATORS.map((op) => (
                                <option key={op.value} value={op.value}>
                                  {op.label}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <span
                              style={{
                                color: "var(--text-dim)",
                                fontSize: "0.85rem",
                              }}
                            >
                              {operatorLabel(t.operator)}
                            </span>
                          )}
                        </td>
                        <td>
                          {isEditing ? (
                            <input
                              type="number"
                              className="input"
                              style={{
                                width: "100px",
                                padding: "4px 8px",
                                fontSize: "0.8rem",
                              }}
                              value={draft.threshold_value ?? t.threshold_value}
                              onChange={(e) =>
                                setDraft(
                                  t.id,
                                  "threshold_value",
                                  parseFloat(e.target.value) || 0,
                                )
                              }
                            />
                          ) : (
                            <span
                              style={{
                                fontFamily: "monospace",
                                fontSize: "0.85rem",
                              }}
                            >
                              {t.threshold_value}
                            </span>
                          )}
                        </td>
                        <td>
                          {isEditing ? (
                            <select
                              className="input select"
                              style={{
                                width: "auto",
                                padding: "4px 8px",
                                fontSize: "0.8rem",
                              }}
                              value={draft.severity ?? t.severity}
                              onChange={(e) =>
                                setDraft(t.id, "severity", e.target.value)
                              }
                            >
                              {SEVERITY_OPTIONS.map((s) => (
                                <option key={s.value} value={s.value}>
                                  {s.label}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <SeverityBadge severity={t.severity} />
                          )}
                        </td>
                        <td>
                          <label
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "6px",
                              cursor: "pointer",
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={
                                isEditing
                                  ? (draft.is_active ?? t.is_active)
                                  : t.is_active
                              }
                              onChange={(e) => {
                                if (isEditing) {
                                  setDraft(t.id, "is_active", e.target.checked);
                                } else {
                                  // Direct toggle without entering edit mode
                                  setEditing((prev) => ({
                                    ...prev,
                                    [t.id]: true,
                                  }));
                                  setDrafts((prev) => ({
                                    ...prev,
                                    [t.id]: {
                                      threshold_value: t.threshold_value,
                                      operator: t.operator,
                                      severity: t.severity,
                                      is_active: e.target.checked,
                                    },
                                  }));
                                }
                              }}
                              style={{ width: "16px", height: "16px" }}
                            />
                            <span
                              style={{
                                fontSize: "0.82rem",
                                color: "var(--text-dim)",
                              }}
                            >
                              {(isEditing ? draft.is_active : t.is_active)
                                ? "Active"
                                : "Inactive"}
                            </span>
                          </label>
                        </td>
                        <td>
                          <div
                            style={{
                              display: "flex",
                              gap: "6px",
                              flexWrap: "wrap",
                            }}
                          >
                            {isEditing ? (
                              <>
                                <button
                                  className="btn btn-sm"
                                  disabled={saving[t.id]}
                                  onClick={() => saveThreshold(t)}
                                >
                                  {saving[t.id] ? "Saving..." : "Save"}
                                </button>
                                <button
                                  className="btn btn-sm"
                                  style={{ color: "var(--text-muted)" }}
                                  onClick={() => cancelEdit(t.id)}
                                >
                                  Cancel
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  className="btn btn-sm"
                                  onClick={() => startEdit(t)}
                                >
                                  Edit
                                </button>
                                <button
                                  className="btn btn-sm btn-danger"
                                  disabled={deleting === t.id}
                                  onClick={() => deleteThreshold(t)}
                                >
                                  {deleting === t.id ? "Deleting..." : "Delete"}
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ),
        )
      )}

      {/* Add new threshold form */}
      <div className="panel" style={{ padding: "20px" }}>
        <SectionHeader
          title="Add New Threshold"
          subtitle="Create an alert threshold to trigger notifications when a metric crosses a defined boundary."
        />
        <form
          onSubmit={addThreshold}
          style={{
            display: "flex",
            gap: "10px",
            flexWrap: "wrap",
            alignItems: "flex-end",
            marginTop: "12px",
          }}
        >
          <div className="field-row" style={{ flex: "1", minWidth: "140px" }}>
            <label>Cluster</label>
            <select
              className="input select"
              value={newCluster}
              onChange={(e) => setNewCluster(e.target.value)}
            >
              {CLUSTERS.map((c) => (
                <option key={c} value={c}>
                  {c
                    .replace(/_/g, " ")
                    .replace(/\b\w/g, (x) => x.toUpperCase())}
                </option>
              ))}
            </select>
          </div>
          <div className="field-row" style={{ flex: "2", minWidth: "160px" }}>
            <label>Metric Name</label>
            <input
              type="text"
              className="input"
              placeholder="e.g. energy_per_unit, scope3_tco2"
              value={newMetric}
              onChange={(e) => setNewMetric(e.target.value)}
              required
            />
          </div>
          <div className="field-row" style={{ flex: "1", minWidth: "140px" }}>
            <label>Operator</label>
            <select
              className="input select"
              value={newOperator}
              onChange={(e) => setNewOperator(e.target.value)}
            >
              {OPERATORS.map((op) => (
                <option key={op.value} value={op.value}>
                  {op.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field-row" style={{ flex: "1", minWidth: "120px" }}>
            <label>Threshold Value</label>
            <input
              type="number"
              className="input"
              placeholder="0.0"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              required
            />
          </div>
          <div className="field-row" style={{ flex: "1", minWidth: "120px" }}>
            <label>Severity</label>
            <select
              className="input select"
              value={newSeverity}
              onChange={(e) => setNewSeverity(e.target.value)}
            >
              {SEVERITY_OPTIONS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" className="btn btn-primary" disabled={adding}>
            {adding ? "Adding..." : "Add Threshold"}
          </button>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 5 — Audit Log
// ---------------------------------------------------------------------------

function AuditLogTab() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  const [filterUser, setFilterUser] = useState("");
  const [filterAction, setFilterAction] = useState("");
  const [filterStart, setFilterStart] = useState("");
  const [filterEnd, setFilterEnd] = useState("");

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  function buildQuery() {
    const params = new URLSearchParams({ page, page_size: pageSize });
    if (filterUser) params.set("user", filterUser);
    if (filterAction) params.set("action", filterAction);
    if (filterStart) params.set("start_date", filterStart);
    if (filterEnd) params.set("end_date", filterEnd);
    return params.toString();
  }

  function loadLogs() {
    setLoading(true);
    const qs = buildQuery();
    apiFetch(`/admin/audit-log${qs ? "?" + qs : ""}`)
      .then((r) => r.json())
      .then((d) => {
        setLogs(d.logs || []);
        setTotal(d.total || 0);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }

  useEffect(() => {
    loadLogs();
  }, [page, filterUser, filterAction, filterStart, filterEnd]);

  function handleFilterChange(setter) {
    return (val) => {
      setter(val);
      setPage(1);
    };
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Filters */}
      <div
        style={{
          display: "flex",
          gap: "10px",
          flexWrap: "wrap",
          alignItems: "flex-end",
          background: "var(--surface2)",
          border: "1px solid var(--border)",
          borderRadius: "10px",
          padding: "16px",
        }}
      >
        <div className="field-row" style={{ flex: "1", minWidth: "140px" }}>
          <label>User</label>
          <input
            type="text"
            className="input"
            placeholder="Filter by user..."
            value={filterUser}
            onChange={(e) => handleFilterChange(setFilterUser)(e.target.value)}
          />
        </div>
        <div className="field-row" style={{ flex: "1", minWidth: "140px" }}>
          <label>Action</label>
          <select
            className="input select"
            value={filterAction}
            onChange={(e) =>
              handleFilterChange(setFilterAction)(e.target.value)
            }
          >
            <option value="">All actions</option>
            <option value="login">Login</option>
            <option value="logout">Logout</option>
            <option value="user_invite">User Invite</option>
            <option value="user_deactivate">User Deactivate</option>
            <option value="role_change">Role Change</option>
            <option value="org_update">Org Update</option>
            <option value="api_key_create">API Key Created</option>
            <option value="api_key_revoke">API Key Revoked</option>
            <option value="questionnaire_submit">Questionnaire Submit</option>
            <option value="report_generate">Report Generate</option>
          </select>
        </div>
        <div className="field-row" style={{ flex: "1", minWidth: "140px" }}>
          <label>From Date</label>
          <input
            type="date"
            className="input"
            value={filterStart}
            onChange={(e) => handleFilterChange(setFilterStart)(e.target.value)}
          />
        </div>
        <div className="field-row" style={{ flex: "1", minWidth: "140px" }}>
          <label>To Date</label>
          <input
            type="date"
            className="input"
            value={filterEnd}
            onChange={(e) => handleFilterChange(setFilterEnd)(e.target.value)}
          />
        </div>
        <button
          className="btn btn-sm"
          style={{ alignSelf: "flex-end" }}
          onClick={() => {
            setFilterUser("");
            setFilterAction("");
            setFilterStart("");
            setFilterEnd("");
            setPage(1);
          }}
        >
          Clear Filters
        </button>
      </div>

      {/* Table */}
      <div className="panel" style={{ padding: "20px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "12px",
          }}
        >
          <span style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
            {loading
              ? "Loading..."
              : `${total} event${total !== 1 ? "s" : ""} found`}
          </span>
        </div>

        {loading ? (
          <div className="panel-loading">Loading audit log...</div>
        ) : (
          <>
            <table className="supplier-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Details</th>
                  <th>IP Address</th>
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 ? (
                  <tr>
                    <td
                      colSpan="5"
                      style={{
                        textAlign: "center",
                        color: "var(--text-muted)",
                        padding: "32px",
                      }}
                    >
                      No audit events match your filters
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id}>
                      <td
                        style={{
                          fontSize: "0.8rem",
                          color: "var(--text-dim)",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td style={{ fontWeight: 600, fontSize: "0.85rem" }}>
                        {log.user_email || "—"}
                      </td>
                      <td>
                        <span
                          style={{
                            fontSize: "0.72rem",
                            fontWeight: 700,
                            padding: "2px 8px",
                            borderRadius: "999px",
                            background: "var(--surface3)",
                            color: "var(--text-dim)",
                            textTransform: "uppercase",
                            letterSpacing: "0.04em",
                          }}
                        >
                          {log.action}
                        </span>
                      </td>
                      <td
                        style={{
                          fontSize: "0.82rem",
                          color: "var(--text-dim)",
                          maxWidth: "260px",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {log.details || "—"}
                      </td>
                      <td
                        style={{
                          fontFamily: "monospace",
                          fontSize: "0.8rem",
                          color: "var(--text-muted)",
                        }}
                      >
                        {log.ip_address || "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginTop: "16px",
                  paddingTop: "12px",
                  borderTop: "1px solid var(--border)",
                }}
              >
                <span style={{ fontSize: "0.78rem", color: "var(--text-dim)" }}>
                  Page {page} of {totalPages}
                </span>
                <div style={{ display: "flex", gap: "6px" }}>
                  <button
                    className="btn btn-sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    Previous
                  </button>
                  <button
                    className="btn btn-sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Admin Settings Page
// ---------------------------------------------------------------------------

const TABS = [
  { id: "users", label: "User Management" },
  { id: "org", label: "Organization" },
  { id: "api-keys", label: "API Keys" },
  { id: "thresholds", label: "Alert Thresholds" },
  { id: "audit", label: "Audit Log" },
];

export default function AdminSettingsPage() {
  const [activeTab, setActiveTab] = useState("users");

  return (
    <div className="app">
      <main className="app-main">
        <div className="panel" style={{ marginBottom: "0" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "0",
            }}
          >
            <div>
              <h2
                style={{
                  fontSize: "1.1rem",
                  fontWeight: 700,
                  margin: "0 0 4px",
                }}
              >
                Admin Settings
              </h2>
              <p
                style={{
                  fontSize: "0.78rem",
                  color: "var(--text-dim)",
                  margin: 0,
                }}
              >
                Manage users, organization profile, API keys, alert thresholds,
                and audit history
              </p>
            </div>
          </div>
          <div className="metric-tabs" style={{ marginTop: "16px" }}>
            {TABS.map((tab) => (
              <button
                key={tab.id}
                className={activeTab === tab.id ? "active" : ""}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginTop: "20px" }}>
          {activeTab === "users" && <UserManagementTab />}
          {activeTab === "org" && <OrgSettingsTab />}
          {activeTab === "api-keys" && <ApiKeysTab />}
          {activeTab === "thresholds" && <ThresholdConfigTab />}
          {activeTab === "audit" && <AuditLogTab />}
        </div>
      </main>
    </div>
  );
}
