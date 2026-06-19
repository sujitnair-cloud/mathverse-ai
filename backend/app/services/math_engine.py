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
    ("²", "**2"), ("³", "**3"), ("⁴", "**4"), ("⁵", "**5"),
    ("⁶", "**6"), ("⁷", "**7"), ("⁸", "**8"), ("⁹", "**9"),
    # Subscripts (often used in labels)
    ("₀", "0"), ("₁", "1"), ("₂", "2"), ("₃", "3"),
    # Operators
    ("×", "*"), ("·", "*"), ("÷", "/"), ("−", "-"), ("–", "-"), ("—", "-"),
    # Constants
    ("π", "pi"), ("∞", "oo"), ("∫", ""),
    # Roots
    ("√", "sqrt"),
    # Greek letters commonly used in math
    ("α", "alpha"), ("β", "beta"), ("γ", "gamma"), ("δ", "delta"),
    ("θ", "theta"), ("λ", "lambda"), ("μ", "mu"), ("σ", "sigma"),
    ("φ", "phi"), ("ω", "omega"),
    # Misc
    ("≤", "<="), ("≥", ">="), ("≠", "!="),
]


def normalize_math_input(s: str) -> str:
    """Convert Unicode math symbols to ASCII equivalents SymPy can parse."""
    for uni, asc in UNICODE_MAP:
        s = s.replace(uni, asc)
    s = s.replace("^", "**")
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
    # Apply Unicode normalization
    p = normalize_math_input(p)
    # Remove natural-language prefixes: "what is", "find", "calculate", etc.
    p = re.sub(
        r"^(what\s+is|find\s+the|find|calculate|compute|evaluate|determine|give\s+me|tell\s+me|solve\s+for|solve)\s+",
        "", p, flags=re.IGNORECASE,
    ).strip()
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
    Catches word problems, proofs, applied/aptitude problems, and exam-style questions.
    """
    return bool(_WORD_PROBLEM_RE.search(problem))


def safe_parse(expr_str: str) -> Any:
    """Parse a math expression string safely, handling Unicode math symbols."""
    expr_str = normalize_math_input(expr_str.strip())
    return parse_expr(expr_str, transformations=TRANSFORMATIONS)


def detect_topic(problem: str) -> str:
    """Heuristically detect the math topic from a problem string."""
    p = problem.lower()
    if any(k in p for k in ["integral", "integrate", "∫", "antiderivative"]):
        return "calculus_integration"
    if any(k in p for k in ["derivative", "differentiate", "d/dx", "gradient"]):
        return "calculus_differentiation"
    if any(k in p for k in ["limit", "lim", "approaches"]):
        return "calculus_limits"
    if any(k in p for k in ["matrix", "determinant", "eigenvalue", "inverse matrix"]):
        return "linear_algebra"
    # Geometry must come before trigonometry because "triangle" contains "angle"
    if any(k in p for k in ["area", "perimeter", "volume", "geometry", "triangle", "circle", "rectangle", "square", "pythagorean", "hypotenuse"]):
        return "geometry"
    if any(k in p for k in ["sin", "cos", "tan", "angle", "degrees", "radians", "trigonometric"]):
        return "trigonometry"
    if any(k in p for k in ["quadratic", "x²", "x^2", "x**2", "**2", "parabola"]):
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

    # Check if it's an equation (contains =)
    if "=" in p:
        parts = p.split("=")
        if len(parts) == 2:
            # Pre-define common variables so implicit multiplication works correctly
            local_ns = {str(s): s for s in symbols("x y z a b c n t")}
            lhs = parse_expr(parts[0].strip(), local_dict=local_ns, transformations=TRANSFORMATIONS)
            rhs = parse_expr(parts[1].strip(), local_dict=local_ns, transformations=TRANSFORMATIONS)
            steps.append({"step": 1, "description": "Identify the equation", "expression": f"{lhs} = {rhs}"})
            steps.append({"step": 2, "description": "Move all terms to one side", "expression": f"{lhs} - ({rhs}) = 0"})
            eq = Eq(lhs, rhs)
            free = eq.free_symbols
            var = sorted(free, key=lambda s: str(s))[0] if free else symbols("x")
            solution = solve(eq, var)
            steps.append({"step": 3, "description": f"Solve for {var}", "expression": f"{var} = {solution}"})
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
    steps.append({"step": 1, "description": "Parse the expression", "expression": str(expr)})
    simplified = simplify(expr)
    steps.append({"step": 2, "description": "Simplify", "expression": str(simplified)})
    try:
        numeric = float(N(simplified))
        steps.append({"step": 3, "description": "Numeric value", "expression": str(numeric)})
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
    p = p.strip("()").strip()

    x = symbols("x")
    expr = safe_parse(p)
    steps.append({"step": 1, "description": "Identify the function to differentiate", "expression": str(expr)})
    steps.append({"step": 2, "description": "Apply differentiation rules (Power, Chain, Product, Quotient)", "expression": ""})
    derivative = diff(expr, x)
    steps.append({"step": 3, "description": "Compute derivative", "expression": str(derivative)})
    simplified_deriv = simplify(derivative)
    steps.append({"step": 4, "description": "Simplify result", "expression": str(simplified_deriv)})

    result["steps"] = steps
    result["answer"] = str(simplified_deriv)
    result["latex_answer"] = f"\\frac{{d}}{{dx}}\\left({latex(expr)}\\right) = {latex(simplified_deriv)}"
    result["formulas_used"] = ["Power Rule: d/dx(xⁿ) = nxⁿ⁻¹", "Chain Rule", "Product Rule", "Quotient Rule"]
    result["common_mistakes"] = [
        "Forgetting the chain rule for composite functions",
        "Treating constants as variables"
    ]
    result["alternate_method"] = f"Using limits: lim(h→0) [f(x+h) - f(x)] / h"
    return result


def _solve_integration(problem: str, result: Dict) -> Dict:
    steps = []
    p = problem.lower().replace("^", "**")
    for keyword in ["integrate", "integral of", "∫", "antiderivative of"]:
        p = p.replace(keyword, "").strip()
    # Remove dx at end
    p = re.sub(r"\s*d[a-z]\s*$", "", p).strip()
    p = p.strip("()").strip()

    x = symbols("x")
    expr = safe_parse(p)
    steps.append({"step": 1, "description": "Identify the integrand", "expression": str(expr)})
    steps.append({"step": 2, "description": "Apply integration rules", "expression": ""})
    integral = integrate(expr, x)
    steps.append({"step": 3, "description": "Compute indefinite integral", "expression": str(integral)})
    steps.append({"step": 4, "description": "Add constant of integration C", "expression": f"{integral} + C"})

    result["steps"] = steps
    result["answer"] = f"{integral} + C"
    result["latex_answer"] = f"\\int {latex(expr)}\\, dx = {latex(integral)} + C"
    result["formulas_used"] = ["Power Rule: ∫xⁿ dx = xⁿ⁺¹/(n+1) + C", "Substitution method"]
    result["common_mistakes"] = [
        "Forgetting the constant of integration C",
        "Incorrect substitution in u-substitution"
    ]
    return result


def _solve_limit(problem: str, result: Dict) -> Dict:
    steps = []
    p = problem.lower().replace("^", "**")
    # Try to extract: limit of <expr> as x -> <val>
    match = re.search(r"(?:limit|lim)\s+(?:of\s+)?(.+?)\s+as\s+x\s*(?:->|→|approaches)\s*([^\s]+)", p)
    if match:
        expr_str = match.group(1).strip()
        val_str = match.group(2).strip()
    else:
        # Try simple: lim x->0 of expr
        match2 = re.search(r"(?:limit|lim)\s*x\s*[-–>→]+\s*([^\s]+)\s+(?:of\s+)?(.+)", p)
        if match2:
            val_str = match2.group(1).strip()
            expr_str = match2.group(2).strip()
        else:
            expr_str = re.sub(r"(?:limit|lim)[\s\w\->→]*", "", p).strip()
            val_str = "0"

    x = symbols("x")
    expr = safe_parse(expr_str)
    try:
        val = safe_parse(val_str)
    except Exception:
        val = 0

    steps.append({"step": 1, "description": "Identify the expression and limit point", "expression": f"lim(x→{val}) {expr}"})
    steps.append({"step": 2, "description": "Check for direct substitution", "expression": ""})
    lim_val = limit(expr, x, val)
    steps.append({"step": 3, "description": "Evaluate limit", "expression": str(lim_val)})

    result["steps"] = steps
    result["answer"] = str(lim_val)
    result["latex_answer"] = f"\\lim_{{x \\to {latex(val)}}} {latex(expr)} = {latex(lim_val)}"
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
            steps.append({"step": 2, "description": "Matrix formed", "expression": str(mat)})
            d = det(mat)
            steps.append({"step": 3, "description": "Determinant", "expression": str(d)})
            if d != 0:
                inv_mat = mat.inv()
                steps.append({"step": 4, "description": "Inverse matrix", "expression": str(inv_mat)})
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


def _solve_probability(problem: str, result: Dict) -> Dict:
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

    # Check for direct evaluation like sin(30) or sin(pi/6)
    for fname, func in trig_funcs.items():
        match = re.search(rf"{fname}\s*\(?\s*([^)]+)\s*\)?", p)
        if match:
            arg_str = match.group(1).strip()
            try:
                x_val = safe_parse(arg_str)
                # Convert degrees to radians if plain number assumed as degrees
                if re.match(r"^\d+\.?\d*$", arg_str):
                    x_rad = x_val * pi / 180
                    steps.append({"step": 1, "description": f"Convert {arg_str}° to radians", "expression": f"{arg_str}° = {latex(x_rad)}"})
                    val = func(x_rad)
                else:
                    x_rad = x_val
                    steps.append({"step": 1, "description": f"Evaluate {fname}({arg_str})", "expression": ""})
                    val = func(x_rad)
                simplified = simplify(val)
                numeric = float(N(simplified, 6))
                steps.append({"step": 2, "description": f"Exact value", "expression": str(simplified)})
                steps.append({"step": 3, "description": "Decimal approximation", "expression": str(numeric)})
                result["answer"] = f"Exact: {simplified}, Decimal: {numeric:.6f}"
                result["latex_answer"] = f"{fname}\\left({latex(x_rad)}\\right) = {latex(simplified)} \\approx {numeric:.6f}"
                result["steps"] = steps
                result["formulas_used"] = [f"Unit circle values", f"Trigonometric identity for {fname}"]
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
