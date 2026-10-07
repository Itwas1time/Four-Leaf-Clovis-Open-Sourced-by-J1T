# Security policy

Run the maintained planner on `127.0.0.1` with debug disabled. The FastAPI map
demo and citizen report API are experimental local tools. They provide no
account system, institutional access controls, or reviewed public deployment.

Servers enforce local hosts and origins, a 2 MB request limit, strict JSON,
and extra candidate/geometry bounds. The citizen API limits submissions by
connection address and reporter ID and stores at most 500 reports. Classifier
access is disabled by default and restricted to relative PNG/JPEG references
inside a server-approved photo directory, with a 5 MB image limit. Enabling it
sends approved image bytes to the configured provider; obtain consent first.
DOCX ingestion bounds XML size and rejects entity declarations.

Public nearby queries use the rounded center. Longitude rounding uses the
public latitude bucket. Rounded coordinates still do not guarantee anonymity
or make sensitive heritage information safe to share. Use synthetic data for
public tests and omit personal information and sensitive locations.

## Publication gates

This edition excludes credentials, personal account references and acquired spatial datasets. Keep local secrets, photos, logs and imported data outside Git. Review licensing and sensitivity before sharing any new dataset. The MIT license covers project code.

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
versions. They do not guarantee the absence of vulnerabilities. Rerun CI and dependency audits on releases and dependency changes.
