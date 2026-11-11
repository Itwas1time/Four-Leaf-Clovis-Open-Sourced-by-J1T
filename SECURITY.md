# Security policy

Run Clovis on `127.0.0.1` with debug disabled. It is a single-user local app:
there is no account system, institutional access control or reviewed public
deployment. (The former FastAPI map demo and citizen report API were removed on
11 November 2026.)

The server enforces local hosts and origins, a 2 MB request limit, strict JSON
with finite numbers and valid Unicode, and extra candidate/geometry bounds.

The resident workflow accepts a public Census place code and fixed history
choices, with no address or arbitrary URL input. An explicit online option
uses a fixed HTTPS Macrostrat endpoint, disables redirects, bounds response
size and time, and prevents concurrent request queues. Reports and provider
responses remain in bounded memory caches. Downloads use server-owned random
tokens, expire after an hour, and must match current inputs. See
[resident data provenance and privacy](docs/RESIDENT_CONTEXT.md).

Public nearby queries use the rounded center. Longitude rounding uses the
public latitude bucket. Rounded coordinates still do not guarantee anonymity
or make sensitive heritage information safe to share. Use synthetic data for
public tests and omit personal information and sensitive locations.

## Publication gates

This edition excludes credentials, personal account references and uncleared acquired spatial datasets. Keep local secrets, photos, logs and imported data outside Git. Review licensing and sensitivity before sharing any new dataset. The MIT license covers project code.

Internet hosting needs authentication, authorization, per-user isolation,
TLS, request/time/worker limits, retention rules, secret-free logs, provider
consent, and a data stewardship review. Review external tiles/CDNs. Configure
explicit production hosts/origins rather than weakening local defaults; use
a production server rather than Flask's development server.

## Report vulnerabilities privately

Use private vulnerability reporting on the repository's
[Security page](https://github.com/Itwas1time/four.leaf.clovis/security) when
enabled. Otherwise request a private channel from the owner. Never publish
credentials, private photographs, or sensitive coordinates in an issue.
Include the commit, synthetic reproduction, expected/actual behavior, and
impact. Maintainers should triage, rotate compromised credentials, add a
regression, and release the fix before disclosing exploit details.

Passing tests and zero advisory findings describe the tested requests and
versions. They do not guarantee the absence of vulnerabilities. Maintainers verify releases and dependency changes privately, including
tests, installation checks, secret scans and dependency audits.
