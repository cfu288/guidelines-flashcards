# Anki Cloze Cards — Key Concepts & Best Practices

A distilled reference for writing cloze cards that actually stick. Built on Wozniak's *20 Rules of Formulating Knowledge* and the AnKing/med-school community's conventions.

---

## The one principle that matters most

**Minimum information principle:** one card = one atomic fact = one distinct memory.

Simple memories refresh uniformly at each review. Complex, multi-fact cards break down — you forget the hardest sub-item repeatedly, the card comes back at punishingly short intervals, and you end up recalling only part of it. That failure pattern is exactly how a card becomes a **leech**.

> If a card is hard, it's usually not too hard to learn — it's too *big*. Split it.

---

## Foundational rules (Wozniak)

- **Understand before you memorize** — never memorize what you don't understand.
- **Learn before you memorize** — get the big picture first, then make cards.
- **Build on the basics** — simple, well-formed fundamentals before complex detail.
- **Stay atomic** — the minimum information principle, above.
- **Avoid sets & enumerations** — lists are the hardest thing to retain. Break them apart, or use overlapping clozes / mnemonics.
- **Combat interference** — make similar-but-different items clearly distinct so they don't blur together.
- **Cloze deletion is the shortcut** — it's the fastest, most effective way to satisfy all of the above and turn textbook prose into spaced-repetition material.

## The two engines underneath

- **Active recall** — retrieve the answer from memory; don't reread.
- **Spaced repetition** — review at expanding intervals, timed to just before you'd forget.

---

## Cloze cards: do / don't

**Do**
- Test **one idea** per card.
- Blank only the **load-bearing concept** (the thing you're actually trying to learn).
- Keep enough surrounding context to **cue** the answer.
- Limit to **~2–3 deletions max** per card.
- Use **images / image occlusion** for visual or spatial material.

**Don't**
- **Over-delete** — hiding too much overwhelms and becomes untestable.
- **Strip context** until the blank is unanswerable.
- Phrase passively so you're testing **recognition, not recall**.
- **Leak the answer** — watch for grammar tells ("a"/"an") or a blank whose length mirrors the answer.

---

## Anki cloze mechanics

- `{{c1::...}} {{c2::...}} {{c3::...}}` → **three separate cards**, each tested independently.
- Reuse the **same number** (hold **Alt/Option** while clozing) → those blanks are hidden **together on one card**.
- Use **separate numbers** for facts you want tested independently; use the **same number** only when the blanks make sense solely together.
- **Hints:**
  - Partial-word cloze — selecting `anberra` shows `C[…] was founded in 1913`.
  - Custom hint syntax — `{{c1::Canberra::city}}` displays the hint "city".
- **Overlapping clozes** (Cloze Overlapper add-on) — for ordered, sequential, or integrated information where the *order* matters.

---

## AnKing workflow

- Cloze-heavy, **tag-organized** (by organ system / exam) rather than subdecks; built on the legacy Zanki deck and now maintained live via **AnkiHub**.
- **Unsuspend by topic** — only unsuspend cards matching your current lectures. Don't dump the whole deck into your queue.
- **Rewrite leeches** into atomic cards instead of spamming "Again."
- **Build redundancy** — test the same fact from multiple angles/directions (you usually learn it in only one).
- **Enable FSRS** — the modern scheduler cuts the total number of reviews needed.
- **~80–100 new cards/day** is a common target, but **completing daily reviews matters more** than new-card volume.

---

## Worked example

**Bad — bloated, everything hidden at once (all `c1`):**

> `{{c1::Lisinopril}}` is an `{{c1::ACE inhibitor}}` for `{{c1::hypertension}}` that causes `{{c1::cough}}` and `{{c1::hyperkalemia}}`.

One card hiding the entire sentence — no context left to cue anything, and you can "pass" it knowing only one piece.

**Better — atomic, each fact cued by real context:**

> - `{{c1::Lisinopril}}` is an ACE inhibitor used for hypertension.
> - Lisinopril is an `{{c1::ACE inhibitor}}`.
> - A class side effect of ACE inhibitors is a dry `{{c1::cough}}`, mediated by `{{c2::bradykinin}}`.
> - ACE inhibitors can cause `{{c1::hyperkalemia}}` — monitor potassium.

Each card tests **one** thing, with enough context to cue the answer but not reveal it.

---

## TL;DR

One card, one fact you already understand. Blank only the key concept. Give enough context to **cue** but not **reveal**. Keep deletions few, keep cards atomic, and trust your reviews over your new-card count.
