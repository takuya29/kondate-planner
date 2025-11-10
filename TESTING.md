# Testing Guide

This document describes the testing infrastructure for the Kondate Planner project.

## Overview

The project uses comprehensive testing and linting to ensure code quality and reliability across all Lambda functions and utilities.

## Testing Framework

- **pytest**: Main test framework
- **pytest-cov**: Coverage measurement
- **pytest-mock**: Mocking support
- **moto**: AWS service mocking (DynamoDB)

## Test Structure

```
tests/
├── unit/                           # Unit tests for individual functions
│   ├── test_get_recipes.py        # Tests for get_recipes action
│   ├── test_get_history.py        # Tests for get_history action
│   ├── test_save_menu.py          # Tests for save_menu action
│   └── test_utils.py              # Tests for shared utilities
├── integration/                    # Integration tests
│   └── test_dynamodb_interactions.py  # DynamoDB workflow tests
├── fixtures/                       # Test data
│   ├── sample_recipes.json        # Sample recipe data
│   └── sample_history.json        # Sample menu history data
└── conftest.py                     # Shared fixtures and setup
```

## Running Tests

### Install Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/unit/test_get_recipes.py
```

### Run Specific Test Class or Function

```bash
pytest tests/unit/test_get_recipes.py::TestGetRecipesAction::test_get_all_recipes
```

### Run with Coverage Report

```bash
pytest --cov=src --cov-report=term-missing
```

### Run with HTML Coverage Report

```bash
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

## Linting and Code Quality

### Black (Code Formatting)

Check formatting:
```bash
black --check src/ tests/
```

Auto-format code:
```bash
black src/ tests/
```

### Flake8 (Style Guide)

```bash
flake8 src/ tests/
```

### Pylint (Code Quality)

```bash
pylint src/ tests/
```

### MyPy (Type Checking)

```bash
mypy src/ --explicit-package-bases --strict
```

**Note**:
- The `--explicit-package-bases` flag is required to handle multiple `app.py` files in different directories without duplicate module errors.
- The `--strict` flag enables all strict type checking options for maximum type safety.
- All source code has complete type annotations and passes strict mode checking.
- boto3-stubs are installed to provide type hints for AWS SDK calls (DynamoDB, Bedrock Runtime).

### Run All Linters

```bash
black --check src/ tests/ && flake8 src/ tests/ && pylint src/ tests/ && mypy src/ --explicit-package-bases --strict
```

## Test Coverage

The project enforces a minimum test coverage of **80%**. Current coverage: **94.38%**

Current coverage by module:

- ✅ **get_recipes action**: 100% coverage (fetch all, filter by category, error handling)
- ✅ **get_history action**: 98% coverage (default/custom days, validation, error handling)
- ✅ **save_menu action**: 98% coverage (save, overwrite, validation, Bedrock parameter parsing)
- ✅ **utils.py**: 83% coverage (decimal conversion, parameter parsing, lazy-loaded AWS clients)
- ✅ **Integration tests**: Full workflow testing across actions

**Note**: The lower coverage in `utils.py` is due to lazy-loaded AWS client getter functions (`get_dynamodb()`, `get_bedrock()`) which are tested indirectly through Lambda function tests but not directly unit tested.

## Key Test Scenarios

### get_recipes Tests

- Fetch all recipes (no filter)
- Fetch recipes by category
- Handle empty table
- Handle DynamoDB errors
- Verify Decimal to float/int conversion
- Verify recipes sorted by name

### get_history Tests

- Fetch with default days (30)
- Fetch with custom days (1-365)
- Validate days parameter (reject invalid values)
- Handle empty history
- Handle DynamoDB errors
- Verify results sorted by date (recent first)

### save_menu Tests

- Save valid menu
- Save menu with notes
- Validate date format (YYYY-MM-DD)
- Handle Bedrock Agent parameter formats (JSON and Python dict)
- Reject duplicate saves without overwrite flag
- Overwrite existing menu with overwrite flag
- Extract recipe_ids into flat list
- Handle missing required fields

### utils.py Tests

- `decimal_to_float()`: Convert Decimals in nested objects/lists
- `parse_bedrock_parameter()`: Parse JSON and Python dict formats
- Validate edge cases and error handling

### Integration Tests

- Full workflow: get recipes → create menu → get history
- Recipe filtering and menu creation
- Overwriting existing menus
- Empty meal slots handling

## Fixtures

### mock_env_vars
Sets up required environment variables (table names, AWS region).

### mock_dynamodb_tables
Creates mock DynamoDB tables with sample data using moto.

### sample_recipes
Loads sample recipe data from `fixtures/sample_recipes.json`.

### sample_history
Loads sample history data from `fixtures/sample_history.json`.

### bedrock_agent_event
Creates a sample Bedrock Agent event structure.

## CI/CD Integration

### GitHub Actions Workflow

A GitHub Actions workflow file (`test-and-lint.yml`) is provided for CI/CD integration. To enable it:

1. Move the file to `.github/workflows/`:
   ```bash
   mv test-and-lint.yml .github/workflows/
   ```

2. The workflow runs on:
   - Pull requests to `main` branch
   - Pushes to `main` branch

3. The workflow performs:
   - Test execution with coverage reporting
   - Code formatting check (Black)
   - Style guide enforcement (Flake8)
   - Code quality analysis (Pylint)
   - Type checking (MyPy)

### Setting Up Codecov (Optional)

To enable coverage reporting with Codecov:

1. Sign up at https://codecov.io
2. Add your repository
3. Add `CODECOV_TOKEN` to your GitHub repository secrets
4. Coverage reports will be automatically uploaded on each PR

## Configuration Files

### pyproject.toml
- Black configuration (line length, target Python version)
- pytest configuration (test paths, coverage settings)
- MyPy configuration (type checking rules)
- Coverage configuration (exclusions, reporting)

### .flake8
- Line length: 88 (matching Black)
- Ignored errors (E203, E266, E501, W503)
- File exclusions (.git, venv, build, etc.)

### .pylintrc
- Disabled checks (docstrings, naming conventions)
- Max line length: 88
- Complexity thresholds

## Best Practices

1. **Write tests first**: Follow TDD when adding new features
2. **Keep tests isolated**: Each test should be independent
3. **Use descriptive names**: Test names should clearly describe what they test
4. **Mock external dependencies**: Use moto for AWS services, pytest-mock for other mocks
5. **Test edge cases**: Include tests for error conditions and boundary values
6. **Maintain fixtures**: Keep sample data in JSON files for easy updates
7. **Run linters before commit**: Ensure code quality before pushing

## Troubleshooting

### Import Errors

If you encounter import errors when running tests, ensure the Python path is set up correctly in `conftest.py`.

### AWS Client Initialization Errors

The project uses **lazy-loaded AWS clients** in `utils.py` to avoid `NoRegionError` during test collection:

- `get_dynamodb()` and `get_bedrock()` functions initialize clients only when called
- Tests use moto's `@mock_aws` decorator to mock AWS services
- Clients are created within the mocked context, not at module import time

If you see `botocore.exceptions.NoRegionError`, ensure:
1. AWS clients are accessed via getter functions (`get_dynamodb()`) not direct imports
2. Tests are using the `mock_aws` context manager from moto
3. Environment variables (`AWS_DEFAULT_REGION`) are set in test fixtures

### DynamoDB Mocking Issues

If moto mocking fails, ensure you're using the `@mock_aws` decorator and creating tables within the mock context.

### Coverage Not Meeting Threshold

Run with verbose coverage to see which lines are missing:
```bash
pytest --cov=src --cov-report=term-missing
```

## Future Enhancements

- [ ] Add performance tests for large datasets
- [ ] Add contract tests for Bedrock Agent integration
- [ ] Add mutation testing with mutmut
- [ ] Set up pre-commit hooks for automated linting
- [ ] Add security scanning with bandit
