# Framework notes: selecting one test and spotting a false red

| Stack | Select one test | Zero-match behavior |
|-------|-----------------|---------------------|
| pytest | `pytest path::test_name -q` | nonzero if node id not found |
| jest | `npx jest path -t "name"` | exit 0 if nothing matched with `--passWithNoTests`; otherwise 1 |
| vitest | `npx vitest run path -t "name"` | check summary |
| JUnit (Maven) | `mvn -q test -Dtest=Class#method` | may exit 0 if none match with `-DfailIfNoTests=false` |
| JUnit (Gradle) | `gradle test --tests 'Class.method'` | fails if no tests match |
| go | `go test ./pkg -run '^TestName$'` | prints `no tests to run`, exit 0 |
| cargo | `cargo test name` | exit 0 with 0 tests run |
| rspec | `rspec path:LINE` | nonzero if not found |

Always read the tail output for "1 passed" or equivalent. A RED caused by a compile error, import error, or missing fixture is a false red: fix the test until it fails on an assertion about the behavior.
