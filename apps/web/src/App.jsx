import { useState, useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { IntlProvider } from "react-intl";
import { AuthProvider, RequireAuth } from "./contexts/AuthContext";
import { ToastProvider } from "./components/Toast";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import AdminSettingsPage from "./pages/AdminSettingsPage";
import OnboardingWizard from "./pages/OnboardingWizard";
import BuyerPortalPage from "./pages/BuyerPortalPage";
import PrivacyPage from "./pages/PrivacyPage";
import TermsPage from "./pages/TermsPage";
import PricingPage from "./pages/PricingPage";

const MESSAGES = {
  en: {
    "app.title": "ESG Supply Chain Platform",
    "nav.operations": "Operations",
    "nav.supplyChain": "Supply Chain",
    "nav.riskAlerts": "Risk Alerts",
    "nav.frameworks": "Frameworks",
    "nav.engagement": "Engagement",
    "nav.templates": "Templates",
    "eng.responded": "Responded",
    "eng.pending": "Pending",
    "eng.total": "Total",
    "eng.sendEmail": "Send Email",
    "eng.portalLink": "Portal Link",
    "eng.manualEntry": "Manual Entry",
    "eng.view.chasing": "Chasing",
    "confidence.high": "High",
    "confidence.medium": "Medium",
    "confidence.low": "Low",
    "supplier.status.pending": "Pending",
    "supplier.status.responded": "Responded",
    "supplier.status.notStarted": "Not Started",
    "chase.stage.whatsapp": "WhatsApp Pending",
    "chase.stage.email": "Email Reminder",
    "chase.stage.riskFlag": "Risk Flag",
    "chase.runButton": "Run Chase Workflow",
    "template.new": "New Template",
    "template.save": "Save Template",
    "template.delete": "Delete Template",
    "template.name": "Template Name",
    "template.description": "Description",
    "template.tier": "Target Tier",
    "question.add": "Add Question",
    "question.remove": "Remove",
    "question.questionId": "Question ID",
    "question.text": "Question Text",
    "question.type": "Type",
    "question.required": "Required",
    "question.choices": "Choices (one per line)",
    "question.type.number": "Number",
    "question.type.choice": "Choice",
    "question.type.text": "Text",
    "lang_selector.label": "Language",
  },
  bn: {
    "app.title": "ইএসজি সাপ্লাই চেইন প্ল্যাটফর্ম",
    "nav.operations": "অপারেশন",
    "nav.supplyChain": "সাপ্লাই চেইন",
    "nav.riskAlerts": "ঝুঁকি সতর্কতা",
    "nav.frameworks": "ফ্রেমওয়ার্ক",
    "nav.engagement": "এনগেজমেন্ট",
    "nav.templates": "টেমপ্লেট",
    "eng.responded": "উত্তর দিয়েছে",
    "eng.pending": "অপেক্ষমাণ",
    "eng.total": "মোট",
    "eng.sendEmail": "ইমেইল পাঠান",
    "eng.portalLink": "পোর্টাল লিংক",
    "eng.manualEntry": "ম্যানুয়াল এন্ট্রি",
    "eng.view.chasing": "চেজিং",
    "confidence.high": "উচ্চ",
    "confidence.medium": "মাঝারি",
    "confidence.low": "নিম্ন",
    "supplier.status.pending": "অপেক্ষমাণ",
    "supplier.status.responded": "উত্তর দিয়েছে",
    "supplier.status.notStarted": "শুরু হয়নি",
    "chase.stage.whatsapp": "হোয়াটসঅ্যাপ প্রতীক্ষিত",
    "chase.stage.email": "ইমেইল রিমাইন্ডার",
    "chase.stage.riskFlag": "ঝুঁকি ফ্ল্যাগ",
    "chase.runButton": "চেজ ওয়ার্কফ্লো চালান",
    "template.new": "নতুন টেমপ্লেট",
    "template.save": "টেমপ্লেট সংরক্ষণ",
    "template.delete": "টেমপ্লেট মুছুন",
    "template.name": "টেমপ্লেট নাম",
    "template.description": "বিবরণ",
    "template.tier": "লক্ষ্য টায়ার",
    "question.add": "প্রশ্ন যোগ করুন",
    "question.remove": "সরান",
    "question.questionId": "প্রশ্ন আইডি",
    "question.text": "প্রশ্নের টেক্সট",
    "question.type": "ধরন",
    "question.required": "আবশ্যক",
    "question.choices": "বিকল্প (প্রতি লাইনে একটি)",
    "question.type.number": "সংখ্যা",
    "question.type.choice": "পছন্দ",
    "question.type.text": "টেক্সট",
    "lang_selector.label": "ভাষা",
  },
  vi: {
    "app.title": "Nền tảng Chuỗi Cung ứng ESG",
    "nav.operations": "Vận hành",
    "nav.supplyChain": "Chuỗi cung ứng",
    "nav.riskAlerts": "Cảnh báo rủi ro",
    "nav.frameworks": "Khung",
    "nav.engagement": "Tương tác",
    "nav.templates": "Mẫu",
    "eng.responded": "Đã phản hồi",
    "eng.pending": "Đang chờ",
    "eng.total": "Tổng",
    "eng.sendEmail": "Gửi Email",
    "eng.portalLink": "Liên kết Cổng",
    "eng.manualEntry": "Nhập thủ công",
    "eng.view.chasing": "Theo dõi",
    "confidence.high": "Cao",
    "confidence.medium": "Trung bình",
    "confidence.low": "Thấp",
    "supplier.status.pending": "Đang chờ",
    "supplier.status.responded": "Đã phản hồi",
    "supplier.status.notStarted": "Chưa bắt đầu",
    "chase.stage.whatsapp": "WhatsApp đang chờ",
    "chase.stage.email": "Nhắc qua Email",
    "chase.stage.riskFlag": "Cờ rủi ro",
    "chase.runButton": "Chạy Quy trình theo dõi",
    "template.new": "Mẫu mới",
    "template.save": "Lưu mẫu",
    "template.delete": "Xóa mẫu",
    "template.name": "Tên mẫu",
    "template.description": "Mô tả",
    "template.tier": "Tầng mục tiêu",
    "question.add": "Thêm câu hỏi",
    "question.remove": "Xóa",
    "question.questionId": "ID câu hỏi",
    "question.text": "Nội dung câu hỏi",
    "question.type": "Loại",
    "question.required": "Bắt buộc",
    "question.choices": "Các lựa chọn (mỗi dòng một)",
    "question.type.number": "Số",
    "question.type.choice": "Chọn",
    "question.type.text": "Văn bản",
    "lang_selector.label": "Ngôn ngữ",
  },
};

export const SUPPORTED_LOCALES = [
  { code: "en", label: "English" },
  { code: "bn", label: "বাংলা" },
  { code: "vi", label: "Tiếng Việt" },
];

export default function App() {
  const [locale, setLocale] = useState(
    () => localStorage.getItem("esg_locale") || "en",
  );

  function handleLocaleChange(newLocale) {
    localStorage.setItem("esg_locale", newLocale);
    setLocale(newLocale);
  }

  return (
    <IntlProvider
      locale={locale}
      messages={MESSAGES[locale] || MESSAGES.en}
      defaultLocale="en"
    >
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/onboarding" element={<OnboardingWizard />} />
            <Route path="/buyer-portal/:token" element={<BuyerPortalPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/pricing" element={<PricingPage />} />
            <Route
              path="/admin-settings"
              element={
                <RequireAuth>
                  <AdminSettingsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/*"
              element={
                <RequireAuth>
                  <DashboardPage
                    locale={locale}
                    onLocaleChange={handleLocaleChange}
                  />
                </RequireAuth>
              }
            />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </IntlProvider>
  );
}
