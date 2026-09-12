import { useEffect, useState, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { BookOpen, ArrowLeft, Users } from 'lucide-react'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'

type Classroom = { id: number; name: string; role: 'teacher' | 'student'; join_code: string | null }
type Assignment = { id: number; title: string; instructions: string; due_at: string | null }
type Submission = { id: number; assignment_id: number; student_name: string; work: string; score: number | null; feedback: string | null; submitted_at: string }
type Detail = Classroom & { member_count: number; assignments: Assignment[]; submissions: Submission[] }
const panel = 'rounded-2xl border border-slate-700 bg-slate-800/60 p-5 sm:p-6'
const field = 'mt-2 w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white'
const button = 'rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-500 disabled:opacity-50'

export default function Classrooms() {
  const { user } = useAuth()
  const [classes, setClasses] = useState<Classroom[]>([])
  const [detail, setDetail] = useState<Detail | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const load = async () => setClasses((await api.get('/classrooms')).data)
  const open = async (id: number) => setDetail((await api.get(`/classrooms/${id}`)).data)
  const act = async (operation: () => Promise<void>) => {
    setBusy(true); setError(''); setNotice('')
    try { await operation() } catch (e) {
      const message = axios.isAxiosError(e) ? e.response?.data?.detail : null
      setError(typeof message === 'string' ? message : 'We could not complete that action. Please try again.')
    } finally { setBusy(false) }
  }
  useEffect(() => { setDetail(null); setClasses([]); if (user) void act(load) }, [user?.id])

  if (!user) return <div className="mx-auto max-w-xl py-16 text-center">
    <BookOpen className="mx-auto mb-4 text-indigo-300" size={40} />
    <h1 className="mb-3 text-3xl font-bold">Your classroom, connected</h1>
    <p className="mb-6 text-slate-300">Create a class, share assignments, and give feedback. Students join with a class code and keep their work in one place.</p>
    <Link className={button} to="/login">Sign in to use classrooms</Link>
  </div>

  const create = (event: FormEvent<HTMLFormElement>, join: boolean) => {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    void act(async () => {
      const result = await api.post(join ? '/classrooms/join' : '/classrooms', join ? { code: data.get('code') } : { name: data.get('name') })
      await load(); await open(result.data.id); form.reset()
    })
  }

  return <div className="mx-auto max-w-5xl space-y-6">
    <header>
      {detail && <button disabled={busy} onClick={() => setDetail(null)} className="mb-4 flex items-center gap-2 text-indigo-300"><ArrowLeft size={16} /> All classrooms</button>}
      <p className="mb-2 text-sm font-medium uppercase tracking-widest text-indigo-300">Learn together</p>
      <h1 className="text-3xl font-bold sm:text-4xl">{detail?.name || 'Classrooms'}</h1>
      <p className="mt-3 text-slate-400">{detail ? `${detail.role === 'teacher' ? 'Teacher workspace' : 'Student workspace'} · ${detail.member_count} students` : 'Assignments, student work, and personal feedback in one shared space.'}</p>
    </header>
    {error && <p role="alert" className="rounded-xl border border-red-400/30 p-4 text-red-200">{error} <button className="underline" disabled={busy} onClick={() => void act(() => detail ? open(detail.id) : load())}>Refresh</button></p>}
    {notice && <p role="status" className="text-emerald-300">{notice}</p>}
    {busy && <p role="status" className="text-indigo-300">Updating your workspace…</p>}
    {!detail ? <>
      <div className="grid gap-4 md:grid-cols-2">
        <form className={panel} onSubmit={e => create(e, false)}>
          <h2 className="mb-2 text-xl font-semibold">Teach a class</h2>
          <p className="mb-4 text-sm text-slate-400">Create a classroom and share its private joining code with your students.</p>
          <label className="block text-sm">Class name<input name="name" required maxLength={100} placeholder="e.g. Year 9 Algebra" className={field} /></label>
          <button disabled={busy} className={`${button} mt-4`}>Create classroom</button>
        </form>
        <form className={panel} onSubmit={e => create(e, true)}>
          <h2 className="mb-2 text-xl font-semibold">Join your class</h2>
          <p className="mb-4 text-sm text-slate-400">Enter the code your teacher shared to see assignments and submit your work.</p>
          <label className="block text-sm">Class code<input name="code" required maxLength={32} autoCapitalize="characters" autoComplete="off" className={field} /></label>
          <button disabled={busy} className={`${button} mt-4`}>Join classroom</button>
        </form>
      </div>
      <h2 className="text-xl font-semibold">Your classrooms</h2>
      {!classes.length && !busy && !error && <p className="text-slate-400">Your first classroom will appear here once you create or join one.</p>}
      <div className="grid gap-4 sm:grid-cols-2">{classes.map(c => <button key={c.id} disabled={busy} onClick={() => void act(() => open(c.id))} className={`${panel} text-left hover:border-indigo-400`}>
        <Users className="mb-3 text-indigo-300" size={24} /><h3 className="text-lg font-semibold">{c.name}</h3><p className="mt-1 text-sm capitalize text-slate-400">{c.role}</p>
      </button>)}</div>
    </> : <>
      {detail.role === 'teacher' && <>
        <div className={panel}><h2 className="font-semibold">Invite students</h2><p className="mt-2 text-sm text-slate-400">Share this code with your class. Anyone signed in with the code can join.</p><code className="mt-3 block select-all text-2xl tracking-widest text-indigo-200">{detail.join_code}</code></div>
        <form className={panel} onSubmit={e => {
          e.preventDefault(); const form = e.currentTarget; const data = new FormData(form)
          void act(async () => { await api.post(`/classrooms/${detail.id}/assignments`, { title: data.get('title'), instructions: data.get('instructions'), due_at: data.get('due') ? new Date(String(data.get('due'))).toISOString() : null }); await open(detail.id); form.reset(); setNotice('Assignment published to your classroom.') })
        }}>
          <h2 className="mb-4 text-xl font-semibold">Create an assignment</h2>
          <label className="mb-4 block text-sm">Title<input name="title" required maxLength={200} className={field} /></label>
          <label className="mb-4 block text-sm">Questions and instructions<textarea name="instructions" required maxLength={20000} rows={5} className={field} placeholder="Write the problems and explain what students should show in their working." /></label>
          <label className="mb-4 block text-sm">Due date (optional, your local time)<input type="datetime-local" name="due" className={field} /></label>
          <button disabled={busy} className={button}>Publish assignment</button>
        </form>
      </>}
      <h2 className="text-xl font-semibold">Assignments</h2>
      {!detail.assignments.length && <p className="text-slate-400">{detail.role === 'teacher' ? 'Create your first assignment above.' : 'Your teacher has not published any assignments yet.'}</p>}
      {detail.assignments.map(a => {
        const submissions = detail.submissions.filter(s => s.assignment_id === a.id)
        return <article key={a.id} className={panel}>
          <h3 className="text-xl font-semibold">{a.title}</h3>
          <p className="mt-2 text-sm text-slate-400">{a.due_at ? `Due ${new Date(a.due_at).toLocaleString()}` : 'No due date'}</p>
          <p className="my-5 whitespace-pre-wrap break-words text-slate-200">{a.instructions}</p>
          {detail.role === 'student' && !submissions.length && <form onSubmit={e => {
            e.preventDefault(); const data = new FormData(e.currentTarget)
            void act(async () => { await api.post(`/classrooms/${detail.id}/assignments/${a.id}/submit`, { work: data.get('work') }); await open(detail.id); setNotice('Your work has been submitted to your teacher.') })
          }}><label className="block text-sm">Your answer and working<textarea name="work" required maxLength={30000} rows={6} className={field} /></label><p className="my-3 text-xs text-slate-400">Check your work before submitting. Each assignment accepts one submission. Late work is accepted and timestamped.</p><button disabled={busy} className={button}>Submit work</button></form>}
          {detail.role === 'teacher' && <p className="text-sm text-slate-400">{submissions.length} of {detail.member_count} students submitted</p>}
          {submissions.map(s => <section key={s.id} className="mt-4 rounded-xl border border-slate-600 p-4">
            <h4 className="font-semibold">{detail.role === 'teacher' ? s.student_name : 'Your submission'}</h4>
            <p className="mt-1 text-xs text-slate-400">Submitted {new Date(s.submitted_at).toLocaleString()}{a.due_at && new Date(s.submitted_at) > new Date(a.due_at) ? ' · Late' : ''}</p>
            <p className="my-4 whitespace-pre-wrap break-words text-slate-200">{s.work}</p>
            {detail.role === 'teacher' ? <form onSubmit={e => {
              e.preventDefault(); const data = new FormData(e.currentTarget)
              void act(async () => { await api.patch(`/classrooms/${detail.id}/submissions/${s.id}`, { score: Number(data.get('score')), feedback: data.get('feedback') }); await open(detail.id); setNotice('Feedback saved and shared with the student.') })
            }}><label className="block text-sm">Score out of 100<input type="number" name="score" required min={0} max={100} step="0.1" defaultValue={s.score ?? ''} className={field} /></label><label className="my-3 block text-sm">Feedback<textarea name="feedback" maxLength={10000} rows={3} defaultValue={s.feedback || ''} className={field} /></label><button disabled={busy} className={button}>Save feedback</button></form> : <div className="text-emerald-200"><p>{s.score === null ? 'Awaiting teacher review' : `Score: ${s.score}/100`}</p>{s.feedback && <p className="mt-2 whitespace-pre-wrap">{s.feedback}</p>}</div>}
          </section>)}
        </article>
      })}
    </>}
  </div>
}
