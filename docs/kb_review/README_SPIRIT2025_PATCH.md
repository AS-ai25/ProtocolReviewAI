# SPIRIT 2025 update for ProtocolReviewAI

This package is a review patch for the repository archive supplied on 21 October 2026. It is not a full repository and is not intended for direct upload to the main branch. Paths match the existing repository.

## Changes

- Updated SPIRIT reference codes in deterministic rules, prompts, schema examples and reference parsing.
- Added a structured checklist of SPIRIT 2025 items and a section coverage screening tool.
- Updated the scientific reviewer to receive section screening signals.
- Updated the labeling guide and template for newly created blind labels. Existing historical labels remain unchanged.
- Added focused tests and a list of legacy labeling files to review.
- Included human-readable PDF drafts of the administrative and scientific knowledge bases for professional review.

## How to test

Apply these files over a fresh checkout on a separate branch. Review the diff, then run:

```bash
python -m compileall -q src/protocol_review eval
python -m pytest tests/test_section_coverage.py tests/test_spirit2025_migration.py -q
python -m pytest tests -q
```

## Limitations

The rules still identify only a subset of SPIRIT reporting issues. This patch updates references, but does not validate all 34 items automatically. A missing heading is a screening signal, not grounds for automatic rejection. The scoring decision rules and locked matching semantics were not changed. Study type and item applicability require review. No paid LLM end-to-end execution or full ablation has been completed. Check the current GitHub branch before copying changes to avoid overwriting Amir's newer work.
