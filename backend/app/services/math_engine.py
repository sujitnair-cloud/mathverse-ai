"""
Core symbolic math engine using SymPy.
Handles solving, simplification, differentiation, integration, and more.
"""
import sympy as sp
from sympy import (
    symbols, solve, simplify, expand, factor, diff, integrate,
    limit, series, Matrix, det, latex, sympify, sqrt,
    sin, cos, tan, asin, acos, atan, exp, log, pi, E,
    Rational, oo, I, Symbol, Function, Eq,
    trigsimp, nsimplify, N, pretty
)
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
import numpy as np
import re
from typing import Any, Dict, List, Optional, Tuple


TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)

# Unicode math symbol normalization map
UNICODE_MAP = [
    # Superscripts → ** (must come before other replacements)
    ("⁰", "**0"), ("¹", "**1"), ("²", "**2"), ("³", "**3"), ("⁴", "**4"),
    ("⁵", "**5"), ("⁶", "**6"), ("⁷", "**7"), ("⁸", "**8"), ("⁹", "**9"),
    # Subscripts (often used in labels)
    ("₀", "0"), ("₁", "1"), ("₂", "2"), ("₃", "3"), ("₄", "4"),
    ("₅", "5"), ("₆", "6"), ("₇", "7"), ("₈", "8"), ("₉", "9"),
    # Operators
    ("×", "*"), ("·", "*"), ("÷", "/"), ("−", "-"), ("–", "-"), ("—", "-"),
    # Constants. "∫" becomes the word "integral" (not deleted!) so that
    # detect_topic()/the integration solver's keyword checks still see it —
    # deleting it outright previously erased every trace that a problem was
    # an integral, letting it fall through to unrelated topic heuristics
    # (e.g. "∫ x e^(x²) dx" got misrouted as "algebra_quadratic" purely
    # because "x**2" appears as a substring, once the ∫ itself was gone).
    ("π", "pi"), ("∞", "oo"), ("∫", " integral "),
    # Roots
    ("√", "sqrt"),
    # Greek letters commonly used in math
    ("α", "alpha"), ("β", "beta"), ("γ", "gamma"), ("δ", "delta"),
    ("θ", "theta"), ("λ", "lambda"), ("μ", "mu"), ("σ", "sigma"),
    ("φ", "phi"), ("ω", "omega"),
    # Misc
    ("≤", "<="), ("≥", ">="), ("≠", "!="),
]

_SUBSCRIPT_DIGITS = "₀₁₂₃₄₅₆₇₈₉"
_SUPERSCRIPT_DIGITS = "⁰¹²³⁴⁵⁶⁷⁸⁹"
_SUB_TO_NUM = str.maketrans(_SUBSCRIPT_DIGITS, "0123456789")
_SUP_TO_NUM = str.maketrans(_SUPERSCRIPT_DIGITS, "0123456789")
# "∫₀¹ ... dx" — a bare integral sign immediately followed by a subscript
# (lower bound) then a superscript (upper bound), the standard way a
# definite integral is typeset. Must run BEFORE the generic superscript
# UNICODE_MAP entries above, which would otherwise misread the upper bound
# digit as an exponent (e.g. "∫₀¹" -> "0**1", losing the bounds entirely).
_DEFINITE_INTEGRAL_RE = re.compile(
    rf"∫\s*([{_SUBSCRIPT_DIGITS}]+)\s*([{_SUPERSCRIPT_DIGITS}]+)"
)


def _extract_definite_integral_bounds(s: str) -> str:
    def _replace(m: "re.Match") -> str:
        lower = m.group(1).translate(_SUB_TO_NUM)
        upper = m.group(2).translate(_SUP_TO_NUM)
        return f" integral from {lower} to {upper} of "
    return _DEFINITE_INTEGRAL_RE.sub(_replace, s)


def normalize_math_input(s: str) -> str:
    """
    Convert common mathematical notation that SymPy's parser can't read
    directly into an equivalent form it can, so students don't have to write
    programming syntax. Shared by both the solver and the grapher.
    """
    s = _extract_definite_integral_bounds(s)
    for uni, asc in UNICODE_MAP:
        s = s.replace(uni, asc)
    s = s.replace("^", "**")
    # |expr| -> Abs(expr). Handles sequential (non-nested) pairs, e.g.
    # "|x| + |x-2|" -> "Abs(x) + Abs(x-2)".
    s = re.sub(r"\|([^|]+)\|", r"Abs(\1)", s)
    # log_3(x) / log_b(x) subscript-base notation -> log(x, 3) / log(x, b),
    # which is how SymPy spells "log base 3 of x". Only handles a
    # non-nested argument (no inner parentheses), which covers the common
    # single-expression case.
    s = re.sub(r"log_(\w+)\(([^()]*)\)", r"log(\2, \1)", s)
    # Standalone "e" -> Euler's number. Without this, SymPy's parser treats
    # a bare "e" as an ordinary free symbol (e**(x**2) integrates to a
    # nonsensical Piecewise case-split on the unknown "e" instead of the
    # correct (E-1)/2-style closed form) -- it has no built-in notion that
    # "e" commonly means Euler's number the way it already does for "pi".
    # The negative lookbehind/lookahead avoid clobbering "e" inside a longer
    # identifier (exp, expr, the) or scientific notation (1e-5, 2e10, where
    # a digit immediately precedes the "e").
    s = re.sub(r"(?<![0-9a-zA-Z_])e(?![a-zA-Z_])", "E", s)
    return s


def preprocess_problem(problem: str) -> str:
    """
    Normalize informal, incomplete, or unusual math notation.
    Tolerates missing brackets, trailing punctuation, natural-language prefixes,
    informal spacing, etc.
    """
    p = problem.strip()
    # Strip trailing punctuation that has no math meaning
    p = re.sub(r"[.!?]+$", "", p).strip()
    # Strip a leading list/question-numbering marker, e.g. "2. Evaluate ..."
    # or "Q3) ...". Without this, "2. Evaluate ..." doesn't start with
    # "evaluate" so the natural-language-prefix strip below never matches,
    # leaving "Evaluate" in the string to later get flagged as prose.
    # Requires whitespace then a letter after the marker (not just any
    # character) so a genuine leading decimal like "3.5 + 2" is left alone.
    p = re.sub(r"^\s*(?:q(?:uestion)?\s*)?\d+[\.\)]\s+(?=[A-Za-z])", "", p, flags=re.IGNORECASE).strip()
    # Apply Unicode normalization
    p = normalize_math_input(p)
    # Remove natural-language prefixes: "what is", "find", "calculate", etc.
    # Applied repeatedly (not just once) so a chain like "Evaluate the
    # integral..." has both "Evaluate " and the leftover "the " stripped —
    # a single pass left "the" dangling, which looks_like_prose() then
    # correctly (but unhelpfully) flagged as English rather than math.
    _prefix_re = re.compile(
        r"^(what\s+is|find\s+the|find|calculate|compute|evaluate|determine|give\s+me|tell\s+me|solve\s+for|solve|the)\s+",
        re.IGNORECASE,
    )
    while True:
        new_p = _prefix_re.sub("", p).strip()
        if new_p == p:
            break
        p = new_p
    # Add brackets to trig/log calls written without them: "sin 30" → "sin(30)"
    for fn in ["sin", "cos", "tan", "asin", "acos", "atan", "log", "ln", "sqrt", "exp"]:
        p = re.sub(rf"\b{fn}\s+([0-9a-zA-Z_]+(?:\.[0-9]+)?)\b", rf"{fn}(\1)", p, flags=re.IGNORECASE)
    return p.strip()


# ── LLM-first routing: problems SymPy can't meaningfully handle ────────────────
_WORD_PROBLEM_RE = re.compile(
    # People / vehicles / objects in motion or transactions
    r"\b(a man|a woman|a train|a car|a boat|a pipe|a tank|a worker|a shopkeeper|"
    r"a merchant|two pipes|two trains|two cars|two cyclists|two runners|a bird|"
    r"a ball|a particle|a body|a projectile)\b"
    # Proofs and verifications
    r"|\bprove\b|\bshow\s+that\b|\bverify\s+that\b|\bprove\s+that\b"
    # Combinatorics word problems
    r"|\bin\s+how\s+many\s+ways\b|\bhow\s+many\s+ways\b"
    # Age / time problems
    r"|\b(ages?|years\s+old|years\s+ago|years\s+hence|days?\s+ago|months?\s+ago)\b"
    # Commerce / finance
    r"|\b(profit|loss|discount|selling\s+price|cost\s+price|marked\s+price|"
    r"simple\s+interest|compound\s+interest|principal|rate\s+of\s+interest)\b"
    # Mixing problems
    r"|\b(mixture|alligation|concentration|solution\s+of)\b"
    # Competitive exams
    r"|\biit[\s-]*jee\b|\bjee\s+(main|advanced)\b|\bolympiad\b|\baptitude\s+test\b"
    # Multi-part / challenge structure (numbered questions, 'Extra Challenge', 'Find:')
    r"|\bextra\s+challenge\b|\bfind\s*:\s*\n|\b(part\s+[123]|question\s+[123])\b"
    # Speed-distance-time word problems
    r"|\bstarts?\s+(from|at)\s+station\b|\bkm\s+apart\b|\btowards?\s+each\s+other\b"
    # Physics word problems
    r"|\b(velocity|acceleration|projectile|momentum|force|gravity|freefall)\b",
    re.IGNORECASE,
)


def is_llm_first_problem(problem: str) -> bool:
    """
    Return True when the problem should bypass SymPy and go straight to the LLM.
    Catches word problems, proofs, applied/aptitude problems, exam-style questions,
    and graduate-level analysis requests (Fourier/Laplace transforms, PDEs, etc.)
    that the per-topic SymPy solvers below have no dedicated handler for — sending
    those through the generic algebra fallback produces fabricated nonsense instead
    of an error (e.g. "Fourier transform of e^(-t^2)" silently multiplying the
    individual letters of "Fourier" and "transform" together as if they were
    single-letter variables).
    """
    p = problem.lower()
    return bool(_WORD_PROBLEM_RE.search(problem)) or any(k in p for k in _EXPERT_KEYWORDS)


class UnsafeExpressionError(ValueError):
    """Raised when input can't be shown safe to hand to SymPy's parser."""


_SAFE_EXPR_CHARS = re.compile(r"^[A-Za-z0-9\s+\-*/.,()=<>!%]*$")


def reject_unsafe_expression(s: str) -> None:
    """
    SymPy's sympify()/parse_expr() parse math input by compiling it to a
    Python expression and calling eval() on it. They are NOT safe on
    untrusted input — this is documented by SymPy itself, and was verified
    directly against this codebase before this check existed:
      __import__("os").system("...")           ran an arbitrary shell command
      ().__class__.__base__.__subclasses__()    walked the whole object graph,
                                                 no __import__ needed
    Both rely on double-underscore dunder access, and both need characters
    (quotes, brackets, colons) a real math expression never needs. Reject
    both categories before the string ever reaches SymPy's parser. Call
    this on every user-supplied string before parse_expr()/sympify(),
    even ones that already went through safe_parse() for something else
    (e.g. the two sides of an equation, split and parsed separately).
    """
    if "__" in s:
        raise UnsafeExpressionError("Expression contains a disallowed pattern.")
    if not _SAFE_EXPR_CHARS.match(s):
        raise UnsafeExpressionError("Expression contains disallowed characters.")


def safe_parse(expr_str: str) -> Any:
    """Parse a math expression string safely, handling Unicode math symbols."""
    expr_str = normalize_math_input(expr_str.strip())
    reject_unsafe_expression(expr_str)
    return parse_expr(expr_str, transformations=TRANSFORMATIONS)


_KNOWN_MATH_WORDS = {
    "sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh",
    "log", "ln", "exp", "sqrt", "abs", "pi", "oo", "min", "max", "gcd",
    "lcm", "mod", "and", "or", "not",
}

# Connector words that are never legitimate variable names but are short
# enough to slip under the length-3 prose check below (e.g. "50% of 200"
# parsing "of" as the implicitly-multiplied variables o*f, alongside "%"
# being read as modulo, to produce "200*f*(Mod(50, o))").
_PROSE_MARKER_WORDS = {"of", "is", "to", "in", "on", "an", "as", "for", "with", "at"}


def looks_like_prose(s: str) -> bool:
    """
    True when a string still contains English-word-like runs after removing
    recognized math function names — a sign this is natural language rather
    than a parseable expression (e.g. "Fourier transform of e^(-t^2)" — SymPy's
    implicit-multiplication parser will happily accept "Fourier" as F*o*u*r*i*e*r
    and silently return a fabricated answer instead of failing).
    Single- and double-letter tokens are allowed through since those are how
    students actually write variables (x, dx, ab for a*b, etc.), except for a
    short list of connector words that are never legitimate variable names.
    """
    for tok in re.findall(r"[a-zA-Z]+", s):
        low = tok.lower()
        if low in _KNOWN_MATH_WORDS:
            continue
        if low in _PROSE_MARKER_WORDS or len(tok) >= 3:
            return True
    return False


def _strip_wrapping_parens(s: str) -> str:
    """
    Remove a single pair of parentheses that wraps the *entire* string, e.g.
    "(x^2 + 1)" -> "x^2 + 1". Unlike `str.strip("()")`, this only strips when
    the leading "(" actually matches the trailing ")" as one pair — plain
    `.strip("()")` also mangles "sin(x)" into "sin(x" (it blindly trims any
    "(" / ")" characters off each end) and turns "(x+1)*(x-1)" into the
    unbalanced "x+1)*(x-1", both previously causing parse errors on
    otherwise-valid input.
    """
    s = s.strip()
    while s.startswith("(") and s.endswith(")"):
        depth = 0
        matches_at_end = False
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    matches_at_end = (i == len(s) - 1)
                    break
        if not matches_at_end:
            break
        s = s[1:-1].strip()
    return s


_PROSE_ERROR = (
    "This doesn't look like a solvable expression or equation — it may need a "
    "full worked derivation (proofs, transforms, and similar advanced requests "
    "aren't handled by the structured solver). Try our AI-powered full solver, "
    "or rephrase this as a direct expression or equation, e.g. 'x^2 + 3x = 10'."
)


def _infer_variable(expr: Any, problem: str, default_name: str = "x") -> Any:
    """
    Pick the variable to differentiate/integrate/take a limit with respect to.
    Prefers an explicit "with respect to <var>" or "d/d<var>" in the problem
    text; otherwise uses the expression's own free variable when there's
    exactly one (fixes e.g. "differentiate t^2 + 3t" silently returning 0
    because the code always differentiated with respect to x regardless of
    what variable the expression actually used); falls back to `default_name`
    for constant or genuinely multivariable expressions, matching prior
    behavior.
    """
    m = re.search(r"with\s+respect\s+to\s+([a-zA-Z])\b", problem, re.IGNORECASE)
    if not m:
        m = re.search(r"\bd\s*/\s*d([a-zA-Z])\b", problem, re.IGNORECASE)
    if not m:
        # Leibniz integral notation: "... x^2 dx" / "... t^2 dt"
        m = re.search(r"\bd([a-zA-Z])\s*$", problem.strip(), re.IGNORECASE)
    if m:
        return symbols(m.group(1))
    default = symbols(default_name)
    free = expr.free_symbols if hasattr(expr, "free_symbols") else set()
    if default in free or not free:
        return default
    if len(free) == 1:
        return next(iter(free))
    return default


_EXTREMA_KEYWORDS = (
    "local maximum", "local minimum", "local max", "local min",
    "global maximum", "global minimum", "absolute maximum", "absolute minimum",
    "extremum", "extrema", "critical point", "critical number", "stationary point",
)


def detect_topic(problem: str) -> str:
    """Heuristically detect the math topic from a problem string."""
    p = problem.lower()
    if any(k in p for k in ["integral", "integrate", "antiderivative"]) or "∫" in p:
        return "calculus_integration"
    if any(k in p for k in ["derivative", "differentiate", "d/dx"]):
        return "calculus_differentiation"
    # Finding a local max/min, extremum, or inflection point requires taking
    # a derivative even when the problem never says "derivative"/"d/dx" —
    # without this, a phrasing like "at which value of x does f have a local
    # maximum" fell through to the quadratic/general checks below.
    if any(k in p for k in _EXTREMA_KEYWORDS + ("inflection point", "concave", "increasing or decreasing", "rate of change")):
        return "calculus_differentiation"
    # Use word boundary so "lim" in "limit" matches but not in "limits" of unrelated words
    if re.search(r"\b(limit|lim|approaches)\b", p):
        return "calculus_limits"
    # "[[" (a nested bracket) is essentially only ever used here for matrix
    # notation, so treat it as linear algebra even without a keyword match —
    # covers phrasings like "det [[1,2],[3,4]]" or "inverse of [[2,0],[0,2]]"
    # that don't contain the literal word "matrix"/"determinant".
    if (any(k in p for k in ["matrix", "determinant", "eigenvalue", "inverse matrix"])
            or re.search(r"\bdet\b", p) or "[[" in p.replace(" ", "")):
        return "linear_algebra"
    # Geometry must come before trigonometry because "triangle" contains "angle"
    if any(k in p for k in ["area", "perimeter", "volume", "geometry", "triangle", "circle", "rectangle", "square", "pythagorean", "hypotenuse"]):
        return "geometry"
    # Use word boundaries to prevent "sin" matching inside "simultaneously", "cosine" in "discourse", etc.
    if re.search(r"\b(sin|cos|tan|asin|acos|atan|sine|cosine|tangent|angle|degrees?|radians?|trigonometric)\b", p):
        return "trigonometry"
    # A cubic like "x³ - 6x² + 9x + 1" contains "x²" as a substring too, so a
    # bare "x²"/"x^2" match alone isn't enough — only treat it as quadratic
    # when there's no higher-degree term also present in the problem.
    _has_higher_degree_term = bool(re.search(r"x\s*(?:\*\*|\^)\s*[3-9]\d*", p)) or any(
        k in p for k in ["x³", "x⁴", "x⁵", "x⁶", "x⁷", "x⁸", "x⁹"]
    )
    if "quadratic" in p or "parabola" in p or (
        any(k in p for k in ["x²", "x^2", "x**2", "**2"]) and not _has_higher_degree_term
    ):
        return "algebra_quadratic"
    if any(k in p for k in ["linear equation", "solve for", "system of equations"]):
        return "algebra_linear"
    if any(k in p for k in ["probability", "permutation", "combination", "ncr", "npr"]):
        return "probability"
    # Detect nCr/nPr shorthand like C(10,3) or 10C3
    if re.search(r"\bc\s*\(\s*\d+\s*,\s*\d+", p) or re.search(r"\d+\s*c\s*\d+", p):
        return "probability"
    if re.search(r"\bp\s*\(\s*\d+\s*,\s*\d+", p) or re.search(r"\d+\s*p\s*\d+", p):
        return "probability"
    if any(k in p for k in ["mean", "median", "mode", "standard deviation", "variance", "statistics"]):
        return "statistics"
    if any(k in p for k in ["factor", "polynomial", "expand", "simplify"]):
        return "algebra_polynomial"
    if any(k in p for k in ["percent", "%", "ratio", "proportion"]):
        return "arithmetic_percent"
    if any(k in p for k in ["log", "logarithm", "ln", "exponent"]):
        return "algebra_logarithm"
    return "algebra_general"


_EXPERT_KEYWORDS = (
    "differential equation", "partial differential", "fourier", "laplace transform",
    "contour integral", "residue theorem", "green's theorem", "stokes",
    "eigenvector", "eigenvalue", "singular value",
    "complex analysis", "real analysis", "abstract algebra", "topology",
    "hilbert space", "banach space", "vector space", "linear transformation",
    "triple integral", "line integral", "surface integral",
    "lagrange multiplier", "taylor series", "maclaurin series",
    "power series", "radius of convergence", "multivariable",
    "jacobian", "hessian", "gradient descent",
    "number theory", "modular arithmetic", "congruence modulo",
    "generating function", "recurrence relation", "graph theory",
    "binomial theorem", "proof by induction", "mathematical induction",
    "iit", "jee", "olympiad", "putnam", "imo", "aime",
    "aptitude", "cat exam", "gmat",
)

_ADVANCED_KEYWORDS = (
    "parametric", "polar coordinates", "implicit differentiation",
    "related rates", "convergence", "divergence test",
    "complex number", "de moivre", "roots of unity",
    "critical point", "inflection point", "system of equation",
    "optimization",
)


def detect_difficulty(problem: str) -> str:
    p = problem.lower()
    if any(k in p for k in _EXPERT_KEYWORDS):
        return "expert"
    if any(k in p for k in _ADVANCED_KEYWORDS):
        return "advanced"
    topic = detect_topic(problem)
    if any(t in topic for t in ("calculus", "linear_algebra")):
        return "advanced"
    if any(t in topic for t in ("trigonometry", "quadratic", "logarithm", "polynomial", "statistics", "probability")):
        return "intermediate"
    return "basic"


def solve_expression(problem: str) -> Dict[str, Any]:
    """
    Main entry point. Attempts to solve or simplify a math expression/equation.
    Returns a structured result with steps, latex, and answer.
    """
    # Normalise input — tolerates missing brackets, punctuation, natural language
    problem_clean = preprocess_problem(problem)

    result = {
        "problem": problem,           # keep original for display
        "topic": detect_topic(problem_clean),
        "difficulty": detect_difficulty(problem_clean),
        "steps": [],
        "answer": None,
        "latex_answer": None,
        "alternate_method": None,
        "formulas_used": [],
        "common_mistakes": [],
        "similar_problems": [],
        "error": None,
    }

    try:
        p = problem_clean

        # Route to specialized solvers
        topic = result["topic"]

        if topic == "calculus_differentiation":
            if any(k in p.lower() for k in _EXTREMA_KEYWORDS):
                return _solve_local_extrema(p, result)
            return _solve_differentiation(p, result)
        if topic == "calculus_integration":
            return _solve_integration(p, result)
        if topic == "calculus_limits":
            return _solve_limit(p, result)
        if topic == "linear_algebra":
            return _solve_linear_algebra(p, result)
        if topic == "statistics":
            return _solve_statistics(p, result)
        if topic == "probability":
            return _solve_probability(p, result)
        if "algebra" in topic or "arithmetic" in topic:
            return _solve_algebra(p, result)
        if topic == "geometry":
            return _solve_geometry(p, result)
        if topic == "trigonometry":
            return _solve_trigonometry(p, result)

        # Generic fallback
        return _solve_algebra(p, result)

    except Exception as e:
        result["error"] = str(e)
        result["steps"] = [{"step": 1, "description": "Could not parse the problem automatically.", "expression": problem}]
        return result


def _solve_algebra(problem: str, result: Dict) -> Dict:
    steps = []
    # Strip common instruction prefixes like "Solve:", "Solve ", "Simplify:", etc.
    p = problem.replace("^", "**")
    for prefix in ["solve:", "simplify:", "expand:", "factor:", "evaluate:", "find:", "calculate:",
                   "solve ", "simplify ", "expand ", "factor ", "evaluate ", "find ", "calculate "]:
        if p.lower().startswith(prefix):
            p = p[len(prefix):].strip()
            break

    if looks_like_prose(p):
        result["error"] = _PROSE_ERROR
        result["answer"] = None
        return result

    # Check if it's an equation (contains =)
    if "=" in p:
        parts = p.split("=")
        if len(parts) == 2:
            # Pre-define common variables as real so implicit multiplication
            # works correctly and so SymPy can solve equations involving
            # Abs()/sqrt() — solve() refuses those for a plain complex-domain
            # symbol (e.g. "|x - 5| = 3" errors with "argument is not real or
            # imaginary" unless x is declared real), and virtually every
            # equation a student writes here is over the reals anyway.
            local_ns = {str(s): s for s in symbols("x y z a b c n t", real=True)}
            lhs_str, rhs_str = parts[0].strip(), parts[1].strip()
            reject_unsafe_expression(lhs_str)
            reject_unsafe_expression(rhs_str)
            lhs = parse_expr(lhs_str, local_dict=local_ns, transformations=TRANSFORMATIONS)
            rhs = parse_expr(rhs_str, local_dict=local_ns, transformations=TRANSFORMATIONS)
            steps.append({
                "step": 1, "description": "Identify the equation",
                "expression": f"{lhs} = {rhs}", "latex": f"{latex(lhs)} = {latex(rhs)}",
            })
            steps.append({
                "step": 2, "description": "Move all terms to one side",
                "expression": f"{lhs} - ({rhs}) = 0",
                "latex": f"{latex(lhs)} - \\left({latex(rhs)}\\right) = 0",
            })
            eq = Eq(lhs, rhs)
            free = eq.free_symbols
            x = symbols("x", real=True)
            if x in free:
                var = x
            elif free:
                var = sorted(free, key=lambda s: str(s))[0]
            else:
                var = x
            solution = solve(eq, var)
            steps.append({
                "step": 3, "description": f"Solve for {var}",
                "expression": f"{var} = {solution}", "latex": f"{latex(var)} = {latex(solution)}",
            })
            result["answer"] = str(solution)
            result["latex_answer"] = f"{latex(var)} = {latex(solution)}"
            result["steps"] = steps
            result["formulas_used"] = ["Algebraic manipulation", "Zero-product property"]
            result["common_mistakes"] = [
                "Forgetting to apply the same operation to both sides",
                "Sign errors when moving terms across the equals sign"
            ]
            result["similar_problems"] = _generate_similar_algebra(var)
            return result

    # Just simplify/evaluate
    expr = safe_parse(p)
    steps.append({"step": 1, "description": "Parse the expression", "expression": str(expr), "latex": latex(expr)})
    simplified = simplify(expr)
    steps.append({"step": 2, "description": "Simplify", "expression": str(simplified), "latex": latex(simplified)})
    try:
        numeric = float(N(simplified))
        steps.append({"step": 3, "description": "Numeric value", "expression": str(numeric), "latex": str(numeric)})
        result["answer"] = str(numeric)
    except Exception:
        result["answer"] = str(simplified)
    result["latex_answer"] = latex(simplified)
    result["steps"] = steps
    result["formulas_used"] = ["Algebraic simplification rules"]
    result["common_mistakes"] = ["Order of operations errors (PEMDAS/BODMAS)"]
    return result


def _solve_differentiation(problem: str, result: Dict) -> Dict:
    steps = []
    p = problem.replace("^", "**")
    # Remove instruction words, keep only the math expression
    for keyword in ["d/dx of", "d/dx", "differentiate", "derivative of", "find the derivative of", "find derivative of"]:
        low = p.lower()
        idx = low.find(keyword)
        if idx != -1:
            p = p[idx + len(keyword):].strip()
            break
    p = _strip_wrapping_parens(p)

    if looks_like_prose(p):
        result["error"] = _PROSE_ERROR
        result["answer"] = None
        return result

    expr = safe_parse(p)
    x = _infer_variable(expr, problem)
    steps.append({"step": 1, "description": "Identify the function to differentiate", "expression": str(expr), "latex": latex(expr)})
    steps.append({"step": 2, "description": "Apply differentiation rules (Power, Chain, Product, Quotient)", "expression": ""})
    derivative = diff(expr, x)
    steps.append({"step": 3, "description": "Compute derivative", "expression": str(derivative), "latex": latex(derivative)})
    simplified_deriv = simplify(derivative)
    steps.append({"step": 4, "description": "Simplify result", "expression": str(simplified_deriv), "latex": latex(simplified_deriv)})

    result["steps"] = steps
    result["answer"] = str(simplified_deriv)
    result["latex_answer"] = f"\\frac{{d}}{{d{latex(x)}}}\\left({latex(expr)}\\right) = {latex(simplified_deriv)}"
    result["formulas_used"] = ["Power Rule: d/dx(xⁿ) = nxⁿ⁻¹", "Chain Rule", "Product Rule", "Quotient Rule"]
    result["common_mistakes"] = [
        "Forgetting the chain rule for composite functions",
        "Treating constants as variables"
    ]
    result["alternate_method"] = f"Using limits: lim(h→0) [f(x+h) - f(x)] / h"
    return result


def _extract_function_expr(problem: str) -> str:
    """
    Pull the expression out of a 'f(x) = ...' (or g(x), y = ...) definition
    embedded in a word problem, e.g. "If f(x) = x^3 - 6x^2 + 9x + 1, at which
    value of x does f have a local maximum?" -> "x^3 - 6x^2 + 9x + 1". Without
    this, the whole prose sentence gets handed to the parser and rejected.
    """
    m = re.search(
        r"[a-zA-Z]\s*\(\s*[a-zA-Z]\s*\)\s*=\s*(.+?)(?:,|\.\s|\.$|$| at | where | for | on \[)",
        problem, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    m = re.search(r"\by\s*=\s*(.+?)(?:,|\.\s|\.$|$)", problem, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return problem


def _solve_local_extrema(problem: str, result: Dict) -> Dict:
    steps = []
    expr_str = _extract_function_expr(problem).replace("^", "**")
    expr_str = _strip_wrapping_parens(expr_str)

    if looks_like_prose(expr_str):
        result["error"] = _PROSE_ERROR
        result["answer"] = None
        return result

    expr = safe_parse(expr_str)
    x = _infer_variable(expr, problem)
    steps.append({
        "step": 1, "description": "Identify the function",
        "expression": f"f({x}) = {expr}", "latex": f"f({latex(x)}) = {latex(expr)}",
    })

    first_deriv = simplify(diff(expr, x))
    steps.append({
        "step": 2, "description": "Compute the first derivative",
        "expression": f"f'({x}) = {first_deriv}", "latex": f"f'({latex(x)}) = {latex(first_deriv)}",
    })

    critical_points = [cp for cp in solve(Eq(first_deriv, 0), x) if cp.is_real]
    if critical_points:
        step3_expr = f"{x} = " + ", ".join(str(cp) for cp in critical_points)
        step3_latex = f"{latex(x)} = " + ", ".join(latex(cp) for cp in critical_points)
    else:
        step3_expr = "No real critical points"
        step3_latex = None
    steps.append({
        "step": 3,
        "description": "Solve f'(x) = 0 for critical points",
        "expression": step3_expr,
        "latex": step3_latex,
    })

    second_deriv = simplify(diff(first_deriv, x))
    steps.append({
        "step": 4, "description": "Compute the second derivative",
        "expression": f"f''({x}) = {second_deriv}", "latex": f"f''({latex(x)}) = {latex(second_deriv)}",
    })

    classified = []
    for cp in critical_points:
        second_at_cp = second_deriv.subs(x, cp)
        if second_at_cp > 0:
            kind = "local minimum"
        elif second_at_cp < 0:
            kind = "local maximum"
        else:
            kind = "inflection point (second derivative test inconclusive)"
        classified.append((cp, kind))
        steps.append({
            "step": len(steps) + 1,
            "description": f"Second derivative test at {x} = {cp}: f''({cp}) = {second_at_cp}",
            "expression": f"{x} = {cp} is a {kind}",
            "latex": f"{latex(x)} = {latex(cp)} \\ \\text{{is a {kind}}}",
        })

    p_lower = problem.lower()
    wants_min = any(k in p_lower for k in ["minimum", "min"])
    wants_max = any(k in p_lower for k in ["maximum", "max"])
    if wants_max and not wants_min:
        matches = [cp for cp, kind in classified if kind == "local maximum"]
    elif wants_min and not wants_max:
        matches = [cp for cp, kind in classified if kind == "local minimum"]
    else:
        matches = [cp for cp, _ in classified]

    if not matches:
        result["error"] = "This function has no local extremum of the requested type."
        result["answer"] = None
        return result

    result["steps"] = steps
    result["answer"] = ", ".join(f"{x} = {m}" for m in matches)
    result["latex_answer"] = f"{latex(x)} = {', '.join(latex(m) for m in matches)}"
    result["formulas_used"] = [
        "First derivative test: critical points occur where f'(x) = 0",
        "Second derivative test: f''(x) > 0 -> local min, f''(x) < 0 -> local max",
    ]
    result["common_mistakes"] = [
        "Forgetting to discard non-real roots of f'(x) = 0",
        "Confusing local maxima with local minima when reading the sign of f''(x)",
        "Not checking endpoints separately when the domain is a closed interval",
    ]
    return result


_DEFINITE_BOUNDS_RE = re.compile(r"integral\s+from\s+(.+?)\s+to\s+(.+?)\s+of\s+", re.IGNORECASE)


def _solve_integration(problem: str, result: Dict) -> Dict:
    steps = []
    p = problem.lower().replace("^", "**")

    # Definite integral bounds, inserted as "integral from L to U of ..." by
    # normalize_math_input()'s handling of "∫₀¹"-style notation. Must be
    # pulled out before the generic keyword-strip below, which would
    # otherwise leave a dangling "from 0 to 1" that looks_like_prose() then
    # correctly (but unhelpfully) rejects as English.
    lower_bound_str = upper_bound_str = None
    bounds_match = _DEFINITE_BOUNDS_RE.search(p)
    if bounds_match:
        lower_bound_str, upper_bound_str = bounds_match.group(1).strip(), bounds_match.group(2).strip()
        p = p[:bounds_match.start()] + p[bounds_match.end():]

    for keyword in ["integrate", "integral of", "integral", "∫", "antiderivative of"]:
        p = p.replace(keyword, "").strip()
    # Remove dx at end
    p = re.sub(r"\s*d[a-z]\s*$", "", p).strip()
    p = _strip_wrapping_parens(p)

    if looks_like_prose(p):
        result["error"] = _PROSE_ERROR
        result["answer"] = None
        return result

    expr = safe_parse(p)
    x = _infer_variable(expr, problem)
    steps.append({"step": 1, "description": "Identify the integrand", "expression": str(expr), "latex": latex(expr)})
    steps.append({"step": 2, "description": "Apply integration rules", "expression": ""})
    antiderivative = integrate(expr, x)
    steps.append({"step": 3, "description": "Compute the antiderivative", "expression": str(antiderivative), "latex": latex(antiderivative)})

    if lower_bound_str is not None and upper_bound_str is not None:
        try:
            lo, hi = safe_parse(lower_bound_str), safe_parse(upper_bound_str)
        except Exception:
            lo = hi = None
        if lo is not None and hi is not None:
            definite_value = simplify(integrate(expr, (x, lo, hi)))
            steps.append({
                "step": 4,
                "description": f"Evaluate from {x} = {lower_bound_str} to {x} = {upper_bound_str}",
                "expression": f"[{antiderivative}] from {lower_bound_str} to {upper_bound_str} = {definite_value}",
                "latex": f"\\Big[{latex(antiderivative)}\\Big]_{{{latex(lo)}}}^{{{latex(hi)}}} = {latex(definite_value)}",
            })
            result["steps"] = steps
            result["answer"] = str(definite_value)
            result["latex_answer"] = f"\\int_{{{latex(lo)}}}^{{{latex(hi)}}} {latex(expr)}\\, d{latex(x)} = {latex(definite_value)}"
            result["formulas_used"] = ["Fundamental Theorem of Calculus: ∫ₐᵇ f(x) dx = F(b) - F(a)"]
            result["common_mistakes"] = [
                "Forgetting to evaluate at both bounds and subtract",
                "Sign errors when substituting the lower bound",
            ]
            return result

    steps.append({"step": 4, "description": "Add constant of integration C", "expression": f"{antiderivative} + C", "latex": f"{latex(antiderivative)} + C"})

    result["steps"] = steps
    result["answer"] = f"{antiderivative} + C"
    result["latex_answer"] = f"\\int {latex(expr)}\\, d{latex(x)} = {latex(antiderivative)} + C"
    result["formulas_used"] = ["Power Rule: ∫xⁿ dx = xⁿ⁺¹/(n+1) + C", "Substitution method"]
    result["common_mistakes"] = [
        "Forgetting the constant of integration C",
        "Incorrect substitution in u-substitution"
    ]
    return result


def _solve_limit(problem: str, result: Dict) -> Dict:
    steps = []
    p = problem.lower().replace("^", "**")
    var_str = None
    # Try to extract: limit of <expr> as <var> -> <val>
    match = re.search(r"(?:limit|lim)\s+(?:of\s+)?(.+?)\s+as\s+([a-zA-Z])\s*(?:->|→|approaches)\s*([^\s]+)", p)
    if match:
        expr_str, var_str, val_str = match.group(1).strip(), match.group(2), match.group(3).strip()
    else:
        # Try simple: lim <var>->0 of expr
        match2 = re.search(r"(?:limit|lim)\s*([a-zA-Z])\s*[-–>→]+\s*([^\s]+)\s+(?:of\s+)?(.+)", p)
        if match2:
            var_str, val_str, expr_str = match2.group(1), match2.group(2).strip(), match2.group(3).strip()
        else:
            expr_str = re.sub(r"(?:limit|lim)[\s\w\->→]*", "", p).strip()
            val_str = "0"

    if looks_like_prose(expr_str):
        result["error"] = _PROSE_ERROR
        result["answer"] = None
        return result

    expr = safe_parse(expr_str)
    x = symbols(var_str) if var_str else _infer_variable(expr, problem)
    try:
        val = safe_parse(val_str)
    except Exception:
        val = 0

    steps.append({
        "step": 1, "description": "Identify the expression and limit point",
        "expression": f"lim({x}→{val}) {expr}",
        "latex": f"\\lim_{{{latex(x)} \\to {latex(val)}}} {latex(expr)}",
    })
    steps.append({"step": 2, "description": "Check for direct substitution", "expression": ""})
    lim_val = limit(expr, x, val)
    steps.append({"step": 3, "description": "Evaluate limit", "expression": str(lim_val), "latex": latex(lim_val)})

    result["steps"] = steps
    result["answer"] = str(lim_val)
    result["latex_answer"] = f"\\lim_{{{latex(x)} \\to {latex(val)}}} {latex(expr)} = {latex(lim_val)}"
    result["formulas_used"] = ["Direct substitution", "L'Hôpital's rule (if 0/0 or ∞/∞ form)"]
    result["common_mistakes"] = ["Not checking if the limit is indeterminate before substituting"]
    return result


def _solve_linear_algebra(problem: str, result: Dict) -> Dict:
    steps = []
    p = problem.lower()
    # Simple 2x2 or 3x3 matrix operations demo
    steps.append({"step": 1, "description": "Parse matrix input", "expression": problem})

    # Try to extract a matrix from brackets notation like [[1,2],[3,4]]
    matrix_match = re.findall(r"\[([^\[\]]+)\]", problem)
    if len(matrix_match) >= 2:
        try:
            rows = []
            for row_str in matrix_match:
                row = [float(x.strip()) for x in row_str.split(",")]
                rows.append(row)
            mat = Matrix(rows)
            steps.append({"step": 2, "description": "Matrix formed", "expression": str(mat), "latex": latex(mat)})
            d = det(mat)
            steps.append({"step": 3, "description": "Determinant", "expression": str(d), "latex": latex(d)})
            if d != 0:
                inv_mat = mat.inv()
                steps.append({"step": 4, "description": "Inverse matrix", "expression": str(inv_mat), "latex": latex(inv_mat)})
                result["answer"] = f"det = {d}, inverse = {inv_mat}"
                result["latex_answer"] = f"\\det(A) = {latex(d)}"
            else:
                result["answer"] = f"det = 0 (matrix is singular, no inverse)"
        except Exception as e:
            result["error"] = str(e)
    else:
        result["answer"] = "Please provide the matrix in format: [[1,2],[3,4]]"
        steps.append({"step": 2, "description": "Input format required", "expression": "[[row1_col1, row1_col2], [row2_col1, row2_col2]]"})

    result["steps"] = steps
    result["formulas_used"] = ["Determinant formula", "Cofactor expansion", "Matrix inverse = adj(A)/det(A)"]
    result["common_mistakes"] = ["Row/column order errors", "Sign errors in cofactor expansion"]
    return result


def _solve_statistics(problem: str, result: Dict) -> Dict:
    steps = []
    p = problem.lower()
    # Extract numbers from the problem
    numbers = [float(x) for x in re.findall(r"-?\d+\.?\d*", problem)]

    if not numbers:
        result["error"] = "No numbers found. Please provide a dataset, e.g.: mean of [2, 4, 6, 8, 10]"
        return result

    arr = np.array(numbers)
    mean_val = float(np.mean(arr))
    median_val = float(np.median(arr))
    std_val = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    var_val = float(np.var(arr, ddof=1)) if len(arr) > 1 else 0.0

    steps.append({"step": 1, "description": "Dataset", "expression": str(list(arr))})
    steps.append({"step": 2, "description": "Sort the data", "expression": str(sorted(numbers))})
    steps.append({"step": 3, "description": f"Mean = sum/n = {sum(numbers)}/{len(numbers)}", "expression": str(mean_val)})
    steps.append({"step": 4, "description": "Median (middle value)", "expression": str(median_val)})
    steps.append({"step": 5, "description": "Standard Deviation", "expression": f"{std_val:.4f}"})
    steps.append({"step": 6, "description": "Variance", "expression": f"{var_val:.4f}"})

    result["steps"] = steps
    result["answer"] = f"Mean: {mean_val:.4f}, Median: {median_val:.4f}, Std Dev: {std_val:.4f}, Variance: {var_val:.4f}"
    result["latex_answer"] = f"\\bar{{x}} = {mean_val:.4f},\\ \\sigma = {std_val:.4f}"
    result["formulas_used"] = ["Mean: Σx/n", "Median: middle value", "Std Dev: √(Σ(x-x̄)²/(n-1))"]
    result["common_mistakes"] = ["Using population std dev instead of sample std dev (divide by n vs n-1)"]
    return result


_DICE_WORD_TO_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}


def _solve_dice_probability(problem: str, result: Dict) -> Optional[Dict]:
    """
    Classic "a fair die is thrown twice/N times, what is the probability the
    sum is K" word problem. Previously fell through to the generic
    "Please specify: nCr(n,r)..." placeholder regardless of what was asked --
    that placeholder isn't wrong-looking (no error field set), just silently
    not an actual answer to the question. Computed by brute-force enumeration
    over the finite sample space rather than a canned formula, so it's
    correct regardless of exactly how many dice/sides are involved.
    """
    p = problem.lower()
    if not re.search(r"\bdi(?:e|ce)\b", p) or not re.search(r"\b(thrown|rolled|tossed)\b", p):
        return None

    num_dice = None
    if re.search(r"\btwice\b", p):
        num_dice = 2
    else:
        m = re.search(r"\b(\d+|one|two|three|four|five|six)\s*(?:dice|di[ec]|times)\b", p)
        if m:
            token = m.group(1)
            num_dice = _DICE_WORD_TO_NUM.get(token, int(token) if token.isdigit() else None)
    if num_dice is None:
        num_dice = 1

    sides_match = re.search(r"(\d+)[\s-]*sided", p)
    sides = int(sides_match.group(1)) if sides_match else 6

    # "sum ... is/equals/of ... K" -- non-greedy up to the first digit run
    # after "sum" so it still matches regardless of phrasing length in
    # between (e.g. "sum of the two outcomes is 8").
    target_match = re.search(r"\bsum\b[^\d]*?(\d+)", p)
    if not target_match:
        return None
    target = int(target_match.group(1))

    from itertools import product
    from math import gcd
    outcomes = list(product(range(1, sides + 1), repeat=num_dice))
    favorable = [o for o in outcomes if sum(o) == target]
    total, fav_count = len(outcomes), len(favorable)
    g = gcd(fav_count, total) if fav_count else total
    simplified = f"{fav_count // g}/{total // g}" if fav_count else "0"
    decimal = fav_count / total

    steps = [
        {
            "step": 1,
            "description": f"Sample space: {num_dice} {'die' if num_dice == 1 else 'dice'} with {sides} faces each",
            "expression": f"Total outcomes = {sides}^{num_dice} = {total}",
            "latex": f"{sides}^{{{num_dice}}} = {total}",
        },
        {
            "step": 2,
            "description": f"List favorable outcomes: rolls summing to {target}",
            "expression": ", ".join(str(o) for o in favorable) if favorable else "none",
        },
        {
            "step": 3,
            "description": "Count favorable outcomes",
            "expression": f"{fav_count} out of {total}",
            "latex": f"\\frac{{{fav_count}}}{{{total}}}",
        },
        {
            "step": 4,
            "description": "Probability = favorable outcomes / total outcomes",
            "expression": f"P = {fav_count}/{total} = {simplified} ≈ {decimal:.4f}",
            "latex": f"P = \\frac{{{fav_count}}}{{{total}}} = {simplified} \\approx {decimal:.4f}",
        },
    ]
    result["steps"] = steps
    result["answer"] = f"{simplified} (≈ {decimal:.4f})"
    result["latex_answer"] = f"P = \\frac{{{fav_count}}}{{{total}}} = {simplified}"
    result["formulas_used"] = ["P(E) = favorable outcomes / total outcomes", "Sample space enumeration"]
    result["common_mistakes"] = [
        "Treating (a,b) and (b,a) as the same outcome when the dice are distinguishable",
        "Miscounting how many ordered pairs give the target sum",
    ]
    return result


def _solve_probability(problem: str, result: Dict) -> Dict:
    dice_result = _solve_dice_probability(problem, result)
    if dice_result is not None:
        return dice_result

    steps = []
    p = problem.lower()

    # nCr or nPr patterns — handles C(10,3), 10C3, nCr(10,3)
    ncr_match = re.search(r"(?:ncr|c)\s*[\(\s]\s*(\d+)\s*[,\s]\s*(\d+)\s*\)?|(\d+)\s*c\s*(\d+)", p)
    npr_match = re.search(r"(?:npr|p)\s*[\(\s]\s*(\d+)\s*[,\s]\s*(\d+)\s*\)?|(\d+)\s*p\s*(\d+)", p)

    if ncr_match:
        groups = [g for g in ncr_match.groups() if g is not None]
        n, r = int(groups[0]), int(groups[1])
        from math import comb
        val = comb(n, r)
        steps.append({"step": 1, "description": f"Combination: C({n}, {r}) = n! / (r!(n-r)!)", "expression": f"C({n},{r})"})
        steps.append({"step": 2, "description": f"= {n}! / ({r}! × {n-r}!)", "expression": ""})
        steps.append({"step": 3, "description": "Result", "expression": str(val)})
        result["answer"] = str(val)
        result["latex_answer"] = f"\\binom{{{n}}}{{{r}}} = {val}"
        result["formulas_used"] = ["C(n,r) = n! / (r!(n-r)!)"]
    elif npr_match:
        groups = [g for g in npr_match.groups() if g is not None]
        n, r = int(groups[0]), int(groups[1])
        from math import perm
        val = perm(n, r)
        steps.append({"step": 1, "description": f"Permutation: P({n}, {r}) = n! / (n-r)!", "expression": f"P({n},{r})"})
        steps.append({"step": 2, "description": f"= {n}! / {n-r}!", "expression": ""})
        steps.append({"step": 3, "description": "Result", "expression": str(val)})
        result["answer"] = str(val)
        result["latex_answer"] = f"P({n},{r}) = {val}"
        result["formulas_used"] = ["P(n,r) = n! / (n-r)!"]
    else:
        # Generic probability
        numbers = re.findall(r"\d+\.?\d*", p)
        result["answer"] = "Please specify: nCr(n,r) for combinations, nPr(n,r) for permutations, or provide favorable/total outcomes."
        steps.append({"step": 1, "description": "Probability = Favorable outcomes / Total outcomes", "expression": "P(E) = n(E)/n(S)"})

    result["steps"] = steps
    result["common_mistakes"] = ["Confusing permutations and combinations", "Not accounting for repetition"]
    return result


def _solve_geometry(problem: str, result: Dict) -> Dict:
    steps = []
    p = problem.lower()
    numbers = [float(x) for x in re.findall(r"\d+\.?\d*", problem)]

    if "circle" in p:
        r = numbers[0] if numbers else 1
        area = float(pi) * r ** 2
        circumference = 2 * float(pi) * r
        steps.append({"step": 1, "description": f"Circle with radius r = {r}", "expression": ""})
        steps.append({"step": 2, "description": "Area = πr²", "expression": f"π × {r}² = {area:.4f}"})
        steps.append({"step": 3, "description": "Circumference = 2πr", "expression": f"2 × π × {r} = {circumference:.4f}"})
        result["answer"] = f"Area = {area:.4f}, Circumference = {circumference:.4f}"
        result["latex_answer"] = f"A = \\pi r^2 = {area:.4f},\\ C = 2\\pi r = {circumference:.4f}"
        result["formulas_used"] = ["Area of circle = πr²", "Circumference = 2πr"]

    elif "triangle" in p:
        if len(numbers) >= 2:
            base, height = numbers[0], numbers[1]
            area = 0.5 * base * height
            steps.append({"step": 1, "description": f"Triangle with base={base}, height={height}", "expression": ""})
            steps.append({"step": 2, "description": "Area = (1/2) × base × height", "expression": f"0.5 × {base} × {height} = {area}"})
            result["answer"] = f"Area = {area}"
            result["latex_answer"] = f"A = \\frac{{1}}{{2}} \\times {base} \\times {height} = {area}"
            result["formulas_used"] = ["Area of triangle = ½ × base × height"]

    elif "rectangle" in p or "square" in p:
        if len(numbers) >= 2:
            l, w = numbers[0], numbers[1]
        elif len(numbers) == 1:
            l = w = numbers[0]
        else:
            l = w = 1
        area = l * w
        perimeter = 2 * (l + w)
        steps.append({"step": 1, "description": f"Rectangle: length={l}, width={w}", "expression": ""})
        steps.append({"step": 2, "description": "Area = length × width", "expression": f"{l} × {w} = {area}"})
        steps.append({"step": 3, "description": "Perimeter = 2(l + w)", "expression": f"2({l} + {w}) = {perimeter}"})
        result["answer"] = f"Area = {area}, Perimeter = {perimeter}"
        result["formulas_used"] = ["Area = l × w", "Perimeter = 2(l + w)"]
    else:
        result["answer"] = "Please specify shape (circle, triangle, rectangle, square) with dimensions."
        steps.append({"step": 1, "description": "Supported shapes: circle, triangle, rectangle, square", "expression": ""})

    result["steps"] = steps
    result["common_mistakes"] = ["Using diameter instead of radius for circles", "Wrong unit conversions"]
    return result


def _solve_trigonometry(problem: str, result: Dict) -> Dict:
    steps = []
    p = problem.lower().replace("^", "**")

    trig_funcs = {"sin": sin, "cos": cos, "tan": tan, "asin": asin, "acos": acos, "atan": atan}

    # Check for direct evaluation like sin(30) or sin(pi/6).
    # \b is required: without it, searching for "tan" against "atan(1)" matches
    # the "tan(1)" substring inside "atan(1)" before the "atan" entry is ever
    # checked, silently computing tan(1°) instead of atan(1). Since 'a' and 't'
    # are both word characters, \b correctly refuses to match "tan" there while
    # still matching a standalone "tan(...)".
    for fname, func in trig_funcs.items():
        match = re.search(rf"\b{fname}\s*\(?\s*([^)]+)\s*\)?", p)
        if match:
            arg_str = match.group(1).strip()
            try:
                x_val = safe_parse(arg_str)

                if fname in ("asin", "acos", "atan"):
                    # Inverse functions take a dimensionless ratio, not an
                    # angle — the input must never go through the
                    # degrees-to-radians conversion below (that conversion
                    # previously ran unconditionally here too, so e.g.
                    # atan(1) silently computed atan(1° in radians) instead
                    # of atan(1)). The result IS an angle, so show it in
                    # both radians and degrees.
                    if fname in ("asin", "acos"):
                        try:
                            in_domain = -1 <= float(N(x_val)) <= 1
                        except (TypeError, ValueError):
                            in_domain = True  # non-numeric (symbolic) input — let SymPy attempt it
                        if not in_domain:
                            result["error"] = (
                                f"{fname}({arg_str}) has no real answer — {fname} is only "
                                f"defined for inputs between -1 and 1 (you gave {arg_str})."
                            )
                            result["answer"] = None
                            return result
                    steps.append({"step": 1, "description": f"Evaluate {fname}({arg_str})", "expression": ""})
                    # nsimplify turns a decimal like 0.5 into Rational(1, 2) first,
                    # so SymPy can return a clean closed form (pi/3) instead of an
                    # un-simplified numeric expression when the input was a float.
                    try:
                        exact_x = nsimplify(x_val, rational=True)
                    except Exception:
                        exact_x = x_val
                    val = func(exact_x)
                    simplified = simplify(val)
                    numeric_rad = float(N(simplified, 6))
                    numeric_deg = numeric_rad * 180 / float(pi)
                    steps.append({"step": 2, "description": "Exact value (radians)", "expression": str(simplified), "latex": latex(simplified)})
                    steps.append({
                        "step": 3, "description": "Decimal approximation",
                        "expression": f"{numeric_rad:.6f} rad = {numeric_deg:.4f}°",
                        "latex": f"{numeric_rad:.6f}\\text{{ rad}} = {numeric_deg:.4f}^\\circ",
                    })
                    result["answer"] = f"Exact: {simplified} rad, Decimal: {numeric_rad:.6f} rad ({numeric_deg:.4f}°)"
                    result["latex_answer"] = f"{fname}\\left({latex(x_val)}\\right) = {latex(simplified)} \\approx {numeric_rad:.6f}\\text{{ rad}}"
                    result["steps"] = steps
                    result["formulas_used"] = [f"Inverse trigonometric identity for {fname}"]
                    result["common_mistakes"] = [
                        "The result is an angle, not a ratio",
                        "Forgetting the restricted range of inverse trig functions",
                    ]
                    return result

                # sin/cos/tan take an angle: assume degrees for a bare number
                # (e.g. sin(30)); treat anything else as already in radians
                # (e.g. sin(pi/6)).
                if re.match(r"^\d+\.?\d*$", arg_str):
                    x_rad = x_val * pi / 180
                    steps.append({
                        "step": 1, "description": f"Convert {arg_str}° to radians",
                        "expression": f"{arg_str}° = {x_rad}", "latex": f"{arg_str}^\\circ = {latex(x_rad)}",
                    })
                else:
                    x_rad = x_val
                    steps.append({"step": 1, "description": f"Evaluate {fname}({arg_str})", "expression": ""})
                val = func(x_rad)
                simplified = simplify(val)
                numeric = float(N(simplified, 6))
                steps.append({"step": 2, "description": "Exact value", "expression": str(simplified), "latex": latex(simplified)})
                steps.append({"step": 3, "description": "Decimal approximation", "expression": str(numeric), "latex": str(numeric)})
                result["answer"] = f"Exact: {simplified}, Decimal: {numeric:.6f}"
                result["latex_answer"] = f"{fname}\\left({latex(x_rad)}\\right) = {latex(simplified)} \\approx {numeric:.6f}"
                result["steps"] = steps
                result["formulas_used"] = ["Unit circle values", f"Trigonometric identity for {fname}"]
                result["common_mistakes"] = ["Using degrees when radians are expected", "Mixing sin/cos identities"]
                return result
            except Exception:
                pass

    # Pythagorean theorem
    if "pythagorean" in p or ("hypotenuse" in p or ("a²" in p or "a^2" in p)):
        nums = [float(x) for x in re.findall(r"\d+\.?\d*", problem)]
        if len(nums) >= 2:
            a, b = nums[0], nums[1]
            c = float(np.sqrt(a**2 + b**2))
            steps.append({"step": 1, "description": "Pythagorean Theorem: c² = a² + b²", "expression": f"c² = {a}² + {b}²"})
            steps.append({"step": 2, "description": "Calculate", "expression": f"c² = {a**2} + {b**2} = {a**2 + b**2}"})
            steps.append({"step": 3, "description": "Take square root", "expression": f"c = √{a**2 + b**2} = {c:.4f}"})
            result["answer"] = f"Hypotenuse = {c:.4f}"
            result["latex_answer"] = f"c = \\sqrt{{{a}^2 + {b}^2}} = {c:.4f}"
            result["steps"] = steps
            result["formulas_used"] = ["Pythagorean Theorem: a² + b² = c²"]
            return result

    # Symbolic simplification fallback, e.g. "sin(x)^2 + cos(x)^2". The
    # per-function loop above only ever evaluates a single sin/cos/tan(...)
    # call in isolation, so a compound symbolic expression like this one
    # never matches it and fell straight through to the generic message
    # below even though SymPy can simplify it directly (to 1, here).
    try:
        candidate = p
        for prefix in ("simplify:", "simplify "):
            if candidate.startswith(prefix):
                candidate = candidate[len(prefix):].strip()
        if not looks_like_prose(candidate):
            expr = safe_parse(candidate)
            if expr.free_symbols:  # symbolic only — numeric cases were already tried above
                simplified = trigsimp(simplify(expr))
                if simplified != expr:
                    steps.append({"step": 1, "description": "Original expression", "expression": str(expr), "latex": latex(expr)})
                    steps.append({"step": 2, "description": "Apply trigonometric identities and simplify", "expression": str(simplified), "latex": latex(simplified)})
                    result["answer"] = str(simplified)
                    result["latex_answer"] = f"{latex(expr)} = {latex(simplified)}"
                    result["steps"] = steps
                    result["formulas_used"] = ["sin²θ + cos²θ = 1", "Trigonometric identities"]
                    result["common_mistakes"] = ["Mixing up sin/cos identities", "Forgetting the Pythagorean identity"]
                    return result
    except Exception:
        pass

    result["answer"] = "Please specify: sin/cos/tan(angle) or use 'pythagorean theorem with a=?, b=?'"
    result["steps"] = steps
    result["formulas_used"] = ["sin²θ + cos²θ = 1", "tan θ = sin θ / cos θ"]
    return result


def _generate_similar_algebra(var: Any) -> List[str]:
    return [
        f"Solve: 2{var} + 5 = 13",
        f"Solve: 3{var} - 7 = 8",
        f"Solve: {var}/4 + 3 = 7",
    ]


def generate_function_points(expr_str: str, x_min: float = -10, x_max: float = 10, points: int = 200) -> Dict:
    """Generate x,y data points for plotting a function."""
    x = symbols("x")
    try:
        expr = safe_parse(expr_str)
        x_vals = np.linspace(x_min, x_max, points)
        f = sp.lambdify(x, expr, modules=["numpy"])
        y_vals = f(x_vals)
        # Filter out infinities and NaN
        mask = np.isfinite(y_vals)
        return {
            "x": x_vals[mask].tolist(),
            "y": y_vals[mask].tolist(),
            "expr": str(expr),
            "latex": latex(expr),
        }
    except Exception as e:
        return {"error": str(e)}
