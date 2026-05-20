import React, { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../api/client";
import { ErrorState } from "../components/ErrorState";
import LanguageSelector from "../components/LanguageSelector";

const QUESTION_TYPES = [
  { value: "text", label: "Text" },
  { value: "number", label: "Number" },
  { value: "choice", label: "Choice" },
];

const TIERS = [
  { value: 1, label: "Tier 1 — Full ESG" },
  { value: 2, label: "Tier 2 — Environmental Focus" },
  { value: 3, label: "Tier 3 — Quick Screening" },
  { value: 4, label: "Tier 4 — Basic" },
];

function generateId() {
  return Math.random().toString(36).slice(2, 8);
}

function WhatsAppPreview({ questions, locale = "en" }) {
  if (!questions || questions.length === 0) {
    return (
      <div className="wa-preview empty">
        <p>Add questions to see the WhatsApp preview</p>
      </div>
    );
  }

  function questionText(q) {
    if (locale === "bn" && q.text_bn) return q.text_bn;
    if (locale === "vi" && q.text_vi) return q.text_vi;
    return q.text || "";
  }

  const lines = questions.map((q, i) => {
    const num = q.sort_order || i + 1;
    const typeHint =
      q.question_type === "number"
        ? " [number]"
        : q.question_type === "choice"
          ? ` [${(q.choices || "A/B").split(",")[0]}, ...}]`
          : "";
    return `${num}. ${questionText(q)}${typeHint}`;
  });
  return (
    <div className="wa-preview">
      <div className="wa-preview-header">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z" />
          <path d="M12 0C5.373 0 0 5.373 0 12c0 2.11.547 4.11 1.472 5.823L0 24l6.335-1.653A11.94 11.94 0 0 0 12 22.99V23c6.627 0 12-5.373 12-12S18.627 0 12 0z" />
        </svg>
        WhatsApp Preview
      </div>
      <div className="wa-preview-body">
        <div className="wa-message">
          <p className="wa-greeting">
            Hello! Please complete your ESG assessment.
          </p>
          {lines.map((line, i) => (
            <p key={i} className="wa-line">
              {line}
            </p>
          ))}
          <p className="wa-closing">
            Reply with numbers separated by newlines, e.g.:
            4200000&#10;1500&#10;Yes
          </p>
        </div>
      </div>
    </div>
  );
}

function QuestionEditor({
  question,
  index,
  total,
  onChange,
  onRemove,
  onMoveUp,
  onMoveDown,
}) {
  function update(field, value) {
    onChange({ ...question, [field]: value });
  }

  function updateChoice(value) {
    const choices = value
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean);
    update("choices", choices);
  }

  return (
    <div className="question-editor-card">
      <div className="question-editor-header">
        <span className="question-number">Q{index + 1}</span>
        <div className="question-sort-btns">
          <button
            className="sort-btn"
            onClick={onMoveUp}
            disabled={index === 0}
            title="Move up"
          >
            ↑
          </button>
          <button
            className="sort-btn"
            onClick={onMoveDown}
            disabled={index === total - 1}
            title="Move down"
          >
            ↓
          </button>
        </div>
        <button
          className="remove-btn"
          onClick={onRemove}
          title="Remove question"
        >
          ✕
        </button>
      </div>

      <div className="question-editor-body">
        <div className="field-row">
          <label>Question ID</label>
          <input
            type="text"
            value={question.question_id}
            onChange={(e) => update("question_id", e.target.value)}
            placeholder="e.g. T1Q1"
            className="input"
          />
        </div>

        <div className="field-row">
          <label>Question Text (English) *</label>
          <textarea
            value={question.text}
            onChange={(e) => update("text", e.target.value)}
            placeholder="Enter the question text..."
            className="input textarea"
            rows={2}
          />
        </div>

        <div className="field-row">
          <label>Question Text (Bengali — বাংলা)</label>
          <textarea
            value={question.text_bn || ""}
            onChange={(e) => update("text_bn", e.target.value)}
            placeholder="আপনার প্রশ্নের বাংলা অনুবাদ এখানে লিখুন..."
            className="input textarea"
            rows={2}
          />
        </div>

        <div className="field-row">
          <label>Question Text (Vietnamese — Tiếng Việt)</label>
          <textarea
            value={question.text_vi || ""}
            onChange={(e) => update("text_vi", e.target.value)}
            placeholder="Nhập bản dịch tiếng Việt của câu hỏi tại đây..."
            className="input textarea"
            rows={2}
          />
        </div>

        <div className="field-row-inline">
          <div className="field-col">
            <label>Type</label>
            <select
              value={question.question_type}
              onChange={(e) => update("question_type", e.target.value)}
              className="input select"
            >
              {QUESTION_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <div className="field-col">
            <label>Required</label>
            <label className="toggle">
              <input
                type="checkbox"
                checked={question.required !== false}
                onChange={(e) => update("required", e.target.checked)}
              />
              <span>{question.required !== false ? "Yes" : "No"}</span>
            </label>
          </div>
        </div>

        {question.question_type === "choice" && (
          <div className="field-row">
            <label>Choices (comma-separated)</label>
            <input
              type="text"
              value={(question.choices || []).join(", ")}
              onChange={(e) => updateChoice(e.target.value)}
              placeholder="e.g. Yes, No, In progress"
              className="input"
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default function TemplateBuilder() {
  const [templates, setTemplates] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saveStatus, setSaveStatus] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [selectedLocale, setSelectedLocale] = useState("en");

  const [form, setForm] = useState({
    name: "",
    description: "",
    tier: 1,
    questions: [],
  });

  const loadTemplates = useCallback(() => {
    setLoading(true);
    setError(null);
    apiFetch("/templates")
      .then((r) => r.json())
      .then((d) => {
        setTemplates(d.templates || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load templates");
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  function selectTemplate(id) {
    setSelectedId(id);
    setIsEditing(false);
    setSaveStatus(null);
    const tmpl = templates.find((t) => t.id === id);
    if (tmpl) {
      apiFetch(`/templates/${id}`)
        .then((r) => r.json())
        .then((data) => {
          setForm({
            name: data.name || "",
            description: data.description || "",
            tier: data.tier || 1,
            questions: data.questions || [],
          });
          if (
            data.questions &&
            data.questions.length > 0 &&
            data.questions[0].text_bn
          ) {
            setSelectedLocale("bn");
          } else if (
            data.questions &&
            data.questions.length > 0 &&
            data.questions[0].text_vi
          ) {
            setSelectedLocale("vi");
          } else {
            setSelectedLocale("en");
          }
        })
        .catch(() => {});
    }
  }

  function startNew() {
    setSelectedId(null);
    setIsEditing(true);
    setForm({ name: "", description: "", tier: 1, questions: [] });
    setSaveStatus(null);
  }

  function addQuestion() {
    const newQ = {
      question_id: `Q${form.questions.length + 1}`,
      text: "",
      text_bn: "",
      text_vi: "",
      question_type: "text",
      choices: null,
      required: true,
    };
    setForm({ ...form, questions: [...form.questions, newQ] });
  }

  function updateQuestion(index, updated) {
    const questions = [...form.questions];
    questions[index] = updated;
    // Re-index sort_order
    questions.forEach((q, i) => {
      q.sort_order = i + 1;
    });
    setForm({ ...form, questions });
  }

  function removeQuestion(index) {
    const questions = form.questions.filter((_, i) => i !== index);
    questions.forEach((q, i) => {
      q.sort_order = i + 1;
    });
    setForm({ ...form, questions });
  }

  function moveQuestion(index, direction) {
    const questions = [...form.questions];
    const target = index + direction;
    if (target < 0 || target >= questions.length) return;
    [questions[index], questions[target]] = [
      questions[target],
      questions[index],
    ];
    questions.forEach((q, i) => {
      q.sort_order = i + 1;
    });
    setForm({ ...form, questions });
  }

  function updateField(field, value) {
    setForm({ ...form, [field]: value });
  }

  async function saveTemplate() {
    if (!form.name.trim()) {
      setSaveStatus({ ok: false, message: "Template name is required" });
      return;
    }
    if (form.questions.length === 0) {
      setSaveStatus({
        ok: false,
        message: "At least one question is required",
      });
      return;
    }
    for (let i = 0; i < form.questions.length; i++) {
      const q = form.questions[i];
      if (!q.text.trim()) {
        setSaveStatus({
          ok: false,
          message: `Question ${i + 1} text is empty`,
        });
        return;
      }
      if (!q.question_id.trim()) {
        setSaveStatus({ ok: false, message: `Question ${i + 1} ID is empty` });
        return;
      }
    }

    setSaveStatus({ ok: null, message: "Saving..." });
    const body = {
      name: form.name,
      description: form.description,
      tier: form.tier,
      questions: form.questions.map((q) => ({
        question_id: q.question_id,
        text: q.text,
        text_bn: q.text_bn || null,
        text_vi: q.text_vi || null,
        question_type: q.question_type,
        choices: q.choices,
        required: q.required,
      })),
    };

    try {
      let res;
      if (selectedId) {
        res = await apiFetch(`/templates/${selectedId}`, {
          method: "PUT",
          body: JSON.stringify(body),
        });
      } else {
        res = await apiFetch("/templates", {
          method: "POST",
          body: JSON.stringify(body),
        });
      }
      const data = await res.json();
      if (!res.ok) {
        setSaveStatus({ ok: false, message: data.detail || "Save failed" });
      } else {
        setSaveStatus({
          ok: true,
          message: selectedId ? "Template updated" : "Template created",
        });
        setIsEditing(false);
        loadTemplates();
        if (!selectedId && data.id) {
          setSelectedId(data.id);
        }
      }
    } catch (err) {
      setSaveStatus({ ok: false, message: err.message || "Save failed" });
    }
  }

  async function deleteTemplate() {
    if (!selectedId) return;
    if (!window.confirm("Delete this template? This cannot be undone.")) return;
    try {
      const res = await apiFetch(`/templates/${selectedId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setSelectedId(null);
        setForm({ name: "", description: "", tier: 1, questions: [] });
        loadTemplates();
      }
    } catch {}
  }

  if (error) return <ErrorState message={error} onRetry={loadTemplates} />;

  return (
    <div className="panel template-builder-panel">
      <h2>Template Builder</h2>
      <p className="panel-subtitle">
        Design ESG questionnaires · Mobile WhatsApp preview
      </p>

      <div className="template-builder-layout">
        {/* Left: Template list + editor */}
        <div className="template-editor-col">
          <div className="template-list-row">
            <select
              value={selectedId || ""}
              onChange={(e) => selectTemplate(Number(e.target.value))}
              className="input select"
            >
              <option value="">— Select a template —</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  [Tier {t.tier}] {t.name}
                </option>
              ))}
            </select>
            <button className="btn btn-primary" onClick={startNew}>
              + New
            </button>
          </div>

          {(selectedId || isEditing) && (
            <div className="template-edit-form">
              <div className="field-row">
                <label>Template Name *</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => updateField("name", e.target.value)}
                  placeholder="e.g. Tier 1 Supplier — Full ESG Assessment"
                  className="input"
                />
              </div>

              <div className="field-row">
                <label>Description</label>
                <textarea
                  value={form.description}
                  onChange={(e) => updateField("description", e.target.value)}
                  placeholder="Brief description of this template..."
                  className="input textarea"
                  rows={2}
                />
              </div>

              <div className="field-row">
                <label>Tier</label>
                <select
                  value={form.tier}
                  onChange={(e) => updateField("tier", Number(e.target.value))}
                  className="input select"
                >
                  {TIERS.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="questions-section">
                <div className="questions-section-header">
                  <h3>Questions ({form.questions.length})</h3>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={addQuestion}
                  >
                    + Add Question
                  </button>
                </div>

                {form.questions.length === 0 && (
                  <p className="no-questions">
                    No questions yet. Click "+ Add Question" to start.
                  </p>
                )}

                {form.questions.map((q, i) => (
                  <QuestionEditor
                    key={q.question_id + i}
                    question={q}
                    index={i}
                    total={form.questions.length}
                    onChange={(updated) => updateQuestion(i, updated)}
                    onRemove={() => removeQuestion(i)}
                    onMoveUp={() => moveQuestion(i, -1)}
                    onMoveDown={() => moveQuestion(i, 1)}
                  />
                ))}
              </div>

              {saveStatus && (
                <div
                  className={`save-status ${saveStatus.ok === false ? "error" : saveStatus.ok === true ? "success" : "info"}`}
                >
                  {saveStatus.message}
                </div>
              )}

              <div className="form-actions">
                <button
                  className="btn btn-primary"
                  onClick={saveTemplate}
                  disabled={saveStatus?.message === "Saving..."}
                >
                  {selectedId ? "Update Template" : "Create Template"}
                </button>
                {selectedId && (
                  <button className="btn btn-danger" onClick={deleteTemplate}>
                    Delete
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right: WhatsApp preview */}
        <div className="wa-preview-col">
          <div className="wa-preview-locale-row">
            <LanguageSelector
              value={selectedLocale}
              onChange={(locale) => setSelectedLocale(locale)}
            />
          </div>
          <WhatsAppPreview questions={form.questions} locale={selectedLocale} />
        </div>
      </div>
    </div>
  );
}
