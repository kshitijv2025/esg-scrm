import { Link } from "react-router-dom";
import "./PrivacyPage.css";

export default function PrivacyPage() {
  return (
    <div className="legal-page">
      <header className="legal-header">
        <div className="legal-header-content">
          <Link to="/" className="legal-logo">
            <span className="legal-logo-text">ESG SCRM</span>
          </Link>
        </div>
      </header>

      <main className="legal-main">
        <div className="legal-container">
          <h1 className="legal-title">Privacy Policy</h1>
          <p className="legal-updated">Last updated: May 21, 2026</p>

          <section className="legal-section">
            <h2>1. Data Collection</h2>
            <p>
              We collect information you provide directly to us, including name,
              email address, company information, and ESG-related supplier data.
              This includes questionnaire responses, evidence documents, and
              sustainability metrics submitted through our platform.
            </p>
            <p>
              We also collect usage data including IP addresses, browser type,
              pages visited, and interaction patterns to improve our service
              delivery and security.
            </p>
          </section>

          <section className="legal-section">
            <h2>2. Data Use</h2>
            <p>We use the information we collect to:</p>
            <ul>
              <li>
                Provide, maintain, and improve our ESG supply chain management
                services
              </li>
              <li>
                Process and analyze supplier sustainability questionnaires
              </li>
              <li>Generate risk assessments and compliance reports</li>
              <li>
                Communicate with you about your account and service updates
              </li>
              <li>Ensure platform security and prevent fraud</li>
              <li>
                Comply with legal obligations under applicable ESG regulations
              </li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>3. Data Storage and Security</h2>
            <p>
              Your data is stored in secure, SOC 2 Type II compliant data
              centers with encryption at rest and in transit. We implement
              industry-standard security measures including access controls,
              audit logging, and regular security assessments.
            </p>
            <p>
              ESG evidence documents are cryptographically hashed to ensure
              tamper-evidence, and our hash chain technology provides verifiable
              audit trails for compliance purposes.
            </p>
          </section>

          <section className="legal-section">
            <h2>4. Cookies</h2>
            <p>
              We use cookies and similar tracking technologies to operate our
              platform. Essential cookies are required for authentication and
              security. Analytics cookies help us understand how visitors
              interact with our platform. You can control cookie preferences
              through your browser settings.
            </p>
          </section>

          <section className="legal-section">
            <h2>5. User Rights (GDPR and Similar Regulations)</h2>
            <p>Depending on your jurisdiction, you may have the right to:</p>
            <ul>
              <li>
                <strong>Access:</strong> Request a copy of your personal data
              </li>
              <li>
                <strong>Rectification:</strong> Request correction of inaccurate
                data
              </li>
              <li>
                <strong>Erasure:</strong> Request deletion of your data ("right
                to be forgotten")
              </li>
              <li>
                <strong>Portability:</strong> Receive your data in a structured,
                machine-readable format
              </li>
              <li>
                <strong>Object:</strong> Object to processing of your personal
                data
              </li>
              <li>
                <strong>Restrict:</strong> Request restriction of processing in
                certain circumstances
              </li>
            </ul>
            <p>
              To exercise these rights, contact our Data Protection Officer at{" "}
              <a href="mailto:privacy@esg-scrm.com" className="legal-link">
                privacy@esg-scrm.com
              </a>
              .
            </p>
          </section>

          <section className="legal-section">
            <h2>6. Data Retention</h2>
            <p>
              We retain your personal data for as long as your account is active
              or as needed to provide services. ESG compliance data and audit
              trails are retained for a minimum of 7 years to meet regulatory
              requirements. When data is no longer necessary, we securely delete
              or anonymize it.
            </p>
          </section>

          <section className="legal-section">
            <h2>7. Contact Information</h2>
            <p>
              If you have questions about this Privacy Policy or our data
              practices, please contact us:
            </p>
            <div className="legal-contact">
              <p>
                <strong>ESG SCRM Platform</strong>
                <br />
                Data Protection Officer
                <br />
                Email:{" "}
                <a href="mailto:privacy@esg-scrm.com" className="legal-link">
                  privacy@esg-scrm.com
                </a>
              </p>
            </div>
          </section>

          <div className="legal-footer-link">
            <Link to="/" className="legal-back-link">
              Back to Application
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
