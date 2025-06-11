# Tests Directory

This directory contains all test files for the AI Agent 3D Print System.

## Test Structure

### Unit Tests
- `test_core/` - Tests for core modules
- `test_agents/` - Tests for individual agents
- `test_api/` - Tests for API endpoints
- `test_integration/` - Integration tests

### Test Types

#### Unit Tests (`test_*.py`)
- Test individual functions and classes
- Mock external dependencies
- Focus on business logic validation
- Target: >80% code coverage

#### Integration Tests (`integration_*.py`)
- Test agent interaction
- End-to-end workflow validation
- Database and queue integration
- Mock hardware interfaces

#### Performance Tests (`performance_*.py`)
- Agent execution timing
- Memory usage validation
- Concurrent request handling
- Stress testing scenarios

## Test Configuration

### Fixtures
- `conftest.py` - Shared test fixtures
- Mock printer interfaces
- Test database setup
- Configuration overrides

### Test Data
- `test_data/` - Sample STL files, G-code, etc.
- Mock API responses
- Test configuration files
- Reference output data

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov=agents --cov-report=html

# Run specific test categories
pytest tests/test_core/
pytest tests/integration_*
```

## Coverage Goals

- Unit tests: >80% code coverage
- Integration tests: Complete workflow coverage
- Error scenarios: All exception paths tested
- Performance tests: Response time validation
