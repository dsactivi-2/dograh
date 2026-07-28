```markdown
# dograh Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches the core development patterns and conventions used in the `dograh` Python codebase. By following these guidelines, contributors can write code that is stylistically consistent, easy to maintain, and aligned with the project's established workflows. The repository uses Python without a specific framework, employs conventional commit messages, and follows clear patterns for file naming, imports, and exports.

## Coding Conventions

### File Naming
- Use **snake_case** for all file names.
  - **Example:**  
    ```
    user_profile.py
    data_loader.py
    ```

### Import Style
- Use **relative imports** within the package.
  - **Example:**  
    ```python
    from .utils import calculate_score
    from ..models import User
    ```

### Export Style
- Use **named exports** by explicitly listing exported members in `__all__`.
  - **Example:**  
    ```python
    __all__ = ["User", "calculate_score"]
    ```

### Commit Messages
- Use **conventional commits** with the `feat` prefix for new features.
  - **Example:**  
    ```
    feat: add user authentication to login module
    ```

## Workflows

### Feature Development
**Trigger:** When adding a new feature to the codebase  
**Command:** `/feature-development`

1. Create a new branch for your feature.
2. Implement the feature using snake_case file naming and relative imports.
3. Add or update named exports as needed.
4. Write or update tests in files matching `*.test.*`.
5. Commit changes using the `feat:` prefix and a concise description.
6. Open a pull request for review.

### Testing Code
**Trigger:** When verifying code correctness  
**Command:** `/run-tests`

1. Identify test files (matching `*.test.*`).
2. Run tests using the project's preferred test runner (framework unknown; use standard Python tools if unsure).
   - **Example:**  
     ```bash
     python -m unittest discover -p "*.test.*"
     ```
3. Review test results and fix any failures.

## Testing Patterns

- Test files follow the pattern `*.test.*` (e.g., `user_profile.test.py`).
- The testing framework is not specified; use Python's built-in `unittest` or another standard tool.
- Place test files alongside the modules they test or in a dedicated test directory.

**Example test file:**
```python
# user_profile.test.py

import unittest
from .user_profile import UserProfile

class TestUserProfile(unittest.TestCase):
    def test_username(self):
        user = UserProfile("alice")
        self.assertEqual(user.username, "alice")

if __name__ == "__main__":
    unittest.main()
```

## Commands
| Command              | Purpose                                   |
|----------------------|-------------------------------------------|
| /feature-development | Start a new feature development workflow  |
| /run-tests           | Run all tests in the repository           |
```
