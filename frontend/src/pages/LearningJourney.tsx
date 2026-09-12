import { useState, useEffect, useCallback } from 'react'
import {
  getSkillMap, getRecommendation, getLesson, nextPracticeQuestion, submitPracticeAnswer,
} from '../services/api'
import { Map, Lock, CheckCircle2, Circle, Lightbulb, ArrowRight, Loader2, Sparkles } from 'lucide-react'
import clsx from 'clsx'

type SkillEvidence = {
  attempts_in_window: number; total_attempts: number; accuracy: number
  mastered: boolean; top_misconceptions: string[]; hints_used_total: number
} | null

type SkillTopic = {
  slug: string; name: string; category: string; prerequisites: string[]
  status: 'locked' | 'ready' | 'in_progress' | 'mastered'; has_practice: boolean
  evidence: SkillEvidence
}

type Recommendation = { topic: string; stage: string; reason: string; evidence: SkillEvidence }

type Lesson = {
  motivation: string; construction: string
  example: { problem: string; solution: string }; transfer: string
} | null

type Question = { question_id: string; question: string; options: string[]; hint: string | null }

type Feedback = {
  correct: boolean; correct_answer: string; explanation: string; misconception: string | null
  remediation?: { action: string; target_topic: string; reason: string; misconception?: string }
}

const STAGES = [
  { value: 'diagnostic', label: 'Diagnostic', blurb: 'A short check of where you stand' },
  { value: 'guided', label: 'Guided practice', blurb: 'Practice right after the lesson' },
  { value: 'independent', label: 'Independent practice', blurb: 'Apply it without the lesson open' },
  { value: 'review', label: 'Review', blurb: 'Spaced check that it still sticks' },
]

const STATUS_STYLE: Record<string, string> = {
  mastered: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  in_progress: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
  ready: 'border-indigo-500/40 bg-indigo-500/10 text-indigo-300',
  locked: 'border-slate-700 bg-slate-800/40 text-slate-500',
}

export default function LearningJourney() {
  const [topics, setTopics] = useState<SkillTopic[]>([])
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [activeTopic, setActiveTopic] = useState<SkillTopic | null>(null)
  const [lesson, setLesson] = useState<Lesson>(null)
  const [stage, setStage] = useState<string>('guided')

  const [question, setQuestion] = useState<Question | null>(null)
  const [selected, setSelected] = useState('')
  const [hintsUsed, setHintsUsed] = useState(0)
  const [showHint, setShowHint] = useState(false)
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [answeredInStage, setAnsweredInStage] = useState(0)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [mapData, rec] = await Promise.all([getSkillMap(), getRecommendation()])
      setTopics(mapData.topics)
      setRecommendation(rec)
    } catch {
      setError('We could not load your learning path. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const openTopic = async (topic: SkillTopic, initialStage?: string) => {
    setActiveTopic(topic)
    setStage(initialStage || (topic.evidence ? 'guided' : 'diagnostic'))
    setQuestion(null)
    setFeedback(null)
    setAnsweredInStage(0)
    try {
      const data = await getLesson(topic.slug)
      setLesson(data.lesson)
    } catch {
      setLesson(null)
    }
  }

  const startPractice = async (chosenStage: string) => {
    if (!activeTopic) return
    setStage(chosenStage)
    setFeedback(null)
    setSelected('')
    setShowHint(false)
    setHintsUsed(0)
    setBusy(true)
    try {
      const q = await nextPracticeQuestion(activeTopic.slug, chosenStage)
      setQuestion(q)
    } catch {
      setError('Could not prepare a practice question. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const submitAnswer = async () => {
    if (!question || !selected) return
    setBusy(true)
    try {
      const result = await submitPracticeAnswer(question.question_id, selected, hintsUsed)
      setFeedback(result)
      setAnsweredInStage(n => n + 1)
    } catch {
      setError('Could not submit your answer. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const nextQuestion = async () => {
    if (!activeTopic) return
    setSelected('')
    setFeedback(null)
    setShowHint(false)
    setHintsUsed(0)
    setBusy(true)
    try {
      const q = await nextPracticeQuestion(activeTopic.slug, stage)
      setQuestion(q)
    } catch {
      setError('Could not prepare the next question. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const finishStage = async () => {
    setActiveTopic(null)
    setQuestion(null)
    setFeedback(null)
    await load()
  }

  const jumpToPrerequisite = (slug: string) => {
    const target = topics.find(t => t.slug === slug)
    if (target) void openTopic(target, target.evidence ? 'guided' : 'diagnostic')
  }

  if (loading) {
    return <div className="text-center py-20 text-indigo-300"><Loader2 size={32} className="animate-spin mx-auto mb-3" /></div>
  }

  return (
    <div className="max-w-4xl mx-auto animate-fade-in">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3 mb-2">
          <Map className="text-indigo-400" size={32} /> Learning Path
        </h1>
        <p className="text-slate-400">A skill map with prerequisites: diagnostic → lesson → guided practice → independent practice → review.</p>
      </div>

      {error && <p role="alert" className="mb-4 rounded-xl border border-red-400/30 p-4 text-red-300">{error}</p>}

      {!activeTopic && recommendation && (
        <div className="mb-6 rounded-2xl border border-indigo-500/40 bg-indigo-500/10 p-5">
          <p className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-300">
            <Sparkles size={14} /> Recommended for you
          </p>
          <h2 className="text-lg font-semibold text-white mb-1">
            {topics.find(t => t.slug === recommendation.topic)?.name || recommendation.topic}
          </h2>
          <p className="text-sm text-slate-300 mb-4">{recommendation.reason}</p>
          <button
            onClick={() => { const t = topics.find(x => x.slug === recommendation.topic); if (t) void openTopic(t, recommendation.stage) }}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
          >
            Start <ArrowRight size={14} />
          </button>
        </div>
      )}

      {!activeTopic && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {topics.map(t => (
            <button
              key={t.slug}
              onClick={() => t.status !== 'locked' && void openTopic(t)}
              disabled={t.status === 'locked'}
              className={clsx('text-left rounded-xl border p-4 transition-all', STATUS_STYLE[t.status], t.status !== 'locked' && 'hover:border-indigo-400 cursor-pointer', t.status === 'locked' && 'cursor-not-allowed')}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold">{t.name}</span>
                {t.status === 'locked' ? <Lock size={14} /> : t.status === 'mastered' ? <CheckCircle2 size={14} /> : <Circle size={14} />}
              </div>
              <p className="text-xs opacity-80 capitalize">{t.status.replace('_', ' ')}{t.evidence ? ` · ${Math.round(t.evidence.accuracy * 100)}% accuracy` : ''}</p>
              {t.prerequisites.length > 0 && (
                <p className="text-xs opacity-60 mt-1">Requires: {t.prerequisites.map(p => topics.find(x => x.slug === p)?.name || p).join(', ')}</p>
              )}
              {!t.has_practice && <p className="text-xs opacity-50 mt-1">Lesson only — practice coming soon</p>}
            </button>
          ))}
        </div>
      )}

      {activeTopic && (
        <div className="space-y-5">
          <button onClick={() => setActiveTopic(null)} className="text-indigo-300 text-sm underline">← Back to skill map</button>
          <h2 className="text-2xl font-bold text-white">{activeTopic.name}</h2>

          {lesson && !question && !feedback && answeredInStage === 0 && (
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-700/50 bg-slate-800/60 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-indigo-300 mb-2">Why this matters</p>
                <p className="text-slate-200 text-sm">{lesson.motivation}</p>
              </div>
              <div className="rounded-xl border border-slate-700/50 bg-slate-800/60 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-indigo-300 mb-2">How it's built</p>
                <p className="text-slate-200 text-sm">{lesson.construction}</p>
              </div>
              <div className="rounded-xl border border-slate-700/50 bg-slate-800/60 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-indigo-300 mb-2">Worked example</p>
                <p className="text-slate-200 text-sm mb-1"><strong>Problem:</strong> {lesson.example.problem}</p>
                <p className="text-slate-300 text-sm"><strong>Solution:</strong> {lesson.example.solution}</p>
              </div>
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-amber-300 mb-2">Now try this yourself</p>
                <p className="text-slate-200 text-sm">{lesson.transfer}</p>
              </div>
            </div>
          )}

          {activeTopic.has_practice ? (
            <>
              {!question && (
                <div className="rounded-xl border border-slate-700/50 bg-slate-800/60 p-5">
                  <p className="text-slate-400 text-sm mb-3">Choose a stage:</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {STAGES.map(s => (
                      <button key={s.value} onClick={() => void startPractice(s.value)}
                        className={clsx('text-left rounded-lg border px-4 py-2.5 text-sm transition-all', stage === s.value ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-200' : 'bg-slate-700/40 border-slate-600 text-slate-300 hover:border-indigo-500/40')}>
                        <span className="font-medium block">{s.label}</span>
                        <span className="text-xs opacity-70">{s.blurb}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {question && (
                <div className="rounded-xl border border-slate-700/50 bg-slate-800/60 p-5">
                  <p className="text-xs text-indigo-300 mb-2 uppercase tracking-wider">{STAGES.find(s => s.value === stage)?.label} · Q{answeredInStage + 1}</p>
                  <p className="text-white font-medium mb-4">{question.question}</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
                    {question.options.map((opt, i) => {
                      const letter = opt.charAt(0)
                      return (
                        <button key={i} disabled={!!feedback} onClick={() => setSelected(letter)}
                          className={clsx('text-left px-4 py-2.5 rounded-lg text-sm border transition-all',
                            feedback && letter === feedback.correct_answer ? 'bg-emerald-500/20 border-emerald-500/60 text-emerald-200' :
                            feedback && letter === selected ? 'bg-red-500/20 border-red-500/60 text-red-200' :
                            selected === letter ? 'bg-indigo-500/25 border-indigo-500/60 text-indigo-200' :
                            'bg-slate-700/50 border-slate-600 text-slate-300 hover:border-indigo-500/40')}>
                          {opt}
                        </button>
                      )
                    })}
                  </div>

                  {!feedback && question.hint && (
                    <div className="mb-3">
                      {!showHint ? (
                        <button onClick={() => { setShowHint(true); setHintsUsed(h => h + 1) }} className="flex items-center gap-1.5 text-amber-300 text-xs underline">
                          <Lightbulb size={13} /> Show a hint
                        </button>
                      ) : (
                        <p className="text-xs text-amber-200 bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">{question.hint}</p>
                      )}
                    </div>
                  )}

                  {!feedback ? (
                    <button onClick={() => void submitAnswer()} disabled={!selected || busy}
                      className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white py-2.5 rounded-lg font-medium text-sm transition-colors">
                      {busy ? 'Checking…' : 'Submit answer'}
                    </button>
                  ) : (
                    <div className="space-y-3">
                      <p className={clsx('text-sm font-medium', feedback.correct ? 'text-emerald-300' : 'text-red-300')}>
                        {feedback.correct ? 'Correct!' : 'Not quite.'}
                      </p>
                      <p className="text-slate-300 text-sm">{feedback.explanation}</p>
                      {feedback.remediation && (
                        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
                          <p className="text-amber-200 text-xs mb-2">{feedback.remediation.reason}</p>
                          {feedback.remediation.action === 'revisit_prerequisite' && (
                            <button onClick={() => jumpToPrerequisite(feedback.remediation!.target_topic)} className="text-amber-300 text-xs underline">
                              Revisit {topics.find(t => t.slug === feedback.remediation!.target_topic)?.name || feedback.remediation.target_topic}
                            </button>
                          )}
                        </div>
                      )}
                      <div className="flex gap-2">
                        <button onClick={() => void nextQuestion()} disabled={busy}
                          className="flex-1 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white py-2.5 rounded-lg font-medium text-sm transition-colors">
                          Next question
                        </button>
                        <button onClick={() => void finishStage()} disabled={busy}
                          className="px-4 py-2.5 rounded-lg text-sm text-indigo-300 border border-slate-700 hover:border-indigo-500/40 transition-colors">
                          Done for now
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {answeredInStage > 0 && (
                <p className="text-slate-500 text-xs">{answeredInStage} question{answeredInStage === 1 ? '' : 's'} answered this session in {STAGES.find(s => s.value === stage)?.label.toLowerCase()}.</p>
              )}
            </>
          ) : (
            <p className="text-slate-500 text-sm">Practice questions for this topic aren't available yet — the lesson above is a preview of what's coming.</p>
          )}
        </div>
      )}
    </div>
  )
}
