import { useIntl, defineMessages } from "react-intl";

const LOCALES = [
  { code: "en", label: "English" },
  { code: "bn", label: "বাংলা" },
  { code: "vi", label: "Tiếng Việt" },
];

const messages = {
  en: () => import("../locales/en.json"),
  bn: () => import("../locales/bn.json"),
  vi: () => import("../locales/vi.json"),
};

const LEGACY_MESSAGES = {
  en: {
    lang_selector_label: "Language",
  },
  bn: {
    lang_selector_label: "ভাষা",
  },
  vi: {
    lang_selector_label: "Ngôn ngữ",
  },
};

// Dynamic locale loading with lazy JSON imports
export async function loadLocaleMessages(locale) {
  const loader = messages[locale];
  if (!loader) return {};
  try {
    const mod = await loader();
    return mod.default || {};
  } catch {
    return LEGACY_MESSAGES[locale] || {};
  }
}

export const SUPPORTED_LOCALES = LOCALES;

export default function LanguageSelector({ value, onChange }) {
  const intl = useIntl();

  return (
    <div className="lang-selector">
      <label className="lang-selector-label">
        {intl.formatMessage({ id: "lang_selector.label" })}
      </label>
      <select
        className="lang-selector-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {LOCALES.map((locale) => (
          <option key={locale.code} value={locale.code}>
            {locale.label}
          </option>
        ))}
      </select>
    </div>
  );
}
