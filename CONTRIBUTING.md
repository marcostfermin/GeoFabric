# Contributing to GeoFabric

Thank you for your interest in contributing to GeoFabric! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/marcostfermin/GeoFabric.git
   cd GeoFabric
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   python -m pip install -U pip
   pip install -e ".[dev,all]"
   ```

4. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

## Code Style

We use the following tools to maintain code quality:

- **Ruff** for linting and formatting
- **MyPy** for type checking
- **Pytest** for testing

### Running Checks Locally

```bash
# Linting
ruff check src/

# Formatting
ruff format src/

# Type checking
mypy src/geofabric

# Tests
pytest

# Tests with coverage
pytest --cov=geofabric --cov-report=term-missing
```

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, concise commit messages
   - Add tests for new functionality
   - Update documentation as needed

3. **Run all checks**
   ```bash
   ruff check src/ && ruff format --check src/ && mypy src/geofabric && pytest
   ```

4. **Push and create a PR**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **PR Requirements**
   - All CI checks must pass
   - Code review approval required
   - Tests for new functionality
   - Documentation updates if applicable

## Testing Guidelines

- Write tests for all new functionality
- Aim for high test coverage (90%+)
- Use descriptive test names
- Use pytest fixtures for common setup
- Mock external dependencies

Example test structure:
```python
class TestFeatureName:
    """Tests for feature description."""

    def test_basic_functionality(self) -> None:
        """Test basic feature behavior."""
        result = function_under_test()
        assert result == expected

    def test_edge_case(self) -> None:
        """Test edge case handling."""
        with pytest.raises(ValueError, match="expected message"):
            function_under_test(invalid_input)
```

## Documentation

- Add docstrings to all public functions, classes, and methods
- Use Google-style docstrings
- Update README.md for user-facing changes
- Update CHANGELOG.md for all notable changes

Example docstring:
```python
def function_name(param1: str, param2: int = 10) -> bool:
    """Short description of function.

    Longer description if needed, explaining the purpose
    and behavior of the function.

    Args:
        param1: Description of param1.
        param2: Description of param2. Defaults to 10.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param1 is empty.

    Example:
        >>> function_name("test", 5)
        True
    """
```

## Reporting Issues

When reporting issues, please include:

1. **Description**: Clear description of the issue
2. **Steps to reproduce**: Minimal code example if possible
3. **Expected behavior**: What you expected to happen
4. **Actual behavior**: What actually happened
5. **Environment**: Python version, OS, package versions

## Feature Requests

Feature requests are welcome! Please include:

1. **Use case**: Why is this feature needed?
2. **Proposed solution**: How should it work?
3. **Alternatives considered**: Other approaches you've thought about

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Focus on the code, not the person

## Questions?

Feel free to open an issue for questions or reach out to the maintainers.

Thank you for contributing!
