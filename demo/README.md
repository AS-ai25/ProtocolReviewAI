# One-minute demo (Checkpoint 2)

Seven auto-advancing screens, Hebrew captions, no narration, built from a saved full-system run so that every
finding, quote, page and verdict on screen is real output (`outputs/abl-agents_full-nct04084990-20261029-205913`).

```
python eval/protocols/fetch_protocols.py      # once: the protocol PDFs (not committed)
python demo/build_demo.py                     # writes demo/index.html (not committed: embeds a page of the protocol)
```

Recording (about 65 s):

1. Open `demo/index.html` in Chrome or Edge, press **F11** (full screen).
2. Start the screen recorder (Windows: **Win+G** → record, or OBS). No microphone needed.
3. Press **Space** - the screens advance by themselves (10-12 s each) and the bar at the bottom shows the time left.
4. When the last screen is reached the bar fills and the page stops; stop the recorder.

Keys: Space start / pause · ← → previous / next screen · R restart. To use another protocol or run:
`python demo/build_demo.py --case <case_id> --stamp <stamp>`.

Screens: 1 what the system is (four agents) · 2 the input protocol (first page, registry record) · 3 administrative
gate (checklist findings, RETURNED_ADMIN, the email) · 4 scientific reviewer (findings with page, quote, SPIRIT code) ·
5 critic (verdicts, unverified routed to a human, critic-raised issues) · 6 the final report PDF · 7 the Checkpoint 2
numbers and the tiered recommendation.
