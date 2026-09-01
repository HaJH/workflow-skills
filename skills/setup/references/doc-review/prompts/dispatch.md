# Dispatch Templates

Fill the `<...>` slots in each section's template block and pass the result as the subagent's
**entire prompt**. How to do the work lives in the agent definition, so **the prompt you fill in**
says only what to look at.

`subagent_type` is required on every dispatch — it pins the model and the effort. Only the
coherence reviewer additionally passes `model` to override it.

---

## Section Layer — `doc-section-reader`, one per section, all in one message

````
Below is a single section cut out of a <one line naming the kind of document> document. The document's other sections, the project context, and how it came to be written are deliberately withheld. Judge from this text alone.

## <section title>

<the section body verbatim - including any nested ###>
````

Copy the section body from the document exactly, code blocks inside it included. Never shorten it,
fix it, or annotate it. **When the section body contains a code block, open the wrapping fence with
more backticks than it uses** — at equal length the section's own fence closes the wrapper, the
rest spills outside the prompt, and the subagent judges a truncated section.

The document's opening counts as one section and uses the same template, with the `## <section
title>` line replaced by `## <document title>` and the body slot holding the text before the first
`##`.

**Never ask for a scale** — do not build a grade slot such as clear / mostly clear / unclear into
the prompt. The one "Biggest problem" slot in the agent definition carries the verdict.

---

## Coherence Layer — `doc-coherence-reviewer`, two (one opus, one second model)

Dispatch **twice** with the same prompt. Name `model: opus` on one and the second model on the
other. This is not two models doing different things but the same thing read twice, so the prompt
is identical.

```
Under review: <absolute path of the document>
Authoring policy: {PROJECT_PATH}/docs/authoring-policy.md
Read alongside: <absolute paths of the link targets without which the document's instructions do not hold - drop this line when there are none>

How it came to be written is not given. Review in the order of perspectives your definition sets and report in the format it defines.
```

Never add what the document is trying to do or why it was written this way. The document speaks
for itself. When the document under review **is** the authoring policy, the two paths become the
same — pass both lines carrying that same path.

---

## Synthesis — `doc-review-synthesizer`, one, after every reviewer has finished

Collect the reviewers' output verbatim into
`docs/reports/doc-review/<basename>.reviews.md`, then:

```
Document under review: <absolute path of the document>
Review-results file: {PROJECT_PATH}/docs/reports/doc-review/<basename>.reviews.md
Repo root: {PROJECT_PATH} - the range to Grep for references behind section delete and merge suggestions

Read the review-results file and the document under review in full, merge the reviewers' findings into one defect list, and report in the format your definition sets.
```

The shape of the review-results file:

```
# <basename> review results

## Sections

### <section title>
<doc-section-reader output verbatim>

## Whole Document

### Coherence A
<opus reviewer output verbatim>

### Coherence B
<second-model reviewer output verbatim>
```

Include a subheading only for a coherence reviewer that was actually dispatched, and when none was,
leave the `## Whole Document` heading out entirely.
