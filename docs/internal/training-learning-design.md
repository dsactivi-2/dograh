# Lernpsychologie für Schulungen (kurz)

Leitplanken für `/training` und Voice-Eval — kein Essay.

## Prinzipien

| Prinzip | Umsetzung in UX |
|---------|-----------------|
| **Kurze Module** | Shadow-Quiz 3–5 Fragen; Text-Drill 1–3 Turns; Voice ≤90s |
| **Sofortiges Feedback** | Score + Erklärung pro Quiz-Item; Assertion-Details; Disposition ok/fail |
| **Spaced practice** | Fortschritt % + best score sichtbar; Module filterbar; erneut versuchen |
| **Scaffolding** | Shadow → Text-Drill → Voice (Reihenfolge kommunizieren) |
| **Klare Success-Criteria** | Taxonomy `success_codes` am Modul; Pass-Score (default 70) |
| **Fehler als Lernsignal** | QA-Tags + Assertion fails anzeigen, nicht nur Pass/Fail |
| **Motivation** | Completion %, Ø Best-Score, kleine Wins (Badge bestanden) |

## Lernpfad (empfohlen)

```
1. Shadow   Script lesen + Quiz          (keine LLM-Kosten)
2. Text     Scripted TEXTCHAT drill      (günstig, Assertions)
3. Voice    Kurzes WebRTC-Gespräch       (teuer → Sampling + Guards)
```

Niemals mit Voice starten, wenn Shadow/Text den Skill schon trainieren können.

## Success-Criteria

- Modul trägt `success_codes` (z.B. `XFER`, `SALE`) aus Disposition-Taxonomy
- Text: 80% Assertions + 20% Disposition
- Voice: 70% Assertions + 20% Disposition + 10% QA (wenn vorhanden)
- Pass = score ≥ `pass_score`

## Fehlerkultur

- Falsche Quiz-Antwort → `explanation` anzeigen
- Assertion fail → expected vs actual (kurz)
- QA-Tags (identity, disclosure, DNC…) als Lernhinweise, nicht nur „fail“
- Re-Try erlaubt; best score zählt für Completion

## Cost-aware Learning

- Voice nur Sampling (max 10 Sessions/Org/Stunde)
- Score-existing-run ist kostenlos → Review realer Calls als „listen & score“
- Feature-Flag / Rate-Limit schützt vor versehentlichem Batch

## Anti-Patterns

- Lange ungeführte Voice-Calls ohne Ziel
- Nur Pass/Fail ohne Feedback
- Unbegrenzte Voice-Batch-Evals
- Dual-Role „Agent vs Agent“ (nicht im Repo)
