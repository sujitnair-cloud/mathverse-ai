"""
Parametrized, SymPy-verified quiz question generator.

Every answer here is computed by SymPy at generation time, not hand-written —
so "solve and validate the answer before showing it" is true by construction,
not by a post-hoc check. This is the fallback path used whenever no LLM is
configured, and it can also validate/backstop LLM-generated numeric questions
in the same topic.

Two independent axes control what gets generated, per the product requirement
that a single "advanced" label conflates two different things:
  - level:  how advanced the topic/formulas involved are (school vs a level
            that assumes more background)
  - demand: how much reasoning a routine application requires, independent
            of level (a routine one-step question vs. a multi-step chain vs.
            an unfamiliar/non-formulaic twist on the same material)
"""
import random
from typing import Callable, Dict, List

import sympy as sp
from sympy import symbols, diff, integrate, sin, cos, tan, latex, Rational, simplify
from math import comb, perm

x = symbols("x")
_LETTERS = ["A", "B", "C", "D"]

Level = str    # "basic" | "intermediate" | "advanced" | "expert"
Demand = str   # "routine" | "multi_step" | "unfamiliar"


def _fmt(v) -> str:
    """Render a SymPy/number/string value the way a student would write it."""
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        if isinstance(v, float) and v == int(v):
            v = int(v)
        return str(v)
    free = getattr(v, "free_symbols", None)
    if not free:
        return sp.sstr(sp.nsimplify(v))
    return sp.sstr(v)


def _build(question: str, correct, distractors: List, explanation: str) -> Dict:
    """
    Assemble a well-formed MCQ from a correct value and candidate distractors:
    dedupes against the correct answer and against each other (a common LLM
    failure mode — two options that evaluate to the same value), pads if
    dedup left too few, shuffles the position of the correct answer, and
    returns the same {question, options, answer, explanation} shape the LLM
    path produces — plus `option_tags`, a server-only (never sent to the
    client) {letter: misconception} map so that picking a specific wrong
    option identifies *which* likely mistake it represents, not just that
    the answer was wrong. Each distractor may be a bare value (tagged
    "computation_error" by default) or a (value, tag) pair for a specific,
    named misconception.
    """
    correct_str = _fmt(correct)
    seen = {correct_str}
    unique = []  # list of (value_str, tag)
    for d in distractors:
        value, tag = d if isinstance(d, tuple) and len(d) == 2 else (d, "computation_error")
        s = _fmt(value)
        if s not in seen:
            seen.add(s)
            unique.append((s, tag))
    # Extremely rare (tiny answer domains): pad with an offset numeric decoy.
    pad = 1
    while len(unique) < 3:
        try:
            candidate = _fmt(sp.sympify(correct_str) + pad)
        except Exception:
            candidate = f"{correct_str} (alt {pad})"
        if candidate not in seen:
            seen.add(candidate)
            unique.append((candidate, "computation_error"))
        pad += 1
    entries = [(correct_str, None)] + unique[:3]
    random.shuffle(entries)
    options = [f"{_LETTERS[i]}) {v}" for i, (v, _tag) in enumerate(entries)]
    answer = _LETTERS[[v for v, _t in entries].index(correct_str)]
    option_tags = {_LETTERS[i]: tag for i, (_v, tag) in enumerate(entries) if tag}
    return {"question": question, "options": options, "answer": answer,
            "explanation": explanation, "option_tags": option_tags}


def _int_range(level: Level, demand: Demand) -> tuple:
    base = {"basic": (1, 9), "intermediate": (2, 15), "advanced": (3, 25), "expert": (5, 40)}
    lo, hi = base.get(level, (2, 15))
    if demand == "multi_step":
        hi = int(hi * 1.5)
    elif demand == "unfamiliar":
        lo = -hi  # allow negatives — breaks the "always positive" pattern-matching shortcut
    return lo, hi


# ── Generators ───────────────────────────────────────────────────────────────

def _term(coef: int, var: str = "x") -> str:
    """Render coef*var the way a student would write it: 'x' not '1x', '-x' not '-1x'."""
    if coef == 1:
        return var
    if coef == -1:
        return f"-{var}"
    return f"{coef}{var}"


def _plus(value: int, var: str = "") -> str:
    """' + N<var>' or ' - N<var>' with a correct sign, for building an
    equation string piece by piece without ever producing '+ -13'."""
    term = _term(abs(value), var) if var else str(abs(value))
    return f" + {term}" if value >= 0 else f" - {term}"


def _gen_arithmetic(level: Level, demand: Demand) -> Dict:
    hi = {"basic": 20, "intermediate": 100, "advanced": 500, "expert": 1000}.get(level, 100)
    if demand == "routine":
        op = random.choice(["+", "-", "*"])
        a, b = random.randint(1, hi), random.randint(1, hi)
        if op == "-" and a < b:
            a, b = b, a  # keep it in positives for a routine question
        correct = {"+": a + b, "-": a - b, "*": a * b}[op]
        q = f"{a} {op} {b} = ?"
        explanation = f"{a} {op} {b} = {correct}."
        distractors = [
            (correct + 1, "arithmetic_slip"),
            (correct - b if op == "+" else correct + b, "wrong_operation"),
            (a * b if op != "*" else a + b, "wrong_operation"),
        ]
    elif demand == "multi_step":
        a, b, c = random.randint(2, hi // 5 or 2), random.randint(2, hi // 5 or 2), random.randint(2, hi // 5 or 2)
        q = f"{a} + {b} * {c} = ?"
        correct = a + b * c
        explanation = f"Multiply first (order of operations): {b}*{c} = {b * c}, then {a} + {b * c} = {correct}."
        distractors = [
            ((a + b) * c, "ignored_order_of_operations"),
            (correct + 1, "arithmetic_slip"),
            (a * b + c, "wrong_operation"),
        ]
    else:  # unfamiliar: fractions, so a memorized whole-number routine doesn't transfer directly
        num1, den1 = random.randint(1, 5), random.randint(2, 6)
        num2, den2 = random.randint(1, 5), random.randint(2, 6)
        f1, f2 = Rational(num1, den1), Rational(num2, den2)
        correct = f1 + f2
        q = f"{num1}/{den1} + {num2}/{den2} = ?"
        lcd = sp.ilcm(den1, den2)
        explanation = f"Lowest common denominator {lcd}: {num1}/{den1} + {num2}/{den2} = {sp.sstr(correct)}."
        distractors = [
            (Rational(num1 + num2, den1 + den2), "added_numerators_and_denominators"),
            (Rational(num1 * num2, den1 * den2), "multiplied_instead_of_added"),
            (correct + 1, "arithmetic_slip"),
        ]
    return _build(q, correct, distractors, explanation)


def _gen_algebra_linear(level: Level, demand: Demand) -> Dict:
    lo, hi = _int_range(level, demand)
    a = random.randint(max(2, lo), hi)
    root = random.randint(lo, hi)
    if demand == "routine":
        b = random.randint(lo, hi)
        c = a * root + b
        q = f"Solve for x: {a}x{_plus(b)} = {c}"
        explanation = f"{a}x = {c}{_plus(-b)} = {a * root}, so x = {root}."
    elif demand == "multi_step":
        b = random.randint(lo, hi)
        d = random.randint(1, hi)  # avoid a 0x term, which would just look like a typo
        c = a * root + b + d * root  # a x + b + d x = c  =>  (a+d) x = c - b
        q = f"Solve for x: {a}x{_plus(b)}{_plus(d, 'x')} = {c}"
        explanation = f"Combine like terms: {a + d}x{_plus(b)} = {c}, so {a + d}x = {c - b}, x = {root}."
    else:  # unfamiliar: variable on both sides, must not pattern-match a fixed template
        b = random.randint(lo, hi)
        d = random.randint(lo, hi) or 1  # avoid a 0x term, which would just look like a typo
        if a == d:
            a += 1  # avoid a degenerate 0x = const equation
        rhs_const = (a - d) * root + b
        q = f"Solve for x: {a}x{_plus(b)} = {_term(d, 'x')}{_plus(rhs_const)}"
        explanation = (
            f"Move the x terms to one side and the constants to the other: "
            f"{_term(a - d, 'x')} = {rhs_const - b}, so x = {root}."
        )
    correct = root
    distractors = [
        (root + 1, "arithmetic_slip"),
        (-root, "sign_error"),  # forgot to flip the sign when moving a term across "="
        (root * 2 if root != 0 else root + 5, "forgot_to_divide"),  # left the coefficient un-divided
    ]
    return _build(q, correct, distractors, explanation)


def _gen_algebra_quadratic(level: Level, demand: Demand) -> Dict:
    r1 = random.randint(-9, 9) or 1
    r2 = random.randint(-9, 9) or -1
    while r2 == r1:
        r2 = random.randint(-9, 9) or -1
    b = -(r1 + r2)
    c = r1 * r2
    b_str = _plus(b, "x") if b != 0 else ""
    c_str = _plus(c) if c != 0 else ""
    q = f"Solve for x: x^2{b_str}{c_str} = 0"
    roots = sorted([r1, r2])
    correct = f"x = {roots[0]} or x = {roots[1]}"
    distractors = [
        (f"x = {roots[0]} or x = {-roots[1]}", "sign_error"),  # flipped the sign of one root
        (f"x = {-roots[0]} or x = {roots[1]}", "sign_error"),  # flipped the sign of the other root
        (f"x = {roots[0] + 1} or x = {roots[1]}", "arithmetic_slip"),
    ]
    factor = lambda r: f"x - {r}" if r >= 0 else f"x + {-r}"
    explanation = f"Factors as ({factor(r1)})({factor(r2)}) = 0, so x = {r1} or x = {r2}."
    return _build(q, correct, distractors, explanation)


def _gen_calculus_derivative(level: Level, demand: Demand) -> Dict:
    if demand == "routine" and level in ("basic", "intermediate"):
        n = random.randint(2, 9)
        expr = x ** n
        q = f"d/dx(x^{n}) = ?"
    elif demand == "multi_step" or level == "advanced":
        a, n, b = random.randint(2, 9), random.randint(2, 6), random.randint(1, 12)
        expr = a * x ** n + b * x
        q = f"d/dx({a}x^{n} + {b}x) = ?"
    else:  # unfamiliar / expert — a trig or product case the routine formula doesn't cover
        choice = random.choice(["sin", "cos", "tan", "x_sin", "x_cos", "sin_shift"])
        if choice == "sin":
            expr = sin(x)
            q = "d/dx(sin(x)) = ?"
        elif choice == "cos":
            expr = cos(x)
            q = "d/dx(cos(x)) = ?"
        elif choice == "tan":
            expr = tan(x)
            q = "d/dx(tan(x)) = ?"
        elif choice == "x_sin":
            expr = x * sin(x)
            q = "d/dx(x * sin(x)) = ?"
        elif choice == "x_cos":
            expr = x * cos(x)
            q = "d/dx(x * cos(x)) = ?"
        else:
            k = random.randint(2, 5)
            expr = sin(k * x)
            q = f"d/dx(sin({k}x)) = ?"
    correct = diff(expr, x)
    # Plausible mistakes: forgetting the chain/product rule, off-by-one power, sign slip
    wrong_power = diff(expr, x) + 1 if not expr.has(sin, cos, tan) else -correct
    distractors = [
        (expr, "forgot_to_differentiate"),  # copied the original function as-is
        (wrong_power, "off_by_one_or_missing_chain_rule"),
        (-correct, "sign_error"),
    ]
    explanation = f"d/dx({sp.sstr(expr)}) = {sp.sstr(correct)}, by standard differentiation rules."
    return _build(q, correct, distractors, explanation)


def _gen_calculus_integral(level: Level, demand: Demand) -> Dict:
    n = random.randint(1, 6) if level in ("basic", "intermediate") else random.randint(2, 8)
    a = random.randint(1, 6)
    expr = a * x ** n
    q = f"Integrate {a}x^{n} dx = ?"
    correct_expr = integrate(expr, x)
    correct = f"{sp.sstr(correct_expr)} + C"
    wrong_no_div = f"{sp.sstr(a * x ** (n + 1))} + C"  # forgot to divide by (n+1)
    distractors = [
        (wrong_no_div, "forgot_to_divide_by_new_exponent"),
        (f"{sp.sstr(a * (n) * x ** (n - 1))} + C", "differentiated_instead_of_integrated"),
        (f"{sp.sstr(correct_expr)}", "forgot_constant_of_integration"),
    ]
    explanation = f"Power rule: integral of x^n dx = x^(n+1)/(n+1) + C, so this is {correct}."
    return _build(q, correct, distractors, explanation)


_SPECIAL_ANGLES_DEG = [0, 30, 45, 60, 90, 120, 135, 150, 180]


def _gen_trigonometry(level: Level, demand: Demand) -> Dict:
    func_name, func = random.choice([("sin", sin), ("cos", cos), ("tan", tan)])
    deg = random.choice(_SPECIAL_ANGLES_DEG if demand != "unfamiliar" else _SPECIAL_ANGLES_DEG[1:])
    if func_name == "tan" and deg == 90:
        deg = 60  # tan(90) is undefined — avoid a degenerate question
    val = simplify(func(sp.rad(deg)))
    q = f"{func_name}({deg}°) = ?"
    correct = val
    distractors = [
        (simplify(func(sp.rad(90 - deg))) if 90 - deg != deg else simplify(-val), "confused_with_complementary_angle"),
        (simplify(-val), "sign_error"),
        (simplify(val + Rational(1, 2)) if val.is_rational else simplify(val * 2), "arithmetic_slip"),
    ]
    explanation = f"{func_name}({deg}°) = {sp.sstr(val)}, a standard angle value."
    return _build(q, correct, distractors, explanation)


def _gen_probability_combinations(level: Level, demand: Demand) -> Dict:
    n = random.randint(5, 12) if level in ("basic", "intermediate") else random.randint(8, 20)
    r = random.randint(2, min(n - 1, 6))
    use_perm = demand == "unfamiliar" or random.random() < 0.35
    if use_perm:
        correct = perm(n, r)
        q = f"How many ways can you arrange {r} items chosen from {n} distinct items (order matters)? P({n},{r}) = ?"
        explanation = f"P(n,r) = n!/(n-r)! = {n}!/{n - r}! = {correct}."
        confusable = comb(n, r)
    else:
        correct = comb(n, r)
        q = f"How many ways can you choose {r} items from {n} distinct items (order doesn't matter)? C({n},{r}) = ?"
        explanation = f"C(n,r) = n!/(r!(n-r)!) = {correct}."
        confusable = perm(n, r)
    distractors = [confusable, correct + r, max(correct - n, 1)]
    return _build(q, correct, distractors, explanation)


def _gen_statistics_mean(level: Level, demand: Demand) -> Dict:
    size = random.randint(5, 6) if level in ("basic", "intermediate") else random.randint(6, 9)
    data = [random.randint(1, 50) for _ in range(size)]
    mean = Rational(sum(data), len(data))
    q = f"Find the mean of: {data}"
    correct = mean if mean.q != 1 else int(mean)
    sorted_data = sorted(data)
    mid = len(sorted_data) // 2
    median = sorted_data[mid] if len(sorted_data) % 2 else Rational(sorted_data[mid - 1] + sorted_data[mid], 2)
    distractors = [median, max(data), Rational(sum(data), len(data) - 1)]
    explanation = f"Mean = sum/count = {sum(data)}/{len(data)} = {_fmt(correct)}."
    return _build(q, correct, distractors, explanation)


def _gen_geometry_area(level: Level, demand: Demand) -> Dict:
    shape = random.choice(["circle", "rectangle", "triangle"])
    if shape == "circle":
        r = random.randint(2, 12)
        q = f"Find the exact area of a circle with radius {r} (in terms of π)."
        correct = f"{r * r}π"
        distractors = [f"{2 * r}π", f"{r * r}", f"{(r + 1) * (r + 1)}π"]
        explanation = f"Area = πr² = π×{r}² = {r * r}π."
    elif shape == "rectangle":
        l, w = random.randint(3, 20), random.randint(2, 15)
        q = f"Find the area of a rectangle with length {l} and width {w}."
        correct = l * w
        distractors = [2 * (l + w), l + w, (l - 1) * w]
        explanation = f"Area = length × width = {l} × {w} = {l * w}."
    else:
        b, h = random.randint(4, 20), random.randint(3, 16)
        q = f"Find the area of a triangle with base {b} and height {h}."
        correct = Rational(b * h, 2)
        distractors = [b * h, b + h, Rational(b * h, 2) + 1]
        explanation = f"Area = (1/2) × base × height = (1/2) × {b} × {h} = {_fmt(correct)}."
    return _build(q, correct, distractors, explanation)


def _gen_linear_algebra_det(level: Level, demand: Demand) -> Dict:
    vals = [random.randint(-9, 9) for _ in range(4)]
    a, b, c, d = vals
    mat = sp.Matrix([[a, b], [c, d]])
    q = f"det([[{a},{b}],[{c},{d}]]) = ?"
    correct = mat.det()
    distractors = [(a * d + b * c, "sign_error"), (a * c - b * d, "wrong_diagonal_pairing"), (correct + 1, "arithmetic_slip")]
    explanation = f"det = ad - bc = ({a})({d}) - ({b})({c}) = {correct}."
    return _build(q, correct, distractors, explanation)


_GENERATORS: Dict[str, Callable[[Level, Demand], Dict]] = {
    "arithmetic": _gen_arithmetic,
    "algebra": _gen_algebra_linear,
    "algebra_linear": _gen_algebra_linear,
    "algebra_quadratic": _gen_algebra_quadratic,
    "calculus": _gen_calculus_derivative,
    "calculus_differentiation": _gen_calculus_derivative,
    "calculus_integration": _gen_calculus_integral,
    "trigonometry": _gen_trigonometry,
    "probability": _gen_probability_combinations,
    "statistics": _gen_statistics_mean,
    "geometry": _gen_geometry_area,
    "linear-algebra": _gen_linear_algebra_det,
    "linear_algebra": _gen_linear_algebra_det,
}


def generate_verified_questions(topic: str, level: Level, demand: Demand, count: int) -> List[Dict]:
    """
    Generate `count` questions for `topic`, each with an answer computed by
    SymPy (not hand-written), varying with every call so repeated requests
    don't repeat the same fixed set. Falls back to the algebra generator for
    an unrecognized topic, matching the previous template bank's behavior.
    """
    t = topic.lower().strip()
    coarse = t.replace(" ", "-").split("_")[0]
    generator = _GENERATORS.get(t) or _GENERATORS.get(coarse) or _gen_algebra_linear
    questions = []
    seen_questions = set()
    attempts = 0
    max_attempts = max(count * 6, 40)
    while len(questions) < count and attempts < max_attempts:
        attempts += 1
        q = generator(level, demand)
        if q["question"] in seen_questions:
            continue  # regenerate rather than show the exact same question twice in one quiz
        seen_questions.add(q["question"])
        questions.append(q)
    # A narrow parameter space (e.g. only a handful of distinct routine
    # derivatives) can exhaust unique variety before reaching `count`. The
    # API promises exactly `count` questions, so top up with repeats rather
    # than silently returning fewer than requested — duplicates are a much
    # smaller problem than a quiz that's quietly short.
    while len(questions) < count:
        questions.append(generator(level, demand))
    return questions
