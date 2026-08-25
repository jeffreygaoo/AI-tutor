# Mastery interpretation

The engine combines evidence with these weights:

- concept quiz: 0.30
- practice: 0.25
- application: 0.20
- transfer: 0.15
- delayed review: 0.10

Score and confidence are separate. A high score based on sparse evidence remains
`familiar`; `mastered` requires score at least 0.80 and confidence at least 0.60.
Other score bands are weak below 0.30, learning below 0.60, and familiar below
0.80. Repeated evidence raises confidence, while later results remain blended with
prior evidence.

Prerequisite thresholds use mastery score deterministically. Do not override an
unlock or next-concept decision in prose. If the path seems wrong, inspect and
correct graph facts through a validated expansion or future graph-maintenance
operation rather than editing learner scores.

After mastery, review intervals are 1, 3, 7, 14, then 30 days. A failed review
shortens the interval. `review` returns due reviews separately from remediation
candidates such as weak concepts and unresolved misconceptions.
