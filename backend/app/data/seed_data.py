"""
Seed the database with starter formulas and topics.
Run once with: python -m app.data.seed_data
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.core.database import AsyncSessionLocal, init_db
from app.models.models import Formula, MathTopic

FORMULAS = [
    # Algebra
    {"name": "Quadratic Formula", "topic": "Algebra", "subtopic": "Quadratic Equations",
     "formula": "x = (-b ± √(b²-4ac)) / 2a",
     "description": "Solves any quadratic equation ax² + bx + c = 0",
     "variables": {"a": "coefficient of x²", "b": "coefficient of x", "c": "constant term"},
     "example": "x² + 5x + 6 = 0 → x = -2 or x = -3",
     "difficulty": "intermediate", "tags": ["quadratic", "roots", "parabola"]},

    {"name": "Distance Formula", "topic": "Geometry", "subtopic": "Coordinate Geometry",
     "formula": "d = √((x₂-x₁)² + (y₂-y₁)²)",
     "description": "Distance between two points in a 2D plane",
     "variables": {"(x₁,y₁)": "first point", "(x₂,y₂)": "second point"},
     "example": "Distance between (1,2) and (4,6) = √(9+16) = 5",
     "difficulty": "basic", "tags": ["distance", "coordinates", "geometry"]},

    {"name": "Pythagorean Theorem", "topic": "Geometry", "subtopic": "Triangles",
     "formula": "a² + b² = c²",
     "description": "In a right triangle, the square of the hypotenuse equals the sum of squares of the other two sides",
     "variables": {"a": "one leg", "b": "other leg", "c": "hypotenuse"},
     "example": "a=3, b=4 → c = √(9+16) = 5",
     "difficulty": "basic", "tags": ["pythagorean", "right triangle", "hypotenuse"]},

    {"name": "Area of Circle", "topic": "Geometry", "subtopic": "Circles",
     "formula": "A = πr²",
     "description": "Area enclosed by a circle",
     "variables": {"r": "radius", "π": "pi ≈ 3.14159"},
     "example": "r=5 → A = π×25 ≈ 78.54",
     "difficulty": "basic", "tags": ["circle", "area", "pi"]},

    {"name": "Slope of a Line", "topic": "Algebra", "subtopic": "Linear Equations",
     "formula": "m = (y₂ - y₁) / (x₂ - x₁)",
     "description": "Rate of change of a line through two points",
     "variables": {"m": "slope", "(x₁,y₁)": "first point", "(x₂,y₂)": "second point"},
     "example": "Points (1,2) and (3,6) → m = (6-2)/(3-1) = 2",
     "difficulty": "basic", "tags": ["slope", "line", "linear"]},

    # Calculus
    {"name": "Power Rule (Differentiation)", "topic": "Calculus", "subtopic": "Derivatives",
     "formula": "d/dx(xⁿ) = nxⁿ⁻¹",
     "description": "Differentiates a power function",
     "variables": {"n": "exponent", "x": "variable"},
     "example": "d/dx(x³) = 3x²",
     "difficulty": "intermediate", "tags": ["derivative", "power rule", "calculus"]},

    {"name": "Integration Power Rule", "topic": "Calculus", "subtopic": "Integrals",
     "formula": "∫xⁿ dx = xⁿ⁺¹/(n+1) + C  (n ≠ -1)",
     "description": "Integrates a power function",
     "variables": {"n": "exponent (not -1)", "C": "constant of integration"},
     "example": "∫x² dx = x³/3 + C",
     "difficulty": "intermediate", "tags": ["integral", "antiderivative", "calculus"]},

    {"name": "Chain Rule", "topic": "Calculus", "subtopic": "Derivatives",
     "formula": "d/dx[f(g(x))] = f'(g(x)) · g'(x)",
     "description": "Differentiates composite functions",
     "variables": {"f": "outer function", "g": "inner function"},
     "example": "d/dx(sin(x²)) = cos(x²) · 2x",
     "difficulty": "advanced", "tags": ["chain rule", "composite", "derivative"]},

    {"name": "Fundamental Theorem of Calculus", "topic": "Calculus", "subtopic": "Integrals",
     "formula": "∫ₐᵇ f(x)dx = F(b) - F(a)",
     "description": "Connects differentiation and integration; F is the antiderivative of f",
     "variables": {"F": "antiderivative of f", "a,b": "integration bounds"},
     "example": "∫₀² x² dx = [x³/3]₀² = 8/3",
     "difficulty": "advanced", "tags": ["definite integral", "FTC", "calculus"]},

    # Trigonometry
    {"name": "Sine Rule", "topic": "Trigonometry", "subtopic": "Triangles",
     "formula": "a/sin(A) = b/sin(B) = c/sin(C)",
     "description": "Relates sides and angles of any triangle",
     "variables": {"a,b,c": "side lengths", "A,B,C": "opposite angles"},
     "example": "If a=5, A=30°, B=45°, then b = 5·sin(45°)/sin(30°) ≈ 7.07",
     "difficulty": "intermediate", "tags": ["sine rule", "triangle", "trigonometry"]},

    {"name": "Cosine Rule", "topic": "Trigonometry", "subtopic": "Triangles",
     "formula": "c² = a² + b² - 2ab·cos(C)",
     "description": "Generalisation of Pythagorean theorem for any triangle",
     "variables": {"a,b,c": "side lengths", "C": "angle opposite to side c"},
     "example": "a=3, b=4, C=60° → c² = 9+16-12 = 13, c ≈ 3.61",
     "difficulty": "intermediate", "tags": ["cosine rule", "triangle"]},

    {"name": "Pythagorean Identity", "topic": "Trigonometry", "subtopic": "Identities",
     "formula": "sin²θ + cos²θ = 1",
     "description": "Fundamental trigonometric identity",
     "variables": {"θ": "angle in radians or degrees"},
     "example": "sin²(30°) + cos²(30°) = 0.25 + 0.75 = 1",
     "difficulty": "basic", "tags": ["identity", "sin", "cos"]},

    # Statistics
    {"name": "Mean (Average)", "topic": "Statistics", "subtopic": "Descriptive",
     "formula": "x̄ = Σxᵢ / n",
     "description": "Average value of a dataset",
     "variables": {"Σxᵢ": "sum of all values", "n": "number of values"},
     "example": "[2,4,6,8,10] → mean = 30/5 = 6",
     "difficulty": "basic", "tags": ["mean", "average", "statistics"]},

    {"name": "Standard Deviation", "topic": "Statistics", "subtopic": "Descriptive",
     "formula": "σ = √(Σ(xᵢ-x̄)² / (n-1))",
     "description": "Measures spread of data around the mean (sample std dev)",
     "variables": {"x̄": "mean", "n": "sample size", "xᵢ": "each value"},
     "example": "[2,4,6,8,10] → σ ≈ 3.16",
     "difficulty": "intermediate", "tags": ["std dev", "variance", "spread"]},

    {"name": "Normal Distribution PDF", "topic": "Statistics", "subtopic": "Distributions",
     "formula": "f(x) = (1/σ√(2π)) · e^(-(x-μ)²/2σ²)",
     "description": "Probability density function of the normal (Gaussian) distribution",
     "variables": {"μ": "mean", "σ": "standard deviation"},
     "example": "Standard normal: μ=0, σ=1",
     "difficulty": "advanced", "tags": ["normal", "gaussian", "probability"]},

    # Probability
    {"name": "Combination (nCr)", "topic": "Probability", "subtopic": "Counting",
     "formula": "C(n,r) = n! / (r!(n-r)!)",
     "description": "Number of ways to choose r items from n without order",
     "variables": {"n": "total items", "r": "items chosen"},
     "example": "C(5,2) = 5!/(2!·3!) = 10",
     "difficulty": "basic", "tags": ["combination", "counting", "nCr"]},

    {"name": "Permutation (nPr)", "topic": "Probability", "subtopic": "Counting",
     "formula": "P(n,r) = n! / (n-r)!",
     "description": "Number of ways to arrange r items from n with order",
     "variables": {"n": "total items", "r": "items chosen"},
     "example": "P(5,2) = 5!/3! = 20",
     "difficulty": "basic", "tags": ["permutation", "counting", "nPr"]},

    {"name": "Bayes Theorem", "topic": "Probability", "subtopic": "Conditional Probability",
     "formula": "P(A|B) = P(B|A) · P(A) / P(B)",
     "description": "Updates probability given new evidence",
     "variables": {"P(A|B)": "posterior", "P(B|A)": "likelihood", "P(A)": "prior", "P(B)": "evidence"},
     "example": "Medical test accuracy via Bayes theorem",
     "difficulty": "advanced", "tags": ["bayes", "conditional probability"]},

    # Linear Algebra
    {"name": "Matrix Determinant (2×2)", "topic": "Linear Algebra", "subtopic": "Matrices",
     "formula": "det([[a,b],[c,d]]) = ad - bc",
     "description": "Determinant of a 2×2 matrix",
     "variables": {"a,b,c,d": "matrix elements"},
     "example": "det([[1,2],[3,4]]) = 4 - 6 = -2",
     "difficulty": "intermediate", "tags": ["determinant", "matrix", "linear algebra"]},

    {"name": "Dot Product", "topic": "Linear Algebra", "subtopic": "Vectors",
     "formula": "a·b = |a||b|cos(θ) = Σaᵢbᵢ",
     "description": "Scalar product of two vectors",
     "variables": {"a,b": "vectors", "θ": "angle between them"},
     "example": "[1,2]·[3,4] = 3+8 = 11",
     "difficulty": "intermediate", "tags": ["dot product", "vectors", "linear algebra"]},

    # Finance
    {"name": "Compound Interest", "topic": "Finance", "subtopic": "Interest",
     "formula": "A = P(1 + r/n)^(nt)",
     "description": "Amount after compound interest",
     "variables": {"P": "principal", "r": "annual rate", "n": "compounds/year", "t": "years"},
     "example": "P=1000, r=10%, n=12, t=5 → A ≈ 1647",
     "difficulty": "intermediate", "tags": ["compound interest", "finance", "investment"]},

    {"name": "Simple Interest", "topic": "Finance", "subtopic": "Interest",
     "formula": "I = P × r × t",
     "description": "Interest on principal without compounding",
     "variables": {"P": "principal", "r": "rate per period", "t": "time periods"},
     "example": "P=1000, r=5%, t=3 years → I = 150",
     "difficulty": "basic", "tags": ["simple interest", "finance"]},
]

TOPICS = [
    {"slug": "arithmetic", "name": "Arithmetic", "category": "Foundation",
     "definition": "The branch of mathematics dealing with basic operations on numbers.",
     "explanation": "Arithmetic is the oldest and most fundamental branch of mathematics. It covers addition, subtraction, multiplication, division, fractions, decimals, percentages, and ratios.",
     "key_formulas": ["a + b = b + a (Commutativity)", "a(b + c) = ab + ac (Distributivity)", "PEMDAS/BODMAS order of operations"],
     "examples": [{"problem": "12 × 15", "solution": "180"}, {"problem": "3/4 + 1/2", "solution": "5/4 = 1.25"}],
     "use_cases": "Everyday calculations, budgeting, cooking, measurements",
     "difficulty": "basic", "related_topics": ["algebra"], "prerequisites": []},

    {"slug": "algebra", "name": "Algebra", "category": "Foundation",
     "definition": "Branch of mathematics that uses letters and symbols to represent numbers and quantities in formulas and equations.",
     "explanation": "Algebra extends arithmetic by introducing variables. It enables solving equations, expressing general rules, and working with unknown quantities. Covers linear, quadratic, polynomial, and exponential expressions.",
     "key_formulas": ["ax + b = c → x = (c-b)/a", "x = (-b ± √(b²-4ac))/2a (Quadratic)", "(a+b)² = a² + 2ab + b²"],
     "examples": [{"problem": "Solve 2x + 3 = 11", "solution": "x = 4"}, {"problem": "Factor x² - 5x + 6", "solution": "(x-2)(x-3)"}],
     "use_cases": "Engineering, physics, economics, computer science",
     "difficulty": "basic", "related_topics": ["calculus", "linear-algebra"], "prerequisites": ["arithmetic"]},

    {"slug": "geometry", "name": "Geometry", "category": "Foundation",
     "definition": "Study of shapes, sizes, properties of figures and spaces.",
     "explanation": "Geometry studies points, lines, surfaces, and solids. It includes Euclidean geometry (flat spaces), coordinate geometry (using algebra), and trigonometry.",
     "key_formulas": ["Area of circle = πr²", "Pythagorean theorem: a² + b² = c²", "Volume of sphere = (4/3)πr³"],
     "examples": [{"problem": "Find area of circle r=5", "solution": "A = 78.54"}, {"problem": "Perimeter of rectangle 4×6", "solution": "P = 20"}],
     "use_cases": "Architecture, engineering, navigation, art, design",
     "difficulty": "basic", "related_topics": ["trigonometry", "calculus"], "prerequisites": ["arithmetic"]},

    {"slug": "trigonometry", "name": "Trigonometry", "category": "Intermediate",
     "definition": "Study of relationships between angles and sides of triangles.",
     "explanation": "Trigonometry focuses on the six trig functions (sin, cos, tan and their inverses). It is fundamental to physics, engineering, signal processing, and navigation.",
     "key_formulas": ["sin²θ + cos²θ = 1", "tan θ = sin θ / cos θ", "Sine Rule: a/sin(A) = b/sin(B)"],
     "examples": [{"problem": "sin(30°)", "solution": "0.5"}, {"problem": "cos(60°)", "solution": "0.5"}],
     "use_cases": "Navigation, physics, engineering, computer graphics, signal processing",
     "difficulty": "intermediate", "related_topics": ["geometry", "calculus"], "prerequisites": ["geometry", "algebra"]},

    {"slug": "calculus", "name": "Calculus", "category": "Advanced",
     "definition": "Branch of mathematics studying continuous change, divided into differential and integral calculus.",
     "explanation": "Calculus was independently developed by Newton and Leibniz. Differential calculus deals with rates of change (derivatives). Integral calculus deals with accumulation (integrals). They are linked by the Fundamental Theorem of Calculus.",
     "key_formulas": ["d/dx(xⁿ) = nxⁿ⁻¹", "∫xⁿ dx = xⁿ⁺¹/(n+1) + C", "∫ₐᵇ f(x)dx = F(b) - F(a)"],
     "examples": [{"problem": "d/dx(x³ + 2x)", "solution": "3x² + 2"}, {"problem": "∫(2x) dx", "solution": "x² + C"}],
     "use_cases": "Physics, engineering, economics, biology, machine learning",
     "difficulty": "advanced", "related_topics": ["algebra", "trigonometry", "differential-equations"], "prerequisites": ["algebra", "trigonometry"]},

    {"slug": "statistics", "name": "Statistics", "category": "Intermediate",
     "definition": "Branch of mathematics dealing with collection, analysis, interpretation, and presentation of data.",
     "explanation": "Statistics provides tools to summarize data (descriptive statistics) and make inferences about populations from samples (inferential statistics). Covers mean, median, mode, standard deviation, distributions, and hypothesis testing.",
     "key_formulas": ["Mean: x̄ = Σxᵢ/n", "Variance: σ² = Σ(xᵢ-x̄)²/(n-1)", "Z-score: z = (x-μ)/σ"],
     "examples": [{"problem": "Mean of [2,4,6,8,10]", "solution": "6"}, {"problem": "Std dev of [2,4,6,8,10]", "solution": "3.16"}],
     "use_cases": "Data science, research, business analytics, social sciences, medicine",
     "difficulty": "intermediate", "related_topics": ["probability", "calculus"], "prerequisites": ["algebra"]},

    {"slug": "probability", "name": "Probability", "category": "Intermediate",
     "definition": "Branch of mathematics measuring the likelihood of events occurring.",
     "explanation": "Probability assigns a number between 0 and 1 to events. It underpins statistics, machine learning, physics, and risk analysis. Covers permutations, combinations, conditional probability, and distributions.",
     "key_formulas": ["P(A) = n(A)/n(S)", "P(A∪B) = P(A) + P(B) - P(A∩B)", "C(n,r) = n!/(r!(n-r)!)"],
     "examples": [{"problem": "Probability of rolling a 6 on a fair die", "solution": "1/6 ≈ 0.167"}, {"problem": "C(5,2)", "solution": "10"}],
     "use_cases": "Insurance, gambling, machine learning, genetics, risk assessment",
     "difficulty": "intermediate", "related_topics": ["statistics", "algebra"], "prerequisites": ["algebra"]},

    {"slug": "linear-algebra", "name": "Linear Algebra", "category": "Advanced",
     "definition": "Branch of mathematics dealing with vectors, matrices, and linear transformations.",
     "explanation": "Linear algebra provides the mathematical foundation for machine learning, computer graphics, physics, and engineering. Topics include vectors, matrices, determinants, eigenvalues, and systems of linear equations.",
     "key_formulas": ["Ax = b (system of equations)", "det([[a,b],[c,d]]) = ad-bc", "Eigenvalue: Av = λv"],
     "examples": [{"problem": "det([[1,2],[3,4]])", "solution": "-2"}, {"problem": "Inverse of [[1,2],[3,4]]", "solution": "[[-2,1],[1.5,-0.5]]"}],
     "use_cases": "Machine learning, computer graphics, quantum mechanics, data compression",
     "difficulty": "advanced", "related_topics": ["algebra", "calculus"], "prerequisites": ["algebra"]},

    {"slug": "differential-equations", "name": "Differential Equations", "category": "Advanced",
     "definition": "Equations involving derivatives of unknown functions.",
     "explanation": "Differential equations describe rates of change and are used throughout science and engineering. ODEs involve one variable; PDEs involve partial derivatives. Solutions describe phenomena like population growth, heat flow, and wave propagation.",
     "key_formulas": ["dy/dx = f(x,y)", "Separable: ∫g(y)dy = ∫f(x)dx", "Linear 1st order: dy/dx + P(x)y = Q(x)"],
     "examples": [{"problem": "dy/dx = 2x", "solution": "y = x² + C"}, {"problem": "dy/dx = ky", "solution": "y = Ce^(kx)"}],
     "use_cases": "Physics, engineering, biology, economics, circuit analysis",
     "difficulty": "advanced", "related_topics": ["calculus", "linear-algebra"], "prerequisites": ["calculus"]},

    {"slug": "number-theory", "name": "Number Theory", "category": "Foundation",
     "definition": "Study of integers and their properties.",
     "explanation": "Number theory explores primes, divisibility, modular arithmetic, and Diophantine equations. It forms the mathematical basis of modern cryptography.",
     "key_formulas": ["Euclidean algorithm: gcd(a,b)", "Euler's theorem: aᶲ(n) ≡ 1 (mod n)", "Fundamental theorem: unique prime factorization"],
     "examples": [{"problem": "gcd(48, 18)", "solution": "6"}, {"problem": "Is 17 prime?", "solution": "Yes"}],
     "use_cases": "Cryptography, coding theory, computer science",
     "difficulty": "intermediate", "related_topics": ["algebra"], "prerequisites": ["arithmetic"]},

    {"slug": "financial-mathematics", "name": "Financial Mathematics", "category": "Applied",
     "definition": "Application of mathematical methods to financial problems.",
     "explanation": "Covers time value of money, interest calculations, annuities, present/future value, loan amortization, and investment analysis. Essential for banking, finance, and business.",
     "key_formulas": ["A = P(1+r/n)^(nt)", "PV = FV/(1+r)^n", "EMI = P·r(1+r)^n/((1+r)^n-1)"],
     "examples": [{"problem": "Compound interest on $1000 at 10% for 5 years", "solution": "$1628.89"}, {"problem": "Present value of $1000 in 3 years at 5%", "solution": "$863.84"}],
     "use_cases": "Banking, investment, loan analysis, retirement planning",
     "difficulty": "intermediate", "related_topics": ["algebra", "statistics"], "prerequisites": ["algebra"]},
]


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        # Check if already seeded
        from sqlalchemy import select
        existing = await db.execute(select(Formula).limit(1))
        if existing.scalar_one_or_none():
            print("Database already seeded.")
            return

        for f in FORMULAS:
            db.add(Formula(**f))
        for t in TOPICS:
            db.add(MathTopic(**t))
        await db.commit()
        print(f"Seeded {len(FORMULAS)} formulas and {len(TOPICS)} topics.")


if __name__ == "__main__":
    asyncio.run(seed())
