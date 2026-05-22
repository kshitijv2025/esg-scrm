import { Link } from "react-router-dom";
import "./TermsPage.css";

export default function TermsPage() {
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
          <h1 className="legal-title">Terms of Service</h1>
          <p className="legal-updated">Last updated: May 21, 2026</p>

          <section className="legal-section">
            <h2>1. Acceptance of Terms</h2>
            <p>
              By accessing or using the ESG SCRM Platform, you agree to be bound
              by these Terms of Service. If you do not agree to these terms,
              please do not use our services. These terms apply to all users
              including enterprises, suppliers, and their authorized
              representatives.
            </p>
          </section>

          <section className="legal-section">
            <h2>2. Service Description</h2>
            <p>
              ESG SCRM provides enterprise supply chain risk management and
              sustainability compliance services, including:
            </p>
            <ul>
              <li>
                Supplier ESG questionnaire distribution and response collection
              </li>
              <li>
                Risk assessment and scoring across environmental, social, and
                governance dimensions
              </li>
              <li>
                Evidence vault with cryptographic hash chains for audit trails
              </li>
              <li>
                Multi-framework compliance reporting (GRI, SASB, TCFD, and
                regional standards)
              </li>
              <li>Real-time risk alerting and supply chain visibility</li>
              <li>WhatsApp Business API integration for supplier engagement</li>
            </ul>
            <p>
              We reserve the right to modify, suspend, or discontinue any part
              of the service with reasonable notice.
            </p>
          </section>

          <section className="legal-section">
            <h2>3. User Accounts</h2>
            <p>
              To access our services, you must register for an account and
              provide accurate, complete information. You are responsible for:
            </p>
            <ul>
              <li>Maintaining the confidentiality of your login credentials</li>
              <li>All activities that occur under your account</li>
              <li>Notifying us immediately of any unauthorized use</li>
              <li>Ensuring your organization's data is current and accurate</li>
            </ul>
            <p>
              Enterprise accounts may have additional terms specific to your
              organization as defined in your service agreement.
            </p>
          </section>

          <section className="legal-section">
            <h2>4. Acceptable Use</h2>
            <p>You agree not to:</p>
            <ul>
              <li>
                Use the platform for any unlawful purpose or in violation of
                these terms
              </li>
              <li>Submit false, misleading, or fraudulent supplier data</li>
              <li>
                Attempt to gain unauthorized access to any part of the platform
              </li>
              <li>
                Interfere with or disrupt the platform or servers connected to
                it
              </li>
              <li>
                Reverse engineer, decompile, or disassemble any component of the
                service
              </li>
              <li>
                Use automated tools to scrape or extract data without
                authorization
              </li>
              <li>Share your account credentials with unauthorized parties</li>
            </ul>
          </section>

          <section className="legal-section">
            <h2>5. Intellectual Property</h2>
            <p>
              The ESG SCRM Platform, including its design, features, and
              content, is owned by ESG SCRM and protected by intellectual
              property laws. You retain ownership of any data you submit to the
              platform.
            </p>
            <p>
              By submitting supplier data, questionnaires, or evidence, you
              grant us a limited license to process, store, and display that
              content as necessary to provide our services to your organization.
            </p>
            <p>
              Our hash chain and audit trail technology is proprietary and may
              not be reproduced or imitated.
            </p>
          </section>

          <section className="legal-section">
            <h2>6. Limitation of Liability</h2>
            <p>
              To the maximum extent permitted by law, ESG SCRM shall not be
              liable for any indirect, incidental, special, consequential, or
              punitive damages, including but not limited to loss of profits,
              data, or business opportunities, arising out of or related to your
              use of the platform.
            </p>
            <p>
              Our total liability for any claim arising from these terms shall
              not exceed the amount you paid for our services in the twelve
              months preceding the claim.
            </p>
            <p>
              Nothing in these terms excludes liability for death or personal
              injury caused by our negligence, fraud, or any other liability
              that cannot be limited by law.
            </p>
          </section>

          <section className="legal-section">
            <h2>7. Governing Law</h2>
            <p>
              These Terms of Service shall be governed by and construed in
              accordance with the laws of the jurisdiction in which ESG SCRM
              operates, without regard to its conflict of law provisions.
            </p>
            <p>
              Any disputes arising from these terms shall be resolved through
              binding arbitration or in the courts of the applicable
              jurisdiction.
            </p>
          </section>

          <section className="legal-section">
            <h2>8. Contact</h2>
            <p>
              For questions about these Terms of Service, please contact us:
            </p>
            <div className="legal-contact">
              <p>
                <strong>ESG SCRM Platform</strong>
                <br />
                Legal Department
                <br />
                Email:{" "}
                <a href="mailto:legal@esg-scrm.com" className="legal-link">
                  legal@esg-scrm.com
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
