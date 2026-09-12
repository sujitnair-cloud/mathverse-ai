"""
LLM abstraction layer.
Supports Anthropic Claude, OpenAI, Gemini, and a rich no-key fallback.

Priority order:
  1. Configured provider + valid key  → real LLM response
  2. No key / wrong key / network err → rich structured fallback (always works)

The fallback produces a complete, educationally accurate explanation so the app
is fully useful even with no API keys set.
"""
import hashlib
import time
import httpx
import json
from typing import Optional
from app.core.config import settings
from app.services.quiz_generator import generate_verified_questions

# ── In-memory response cache ────────────────────────────────────────────────────
# Identical problems (same text + difficulty) return a cached result instantly.
# This dramatically reduces quota consumption when multiple users ask the same
# or similar questions. Cache survives the process lifetime (cleared on restart).
_SOLVE_CACHE: dict = {}   # llm_full_solve results
_EXPL_CACHE: dict = {}    # get_explanation results
_CACHE_TTL: int = 259200  # 72 hours in seconds
_CACHE_MAX: int = 5000    # max entries before evicting oldest

def _ck(*parts) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()

def _cache_get(store: dict, key: str):
    entry = store.get(key)
    if entry and (time.monotonic() - entry["ts"]) < _CACHE_TTL:
        return entry["v"]
    store.pop(key, None)
    return None

def _cache_set(store: dict, key: str, value):
    if len(store) >= _CACHE_MAX:
        oldest_key = min(store, key=lambda k: store[k]["ts"])
        del store[oldest_key]
    store[key] = {"v": value, "ts": time.monotonic()}


class QuotaExhaustedError(Exception):
    """Raised when all Gemini models return HTTP 429 (daily quota exhausted)."""


# ── Difficulty-level instructions ──────────────────────────────────────────────
DIFFICULTY_INSTRUCTIONS = {
    "kids":         "Teach a child in grades 1–5. Use one method, everyday words, and short sentences. Use at most one concrete model when helpful. Keep the explanation under 90 words, with at most three short steps for a simple problem. Preserve necessary reasoning and all requested parts; never sacrifice correctness to meet a length target. Avoid extra methods, jargon, decorative emojis, and unrelated practice questions.",
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
    if difficulty == "kids":
        # Do not substitute an adult topic lecture when AI is unavailable.
        # Keep the engine's full working in the separate steps panel.
        answer = sympy_result.get("answer")
        if not answer or str(answer) in ("See steps", "None", "none"):
            return "I couldn't work this out reliably yet. Let's try one small part at a time."
        return (
            f"**Answer:** {answer}\n\n"
            "A simple explanation is unavailable right now. "
            "The working is shown in the steps section."
        )

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
    answer = sympy_result.get("answer")
    sympy_failed = not answer or str(answer) in ("See steps", "None", "none")

    if difficulty == "kids":
        return f"""You are MathVerse AI, a careful primary-school maths tutor.
Problem: {problem}
Computed answer: {answer}
Working: {json.dumps(sympy_result.get('steps', []))}

{level_instruction}
Use one short answer line, then explain why the method works in a small paragraph
or up to three short steps. Do not add a rules list, pro tip, common-mistakes
section, or practice exercise. Use a familiar model only if it fits this problem.
For a problem beyond primary school, say so gently and explain only what you can
accurately; do not invent a child-friendly rule that is mathematically false.
If the computed answer is missing or unreliable, solve and check it before stating
it. If you cannot, say that clearly. Never present 'See steps' as an answer.
Use markdown. Start a newly solved answer with **Final Answer:**.
"""

    final_answer_instruction = ""
    if sympy_failed:
        final_answer_instruction = (
            "IMPORTANT: This is a word/applied problem the symbolic engine could not parse.\n"
            "Start your ENTIRE response with this line (fill in the actual answers):\n"
            "**Final Answer:** Part 1: [value]. Part 2: [value]. [etc.]\n\n"
            "Then explain the full solution step by step.\n\n"
        )

    return f"""You are MathVerse AI, a world-class mathematics tutor.

A student asked: "{problem}"

{final_answer_instruction}The symbolic engine computed:
- Topic: {sympy_result.get('topic')}
- Answer: {answer}
- Steps: {json.dumps(sympy_result.get('steps', []), indent=2)}
- Formulas used: {sympy_result.get('formulas_used', [])}

Your task:
1. {'Solve completely and e' if sympy_failed else 'E'}xplain the solution clearly.
2. {level_instruction}
3. Highlight the key concept or formula.
4. Mention 1–2 common mistakes to avoid.
5. Suggest one similar practice problem.

Format in markdown. Be clear and complete.
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
    import sys
    api_keys = _get_gemini_keys()
    if not api_keys:
        raise RuntimeError("No Gemini API key configured")

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    models_to_try = list(dict.fromkeys([
        "gemini-2.5-flash-lite",
        settings.GEMINI_MODEL,
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ]))
    api_versions = ["v1beta", "v1"]

    async with httpx.AsyncClient(timeout=60) as client:
        last_err: Exception = RuntimeError("No Gemini model responded successfully")
        exhausted_key_count = 0

        for key_idx, api_key in enumerate(api_keys):
            key_label = f"key#{key_idx + 1}/{len(api_keys)}"
            quota_hit = False

            for model in models_to_try:
                if quota_hit:
                    break
                for api_ver in api_versions:
                    if quota_hit:
                        break
                    base_url = (f"https://generativelanguage.googleapis.com/{api_ver}/models/"
                                f"{model}:generateContent")
                    auth_variants = [
                        (base_url, {"x-goog-api-key": api_key}),
                        (f"{base_url}?key={api_key}", {}),
                        (base_url, {"Authorization": f"Bearer {api_key}"}),
                    ]
                    for url, extra_headers in auth_variants:
                        auth_label = list(extra_headers.keys())[0] if extra_headers else "query-param"
                        try:
                            resp = await client.post(url, json=payload, headers=extra_headers)
                            print(f"[MathVerse] {key_label} {model}/{api_ver}/{auth_label} → HTTP {resp.status_code}", file=sys.stderr)
                            if resp.status_code == 404:
                                break
                            if resp.status_code in (400, 401, 403):
                                print(f"[MathVerse] Error body: {resp.text[:300]}", file=sys.stderr)
                                continue
                            if resp.status_code == 429:
                                print(f"[MathVerse] {key_label}: quota exceeded, trying next key", file=sys.stderr)
                                quota_hit = True
                                break
                            resp.raise_for_status()
                            parts = resp.json()["candidates"][0]["content"]["parts"]
                            text = ""
                            for part in parts:
                                if not part.get("thought", False) and "text" in part:
                                    text = part["text"]
                                    break
                            if not text:
                                text = parts[-1].get("text", "")
                            print(f"[MathVerse] Gemini REST success: {key_label} {model} ({api_ver})", file=sys.stderr)
                            return text
                        except Exception as e:
                            last_err = e
                            continue

            if quota_hit:
                exhausted_key_count += 1

        if exhausted_key_count >= len(api_keys):
            n = len(api_keys)
            raise QuotaExhaustedError(
                f"Daily AI quota exhausted across all {n} configured API key(s). "
                "The solver will reset at midnight UTC. "
                "Add more GEMINI_API_KEYS or upgrade to a paid plan for unlimited access."
            )
    raise last_err


def _repair_json_backslashes(s: str) -> str:
    # Fix invalid JSON escape sequences from LLM LaTeX output.
    # Valid JSON escapes: \" \\ \/ \b \f \n \r \t and \\u+4hex.
    # LaTeX like \cdot \sqrt \leq breaks json.loads — double-escape them.
    import re as _re
    VALID_JSON_ESCAPES = set('"\\bfnrtu/')
    result: list = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in VALID_JSON_ESCAPES:
                if nxt == 'u' and _re.match(r'[0-9A-Fa-f]{4}', s[i + 2:i + 6]):
                    result.append(s[i:i + 6])  # valid \uXXXX
                    i += 6
                    continue
                elif nxt == 'u':
                    result.append('\\\\u')  # not a valid unicode escape
                    i += 2
                    continue
                result.append(s[i:i + 2])  # valid 2-char escape
                i += 2
            else:
                result.append('\\\\')  # double-escape the stray backslash
                result.append(nxt)
                i += 2
        else:
            result.append(s[i])
            i += 1
    return ''.join(result)


def _key_looks_real(key: str) -> bool:
    """Return True only if the key is not a placeholder."""
    placeholders = {"sk-...", "sk-ant-...", "AIza...", "", "your-key-here", "sk-proj-..."}
    return bool(key) and key not in placeholders and len(key) > 20


def _get_gemini_keys() -> list:
    """Return all configured Gemini API keys, deduped and validated. Primary key first."""
    keys: list = []
    if settings.GEMINI_API_KEYS:
        for k in settings.GEMINI_API_KEYS.split(","):
            k = k.strip()
            if _key_looks_real(k) and k not in keys:
                keys.append(k)
    if _key_looks_real(settings.GEMINI_API_KEY) and settings.GEMINI_API_KEY not in keys:
        keys.append(settings.GEMINI_API_KEY)
    return keys


# ── Public API ─────────────────────────────────────────────────────────────────
async def get_explanation(problem: str, sympy_result: dict, difficulty: str = "intermediate", plan: str = "free") -> str:
    """
    Return an explanation for a solved math problem.
    Free-plan users receive the structured fallback (no LLM call, zero quota cost).
    Student/Pro users get a full LLM explanation, cached 72 h.
    """
    # Free users: return structured fallback immediately — no LLM cost
    if plan not in ("student", "pro", "school"):
        return _rich_fallback(problem, sympy_result, difficulty)

    cache_key = _ck(problem, difficulty)
    cached = _cache_get(_EXPL_CACHE, cache_key)
    if cached is not None:
        return cached

    provider = settings.LLM_PROVIDER.lower()
    result_text: str | None = None

    if provider == "anthropic" and _key_looks_real(settings.ANTHROPIC_API_KEY):
        try:
            result_text = await _call_anthropic(_build_prompt(problem, sympy_result, difficulty))
        except QuotaExhaustedError:
            result_text = (
                _rich_fallback(problem, sympy_result, difficulty)
                + "\n\n---\n> **Note:** AI explanation quota reached for today. "
                "The structured solution above is always available. Quota resets at midnight UTC."
            )
        except Exception as e:
            result_text = _rich_fallback(problem, sympy_result, difficulty) + f"\n\n---\n*LLM error: {e}*"

    elif provider == "openai" and _key_looks_real(settings.OPENAI_API_KEY):
        try:
            result_text = await _call_openai(_build_prompt(problem, sympy_result, difficulty))
        except QuotaExhaustedError:
            result_text = (
                _rich_fallback(problem, sympy_result, difficulty)
                + "\n\n---\n> **Note:** AI explanation quota reached for today. Quota resets at midnight UTC."
            )
        except Exception as e:
            result_text = _rich_fallback(problem, sympy_result, difficulty) + f"\n\n---\n*LLM error: {e}*"

    elif provider == "gemini" and _get_gemini_keys():
        try:
            result_text = await _call_gemini(_build_prompt(problem, sympy_result, difficulty))
        except QuotaExhaustedError:
            result_text = (
                _rich_fallback(problem, sympy_result, difficulty)
                + "\n\n---\n> **Note:** AI explanation quota reached for today. "
                "The structured solution above is always available. Quota resets at midnight UTC."
            )
        except Exception as e:
            result_text = _rich_fallback(problem, sympy_result, difficulty) + f"\n\n---\n*LLM error: {e}*"

    if result_text is None:
        result_text = _rich_fallback(problem, sympy_result, difficulty)

    # Cache successful full LLM responses (not quota-notice fallbacks)
    if "Quota resets at midnight UTC" not in result_text:
        _cache_set(_EXPL_CACHE, cache_key, result_text)

    return result_text


async def llm_full_solve(problem: str, difficulty: str = "intermediate") -> Optional[dict]:
    """
    Ask the configured LLM to fully solve a problem that SymPy couldn't handle.
    Returns a dict matching solve_expression's output shape, or None if no LLM is available.
    """
    import sys
    provider = settings.LLM_PROVIDER.lower()
    has_llm = (
        (provider == "anthropic" and _key_looks_real(settings.ANTHROPIC_API_KEY)) or
        (provider == "openai" and _key_looks_real(settings.OPENAI_API_KEY)) or
        (provider == "gemini" and bool(_get_gemini_keys()))
    )
    if not has_llm:
        print(f"[MathVerse] llm_full_solve: no LLM configured (provider={provider!r})", file=sys.stderr)
        return None

    level_instruction = DIFFICULTY_INSTRUCTIONS.get(difficulty, DIFFICULTY_INSTRUCTIONS["intermediate"])

    # Detect multi-part questions
    import re as _re
    parts = _re.findall(
        r"(?:^|\n)\s*(?:\d+[\.\)]\s|part\s+\d|extra\s+challenge)",
        problem, _re.IGNORECASE | _re.MULTILINE,
    )
    multi_note = (
        f"This problem has {len(parts)} parts. Solve ALL of them. "
        "In 'answer' write: 'Part 1: X. Part 2: Y. Extra Challenge: Z.' "
        "In 'steps' label each step with its part number."
        if len(parts) >= 2
        else "Solve completely, showing all working."
    )

    working_instruction = (
        "Show one method with short, child-friendly steps. Combine routine arithmetic "
        "where clear, but preserve all necessary reasoning and requested parts. "
        "Keep common_mistakes and similar_problems empty for this first explanation."
        if difficulty == "kids"
        else "Show ALL intermediate arithmetic steps. Define variables before using them."
    )

    prompt = f"""You are MathVerse AI, an expert math tutor. Solve this problem completely.

PROBLEM:
{problem}

INSTRUCTIONS:
- {multi_note}
- Solve completely regardless of complexity (IIT JEE, olympiad, aptitude, word problems — all fine).
- {working_instruction}
- For infinite series: use S = a/(1-r) and verify |r| < 1.
- Explanation style: {level_instruction}

OUTPUT FORMAT — respond with ONLY the JSON below. NO markdown fences, NO text before or after.
IMPORTANT: In "expression" fields write plain arithmetic like "540/135 = 4" — do NOT use
LaTeX backslash commands like \\frac or \\times (they break JSON parsing).

{{
  "topic": "word_problem",
  "difficulty": "expert",
  "answer": "Complete answer for all parts (e.g. Part 1: 4 hours. Part 2: 480 km.)",
  "steps": [
    {{"step": 1, "description": "Identify what is given and what to find", "expression": "Distance = 540 km, Speed_A = 60 km/h, Speed_B = 75 km/h"}},
    {{"step": 2, "description": "Next calculation step", "expression": "plain arithmetic here"}}
  ],
  "formulas_used": ["Relative speed = v1 + v2 (objects moving towards each other)"],
  "common_mistakes": ["Trying to track each bird trip instead of using total time"],
  "similar_problems": ["Two cars 400 km apart approach at 50 and 70 km/h. Find collision time."],
  "explanation": "Brief explanation of the key concept used"
}}"""

    if difficulty == "kids":
        # Use a neutral schema instead of the advanced worked-example scaffold.
        prompt = prompt[:prompt.index("OUTPUT FORMAT")]
        prompt += "OUTPUT FORMAT: Return only valid JSON using this structure. Replace placeholders with this problem's solution.\n"
        prompt += json.dumps({
            "topic": "actual topic",
            "difficulty": "actual problem difficulty",
            "answer": "short complete answer",
            "steps": [{"step": 1, "description": "short explanation", "expression": "plain arithmetic"}],
            "formulas_used": [], "common_mistakes": [], "similar_problems": [],
            "explanation": "Briefly explain why the one method works; do not repeat all the steps.",
        })

    cache_key = _ck(problem, difficulty)
    cached = _cache_get(_SOLVE_CACHE, cache_key)
    if cached is not None:
        print(f"[MathVerse] llm_full_solve: cache hit", file=sys.stderr)
        return cached

    try:
        raw = ""
        if provider == "anthropic" and _key_looks_real(settings.ANTHROPIC_API_KEY):
            raw = await _call_anthropic(prompt, max_tokens=2048)
        elif provider == "openai" and _key_looks_real(settings.OPENAI_API_KEY):
            raw = await _call_openai(prompt, max_tokens=2048)
        elif provider == "gemini" and _key_looks_real(settings.GEMINI_API_KEY):
            raw = await _call_gemini(prompt, max_tokens=2048)

        print(f"[MathVerse] llm_full_solve raw (first 300 chars): {raw[:300]!r}", file=sys.stderr)

        if raw:
            raw_clean = _re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=_re.MULTILINE)
            raw_clean = _re.sub(r"```\s*$", "", raw_clean.strip(), flags=_re.MULTILINE)

            start = raw_clean.find("{")
            end = raw_clean.rfind("}") + 1
            if start == -1 or end <= start:
                print(f"[MathVerse] llm_full_solve: no JSON braces found", file=sys.stderr)
            else:
                json_str = raw_clean[start:end]
                parsed = None
                try:
                    parsed = json.loads(json_str)
                except json.JSONDecodeError as e1:
                    print(f"[MathVerse] llm_full_solve: JSON parse failed ({e1}); trying backslash repair", file=sys.stderr)
                    try:
                        repaired = _repair_json_backslashes(json_str)
                        parsed = json.loads(repaired)
                    except json.JSONDecodeError as e2:
                        print(f"[MathVerse] llm_full_solve: repaired JSON also failed ({e2})", file=sys.stderr)
                        print(f"[MathVerse] Repaired JSON (first 400 chars): {repaired[:400]!r}", file=sys.stderr)

                if parsed is not None:
                    _cache_set(_SOLVE_CACHE, cache_key, parsed)
                    return parsed

    except QuotaExhaustedError as qe:
        print(f"[MathVerse] llm_full_solve: quota exhausted — {qe}", file=sys.stderr)
        # Return a sentinel so solve.py can show a friendly quota message
        return {"_quota_exceeded": True}
    except Exception as e:
        print(f"[MathVerse] llm_full_solve error: {e}", file=sys.stderr)

    return None


_DEMAND_DESCRIPTIONS = {
    "routine": "a single, direct application of one formula or rule — no multi-step reasoning",
    "multi_step": "two or more connected steps (e.g. combine like terms, then solve; or apply one rule, then another)",
    "unfamiliar": "a variation that can't be solved by pattern-matching a memorized template — "
                  "e.g. the variable on both sides, a non-obvious substitution, or a twist on the routine form",
}


def _valid_quiz_question(q) -> bool:
    """
    Structural validation applied to every question regardless of source
    (LLM or generator) before it's ever shown to a student: well-formed
    options, a unique answer letter that matches one option, and — the part
    a naive structural check misses — no two options sharing the same value,
    which would make the question ambiguous even though it "looks" valid.
    """
    if not isinstance(q, dict):
        return False
    if not isinstance(q.get("question"), str) or not q["question"].strip():
        return False
    options = q.get("options")
    if not isinstance(options, list) or len(options) < 2:
        return False
    if any(not isinstance(o, str) or not o.strip() for o in options):
        return False
    option_letters = {o[0].upper() for o in options}
    if len(option_letters) != len(options):
        return False  # duplicate letters
    option_values = {o[3:].strip().lower() for o in options}
    if len(option_values) != len(options):
        return False  # two options evaluate/read the same — ambiguous
    answer = q.get("answer")
    return isinstance(answer, str) and answer.strip().upper() in option_letters


async def generate_quiz_questions(topic: str, level: str, demand: str = "routine", count: int = 5) -> list:
    """
    Generate quiz questions either via LLM (given a rigor-and-validation
    blueprint) or via generate_verified_questions(), whose answers are
    computed by SymPy rather than hand-written or guessed by a model.

    `level` is how advanced the topic/formulas are (basic/intermediate/
    advanced/expert); `demand` is how much reasoning a routine application
    takes, independent of level (routine/multi_step/unfamiliar) — these are
    deliberately two separate axes instead of one flattened "difficulty",
    since a routine question and an unfamiliar one at the same level are not
    interchangeable, and a single label was collapsing that distinction.

    Every question — from either source — is structurally validated before
    being returned; an LLM question that fails validation (ambiguous
    options, a stated answer that doesn't match any option, etc.) is
    dropped and backfilled with a verified generated question rather than
    shown to a student.
    """
    provider = settings.LLM_PROVIDER.lower()
    demand_desc = _DEMAND_DESCRIPTIONS.get(demand, _DEMAND_DESCRIPTIONS["routine"])
    prompt = f"""Generate {count} multiple-choice math questions about '{topic}' at '{level}' level.

Question demand: '{demand}' — each question should require {demand_desc}.

Work out the full solution yourself, step by step, BEFORE writing the
question down, so the "answer" you report is verified, not guessed. Then:
- Write exactly 4 options. Exactly ONE may be correct.
- Make the 3 incorrect options plausible: each should be the value a
  student would get from one specific, realistic mistake (a sign error,
  the wrong formula, an off-by-one, a dropped constant of integration,
  etc.) — not random unrelated numbers.
- No two options may share the same value.
- Every question in the batch must be different from the others.

Return ONLY a JSON array. Each element: {{"question": "...", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "answer": "A", "explanation": "..."}}

No extra text — pure JSON array only."""

    questions: list = []
    try:
        raw = ""
        if provider == "anthropic" and _key_looks_real(settings.ANTHROPIC_API_KEY):
            raw = await _call_anthropic(prompt)
        elif provider == "openai" and _key_looks_real(settings.OPENAI_API_KEY):
            raw = await _call_openai(prompt)
        elif provider == "gemini" and _get_gemini_keys():
            raw = await _call_gemini(prompt)

        if raw:
            start, end = raw.find("["), raw.rfind("]") + 1
            if start != -1 and end > start:
                parsed = json.loads(raw[start:end])
                if isinstance(parsed, list):
                    questions = [q for q in parsed if _valid_quiz_question(q)]
    except Exception:
        pass

    if len(questions) < count:
        # Either no LLM is configured, or it returned fewer valid questions
        # than asked for — top up with SymPy-verified generated ones rather
        # than show fewer questions than the student requested.
        questions += generate_verified_questions(topic, level, demand, count - len(questions))

    return questions[:count]
