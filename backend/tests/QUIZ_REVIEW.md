Quiz calibration release review
===============================

Automated checks
----------------
Run `PYTHONPATH=backend python -m unittest discover -s backend/tests` with backend dependencies installed, then `npm run build` in frontend.
Tests use simulated model transport; they do not establish live question quality.

Live review before release
--------------------------
Generate three five-question quizzes for each calculus level. Have a mathematics
reviewer solve every item without seeing the key, then check the answer, uniqueness
of options, explanation, assumptions, and fit to the selected level. Repeat across
the other six topics before claiming calibration across the whole application.

Basic: a direct definition or rule. Intermediate: method selection and multiple
steps. Advanced: connected concepts, non-routine reasoning and conditions; merely
larger numbers or technical wording do not qualify. These are product definitions,
not claims of alignment to any specific national curriculum.

Release only with no incorrect or ambiguous items in the reviewed sample and every
item matching its level. Record rejected items and revise the topic contract before
regenerating. This sample is a release check, not a statistical accuracy guarantee.
Track rejection rate, latency and provider cost; each quiz now needs two model calls.
The model's second-pass review can still share the first pass's mistakes.

Browser checks: configure each level, generate, answer out of order, submit, verify
the original questions and grade, then try another quiz. Simulate unavailable AI
and confirm a useful error appears without an easier replacement quiz.

Rollout
-------
Deploy the backend first: startup creates the new generated_quizzes table through
the existing init_db path. Then deploy the frontend that submits quiz_id. Old open
quizzes must be restarted. Check database persistence on the hosting service:
storing a quiz in an ephemeral SQLite file will not survive replacement of that file.
Answer keys stay server-side. Anonymous session IDs provide continuity, not user
authentication. Retention limits and stronger account ownership are separate follow-ups.

Status: offline checks only; live model and browser review remain pending.
