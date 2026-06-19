"""
LLM abstraction layer.
Supports Anthropic Claude, OpenAI, Gemini, and a rich no-key fallback.

Priority order:
  1. Configured provider + valid key  → real LLM response
  2. No key / wrong key / network err → rich structured fallback (always works)

The fallback produces a complete, educationally accurate explanation so the app
is fully useful even with no API keys set.
"""
import httpx
import json
from typing import Optional
from app.core.config import settings


# ── Difficulty-level instructions ──────────────────────────────────────────────
DIFFICULTY_INSTRUCTIONS = {
    "kids":         "Explain like I am 8 years old. Use very simple words, fun analogies, and emojis. Be very encouraging.",
    "basic":        "Explain simply and clearly. Use everyday examples. Avoid jargon.",
    "intermediate": "Explain clearly with proper math terminology. Show the reasoning at each step.",
    "advanced":     "Explain rigorously. Include the mathematical justification for each step.",
    "expert":       "Provide a graduate-level explanation with full mathematical rigour, edge cases, and connections to theory.",
}

# ── Topic-aware explanation templates ──────────────────────────────────────────
TOPIC_EXPLANATIONS = {
    "calculus_differentiation": {
        "intro": "Differentiation measures the **rate of change** of a function. The derivative f'(x) tells you how steep the graph is at every point.",
        "key_rules": [
            "**Power Rule:** d/dx(xⁿ) = n·xⁿ⁻¹  — bring the exponent down, reduce it by 1",
            "**Sum Rule:** d/dx[f+g] = f' + g'  — differentiate each term independently",
            "**Product Rule:** d/dx[f·g] = f'g + fg'",
            "**Chain Rule:** d/dx[f(g(x))] = f'(g(x))·g'(x)  — 'outside × derivative of inside'",
            "**Constants:** d/dx(c) = 0  — constants vanish under differentiation",
        ],
        "tip": "Always simplify the expression before differentiating when possible — it reduces mistakes.",
    },
    "calculus_integration": {
        "intro": "Integration is the **reverse of differentiation** (antiderivative) and also measures the **area under a curve**.",
        "key_rules": [
            "**Power Rule:** ∫xⁿ dx = xⁿ⁺¹/(n+1) + C  (n ≠ −1)",
            "**Constant:** ∫c dx = cx + C",
            "**Sum Rule:** ∫[f+g] dx = ∫f dx + ∫g dx",
            "**∫eˣ dx = eˣ + C**",
            "**∫sin(x) dx = −cos(x) + C**,  **∫cos(x) dx = sin(x) + C**",
            "**Always add +C** for indefinite integrals (the constant of integration).",
        ],
        "tip": "Check your answer by differentiating it — you should get back the original integrand.",
    },
    "calculus_limits": {
        "intro": "A **limit** describes the value a function approaches as the input approaches some point — even if the function is undefined there.",
        "key_rules": [
            "**Direct substitution** — try plugging in the value first",
            "**0/0 or ∞/∞ form** → use L'Hôpital's Rule: lim f/g = lim f'/g'",
            "**Factoring** — cancel common factors to remove discontinuities",
            "**Standard limits:** lim(x→0) sin(x)/x = 1,  lim(x→0) (eˣ−1)/x = 1",
        ],
        "tip": "If direct substitution gives 0/0, always try factoring or L'Hôpital before any other method.",
    },
    "algebra_general": {
        "intro": "Algebra uses **symbols to represent unknowns** and rules to manipulate equations while preserving equality.",
        "key_rules": [
            "**Balance rule:** whatever you do to one side, do to the other",
            "**Collect like terms** before solving",
            "**Isolate the variable** step by step using inverse operations",
            "**Check your answer** by substituting back into the original equation",
        ],
        "tip": "Write every step on a new line. Most errors come from skipping steps mentally.",
    },
    "algebra_quadratic": {
        "intro": "A **quadratic equation** (ax² + bx + c = 0) can have 0, 1, or 2 real solutions, found via factoring, completing the square, or the quadratic formula.",
        "key_rules": [
            "**Quadratic Formula:** x = (−b ± √(b²−4ac)) / 2a  — always works",
            "**Discriminant Δ = b²−4ac:** Δ>0 → 2 real roots; Δ=0 → 1 repeated root; Δ<0 → complex roots",
            "**Factoring:** find two numbers that multiply to ac and add to b",
            "**Vieta's formulas:** sum of roots = −b/a,  product of roots = c/a",
        ],
        "tip": "When factoring doesn't come easily, fall back to the quadratic formula — it always works.",
    },
    "geometry": {
        "intro": "Geometry studies **shapes, sizes, and spatial relationships**. Most area/perimeter/volume formulas come from first principles.",
        "key_rules": [
            "**Circle:** Area = πr²,  Circumference = 2πr",
            "**Triangle:** Area = ½·base·height  (for any triangle)",
            "**Rectangle:** Area = l×w,  Perimeter = 2(l+w)",
            "**Pythagorean Theorem:** a² + b² = c²  (right triangles only)",
            "**Sphere:** Volume = (4/3)πr³,  Surface Area = 4πr²",
        ],
        "tip": "Always check your units — mixing cm and m is the most common geometry mistake.",
    },
    "trigonometry": {
        "intro": "Trigonometry connects **angles and side lengths** of triangles, and extends to periodic phenomena everywhere in science.",
        "key_rules": [
            "**SOH-CAH-TOA:** sin=opp/hyp, cos=adj/hyp, tan=opp/adj",
            "**Pythagorean identity:** sin²θ + cos²θ = 1",
            "**Special angles:** sin30°=½, cos60°=½, sin45°=cos45°=1/√2, tan45°=1",
            "**Sine Rule:** a/sin A = b/sin B = c/sin C",
            "**Cosine Rule:** c² = a² + b² − 2ab·cos C",
        ],
        "tip": "Convert degrees to radians (multiply by π/180) before using a calculator in radian mode.",
    },
    "statistics": {
        "intro": "Statistics **summarises and interprets data**. Descriptive statistics describe what's in your sample; inferential statistics make predictions about populations.",
        "key_rules": [
            "**Mean x̄ = Σx/n** — average (sensitive to outliers)",
            "**Median** — middle value when sorted (robust to outliers)",
            "**Mode** — most frequent value",
            "**Sample std dev σ = √(Σ(x−x̄)²/(n−1))** — use n−1 (Bessel's correction) for samples",
            "**Z-score = (x−μ)/σ** — how many std devs from the mean",
        ],
        "tip": "Use median instead of mean when your data has extreme outliers (e.g., income data).",
    },
    "probability": {
        "intro": "Probability assigns a number **0–1** to how likely an event is. 0 = impossible, 1 = certain.",
        "key_rules": [
            "**P(E) = favourable outcomes / total outcomes** (equally likely)",
            "**Addition rule:** P(A∪B) = P(A) + P(B) − P(A∩B)",
            "**Multiplication rule:** P(A∩B) = P(A)·P(B|A)",
            "**Combinations C(n,r) = n! / (r!(n−r)!)** — order doesn't matter",
            "**Permutations P(n,r) = n! / (n−r)!** — order matters",
        ],
        "tip": "Always ask: does order matter? Yes → permutation. No → combination.",
    },
    "linear_algebra": {
        "intro": "Linear algebra studies **vectors, matrices, and linear transformations** — the mathematical backbone of machine learning, graphics, and physics.",
        "key_rules": [
            "**det(2×2):** |a b; c d| = ad − bc",
            "**Matrix inverse exists** only when det ≠ 0",
            "**Ax = b** — system of equations in matrix form",
            "**Eigenvalue equation:** Av = λv — special vectors unchanged in direction",
            "**Dot product:** a·b = |a||b|cos θ",
        ],
        "tip": "Always check det ≠ 0 before attempting to invert a matrix.",
    },
    "arithmetic_percent": {
        "intro": "Percentages, ratios, and proportions describe **relative quantities** — how much of a whole something represents.",
        "key_rules": [
            "**Percentage:** part/whole × 100",
            "**Percentage increase:** (new−old)/old × 100",
            "**Ratio a:b** means for every a of one thing there are b of another",
            "**Proportion:** a/b = c/d → cross-multiply: ad = bc",
        ],
        "tip": "Convert percentages to decimals (÷100) before multiplying — avoids the most common errors.",
    },
    "algebra_logarithm": {
        "intro": "Logarithms are the **inverse of exponentiation**: logₐ(x) = y means aʸ = x.",
        "key_rules": [
            "**log(ab) = log(a) + log(b)**",
            "**log(a/b) = log(a) − log(b)**",
            "**log(aⁿ) = n·log(a)**",
            "**Change of base:** logₐ(x) = ln(x)/ln(a)",
            "**ln(eˣ) = x**,  **e^(ln x) = x**",
        ],
        "tip": "ln means log base e (≈2.718). On calculators, 'log' usually means base 10.",
    },
}

_DEFAULT_TOPIC_EXPLANATION = {
    "intro": "Mathematics uses precise rules to find unknown quantities and relationships.",
    "key_rules": ["Apply the relevant formula", "Simplify step by step", "Check your answer"],
    "tip": "Show every step — it makes errors easy to spot.",
}


def _get_topic_info(topic: str) -> dict:
    for key in TOPIC_EXPLANATIONS:
        if key in topic:
            return TOPIC_EXPLANATIONS[key]
    return _DEFAULT_TOPIC_EXPLANATION


# ── Rich fallback explanation (no LLM needed) ──────────────────────────────────
def _rich_fallback(problem: str, sympy_result: dict, difficulty: str) -> str:
    """
    Generate the AI Explanation block.
    The UI already shows: answer, step-by-step, formulas, common mistakes, similar problems.
    This block focuses on the WHY — concept, rules, and a pro tip.
    """
    topic = sympy_result.get("topic", "algebra_general")
    info = _get_topic_info(topic)
    topic_label = topic.replace("_", " ").title()

    # Difficulty-appropriate opener
    openers = {
        "kids":         f"Great question! 🎉 Here's what you need to know to solve **{problem}**!",
        "basic":        f"Here's the concept behind **{problem}**.",
        "intermediate": f"Here's the mathematical reasoning behind **{problem}**.",
        "advanced":     f"Mathematical analysis of **{problem}**.",
        "expert":       f"Rigorous treatment of **{problem}**.",
    }
    opener = openers.get(difficulty, openers["intermediate"])

    # Key concept
    concept_md = f"\n### 📐 Key Concept — {topic_label}\n\n{info['intro']}\n"

    # Rules as numbered list for clarity
    rules_list = "\n".join(f"{i+1}. {r}" for i, r in enumerate(info["key_rules"]))
    rules_md = f"\n### 📏 Essential Rules\n\n{rules_list}\n"

    # Pro tip as callout
    tip_md = f"\n### 💡 Pro Tip\n\n> {info['tip']}\n"

    # Difficulty-tailored note
    level_notes = {
        "kids":         "\n---\n*Maths is like a puzzle — every piece fits perfectly! Keep practising! 🧩*",
        "basic":        "\n---\n*Try 2–3 similar problems to build confidence with this method.*",
        "intermediate": "\n---\n*Challenge yourself: can you solve this using an alternative method?*",
        "advanced":     "\n---\n*Explore the proof of the core theorem to deepen your understanding.*",
        "expert":       "\n---\n*Consider edge cases: singularities, boundary conditions, and degenerate forms.*",
    }
    level_note = level_notes.get(difficulty, "")

    return (
        f"{opener}\n"
        f"{concept_md}"
        f"{rules_md}"
        f"{tip_md}"
        f"{level_note}"
    )


# ── LLM prompt builder ─────────────────────────────────────────────────────────
def _build_prompt(problem: str, sympy_result: dict, difficulty: str) -> str:
    level_instruction = DIFFICULTY_INSTRUCTIONS.get(difficulty, DIFFICULTY_INSTRUCTIONS["intermediate"])
    return f"""You are MathVerse AI, a world-class mathematics tutor.

A student asked: "{problem}"

The symbolic engine already computed:
- Topic: {sympy_result.get('topic')}
- Answer: {sympy_result.get('answer')}
- Steps: {json.dumps(sympy_result.get('steps', []), indent=2)}
- Formulas used: {sympy_result.get('formulas_used', [])}

Your task:
1. Write a clear, engaging explanation of the solution.
2. {level_instruction}
3. Highlight the key concept or formula.
4. Mention 1–2 common mistakes to avoid.
5. Suggest one similar practice problem.

Format in markdown. Be concise but complete. Do NOT repeat the step-by-step since it's already shown — focus on the WHY and the concept.
"""


# ── Provider calls ─────────────────────────────────────────────────────────────
async def _call_anthropic(prompt: str, max_tokens: int = 1024) -> str:
    headers = {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


async def _call_openai(prompt: str, max_tokens: int = 1024) -> str:
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_gemini(prompt: str, max_tokens: int = 1024) -> str:
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def _key_looks_real(key: str) -> bool:
    """Return True only if the key is not a placeholder."""
    placeholders = {"sk-...", "sk-ant-...", "AIza...", "", "your-key-here", "sk-proj-..."}
    return bool(key) and key not in placeholders and len(key) > 20


# ── Public API ─────────────────────────────────────────────────────────────────
async def get_explanation(problem: str, sympy_result: dict, difficulty: str = "intermediate") -> str:
    """
    Return an explanation for a solved math problem.
    Tries the configured LLM provider first; falls back to the rich built-in
    explainer if no valid key is present or if the LLM call fails.
    """
    provider = settings.LLM_PROVIDER.lower()

    # Only attempt LLM if the key looks like a real key
    if provider == "anthropic" and _key_looks_real(settings.ANTHROPIC_API_KEY):
        try:
            return await _call_anthropic(_build_prompt(problem, sympy_result, difficulty))
        except Exception as e:
            # Key exists but call failed (rate limit, network, etc.) — still use fallback
            fallback = _rich_fallback(problem, sympy_result, difficulty)
            return fallback + f"\n\n---\n*LLM error: {e}*"

    if provider == "openai" and _key_looks_real(settings.OPENAI_API_KEY):
        try:
            return await _call_openai(_build_prompt(problem, sympy_result, difficulty))
        except Exception as e:
            fallback = _rich_fallback(problem, sympy_result, difficulty)
            return fallback + f"\n\n---\n*LLM error: {e}*"

    if provider == "gemini" and _key_looks_real(settings.GEMINI_API_KEY):
        try:
            return await _call_gemini(_build_prompt(problem, sympy_result, difficulty))
        except Exception as e:
            fallback = _rich_fallback(problem, sympy_result, difficulty)
            return fallback + f"\n\n---\n*LLM error: {e}*"

    # No valid key — return the rich structured explanation
    return _rich_fallback(problem, sympy_result, difficulty)


async def llm_full_solve(problem: str, difficulty: str = "intermediate") -> Optional[dict]:
    """
    Ask the configured LLM to fully solve a problem that SymPy couldn't handle.
    Returns a dict matching solve_expression's output shape, or None if no LLM is available.
    """
    provider = settings.LLM_PROVIDER.lower()
    has_llm = (
        (provider == "anthropic" and _key_looks_real(settings.ANTHROPIC_API_KEY)) or
        (provider == "openai" and _key_looks_real(settings.OPENAI_API_KEY)) or
        (provider == "gemini" and _key_looks_real(settings.GEMINI_API_KEY))
    )
    if not has_llm:
        return None

    level_instruction = DIFFICULTY_INSTRUCTIONS.get(difficulty, DIFFICULTY_INSTRUCTIONS["intermediate"])
    prompt = f"""You are MathVerse AI — an expert mathematics tutor capable of solving any problem from primary school arithmetic to IIT JEE, PhD-level research, and competitive olympiads.

Problem: {problem}

IMPORTANT RULES:
- Solve completely regardless of complexity — advanced calculus, proofs, word problems, aptitude, number theory, all are fine.
- Do NOT ask for clarification or say the problem is unclear. Make your best interpretation and solve it.
- Ignore any typos, missing brackets, or informal notation — understand the user's intent.
- Explanation style: {level_instruction}

Return ONLY a valid JSON object (no markdown fences, no preamble, no trailing text):
{{
  "topic": "one of: algebra_general|algebra_quadratic|algebra_linear|algebra_polynomial|algebra_logarithm|calculus_differentiation|calculus_integration|calculus_limits|geometry|trigonometry|statistics|probability|linear_algebra|arithmetic_percent|number_theory|word_problem|differential_equations|combinatorics",
  "difficulty": "one of: basic|intermediate|advanced|expert",
  "answer": "the complete final answer as a clear string",
  "steps": [
    {{"step": 1, "description": "what this step does and why", "expression": "the math expression or working"}},
    {{"step": 2, "description": "next step", "expression": "math"}}
  ],
  "formulas_used": ["Complete formula 1 with name", "Complete formula 2 with name"],
  "common_mistakes": ["Common error 1 students make", "Common error 2"],
  "similar_problems": ["A related practice problem 1", "Related practice problem 2", "Related practice problem 3"],
  "explanation": "Thorough explanation of the method, key concept, and why each step works. {level_instruction}"
}}"""

    try:
        raw = ""
        if provider == "anthropic" and _key_looks_real(settings.ANTHROPIC_API_KEY):
            raw = await _call_anthropic(prompt, max_tokens=2048)
        elif provider == "openai" and _key_looks_real(settings.OPENAI_API_KEY):
            raw = await _call_openai(prompt, max_tokens=2048)
        elif provider == "gemini" and _key_looks_real(settings.GEMINI_API_KEY):
            raw = await _call_gemini(prompt, max_tokens=2048)

        if raw:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(raw[start:end])
    except Exception:
        pass

    return None


async def generate_quiz_questions(topic: str, difficulty: str, count: int = 5) -> list:
    """Generate quiz questions via LLM or local templates."""
    provider = settings.LLM_PROVIDER.lower()
    prompt = f"""Generate {count} multiple-choice math questions about '{topic}' at '{difficulty}' level.

Return ONLY a JSON array. Each element: {{"question": "...", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "answer": "A", "explanation": "..."}}

No extra text — pure JSON array only."""

    try:
        raw = ""
        if provider == "anthropic" and _key_looks_real(settings.ANTHROPIC_API_KEY):
            raw = await _call_anthropic(prompt)
        elif provider == "openai" and _key_looks_real(settings.OPENAI_API_KEY):
            raw = await _call_openai(prompt)
        elif provider == "gemini" and _key_looks_real(settings.GEMINI_API_KEY):
            raw = await _call_gemini(prompt)

        if raw:
            start, end = raw.find("["), raw.rfind("]") + 1
            if start != -1 and end > start:
                return json.loads(raw[start:end])
    except Exception:
        pass

    return _template_questions(topic, difficulty, count)


def _template_questions(topic: str, difficulty: str, count: int) -> list:
    """Comprehensive built-in question bank — used when no LLM key is set."""
    bank: dict = {
        "algebra": [
            {"question": "Solve: 2x + 4 = 10",
             "options": ["A) x = 2", "B) x = 3", "C) x = 4", "D) x = 7"],
             "answer": "B", "explanation": "2x = 6, x = 3"},
            {"question": "Expand: (x + 3)²",
             "options": ["A) x² + 6x + 9", "B) x² + 9", "C) x² + 3x + 9", "D) x² + 6x + 6"],
             "answer": "A", "explanation": "(a+b)² = a² + 2ab + b²"},
            {"question": "Factor: x² − 9",
             "options": ["A) (x−3)²", "B) (x+3)(x−3)", "C) (x+9)(x−1)", "D) (x+3)²"],
             "answer": "B", "explanation": "Difference of squares: a²−b² = (a+b)(a−b)"},
            {"question": "Solve: x² − 5x + 6 = 0",
             "options": ["A) x=1, x=6", "B) x=2, x=3", "C) x=−2, x=−3", "D) x=−1, x=6"],
             "answer": "B", "explanation": "Factor: (x−2)(x−3)=0"},
            {"question": "If f(x) = 3x − 2, what is f(4)?",
             "options": ["A) 10", "B) 12", "C) 14", "D) 8"],
             "answer": "A", "explanation": "f(4) = 3(4) − 2 = 10"},
        ],
        "calculus": [
            {"question": "d/dx(x³) = ?",
             "options": ["A) 3x", "B) 3x²", "C) x²", "D) 2x³"],
             "answer": "B", "explanation": "Power rule: d/dx(xⁿ) = nxⁿ⁻¹"},
            {"question": "∫2x dx = ?",
             "options": ["A) 2x² + C", "B) x² + C", "C) x + C", "D) 2 + C"],
             "answer": "B", "explanation": "∫2x dx = x² + C"},
            {"question": "d/dx(sin x) = ?",
             "options": ["A) cos x", "B) −cos x", "C) tan x", "D) −sin x"],
             "answer": "A", "explanation": "Standard derivative: d/dx(sin x) = cos x"},
            {"question": "lim(x→0) sin(x)/x = ?",
             "options": ["A) 0", "B) ∞", "C) 1", "D) undefined"],
             "answer": "C", "explanation": "Standard limit: lim(x→0) sin(x)/x = 1"},
            {"question": "∫eˣ dx = ?",
             "options": ["A) eˣ + C", "B) eˣ/x + C", "C) xeˣ + C", "D) e + C"],
             "answer": "A", "explanation": "eˣ is its own antiderivative"},
        ],
        "statistics": [
            {"question": "Mean of [2, 4, 6, 8, 10] = ?",
             "options": ["A) 5", "B) 6", "C) 7", "D) 4"],
             "answer": "B", "explanation": "Sum=30, Count=5, Mean=6"},
            {"question": "Median of [3, 1, 4, 1, 5, 9, 2] = ?",
             "options": ["A) 3", "B) 4", "C) 1", "D) 5"],
             "answer": "A", "explanation": "Sorted: [1,1,2,3,4,5,9], middle=3"},
            {"question": "Which measure is most affected by outliers?",
             "options": ["A) Median", "B) Mode", "C) Mean", "D) Range"],
             "answer": "C", "explanation": "Mean uses all values so extreme values shift it"},
            {"question": "Standard deviation measures…",
             "options": ["A) central tendency", "B) spread around the mean", "C) most frequent value", "D) largest value"],
             "answer": "B", "explanation": "Std dev = √(variance) = spread of data"},
        ],
        "geometry": [
            {"question": "Area of a circle with radius 5 = ?",
             "options": ["A) 25π", "B) 10π", "C) 5π", "D) 50π"],
             "answer": "A", "explanation": "A = πr² = π×25 = 25π"},
            {"question": "Hypotenuse when a=3, b=4 = ?",
             "options": ["A) 5", "B) 7", "C) 6", "D) 12"],
             "answer": "A", "explanation": "c = √(9+16) = 5"},
            {"question": "Perimeter of rectangle 6×4 = ?",
             "options": ["A) 24", "B) 20", "C) 10", "D) 16"],
             "answer": "B", "explanation": "P = 2(l+w) = 2×10 = 20"},
        ],
        "trigonometry": [
            {"question": "sin(30°) = ?",
             "options": ["A) 1", "B) 0", "C) 1/2", "D) √3/2"],
             "answer": "C", "explanation": "Special angle: sin 30° = 1/2"},
            {"question": "cos(60°) = ?",
             "options": ["A) 1/2", "B) √3/2", "C) 1", "D) 0"],
             "answer": "A", "explanation": "Special angle: cos 60° = 1/2"},
            {"question": "tan(45°) = ?",
             "options": ["A) 0", "B) ∞", "C) √2", "D) 1"],
             "answer": "D", "explanation": "tan 45° = sin/cos = (1/√2)/(1/√2) = 1"},
        ],
        "probability": [
            {"question": "C(5, 2) = ?",
             "options": ["A) 10", "B) 20", "C) 5", "D) 25"],
             "answer": "A", "explanation": "5!/(2!×3!) = 10"},
            {"question": "P(rolling a 6 on a fair die) = ?",
             "options": ["A) 1/3", "B) 1/6", "C) 1/2", "D) 1/12"],
             "answer": "B", "explanation": "1 favourable / 6 total outcomes"},
            {"question": "P(5, 2) = ?",
             "options": ["A) 10", "B) 20", "C) 15", "D) 25"],
             "answer": "B", "explanation": "5!/(5-2)! = 5×4 = 20"},
        ],
        "linear-algebra": [
            {"question": "det([[1,2],[3,4]]) = ?",
             "options": ["A) 2", "B) −2", "C) 10", "D) 4"],
             "answer": "B", "explanation": "1×4 − 2×3 = 4−6 = −2"},
            {"question": "The inverse of a matrix exists when…",
             "options": ["A) det = 0", "B) det ≠ 0", "C) det = 1", "D) det < 0"],
             "answer": "B", "explanation": "If det = 0, the matrix is singular (no inverse)"},
        ],
    }

    key = topic.lower().replace(" ", "-").split("_")[0]
    questions = bank.get(key, bank["algebra"])
    result = []
    for i in range(count):
        result.append(questions[i % len(questions)])
    return result
