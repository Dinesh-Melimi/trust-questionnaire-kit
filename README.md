# Trust Questionnaire Kit

At a growing SaaS company the security team is often one person, and security questionnaires block deals. Every customer asks the same 200 questions in different words, answers drift out of date, and nobody tracks what was promised.

This kit drafts answers from a **reviewed answer library** and keeps them honest:

- **Matches reworded questions** ("Is 2FA enforced for personnel?" to the MFA answer) with TF-IDF similarity, in pure Python, so questionnaires and evidence never leave your machine
- **Attaches evidence** (SOC 2 control, policy, report) to every answer
- **Routes to a human** when no approved answer fits or the match is weak, instead of guessing
- **Flags stale answers** not reviewed in the last 12 months
- **Tracks commitments** made to each customer (72-hour breach notice, no AI training on customer data) so sales promises stay true after the deal closes

## Run

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

The library is plain JSON, so it can be kept in Git with review on every change, or exported from a GRC platform such as Vanta or Drata.
