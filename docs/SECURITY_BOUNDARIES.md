# Security Boundaries

OpsGuard AI is designed to demonstrate safer agentic operations patterns, not autonomous infrastructure control.

## Core Boundary

The system can investigate, retrieve context, summarize evidence, run safe mock tools, and draft recommendations.

The system cannot:

- execute real infrastructure commands
- drain nodes, cancel jobs, block users, isolate systems, or disable services
- call arbitrary shell commands
- bypass human approval
- treat retrieved documents or logs as trusted instructions

## Why Dangerous Actions Are Blocked

Operational AI can sound decisive at exactly the wrong moment. In real environments, low-confidence or poisoned evidence can lead to destructive recommendations. OpsGuard AI therefore keeps dangerous actions behind an explicit approval boundary.

Blocked tool examples:

- `cancel_job`
- `drain_node`
- `block_user`
- `isolate_node`
- `disable_service`

These actions return blocked responses and can generate audit or safety evidence, but they do not execute.

## Trust Model

The system treats these as untrusted by default:

- retrieved documents
- log content
- tool outputs
- suspicious or policy-shaped text inside evidence

Even trusted documents are treated as data for grounding, not as instructions that override system policy.

## Human Approval Model

The agent workflow always ends at a human-review boundary.

That means:

- recommendations can be generated
- ticket drafts can be created internally
- dangerous or disruptive actions remain recommendation-only
- final approval must come from a human operator

## Prompt-Injection Boundary

The system includes lightweight detection at the RAG and watchdog layers for patterns such as:

- system override text
- “ignore previous instructions”
- secret-exfiltration language
- unsafe tool redirection
- shell-command style directives

Suspicious evidence lowers confidence, creates findings, and can force `require_human_approval` or `block`.

## Demo-Only Scope

This repository is a deterministic local demo.

It intentionally does not claim:

- production hardening
- real SOC integration
- deployment security review
- live containment automation
- external compliance certification

## Why This Still Matters

Even as a demo, these boundaries are the point of the project. The value is showing how to architect AI systems that:

- stay grounded
- keep audit trails
- measure uncertainty
- resist unsafe escalation
- remain explainable to humans
