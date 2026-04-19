"""Shared test fixtures for AI Quality Gate."""

import pytest

from src.analyzers.patterns import register_default_patterns
from src.analyzers.patterns.registry import PatternRegistry
from src.domain.entities import ContributionContext
from src.domain.enums import ContributionType


@pytest.fixture
def pattern_registry() -> PatternRegistry:
    """Fresh pattern registry with all default patterns registered."""
    registry = PatternRegistry()
    register_default_patterns(registry)
    return registry


@pytest.fixture
def ai_generated_text() -> str:
    """Sample AI-generated text loaded with trigger words."""
    return (
        "This issue delves into the intricacies of the current codebase architecture. "
        "It's worth noting that the existing approach, while commendable, could benefit "
        "from a more holistic refactoring effort.\n\n"
        "Here's a breakdown of the proposed changes:\n\n"
        "1. Leverage the existing module system to foster better code organization\n"
        "2. Implement a seamless integration layer for the API endpoints\n"
        "3. Ensure robust error handling across all components\n"
        "4. Create a meticulous testing framework for comprehensive coverage\n\n"
        "Furthermore, this ensures that the overall developer experience is significantly "
        "improved. Additionally, the proposed changes align with industry best practices.\n\n"
        "I'd be happy to provide more details on any of these points. "
        "Feel free to reach out if you have questions. Hope this helps!"
    )


@pytest.fixture
def human_written_text() -> str:
    """Sample human-written bug report."""
    return (
        "The login page crashes when I click submit with an empty email field. "
        "Stack trace in the console shows TypeError at auth.js:42.\n\n"
        "Steps to reproduce:\n"
        "1. Go to /login\n"
        "2. Leave email empty\n"
        "3. Click Submit\n\n"
        "Expected: Validation error message\n"
        "Actual: Page crashes\n\n"
        "Running Chrome 120 on macOS 14.2."
    )


@pytest.fixture
def issue_context() -> ContributionContext:
    """Sample issue context for testing."""
    return ContributionContext(
        title="TypeError in auth.js:42 when email is empty",
        body=(
            "## Bug\n\nLogin crashes with empty email.\n\n"
            "## Steps to Reproduce\n1. Go to /login\n2. Leave email empty\n3. Click Submit\n\n"
            "## Expected\nValidation error\n\n## Actual\n```\nTypeError at auth.js:42\n```\n\n"
            "## Environment\nChrome 120, macOS 14.2, Node 20.11.0\n\nRelated to #23"
        ),
        author="testuser",
        labels=[],
        is_bot=False,
        contribution_type=ContributionType.ISSUE,
        number=1,
        repo_owner="testorg",
        repo_name="testrepo",
    )


@pytest.fixture
def pr_context() -> ContributionContext:
    """Sample PR context for testing."""
    return ContributionContext(
        title="fix(auth): handle empty email validation on login",
        body=(
            "## What\nAdded email validation before form submission.\n\n"
            "## Why\nFixes #42 — login crashes when email is empty.\n\n"
            "## Testing\nAdded unit tests for validateEmail().\n"
        ),
        author="testuser",
        labels=[],
        is_bot=False,
        contribution_type=ContributionType.PULL_REQUEST,
        number=2,
        repo_owner="testorg",
        repo_name="testrepo",
        diff=(
            "+++ b/src/auth.js\n"
            "+function validateEmail(email) {\n"
            "+  if (!email || !email.trim()) {\n"
            "+    throw new ValidationError('Email is required');\n"
            "+  }\n"
            "+}\n"
            "+++ b/tests/auth.test.js\n"
            "+describe('validateEmail', () => {\n"
            "+  it('throws on empty email', () => {\n"
            "+    expect(() => validateEmail('')).toThrow();\n"
            "+  });\n"
            "+});\n"
        ),
        head_sha="abc123",
    )


@pytest.fixture
def empty_issue_context() -> ContributionContext:
    """Minimal issue with no body — should score very low."""
    return ContributionContext(
        title="bug",
        body="",
        author="spammer",
        labels=[],
        is_bot=False,
        contribution_type=ContributionType.ISSUE,
        number=99,
        repo_owner="testorg",
        repo_name="testrepo",
    )
