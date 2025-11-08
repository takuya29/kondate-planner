# Tests

This directory contains comprehensive test coverage for the kondate-planner application.

## Structure

```
tests/
├── unit/                       # Unit tests for individual Lambda functions
│   ├── test_create_recipe.py  # Tests for create_recipe Lambda
│   ├── test_get_recipes.py    # Tests for get_recipes Lambda
│   ├── test_save_history.py   # Tests for save_history Lambda
│   └── test_suggest_menu.py   # Tests for suggest_menu Lambda
├── integration/                # Integration tests
│   └── test_api_integration.py # End-to-end workflow tests
├── fixtures/                   # Test data and fixtures
│   └── sample_data.py         # Sample test data
└── conftest.py                # Shared pytest fixtures

## Running Tests

### Install Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run Unit Tests Only

```bash
pytest tests/unit -m unit
```

### Run Integration Tests Only

```bash
pytest tests/integration -m integration
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html
```

Then open `htmlcov/index.html` in your browser to view the coverage report.

### Run Specific Test File

```bash
pytest tests/unit/test_create_recipe.py -v
```

### Run Specific Test

```bash
pytest tests/unit/test_create_recipe.py::TestCreateRecipe::test_create_recipe_success -v
```

## Test Categories

Tests are marked with pytest markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower, test interactions)
- `@pytest.mark.slow` - Slow tests (can be skipped for quick runs)

### Run Fast Tests Only

```bash
pytest -m "not slow"
```

## Coverage Goals

- **Minimum**: 70% code coverage
- **Target**: 80%+ code coverage
- **Focus**: 100% coverage on critical paths (error handling, validation)

### Check Coverage

```bash
pytest --cov=src --cov-report=term
```

## Mocking Strategy

### DynamoDB Mocking

We use `moto` to mock DynamoDB:

```python
from moto import mock_dynamodb

@mock_dynamodb
def test_example(mock_dynamodb_recipes_table):
    # Test code here
    pass
```

### Bedrock Mocking

We use `unittest.mock` to mock Bedrock API calls:

```python
from unittest.mock import patch

@patch('app.call_bedrock')
def test_example(mock_bedrock):
    mock_bedrock.return_value = {'menu_plan': [], 'summary': 'test'}
    # Test code here
```

## Fixtures

Common fixtures are defined in `conftest.py`:

- `mock_dynamodb_recipes_table` - Mock DynamoDB recipes table
- `mock_dynamodb_history_table` - Mock DynamoDB history table
- `sample_recipe` - Sample recipe data
- `sample_history` - Sample history data
- `api_gateway_event` - Mock API Gateway event
- `lambda_context` - Mock Lambda context

## Writing New Tests

### Unit Test Example

```python
import pytest
from unittest.mock import patch

@pytest.mark.unit
def test_my_function(lambda_context):
    event = {
        'body': json.dumps({'key': 'value'})
    }

    response = my_lambda_handler(event, lambda_context)

    assert response['statusCode'] == 200
```

### Integration Test Example

```python
import pytest
from moto import mock_dynamodb

@pytest.mark.integration
@mock_dynamodb
def test_workflow(lambda_context, mock_dynamodb_recipes_table):
    # Test multiple operations together
    pass
```

## CI/CD Integration

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

See `.github/workflows/tests.yml` for the CI configuration.

## Troubleshooting

### Import Errors

If you encounter import errors, make sure you've installed the dependencies:

```bash
pip install -r requirements-dev.txt
```

### DynamoDB Connection Errors

Unit tests use mocked DynamoDB, so no real AWS connection is needed. If you see connection errors, ensure you're using the `@mock_dynamodb` decorator and the appropriate fixtures.

### Coverage Not Showing

Make sure you're running pytest with the coverage flags:

```bash
pytest --cov=src --cov-report=term
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Clear Names**: Use descriptive test names that explain what is being tested
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Mock External Services**: Always mock AWS services (DynamoDB, Bedrock)
5. **Test Edge Cases**: Include tests for error conditions and edge cases
6. **Keep Tests Fast**: Unit tests should run in milliseconds

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [moto documentation](https://docs.getmoto.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
