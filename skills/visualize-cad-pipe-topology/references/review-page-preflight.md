# Review page data before publication

Call `scripts/review_page_preflight.py` or its `validate_dataset(data, page_root)`
before replacing `cases.js`. Review contexts consumed by `renderSection` need
`title`, a local `path`, and a `locators` array; each locator needs a `label`.
An absent optional SVG must not be confused with missing required locators.
Validate displayed Pair SHA256, safe media paths, unique question IDs, options
and readable Unicode. Reject malformed data before it can interrupt the page;
do not silently remove a section or retire a question to make validation pass.

Derive the progress banner with `coverage_summary(coverage, rows)` from the same
versioned row inventory used by the detailed floor page. Mapping, native
candidate attributes and published attributes are separate counters. An absent
candidate counter stays unknown. Keep the supplied floor identity explicit.
This check neither verifies CAD topology nor accepts a human answer.

```
python review_page_preflight.py --dataset PAGE/cases.js --page-root PAGE --coverage RUN/coverage.json --rows RUN/all-plan-edge-coverage.json --output preflight.json
```

Run `test_review_page_preflight.py`, existing review-workflow/archive tests and
an actual isolated-browser check showing every pending and archived question.
Then inspect both the large native locator image and local Pair in the page.
