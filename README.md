# Trust Questionnaire Kit

Compliance automation for a fast-growing AI company: answer enterprise security questionnaires quickly **without ever sending a "Yes" that is false today**, keep SOC 2, ISO 27001 and HIPAA evidence collected all year, and know what to fix first.

**Live sample report:** https://dinesh-melimi.github.io/trust-questionnaire-kit/

It is built around a voice AI company, where call audio and transcripts can contain PHI, go to speech and LLM vendors, and must be deleted on a promised schedule.

## Audit readiness in one command

```bash
python -m tqk.cli audit --env samples/env.json --controls samples/controls.json --retention-days 30
```

```
3/12 controls passing; 14 findings
  P0 AC-1  leo@acmevoice.ai can reach production without MFA
  P0 AC-2  sam@acmevoice.ai left 2026-11-20 (5 days ago) and is still active in Okta with aws-prod, github, call-console
  P0 EN-2  call-exports-temp is public and contains recordings
  P0 VD-1  Analytics warehouse receives transcripts (may contain PHI) without a BAA
  ...
  P1 AC-3  review said revoke nina@acmevoice.ai from call-console but access is still there (approval is not proof of removal)
  P2 VM-1  CVE-2026-0450 past SLA but has an approved exception until 2027-01-31
Questionnaire: 3/10 ready, 5 held because a linked control is failing
Retention (30 days): Not fully today. ... 3 location(s) keep data longer.
```

What it does:

- **One control set, three frameworks.** 12 controls (MFA, offboarding, access reviews, recording access, encryption, public buckets, logging, retention, vendor BAAs, AI training opt-in, code review, vuln SLAs), each mapped to SOC 2, ISO 27001 and HIPAA. One test and one piece of evidence covers all three.
- **Triage, not a wall of red.** Findings are sorted into P0 (customer data exposed right now), P1 (a real gap, ticket it), and P2 (noise or an accepted risk with an owner and an expiry date). When you walk into 25 failing checks, this is the order to work them in.
- **Questionnaires stay honest.** Library answers are linked to controls. If MFA or retention is failing today, the matching questionnaire answer is put on hold instead of auto-filled.
- **"Is all our data deleted within 30 days?"** answered from what the systems actually do: primary storage, backups, temp exports and every sub-processor, not just the policy.
- **Access reviews that prove removal.** Each manager gets a short list of only their people. Leavers and service accounts are flagged before the review, and a revoke counts as done only when the identity provider shows the access is gone.
- **Evidence auditors can sample.** Every run writes `evidence/<control>/<date>.json` with a SHA-256 manifest, so a Type II period has evidence for the whole window.

`samples/env.json` is a simulated export of Okta, AWS, GitHub, HR and the vendor register for a fictional company. In real use each section comes from that system's API or from a GRC platform such as Vanta or Drata.

## Questionnaire drafting

At a growing SaaS company the security team is often one person, and security questionnaires block deals. Every customer asks the same 200 questions in different words, answers drift out of date, and nobody tracks what was promised.

This kit drafts answers from a **reviewed answer library** and keeps them honest:

- **Matches reworded questions** ("Is 2FA enforced for personnel?" to the MFA answer) with TF-IDF similarity, in pure Python, so questionnaires and evidence never leave your machine
- **Attaches evidence** (SOC 2 control, policy, report) to every answer
- **Routes to a human** when no approved answer fits or the match is weak, instead of guessing
- **Flags stale answers** not reviewed in the last 12 months
- **Tracks commitments** made to each customer (72-hour breach notice, no AI training on customer data) so sales promises stay true after the deal closes

### Run

```bash
python -m tqk.cli --library samples/library.json --questions samples/questionnaire.csv --customer "Acme CPA" --out answered.csv
```

```
5/7 answered from the library; 2 need a human
  [3] NEEDS REVIEW: answer last reviewed 2025-03-10 (score 0.64): Has a third-party pen test been performed in the last 12 months?
  [7] NEEDS REVIEW: no approved answer (score 0.0): Do you maintain a software bill of materials (SBOM) for your application?
Commitments made to Acme CPA:
  - Share the annual pentest summary under NDA on request
  - Notify within 72 hours of a confirmed incident affecting customer data
  - Do not use customer data to train AI models
```

## Keep the KB growing

```bash
python -m tqk.cli --library samples/library.json --questions samples/questionnaire.csv \
  --drafts drafts.json --owner security-team --kb-report
```

```
1 draft KB entry written to drafts.json (owner: security-team)
Review queue (next 30 days): 1
  VM-01 OVERDUE 2026-03-10
SOC 2 coverage: CC6(2)
```

- **Draft entries**: every question the library could not answer becomes a draft KB entry with an owner, so the next RFP reuses a reviewed answer instead of starting over
- **Review queue**: answers expiring in the next 30 days, so reviews happen before a deal is waiting on them
- **SOC 2 coverage**: which Trust Services Criteria have approved answers

The library is plain JSON, so it can be kept in Git with review on every change, or exported from a GRC platform such as Vanta or Drata.
