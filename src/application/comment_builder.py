"""Builds human, specific, actionable review comments for AI Quality Gate.

Every comment produced here should read like a senior maintainer wrote it —
not a bot scoring your submission. The goal is to help contributors improve,
not to make them feel rejected.
"""

from __future__ import annotations

from src.domain.entities import AnalysisResult, ContributionContext, Signal
from src.domain.enums import ContributionType, SignalType
from src.infrastructure.config.schema import AppConfig

__all__ = ["CommentBuilder"]


# Maps signal pattern labels to plain-English explanations
# that a contributor can actually act on.
_SIGNAL_EXPLANATIONS: dict[str, str] = {
    # AI vocabulary
    "delve": "only appears in AI output; real bugs are described concretely",
    "leverage": "almost never used in genuine bug reports or feature requests",
    "holistic": "AI filler — what specifically needs to change?",
    "tapestry": "AI metaphor that adds no information",
    "seamless": "vague adjective with no measurable meaning",
    "robust": "vague — what failure cases does this handle?",
    "pivotal": "AI superlative; the PR should speak for itself",
    "meticulous": "AI intensifier; describe what was actually done",
    "commendable": "AI compliment pattern; opens or closes AI-generated text",
    "comprehensive": "vague — list what is actually covered",
    "intricate": "AI filler; describe the actual complexity if relevant",
    "paramount": "AI intensifier with no concrete meaning",
    "noteworthy": "AI intensifier; what is the actual note?",
    "groundbreaking": "AI superlative; let the feature speak for itself",
    "foster": "bureaucratic AI verb; be specific",
    "facilitate": "bureaucratic AI verb; be specific",
    "endeavor": "AI formality; use plain language",
    "multifaceted": "AI complexity descriptor with no substance",
    "nuanced": "AI qualifier; explain the nuance specifically",
    "streamline": "AI buzzword; describe the actual change",
    # AI phrasing
    "it's worth noting": "AI hedge phrase — state the point directly",
    "I'd be happy to": "AI assistant opener — not typical for a bug report",
    "hope this helps": "AI assistant closer — not typical for issue/PR descriptions",
    "here's a breakdown": "AI report opener — structure is fine, the phrase isn't",
    "feel free to": "AI politeness filler",
    "let me know if you": "AI assistant closer",
    "in conclusion": "AI essay closer — this isn't an essay",
    "in summary": "AI summariser — end with the summary, drop the label",
    "this ensures that": "AI passive construction; state what it does directly",
    "by doing so": "AI connector with no specificity",
    "overall,": "AI summariser opener — often precedes a generic conclusion",
    "it is important to note": "AI hedge; state the important thing directly",
    "plays a crucial role": "AI filler phrase",
    "furthermore": "academic connector; one sentence per thought",
    "additionally": "AI padding; combine or drop",
    # Structural
    "numbered-list-heavy": "AI output often lists every point as a numbered step; genuine descriptions mix prose and lists",
    "header-heavy": "dense header structure on a short description is an AI formatting signature",
    "uniform-paragraph-length": "every paragraph is nearly the same length — AI tends to pad paragraphs to fill expected length",
    "summary-conclusion": "ends with a summary section; AI closes with a wrap-up that real contributors don't write",
    "excessive-emoji": "heavy emoji use in technical content is an AI writing pattern",
    "bullet-symmetry": "all bullet points start with the same verb form — an AI list-generation signature",
    "repetitive-structure": "consecutive sentences follow identical patterns; AI tends to repeat its own sentence templates",
    "low-substance": "high word count with low information density — many filler words relative to content words",
    # Hallucination
    "nonexistent-api-refs": "references a very specific API method that likely does not exist",
    "version-hallucination": "mentions very specific version numbers that may not be accurate",
    "fake-references": "mentions documentation without providing an actual link",
    # Code patterns
    "excessive-comments": "every line has an inline comment — AI generates explanatory comments for obvious code",
    "boilerplate-heavy": "high ratio of import/boilerplate lines to logic; AI scaffolding often looks like this",
    "todo-placeholder": "multiple TODO/PLACEHOLDER markers suggest the implementation is not complete",
    "generic-variable-names": "high density of generic names like `data`, `result`, `handleClick`",
}


# Maps quality check names to specific, actionable next-step messages.
_QUALITY_ADVICE: dict[str, str] = {
    "title-length": "Aim for 20-72 characters. Enough to understand the issue without opening it.",
    "title-specificity": (
        "Vague titles like 'bug' or 'not working' make it impossible to triage without reading the full body. "
        "Include the component, the symptom, and ideally the trigger — e.g. "
        "'TypeError in login form when email field is empty'."
    ),
    "title-convention": (
        "Use conventional commit format: `type(scope): description`. "
        "For example: `fix(auth): handle null email on login`, `feat(api): add /v2/search endpoint`. "
        "Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore."
    ),
    "body-present": (
        "This submission has no description. Before assigning or triaging, maintainers need to understand: "
        "what is the problem, what have you tried, and what outcome do you expect?"
    ),
    "body-length": (
        "The description is too brief to act on. Add: what were you doing, what did you expect, what happened instead."
    ),
    "reproduction-steps": (
        "Add numbered reproduction steps. Without them, this bug cannot be reproduced or verified as fixed. "
        "Format:\n"
        "1. Go to `/login`\n"
        "2. Leave the email field empty\n"
        "3. Click Submit\n"
        "**Expected:** Validation error message\n"
        "**Actual:** Page crashes with TypeError"
    ),
    "environment-info": (
        "Add environment details: OS, browser (with version), Node/Python version, and any relevant package versions. "
        "Bugs that only reproduce on specific versions need this to be investigated."
    ),
    "code-snippets": (
        "Paste the relevant code, error output, or stack trace as a fenced code block. "
        "This is the fastest way to help maintainers understand the problem."
    ),
    "screenshots": "Attach a screenshot or screen recording for any visible UI issue.",
    "search-evidence": (
        "Have you searched existing issues? If this is a duplicate, it should be linked. "
        "If you searched and found nothing, mention that — it helps maintainers know you checked."
    ),
    "pr-description": (
        "The description should answer two questions:\n"
        "1. **What** changed? (a brief summary of the diff)\n"
        "2. **Why** does this change need to happen? (the motivation or bug it fixes)\n"
        "Without both, reviewers cannot assess whether the approach is correct."
    ),
    "linked-issue": (
        "Link this PR to the issue it resolves with `Closes #N` or `Fixes #N`. "
        "This auto-closes the issue when the PR merges and makes the review thread navigable."
    ),
    "test-mention": (
        "Describe how this change was tested. "
        "If you added automated tests, mention which file and what cases they cover. "
        "If you tested manually, describe the steps and environment."
    ),
    "breaking-change": (
        "This PR removes or changes a public API. Add a **BREAKING CHANGE** section to the description "
        "explaining what changed, what breaks, and how consumers should migrate."
    ),
    "diff-size": (
        "This PR is very large. Large PRs are harder to review thoroughly, more likely to introduce regressions, "
        "and slower to get through the review queue. "
        "Consider splitting into smaller, independently-mergeable PRs."
    ),
    "tests-included": (
        "The diff touches source files but includes no test changes. "
        "If the behaviour is already covered by existing tests, mention which test file(s). "
        "If it is not covered, this is the right time to add tests."
    ),
    "single-purpose": (
        "This PR touches many unrelated areas. Single-purpose PRs are easier to review, revert if needed, "
        "and attribute in the changelog. Consider splitting by concern."
    ),
}


class CommentBuilder:
    """Builds human-readable, specific review comments.

    Comments are written to help contributors understand *why* their submission
    was flagged and *exactly what* to do about it — not just that a score is low.
    """

    def build(
        self,
        context: ContributionContext,
        result: AnalysisResult,
        config: AppConfig,
    ) -> str:
        """Build the full review comment for a contribution.

        Chooses the right comment shape based on what was detected and
        how severe it is.
        """
        is_pr = context.contribution_type == ContributionType.PULL_REQUEST
        subject = "pull request" if is_pr else "issue"

        ai_flagged = result.ai_score >= config.ai.warn
        quality_flagged = result.quality_report.score < config.quality.minimum

        parts: list[str] = []

        if ai_flagged:
            parts.append(self._ai_section(result, config, subject))

        if quality_flagged:
            parts.append(self._quality_section(result, context, subject))

        if not parts:
            return ""

        header = self._header(result, config, ai_flagged, quality_flagged)
        body = "\n\n---\n\n".join(parts)
        footer = self._footer(ai_flagged, quality_flagged, context)

        return f"{header}\n\n{body}\n\n{footer}"

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _header(
        self,
        result: AnalysisResult,
        config: AppConfig,
        ai_flagged: bool,
        quality_flagged: bool,
    ) -> str:
        ai_bar = self._score_bar(result.ai_score, invert=False)
        q_bar = self._score_bar(result.quality_report.score, invert=True)

        rows = []
        if ai_flagged:
            rows.append(f"| AI Detection | {ai_bar} {result.ai_score}/100 ({result.ai_confidence.value} confidence) |")
        if quality_flagged:
            rows.append(
                f"| Quality | {q_bar} {result.quality_report.score}/100 (Grade {result.quality_report.grade.value}) |"
            )

        table = "| Check | Score |\n|-------|-------|\n" + "\n".join(rows)
        return f"## AI Quality Gate\n\n{table}"

    def _ai_section(self, result: AnalysisResult, config: AppConfig, subject: str) -> str:
        """Build the AI detection section with human-readable signal explanations."""
        top_signals = result.ai_signals[:8]

        if result.ai_score >= config.ai.fail:
            opener = (
                f"This {subject} is very likely AI-generated "
                f"({result.ai_score}/100, {result.ai_confidence.value} confidence). "
                "The detected patterns are listed below."
            )
        else:
            opener = (
                f"This {subject} has patterns commonly found in AI-generated text "
                f"({result.ai_score}/100). It may be AI-assisted — "
                "if so, please review for accuracy before submitting."
            )

        if not top_signals:
            return f"### AI Content\n\n{opener}"

        signal_lines = self._format_signals(top_signals)
        signals_block = "\n".join(signal_lines)

        note = (
            "\n\n> If this is a false positive, a maintainer can dismiss this check. "
            "The signal list above explains what triggered it."
        )

        return f"### AI Content\n\n{opener}\n\n**Signals detected:**\n{signals_block}{note}"

    def _quality_section(
        self,
        result: AnalysisResult,
        context: ContributionContext,
        subject: str,
    ) -> str:
        """Build the quality section with specific, actionable advice per failed check."""
        failed = result.quality_report.failed_checks
        partial = result.quality_report.partial_checks

        if not failed and not partial:
            return ""

        score = result.quality_report.score

        if score < 20:
            opener = (
                f"This {subject} is missing most of the information needed to act on it "
                f"(quality score: {score}/100). Please see below."
            )
        elif score < 40:
            opener = (
                f"This {subject} needs a few important additions before it can be reviewed "
                f"(quality score: {score}/100)."
            )
        else:
            opener = (
                f"This {subject} is almost there — a couple of gaps make it harder to review "
                f"(quality score: {score}/100)."
            )

        items: list[str] = []
        for check in failed + partial:
            advice = _QUALITY_ADVICE.get(check.name, check.detail)
            label = "Missing" if check.score == 0 else "Partial"
            items.append(f"**{label} — {self._friendly_name(check.name)}**\n{advice}")

        items_text = "\n\n".join(items)
        return f"### What's Needed\n\n{opener}\n\n{items_text}"

    def _footer(self, ai_flagged: bool, quality_flagged: bool, context: ContributionContext) -> str:
        is_pr = context.contribution_type == ContributionType.PULL_REQUEST
        parts: list[str] = []

        if ai_flagged and quality_flagged:
            parts.append(
                "Once you've revised the description, this check will re-run automatically "
                "when you edit the " + ("PR." if is_pr else "issue.")
            )
        elif quality_flagged:
            parts.append(
                "Edit the "
                + ("PR description" if is_pr else "issue body")
                + " and this check will re-run automatically."
            )
        elif ai_flagged:
            parts.append("If you wrote this yourself, don't worry — the check can be dismissed by a maintainer.")

        parts.append(
            "_[AI Quality Gate](https://github.com/AbdullahBakir97/ai-quality-gate) "
            "— automated contribution quality enforcement_"
        )
        return "\n\n".join(parts)

    def _format_signals(self, signals: list[Signal]) -> list[str]:
        """Format signals as human-readable bullet points."""
        lines: list[str] = []
        seen_types: set[str] = set()

        # Normalise the explanation map once for case-insensitive lookup so
        # we don't re-do the work for every signal.
        normalised = {k.lower(): v for k, v in _SIGNAL_EXPLANATIONS.items()}

        for signal in signals:
            key = signal.pattern.lower()
            explanation = normalised.get(key, signal.description or signal.pattern)
            type_label = self._signal_type_label(signal.type)

            # Don't repeat the same type label for every signal
            if signal.type.value not in seen_types:
                seen_types.add(signal.type.value)

            count_note = f" (x{signal.occurrences})" if signal.occurrences > 1 else ""
            lines.append(f"- `{signal.pattern}`{count_note} — {explanation} _{type_label}_")

        return lines

    @staticmethod
    def _signal_type_label(signal_type: SignalType) -> str:
        return {
            SignalType.AI_VOCABULARY: "[word choice]",
            SignalType.AI_PHRASING: "[phrase]",
            SignalType.STRUCTURAL: "[structure]",
            SignalType.CODE: "[code pattern]",
            SignalType.HALLUCINATION: "[hallucination]",
            SignalType.META: "[meta]",
        }.get(signal_type, "")

    @staticmethod
    def _score_bar(score: int, invert: bool = False) -> str:
        """Return a simple emoji indicator for a score."""
        good = score >= 70
        ok = score >= 40
        if invert:
            # For quality: high score = good
            if good:
                return "🟢"
            if ok:
                return "🟡"
            return "🔴"
        else:
            # For AI: high score = bad
            if score >= 70:
                return "🔴"
            if score >= 40:
                return "🟡"
            return "🟢"

    @staticmethod
    def _friendly_name(check_name: str) -> str:
        """Convert a check name like 'reproduction-steps' to 'Reproduction Steps'."""
        return check_name.replace("-", " ").title()
