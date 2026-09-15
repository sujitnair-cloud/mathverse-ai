"""
Regression cases for solver/grapher correctness bugs found during a Phase 4
reliability review. Each case reproduces a failure that previously returned a
wrong or fabricated answer instead of erroring clearly, per the project's
"every complaint becomes a reproducible test case" policy.
"""
import math
import unittest

from app.services.math_engine import (
    solve_expression, generate_function_points, is_llm_first_problem, looks_like_prose,
    safe_parse, UnsafeExpressionError, detect_topic,
)
from app.services.graph_service import build_3d_surface, build_function_graph


class SecurityTests(unittest.TestCase):
    """
    SymPy's sympify()/parse_expr() compile input to a Python expression and
    eval() it — verified directly (before this fix existed) that this let
    arbitrary code run through /api/v1/solve, /api/v1/graph, and
    /api/v1/graph/3d, all reachable without authentication:
      __import__("os").system(...)              -> ran an arbitrary shell command
      ().__class__.__base__.__subclasses__()     -> walked the whole object graph
    These are the two known escape shapes; both require "__". If this test
    ever starts failing because the payload didn't raise, treat it as a
    live remote-code-execution regression, not a flaky test.
    """
    PAYLOADS = [
        '__import__("os").system("echo pwned")',
        '().__class__.__base__.__subclasses__()',
        'open("whatever").read()',
        '[x for x in ().__class__.__base__.__subclasses__()]',
    ]

    def test_safe_parse_rejects_known_rce_payloads(self):
        for payload in self.PAYLOADS:
            with self.subTest(payload=payload):
                with self.assertRaises(UnsafeExpressionError):
                    safe_parse(payload)

    def test_solve_rejects_payloads_without_raising(self):
        # The public endpoint must never propagate a raw exception either —
        # solve_expression() catches internally and reports a clean error.
        for payload in self.PAYLOADS:
            with self.subTest(payload=payload):
                r = solve_expression(payload)
                self.assertIsNone(r["answer"])
                self.assertIsNotNone(r["error"])

    def test_3d_graph_rejects_payloads(self):
        for payload in self.PAYLOADS:
            with self.subTest(payload=payload):
                r = build_3d_surface(payload)
                self.assertIn("error", r)

    def test_2d_graph_rejects_payloads(self):
        for payload in self.PAYLOADS:
            with self.subTest(payload=payload):
                r = build_function_graph([payload])
                self.assertEqual(r["data"], [])
                self.assertEqual(len(r["errors"]), 1)

    def test_legitimate_expressions_still_parse(self):
        for expr in ["x**2 + 3*x - 1", "sin(x) + log(x)", "|x - 2|", "log_3(x)"]:
            with self.subTest(expr=expr):
                safe_parse(expr)  # must not raise


class MatrixRoutingTests(unittest.TestCase):
    """"det [[1,2],[3,4]]" and "inverse of [[2,0],[0,2]]" don't contain the
    literal words "matrix"/"determinant" that topic detection looked for,
    so they fell through to the generic algebra solver and crashed trying
    to parse bracket syntax as an ordinary expression."""

    def test_det_without_the_word_matrix_routes_correctly(self):
        r = solve_expression("det [[1,2],[3,4]]")
        self.assertIn("-2", r["answer"])
        self.assertIsNone(r["error"])

    def test_inverse_of_without_the_word_matrix_routes_correctly(self):
        r = solve_expression("inverse of [[2,0],[0,2]]")
        self.assertIsNone(r["error"])
        self.assertIn("det", r["answer"])


class TrigSimplificationTests(unittest.TestCase):
    """The trig solver only ever evaluated a single sin/cos/tan(...) call
    in isolation, so a compound symbolic expression like the Pythagorean
    identity never matched and fell through to a generic non-answer even
    though SymPy can simplify it directly."""

    def test_pythagorean_identity_simplifies_to_one(self):
        r = solve_expression("sin(x)^2 + cos(x)^2")
        self.assertEqual(r["answer"], "1")

    def test_tan_cos_simplifies_to_sin(self):
        r = solve_expression("tan(x)*cos(x)")
        self.assertEqual(r["answer"], "sin(x)")

    def test_numeric_evaluation_still_works(self):
        r = solve_expression("sin(45)")
        self.assertIn("sqrt(2)/2", r["answer"])


class InverseTrigTests(unittest.TestCase):
    """atan/acos/asin were silently matched as tan/cos/sin (substring match),
    and even once matched correctly, the degrees-to-radians conversion meant
    for sin/cos/tan's *angle* input was wrongly also applied to the inverse
    functions' *ratio* input."""

    def test_atan_is_not_confused_with_tan(self):
        r = solve_expression("atan(1)")
        self.assertIn("pi/4", r["answer"])
        self.assertIn("45", r["answer"])

    def test_acos_is_not_confused_with_cos(self):
        r = solve_expression("acos(0.5)")
        self.assertIn("pi/3", r["answer"])
        self.assertIn("60", r["answer"])

    def test_asin_is_not_confused_with_sin(self):
        r = solve_expression("asin(0.5)")
        self.assertIn("pi/6", r["answer"])
        self.assertIn("30", r["answer"])

    def test_plain_tan_still_works(self):
        r = solve_expression("tan(45)")
        self.assertIn("1.000000", r["answer"])

    def test_asin_out_of_domain_gives_clear_error_not_garbage(self):
        r = solve_expression("asin(2)")
        self.assertIsNone(r["answer"])
        self.assertIn("-1 and 1", r["error"])


class VariableInferenceTests(unittest.TestCase):
    """diff/integrate/limit always differentiated with respect to x
    regardless of the expression's actual variable, so e.g. differentiating
    a pure-t expression silently returned 0."""

    def test_differentiate_non_x_variable(self):
        r = solve_expression("differentiate t^2 + 3t")
        self.assertEqual(r["answer"], "2*t + 3")

    def test_differentiate_x_still_works(self):
        r = solve_expression("differentiate x^2")
        self.assertEqual(r["answer"], "2*x")

    def test_integrate_non_x_variable(self):
        r = solve_expression("integrate t^2 dt")
        self.assertEqual(r["answer"], "t**3/3 + C")


class ProseGuardTests(unittest.TestCase):
    """Problems with no dedicated handler (Fourier transforms, etc.) used to
    fall through to the generic algebra solver, which would implicit-multiply
    the individual letters of English words together and return a fabricated
    symbolic "answer" instead of failing."""

    def test_fourier_transform_does_not_fabricate_an_answer(self):
        r = solve_expression("Find the Fourier transform of e^(-t^2)")
        self.assertIsNone(r["answer"])
        self.assertIsNotNone(r["error"])
        # The old bug produced a product of single-letter symbols spelling
        # out "Fourier"/"transform" — make sure that shape can't come back.
        self.assertNotIn("*f*", r["error"] or "")

    def test_fourier_routes_to_llm_first(self):
        self.assertTrue(is_llm_first_problem("Find the Fourier transform of e^(-t^2)"))

    def test_ordinary_expression_is_not_flagged_as_prose(self):
        self.assertFalse(looks_like_prose("x**2 + 3*x - 10"))
        self.assertFalse(looks_like_prose("sin(x) + log(x)"))

    def test_sentence_is_flagged_as_prose(self):
        self.assertTrue(looks_like_prose("Fourier transform of something"))


class NotationTests(unittest.TestCase):
    """|x| and log_3(x) are how students actually write these, not Abs(x)
    and log(x, 3); both used to fail outright."""

    def test_absolute_value_bars_parse_for_graphing(self):
        r = generate_function_points("|x|")
        self.assertNotIn("error", r)
        self.assertEqual(r["expr"], "Abs(x)")

    def test_log_subscript_base_parses_for_graphing(self):
        r = generate_function_points("log_3(x)")
        self.assertNotIn("error", r)
        # log_3(9) should be 2
        idx = min(range(len(r["x"])), key=lambda i: abs(r["x"][i] - 9))
        self.assertAlmostEqual(r["y"][idx], 2.0, delta=0.05)

    def test_absolute_value_equation_solves(self):
        r = solve_expression("|x - 5| = 3")
        self.assertEqual(sorted(eval(r["answer"], {"__builtins__": {}})), [2, 8])

    def test_graph_reports_unparseable_expression_instead_of_silently_dropping(self):
        from app.services.graph_service import build_function_graph
        result = build_function_graph(["x**2", "this is not math("])
        self.assertEqual(len(result["data"]), 1)  # the valid one still plots
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["errors"][0]["expression"], "this is not math(")


class EquationVariableChoiceTests(unittest.TestCase):
    """Solving an equation with several free variables picked whichever
    sorted alphabetically first — e.g. "y = m*x + c" solved for "c" instead
    of the far more likely intended "x"."""

    def test_prefers_x_over_alphabetically_earlier_variables(self):
        r = solve_expression("y = m*x + c")
        self.assertIn("/m", r["answer"])  # solved for x: (y - c) / m


class LocalExtremaTests(unittest.TestCase):
    """
    "If f(x) = x^3 - 6x^2 + 9x + 1, at which value of x does f have a local
    maximum?" was misrouted as topic "algebra_quadratic" — the topic detector
    did a bare substring match for "x^2", which also matches the "-6x^2" term
    inside a genuinely cubic expression. That produced a wrong-topic AI
    explanation (quadratic formula/discriminant) for a calculus problem, and
    the differentiation solver itself only strips instruction words like
    "derivative of" — it had no handling for this word-problem phrasing at
    all, so it fell through to the prose-rejection guard instead of solving.
    """

    def test_cubic_with_x_squared_term_is_not_misdetected_as_quadratic(self):
        topic = detect_topic("If f(x) = x^3 - 6x^2 + 9x + 1, at which value of x does f have a local maximum?")
        self.assertEqual(topic, "calculus_differentiation")

    def test_true_quadratic_is_still_detected_correctly(self):
        self.assertEqual(detect_topic("Solve x^2 - 5x + 6 = 0"), "algebra_quadratic")

    def test_local_maximum_word_problem_solves_to_correct_critical_point(self):
        r = solve_expression("If f(x) = x^3 - 6x^2 + 9x + 1, at which value of x does f have a local maximum?")
        self.assertIsNone(r["error"])
        self.assertEqual(r["answer"], "x = 1")

    def test_local_minimum_word_problem_solves_to_correct_critical_point(self):
        r = solve_expression("If f(x) = x^3 - 6x^2 + 9x + 1, at which value of x does f have a local minimum?")
        self.assertIsNone(r["error"])
        self.assertEqual(r["answer"], "x = 3")


class StepLatexTests(unittest.TestCase):
    """
    Every step's plain-text `expression` used Python/SymPy str() syntax
    (e.g. "x**3 - 6*x**2 + 9*x + 1") with no way to render real exponents —
    the raw "**" showed up literally in the UI instead of a superscript,
    unlike a reference like ChatGPT's rendering. Steps now also carry a
    `latex` field for KaTeX to render; this locks in that it's actually
    present and free of leftover Python operator syntax, for every solver
    that produces algebraic steps.
    """

    def _assert_steps_have_clean_latex(self, r):
        self.assertIsNone(r["error"], r.get("error"))
        latex_steps = [s for s in r["steps"] if s.get("latex")]
        self.assertTrue(latex_steps, "expected at least one step with a latex field")
        for s in latex_steps:
            self.assertNotIn("**", s["latex"], s)
            self.assertNotIn("*", s["latex"], s)  # SymPy's latex() uses \cdot / juxtaposition, not *

    def test_local_extrema_steps_have_clean_latex(self):
        r = solve_expression("If f(x) = x^3 - 6x^2 + 9x + 1, at which value of x does f have a local maximum?")
        self._assert_steps_have_clean_latex(r)

    def test_differentiation_steps_have_clean_latex(self):
        r = solve_expression("d/dx of x^3 + 2x")
        self._assert_steps_have_clean_latex(r)

    def test_integration_steps_have_clean_latex(self):
        r = solve_expression("integrate 3x^2")
        self._assert_steps_have_clean_latex(r)

    def test_algebra_equation_steps_have_clean_latex(self):
        r = solve_expression("Solve: 2x + 3 = 11")
        self._assert_steps_have_clean_latex(r)


if __name__ == "__main__":
    unittest.main()
