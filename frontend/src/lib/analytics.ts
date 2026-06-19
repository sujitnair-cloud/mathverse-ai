/* Google Analytics 4 event helpers */

declare global {
  interface Window { gtag?: (...args: unknown[]) => void }
}

const track = (event: string, params?: Record<string, unknown>) => {
  window.gtag?.('event', event, params)
}

export const analytics = {
  solveProblem: (topic: string, difficulty: string) =>
    track('solve_problem', { topic, difficulty }),

  quizComplete: (topic: string, score: number, total: number) =>
    track('quiz_complete', { topic, score, total, percent: Math.round((score / total) * 100) }),

  viewFormula: (name: string, topic: string) =>
    track('view_formula', { name, topic }),

  plotGraph: (expression: string) =>
    track('plot_graph', { expression }),

  signIn: () => track('login', { method: 'google' }),

  beginCheckout: (plan: string, price: number) =>
    track('begin_checkout', { currency: 'USD', value: price, items: [{ item_name: plan }] }),

  pageView: (path: string, title: string) =>
    track('page_view', { page_path: path, page_title: title }),
}
