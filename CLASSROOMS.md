# Classrooms

Open `/classrooms` or choose **Classes** in the navigation.

## Teacher workflow

1. Sign in with the existing Google account flow.
2. Create a classroom and share its joining code with students.
3. Publish an assignment with questions, instructions, and an optional due date.
4. Open submitted work, enter a score from 0 to 100, and save feedback.

## Student workflow

1. Sign in and join with the teacher's code.
2. Open an assignment, enter an answer and working, and submit.
3. Return to the assignment to see the teacher's score and feedback.

Students can only read their own submissions. Only the classroom creator can
publish assignments, view all submissions, and grade work. Classroom membership
does not grant administrative access to the rest of MathVerse.

The current version supports text assignments and one submission per student per
assignment. Late submissions remain available and are visibly marked by comparing
the due date with the submission timestamp. Attachments, resubmissions, roster
management, and classroom archival are not implemented in this version.

## Storage and deployment

The backend creates five additional tables on startup through its existing
`init_db` workflow: `quiz_sessions`, `classrooms`, `class_members`, `assignments`,
and `assignment_submissions`. Existing data and columns are retained. Restart
the backend before serving the new frontend. Quiz generation now returns a
`quiz_id`; quiz submission accepts that ID and answers instead of client-provided
questions. In-progress quizzes from the old frontend must be restarted.

For Railway, use persistent PostgreSQL or a persistent SQLite volume. The server
must have permission to create the new tables. This change has not been deployed
or verified against the live Railway database. Existing Google OAuth configuration
is required; no alternate login or production test accounts were added.

## Verification

From `frontend`, run `npm run build`.
From `backend`, run `python -m unittest discover -s tests -v` with the backend
dependencies installed. Tests use an isolated in-memory database and mock quiz
generation; they do not call live AI providers or Google sign-in.

Regression checks cover original-question quiz grading, hidden answer keys,
invalid answers, repeated submissions, account history isolation, classroom
membership, teacher-only assignment creation and grading, student work privacy,
and feedback retrieval.
