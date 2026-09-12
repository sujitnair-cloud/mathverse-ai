"""
Lesson content for the learning journey (Phase 5), one entry per topic that
has a practice generator. Deliberately NOT a formula sheet: each lesson
follows motivation -> construction -> example -> transfer, because a list
of rules with no reason to want them is exactly what "lessons lack
motivation" was about. Calculus is written the way the roadmap names
explicitly: starting from the problem of measuring a changing quantity,
not from "here are the differentiation rules."

  motivation:   the real problem that makes you want this idea
  construction: how the idea gets built from what you already know
  example:      one worked example connecting motivation to method
  transfer:     a prompt (not an answer) for applying it somewhere new —
                the learner does this, it isn't done for them
"""

LESSONS = {
    "arithmetic": {
        "motivation": (
            "You're splitting a restaurant bill four ways, or figuring out if you have enough money "
            "for what's in your cart. You need a way to combine and compare quantities that always "
            "gives the same answer no matter who's doing the counting."
        ),
        "construction": (
            "Addition is just counting onward. Subtraction is counting backward, or 'what's left.' "
            "Multiplication is repeated addition (3×4 is four groups of three), and division is "
            "splitting into equal groups. Fractions and percentages are just ways of naming a part "
            "of a whole. Everything else in arithmetic is these four ideas combined."
        ),
        "example": {
            "problem": "A pizza is cut into 8 slices. You eat 3. What fraction is left, as a percentage?",
            "solution": "5 slices remain out of 8, so 5/8 remain. As a percentage: 5/8 × 100 = 62.5%.",
        },
        "transfer": (
            "A recipe serves 4 and uses 3/4 cup of flour. You want to make it for 6 people. "
            "How much flour do you need? (Don't compute it here — just notice which of the four "
            "basic operations you'd reach for, and why.)"
        ),
    },
    "algebra": {
        "motivation": (
            "You know a rectangle's perimeter is 20 and its length is twice its width — but you don't "
            "know either number yet. Arithmetic can't help until you know a value to start from. "
            "Algebra lets you reason about a quantity *before* you know what it is."
        ),
        "construction": (
            "A variable (like x) is just a placeholder for a number you don't know yet. An equation "
            "is a true statement about that number: whatever operation you see on one side, the same "
            "is true on the other. The core trick is that you can do anything to an equation — add, "
            "subtract, multiply, divide — as long as you do it to *both* sides, because that keeps "
            "the statement true while slowly isolating the unknown."
        ),
        "example": {
            "problem": "A rectangle's perimeter is 20. Its length is twice its width. Find the width.",
            "solution": (
                "Let width = w, so length = 2w. Perimeter = 2(length + width) = 2(2w + w) = 6w. "
                "6w = 20, so w = 20/6 = 10/3."
            ),
        },
        "transfer": (
            "Two numbers add to 15, and one is 3 more than the other. Set up an equation for this "
            "using a single variable — you don't need to solve it, just write the equation."
        ),
    },
    "geometry": {
        "motivation": (
            "A rug covers part of your floor and you're charged by the square foot. A ladder needs to "
            "reach a window at a known height. Geometry is the mathematics of *space itself* — how much "
            "room something takes up, and how shapes constrain each other."
        ),
        "construction": (
            "Every area formula comes from counting unit squares, even when it doesn't look like it: "
            "a rectangle's area (length × width) IS the count of unit squares in a grid. A triangle is "
            "exactly half of the rectangle that encloses it, which is where 'half base times height' "
            "comes from. The Pythagorean theorem (a² + b² = c²) comes from the same rectangle-splitting "
            "idea applied to a right triangle's own squares built on each side."
        ),
        "example": {
            "problem": "A ladder leans against a wall, its base 6 feet from the wall, reaching a point 8 feet up. How long is the ladder?",
            "solution": "The ladder is the hypotenuse: c² = 6² + 8² = 36 + 64 = 100, so c = 10 feet.",
        },
        "transfer": (
            "A TV is advertised by the length of its diagonal. If a TV is 40 inches wide and 22.5 "
            "inches tall, which formula from this lesson would you use to find its advertised size?"
        ),
    },
    "trigonometry": {
        "motivation": (
            "You know one angle and one side of a triangle — say, the angle to the top of a building "
            "and your distance from its base — and you want the building's height without climbing it. "
            "You need a fixed relationship between angles and side lengths that holds for *every* "
            "triangle with that angle, regardless of size."
        ),
        "construction": (
            "Take a right triangle and only look at one of its non-right angles, θ. As you scale the "
            "triangle up or down, the *ratio* of any two sides stays the same — only the actual lengths "
            "change. Those fixed ratios are named: sin θ = opposite/hypotenuse, cos θ = adjacent/"
            "hypotenuse, tan θ = opposite/adjacent. Because they're ratios of a triangle's own sides, "
            "sin²θ + cos²θ = 1 always holds — it's the Pythagorean theorem in disguise, divided through "
            "by the hypotenuse squared."
        ),
        "example": {
            "problem": "You stand 50 m from a building's base and measure a 30° angle to its top. How tall is the building?",
            "solution": "tan(30°) = height/50, so height = 50 × tan(30°) = 50 × (1/√3) ≈ 28.9 m.",
        },
        "transfer": (
            "A kite string makes a 40° angle with the ground and you've let out 60 m of string. Which "
            "trig ratio would you use to find how high the kite is — and why that one, not the others?"
        ),
    },
    "calculus": {
        "motivation": (
            "A car's position is changing, but the speedometer needle doesn't show you 'total distance "
            "so far' — it shows you *how fast position is changing right now*. Average speed over a trip "
            "is easy (distance ÷ time), but 'speed at this exact instant' seems to need a time interval "
            "of zero, which makes distance ÷ time into 0/0. Calculus exists to make sense of that."
        ),
        "construction": (
            "Instead of an instant, look at a very short interval: the average rate of change from "
            "time t to time t+h is [f(t+h) − f(t)] / h. As h shrinks toward zero, that average rate "
            "settles down to a single number — the *instantaneous* rate of change, called the "
            "derivative, written f'(x). Working this limit out for f(x) = xⁿ, the h's cancel "
            "algebraically before you'd need to divide by zero, and what's left is the power rule: "
            "d/dx(xⁿ) = n·xⁿ⁻¹. The rule isn't the starting point — it's what falls out of this process "
            "for one specific, common shape of function."
        ),
        "example": {
            "problem": "A ball's height is h(t) = 20t − 5t². Find its velocity (rate of change of height) at t = 1.",
            "solution": (
                "h'(t) = 20 − 10t (power rule applied to each term). At t = 1: h'(1) = 20 − 10 = 10, "
                "so the ball is rising at 10 units per second at that instant."
            ),
        },
        "transfer": (
            "A tank's water volume is V(t) = 100 + 3t² liters, t in minutes. What question would you "
            "ask — and what would you compute — to find how fast the tank is filling at t = 5 minutes?"
        ),
    },
    "statistics": {
        "motivation": (
            "Two classes take the same test and both average 75%. Were they equally consistent? The "
            "average alone can't tell you — one class could be all 75s, the other half 100s and half "
            "50s. You need a number that captures how *spread out* the data is, not just its center."
        ),
        "construction": (
            "The mean is the balance point of the data. To measure spread, look at each value's "
            "distance from that balance point, (x − mean). Simply adding those distances always gives "
            "zero (that's what 'balance point' means), so square each distance first — squaring also "
            "makes big deviations count more than small ones. Average the squared distances (variance), "
            "then undo the squaring with a square root to get back to the original units: that's the "
            "standard deviation."
        ),
        "example": {
            "problem": "Class A: [70, 75, 80]. Class B: [50, 75, 100]. Both average 75 — which is more consistent?",
            "solution": (
                "Class A's deviations from 75 are ±5, ±0 — small spread, low standard deviation. "
                "Class B's deviations are ±25, ±0 — much larger spread, higher standard deviation. "
                "Class A is more consistent even though both average the same."
            ),
        },
        "transfer": (
            "Two delivery services both average 30 minutes. One is always within 5 minutes of that; "
            "the other ranges from 10 to 50 minutes. Which statistic from this lesson tells them apart, "
            "and which service would you trust for a time-sensitive delivery?"
        ),
    },
    "probability": {
        "motivation": (
            "A lottery has a huge number of possible ticket combinations, and you want to know your "
            "actual odds of winning — not a vague sense of 'unlikely,' but a specific number. You need "
            "a reliable way to *count* possibilities without listing every single one by hand."
        ),
        "construction": (
            "Probability of an event = (favorable outcomes) / (total outcomes) — the hard part is "
            "usually counting each side correctly. When order doesn't matter (choosing a 3-person "
            "committee from 10 people), you're counting combinations: C(n,r) = n!/(r!(n−r)!). When "
            "order does matter (1st, 2nd, 3rd place from 10 runners), you're counting permutations: "
            "P(n,r) = n!/(n−r)!. Permutations count every arrangement of the r choices separately; "
            "combinations then divide that by r! to collapse arrangements of the *same* group into one."
        ),
        "example": {
            "problem": "A committee of 3 is chosen from 8 people. How many different committees are possible?",
            "solution": "Order doesn't matter for a committee, so use combinations: C(8,3) = 8!/(3!·5!) = 56.",
        },
        "transfer": (
            "A race has 6 runners and you want to count the possible arrangements of 1st, 2nd, and 3rd "
            "place. Is this a combination or a permutation — and why does the difference matter here "
            "in a way it didn't for the committee?"
        ),
    },
    "linear-algebra": {
        "motivation": (
            "A system of equations — 2x + y = 5 and x − y = 1 — can be solved by substitution, but with "
            "10 equations and 10 unknowns that approach collapses under its own bookkeeping. You need a "
            "way to handle many linear equations at once as a single object."
        ),
        "construction": (
            "A matrix is just a grid of numbers that packages a system of linear equations together. "
            "For a 2×2 matrix [[a,b],[c,d]], the determinant ad − bc tells you whether the system has "
            "exactly one solution (determinant ≠ 0) or is degenerate — parallel or overlapping lines "
            "(determinant = 0). It comes directly from eliminating one variable algebraically across "
            "both equations at once, the same elimination you'd do by hand, just tracked systematically."
        ),
        "example": {
            "problem": "Does the system 2x + y = 5, x − y = 1 have exactly one solution?",
            "solution": (
                "Coefficient matrix [[2,1],[1,-1]]. Determinant = (2)(-1) - (1)(1) = -2 - 1 = -3. "
                "Since -3 ≠ 0, the system has exactly one solution."
            ),
        },
        "transfer": (
            "The system 2x + 4y = 6 and x + 2y = 3 describes the same line written two ways. What would "
            "you expect its determinant to be, and why, before computing it?"
        ),
    },
}
