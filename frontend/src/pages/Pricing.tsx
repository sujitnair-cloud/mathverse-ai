import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Check, Zap, Star, Building2, X } from 'lucide-react'
import clsx from 'clsx'
import { analytics } from '../lib/analytics'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : '/api/v1'

const PLANS = [
  {
    id: 'free',
    name: 'Free',
    icon: Star,
    price: { monthly: 0, annual: 0 },
    color: 'slate',
    badge: null,
    description: 'Perfect for casual learners',
    cta: 'Get started free',
    features: [
      { text: '10 AI solves per day', included: true },
      { text: 'Step-by-step solutions', included: true },
      { text: 'Formula library', included: true },
      { text: '5 quiz questions per session', included: true },
      { text: 'Basic graphing', included: true },
      { text: 'Full AI explanations', included: false },
      { text: 'Unlimited solves', included: false },
      { text: 'PDF export', included: false },
      { text: 'History & progress tracking', included: false },
    ],
  },
  {
    id: 'student',
    name: 'Student',
    icon: Zap,
    price: { monthly: 4.99, annual: 3.99 },
    color: 'indigo',
    badge: 'Most Popular',
    description: 'For serious students who solve daily',
    cta: 'Start 7-day free trial',
    features: [
      { text: 'Unlimited AI solves', included: true },
      { text: 'Full step-by-step solutions', included: true },
      { text: 'Complete formula library', included: true },
      { text: 'Unlimited quiz questions', included: true },
      { text: 'Advanced graphing (2D + 3D)', included: true },
      { text: 'Full AI explanations', included: true },
      { text: 'History & progress tracking', included: true },
      { text: 'PDF export', included: false },
      { text: 'Priority support', included: false },
    ],
  },
  {
    id: 'pro',
    name: 'Pro',
    icon: Building2,
    price: { monthly: 9.99, annual: 7.99 },
    color: 'purple',
    badge: 'Best Value',
    description: 'For educators and power users',
    cta: 'Start 7-day free trial',
    features: [
      { text: 'Everything in Student', included: true },
      { text: 'PDF export of solutions', included: true },
      { text: 'Priority support', included: true },
      { text: 'Early access to new features', included: true },
      { text: 'No ads (ever)', included: true },
      { text: 'API access', included: true },
      { text: 'Custom quiz sets', included: true },
      { text: 'Bulk problem solving', included: true },
    ],
  },
]

const FAQS = [
  { q: 'Can I cancel anytime?', a: 'Yes. Cancel from your billing portal with one click. You keep access until the end of your billing period.' },
  { q: 'Is there a free trial?', a: 'Student and Pro plans include a 7-day free trial. No charge until the trial ends. Cancel anytime.' },
  { q: 'What payment methods are accepted?', a: 'All major credit/debit cards (Visa, Mastercard, Amex), and UPI via Stripe.' },
  { q: 'Can I switch plans?', a: 'Yes, upgrade or downgrade anytime. Upgrades take effect immediately with prorated billing.' },
  { q: 'Do you offer student discounts?', a: 'The Student plan at $4.99/month IS the student discount. Email us with your .edu address for an extra 20% off.' },
  { q: 'Is my data safe?', a: 'All data is encrypted in transit (HTTPS) and at rest. We never sell your data. See our Privacy Policy.' },
]

export default function Pricing() {
  const [annual, setAnnual] = useState(false)
  const [loading, setLoading] = useState<string | null>(null)
  const { user, token } = useAuth()
  const navigate = useNavigate()

  const handleUpgrade = async (planId: string, price: number) => {
    if (planId === 'free') { navigate('/solver'); return }
    if (!user) { navigate('/login'); return }

    analytics.beginCheckout(planId, price)
    setLoading(planId)
    try {
      const origin = window.location.origin
      const { data } = await axios.post(`${API}/payments/create-checkout`, {
        plan: planId,
        success_url: `${origin}/pricing?success=1`,
        cancel_url: `${origin}/pricing`,
      }, { headers: { Authorization: `Bearer ${token}` } })
      window.location.href = data.checkout_url
    } catch {
      alert('Could not start checkout. Stripe payments may not be configured yet.')
    } finally {
      setLoading(null)
    }
  }

  const success = new URLSearchParams(window.location.search).get('success')

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      {/* Success banner */}
      {success && (
        <div className="mb-8 bg-emerald-500/15 border border-emerald-500/30 rounded-2xl p-5 flex items-center gap-3">
          <Check size={20} className="text-emerald-400 flex-shrink-0" />
          <div>
            <p className="text-emerald-300 font-semibold">Payment successful! Welcome to premium.</p>
            <p className="text-emerald-400/70 text-sm">Your plan is now active. Enjoy unlimited solving!</p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-4 py-1.5 text-indigo-300 text-sm mb-4">
          <Zap size={14} /> Simple, transparent pricing
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4">
          Invest in your<br />
          <span className="text-indigo-400">math skills</span>
        </h1>
        <p className="text-slate-400 text-lg max-w-xl mx-auto">
          Start free. Upgrade when you need unlimited power. Cancel anytime.
        </p>

        {/* Annual toggle */}
        <div className="flex items-center justify-center gap-3 mt-8">
          <span className={clsx('text-sm', !annual ? 'text-white' : 'text-slate-400')}>Monthly</span>
          <button
            onClick={() => setAnnual(a => !a)}
            className={clsx(
              'relative w-12 h-6 rounded-full transition-colors',
              annual ? 'bg-indigo-600' : 'bg-slate-600'
            )}
          >
            <span className={clsx(
              'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
              annual ? 'translate-x-7' : 'translate-x-1'
            )} />
          </button>
          <span className={clsx('text-sm', annual ? 'text-white' : 'text-slate-400')}>
            Annual <span className="text-emerald-400 text-xs font-semibold ml-1">Save 20%</span>
          </span>
        </div>
      </div>

      {/* Plans */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
        {PLANS.map(plan => {
          const price = annual ? plan.price.annual : plan.price.monthly
          const Icon = plan.icon
          const isPopular = plan.badge === 'Most Popular'
          const isPro = plan.id === 'pro'

          return (
            <div
              key={plan.id}
              className={clsx(
                'relative rounded-2xl border p-6 flex flex-col transition-all',
                isPopular
                  ? 'border-indigo-500/60 bg-indigo-950/40 shadow-xl shadow-indigo-500/10 scale-[1.02]'
                  : isPro
                  ? 'border-purple-500/40 bg-purple-950/20'
                  : 'border-slate-700/50 bg-slate-800/40'
              )}
            >
              {plan.badge && (
                <div className={clsx(
                  'absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-xs font-semibold',
                  isPopular ? 'bg-indigo-500 text-white' : 'bg-purple-500 text-white'
                )}>
                  {plan.badge}
                </div>
              )}

              {/* Plan header */}
              <div className="mb-6">
                <div className={clsx(
                  'w-10 h-10 rounded-xl flex items-center justify-center mb-3',
                  isPopular ? 'bg-indigo-500/20' : isPro ? 'bg-purple-500/20' : 'bg-slate-700/50'
                )}>
                  <Icon size={20} className={isPopular ? 'text-indigo-400' : isPro ? 'text-purple-400' : 'text-slate-400'} />
                </div>
                <h3 className="text-lg font-bold text-white mb-1">{plan.name}</h3>
                <p className="text-slate-400 text-sm">{plan.description}</p>
              </div>

              {/* Price */}
              <div className="mb-6">
                <div className="flex items-end gap-1">
                  <span className="text-4xl font-bold text-white">
                    {price === 0 ? 'Free' : `$${price}`}
                  </span>
                  {price > 0 && <span className="text-slate-400 text-sm mb-1">/month</span>}
                </div>
                {annual && price > 0 && (
                  <p className="text-emerald-400 text-xs mt-1">
                    Billed ${(price * 12).toFixed(0)}/year · Save ${((plan.price.monthly - price) * 12).toFixed(0)}
                  </p>
                )}
              </div>

              {/* CTA */}
              <button
                onClick={() => handleUpgrade(plan.id, price)}
                disabled={loading === plan.id}
                className={clsx(
                  'w-full py-3 rounded-xl font-semibold text-sm transition-all mb-6',
                  loading === plan.id ? 'opacity-60 cursor-not-allowed' : '',
                  isPopular
                    ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/25'
                    : isPro
                    ? 'bg-purple-600 hover:bg-purple-500 text-white'
                    : 'bg-slate-700 hover:bg-slate-600 text-white'
                )}
              >
                {loading === plan.id ? 'Redirecting…' : plan.cta}
              </button>

              {/* Features */}
              <ul className="space-y-2.5 flex-1">
                {plan.features.map((f, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm">
                    {f.included
                      ? <Check size={15} className={clsx('flex-shrink-0 mt-0.5', isPopular ? 'text-indigo-400' : isPro ? 'text-purple-400' : 'text-emerald-400')} />
                      : <X size={15} className="flex-shrink-0 mt-0.5 text-slate-600" />}
                    <span className={f.included ? 'text-slate-300' : 'text-slate-600'}>{f.text}</span>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>

      {/* Trust badges */}
      <div className="flex flex-wrap justify-center gap-6 mb-16 text-sm text-slate-400">
        {['🔒 Secured by Stripe', '✅ Cancel anytime', '7-day free trial', '💳 No hidden fees', '🌍 Works worldwide'].map(t => (
          <span key={t} className="bg-slate-800/60 border border-slate-700/50 px-4 py-2 rounded-full">{t}</span>
        ))}
      </div>

      {/* FAQ */}
      <div className="max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold text-white text-center mb-8">Frequently asked questions</h2>
        <div className="space-y-4">
          {FAQS.map((faq, i) => (
            <div key={i} className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5">
              <p className="font-semibold text-white mb-2">{faq.q}</p>
              <p className="text-slate-400 text-sm leading-relaxed">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
