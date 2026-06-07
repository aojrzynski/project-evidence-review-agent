# Safety and authority boundaries

Project Evidence Review Agent prepares review material from local project files. It does not approve projects or replace human review.

## What local project text may include

Project files may include requirements, notes, risks, decisions, testing details, release summaries, configuration notes, operational concerns, or other internal project text.

Only run the tool on material you are allowed to process locally and, in full mode, allowed to send to the configured LLM provider.

## Synthetic examples should not contain secrets

Example packs should be synthetic and should not include real secrets, credentials, tokens, private keys, sensitive personal data, or confidential production details.

Even local artifacts can be copied, committed, or shared by mistake. Keep examples safe.

## What the tool may include in artifacts

The tool may include bounded excerpts from supported local project documents. This is necessary because evidence review depends on citations. A reviewer needs to see the cited text, not just a file name.

This differs from workflows that avoid copying dataset content into artifacts. For this project, bounded excerpts are acceptable only because they are:

- supplied by the user;
- local to the run;
- limited to selected chunks;
- tied to source IDs and evidence IDs;
- written to user-controlled output files;
- used for review support, not broad publication.

Do not treat generated artifacts as automatically safe to share. They may contain excerpts from the input files.

## Why selected excerpts are bounded

Bounded excerpts keep review focused. They help a human check the exact text behind a claim. They also limit what the LLM can see in full mode.

A bounded excerpt is still sensitive if the source text is sensitive. The boundary reduces scope; it does not remove confidentiality concerns.

## What the LLM sees

In full mode, the LLM sees the content recorded in `llm_safe_review_context.json`:

- the review question;
- selected evidence chunks;
- allowed evidence IDs;
- source metadata needed for citation;
- instructions and authority boundaries.

The LLM does not receive unselected local files from this workflow. The workflow does not use web search, file upload tools, function calling, or streaming tool calls.

## What the LLM must not do

The LLM must not:

- answer from memory;
- invent source IDs or evidence IDs;
- cite whole sources instead of evidence chunks for supported claims;
- make approval decisions;
- decide readiness;
- approve go-live;
- certify compliance, privacy, security, legal status, or governance;
- replace a human reviewer.

## Validation boundaries

Validation checks structure, citation references, required fields, allowed statuses, and authority language.

Validation does not prove that the project evidence is true. It does not prove that the supplied files are complete. It does not certify compliance. It does not decide readiness.

Failed validation blocks successful downstream report assembly because a failed artifact is safer than a polished but unsafe answer.

## Authority boundaries

Output is review material, not approval.

The tool cannot decide that a project is ready. It cannot approve go-live. It cannot certify compliance, security, privacy, legal status, or governance.

Human review remains final.

## Forbidden decisions and verdicts

The workflow must not produce:

- project approval;
- readiness approval;
- go-live approval;
- compliance certification;
- security certification;
- privacy certification;
- legal verdicts;
- governance verdicts;
- final contradiction findings;
- proof that missing evidence does not exist elsewhere.

## Review material, not approval

Use the artifacts to organize a human review conversation. Do not use them as a substitute for the responsible review process.
