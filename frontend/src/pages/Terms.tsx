import { FileText } from 'lucide-react'

export default function Terms() {
  return (
    <div className="max-w-3xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center">
            <FileText size={20} className="text-indigo-400" />
          </div>
          <span className="text-xs font-semibold uppercase tracking-widest text-indigo-400">Legal</span>
        </div>
        <h1 className="text-3xl font-bold text-white mb-2">Terms of Service</h1>
        <p className="text-slate-400 text-sm">Last updated: June 19, 2026</p>
      </div>

      <div className="prose-legal">
        <p>
          By accessing or using MathVerse AI at <a href="https://mathverseai.org">mathverseai.org</a>,
          you agree to be bound by these Terms of Service. If you do not agree with any part of these
          terms, you may not access the Service.
        </p>

        <h2>1. Use of Service</h2>
        <p>
          MathVerse AI grants you a limited, non-exclusive, non-transferable licence to access and use
          the Service for personal, non-commercial educational purposes. You must not misuse the Service,
          attempt to gain unauthorised access, or use it in any way that could damage, disable, or
          impair the Service.
        </p>

        <h2>2. Accounts</h2>
        <p>
          When you create an account via Google Sign-In, you are responsible for maintaining the
          security of your account and for all activities that occur under it. You must notify us
          immediately at <a href="mailto:shilpy.tandon@gmail.com">shilpy.tandon@gmail.com</a> of any
          unauthorised use.
        </p>

        <h2>3. Subscriptions and Payments</h2>
        <p>
          Paid plans (Student, Pro) are billed monthly or annually through Stripe. Subscriptions
          auto-renew unless cancelled before the renewal date. No refunds are issued for partial
          billing periods. You may cancel at any time via your account settings.
        </p>

        <h2>4. Free Tier Limits</h2>
        <p>
          Free accounts are limited to 10 problem solves per day. We reserve the right to change
          these limits at any time with reasonable notice.
        </p>

        <h2>5. Intellectual Property</h2>
        <p>
          All content, features, and functionality of MathVerse AI — including but not limited to
          text, graphics, logos, icons, and software — are the exclusive property of MathVerse AI
          and are protected by intellectual property laws. You may not reproduce, distribute, or
          create derivative works without prior written permission.
        </p>

        <h2>6. User Content</h2>
        <p>
          Math problems and queries you submit are processed to provide the Service. We do not claim
          ownership over your submitted content. By using the Service, you grant us a limited licence
          to process your inputs solely for the purpose of delivering results to you.
        </p>

        <h2>7. Disclaimer of Warranties</h2>
        <p>
          The Service is provided on an "AS IS" and "AS AVAILABLE" basis without warranties of any
          kind, either express or implied. Mathematical results are provided for educational purposes
          — always verify critical calculations independently.
        </p>

        <h2>8. Limitation of Liability</h2>
        <p>
          To the maximum extent permitted by law, MathVerse AI shall not be liable for any indirect,
          incidental, special, consequential, or punitive damages arising from your use of the Service.
        </p>

        <h2>9. Governing Law</h2>
        <p>
          These Terms shall be governed by the laws of India without regard to its conflict of law
          provisions. Any disputes shall be subject to the exclusive jurisdiction of the courts of
          Haryana, India.
        </p>

        <h2>10. Changes to Terms</h2>
        <p>
          We reserve the right to modify these Terms at any time. We will post the updated Terms on
          this page and update the "Last updated" date. Continued use of the Service after changes
          constitutes acceptance of the new Terms.
        </p>

        <h2>11. Contact Us</h2>
        <p>For any questions about these Terms, contact us:</p>
        <ul>
          <li>By email: <a href="mailto:shilpy.tandon@gmail.com">shilpy.tandon@gmail.com</a></li>
          <li>Website: <a href="https://mathverseai.org">mathverseai.org</a></li>
        </ul>
      </div>
    </div>
  )
}
