# Contributing to MonitorX

<div align="center">

![MonitorX](https://img.shields.io/badge/MonitorX-Contributing-blue.svg)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Code of Conduct](https://img.shields.io/badge/Code%20of%20Conduct-Contributor%20Covenant-violet.svg)](CODE_OF_CONDUCT.md)

**Thank you for considering contributing to MonitorX!**

We welcome contributions from the community to help make MonitorX better.

</div>

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Guidelines](#coding-guidelines)
- [Testing Guidelines](#testing-guidelines)
- [Submitting Changes](#submitting-changes)
- [License](#license)

---

## 📜 Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the maintainers.

**Key Principles:**
- Be respectful and inclusive
- Welcome newcomers
- Focus on what is best for the community
- Show empathy towards others

---

## 🤝 How Can I Contribute?

### Reporting Bugs

Before submitting a bug report:
1. **Check the documentation** - The issue might be covered there
2. **Search existing issues** - Someone may have already reported it
3. **Test with the latest version** - The bug might be fixed

**When filing a bug report, include:**
- MonitorX version
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs/screenshots

**Use this template:**
```markdown
**Environment:**
- MonitorX version: 0.1.0
- Python version: 3.9.7
- OS: Ubuntu 22.04

**Description:**
Brief description of the bug

**Steps to Reproduce:**
1. Step one
2. Step two
3. ...

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Logs/Screenshots:**
Attach relevant information
```

### Suggesting Enhancements

We welcome feature suggestions! Before submitting:
1. **Check existing issues** - It might already be planned
2. **Provide context** - Explain the use case
3. **Be specific** - Detailed proposals are easier to implement

**Use this template:**
```markdown
**Feature Request:**
Brief title of the feature

**Use Case:**
Why is this feature needed?

**Proposed Solution:**
How should it work?

**Alternatives Considered:**
Other approaches you've thought about

**Additional Context:**
Any other relevant information
```

### Contributing Code

We love code contributions! Here's how:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Write/update tests**
5. **Run the test suite**
6. **Update documentation**
7. **Commit your changes**
8. **Push to your fork**
9. **Open a Pull Request**

### Contributing Documentation

Documentation improvements are always welcome:
- Fix typos or clarify existing docs
- Add examples
- Write tutorials
- Improve API documentation

---

## 🛠️ Development Setup

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- git
- InfluxDB 2.7+ (for testing)
- Docker & Docker Compose (optional)

### Clone the Repository

```bash
git clone https://github.com/your-org/monitorx.git
cd monitorx
```

### Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Install Dependencies

```bash
# Install in development mode
pip install -e ".[dev]"

# Or install from requirements
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If exists
```

### Set Up InfluxDB (for testing)

```bash
# Using Docker
docker run -d --name influxdb-dev \
  -p 8086:8086 \
  -e DOCKER_INFLUXDB_INIT_MODE=setup \
  -e DOCKER_INFLUXDB_INIT_USERNAME=admin \
  -e DOCKER_INFLUXDB_INIT_PASSWORD=password123 \
  -e DOCKER_INFLUXDB_INIT_ORG=monitorx \
  -e DOCKER_INFLUXDB_INIT_BUCKET=metrics \
  influxdb:2.7
```

### Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your settings
vim .env
```

### Verify Setup

```bash
# Run quick verification
./verify_quick.sh

# Should show: ✅ MonitorX is Working As Intended (WAI)
```

---

## 📝 Coding Guidelines

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

**Code Formatting:**
```bash
# Format code with black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Type check with mypy
mypy src/
```

**Key Guidelines:**
- **Line Length**: 100 characters (not 79)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes for strings
- **Imports**: Grouped (stdlib, third-party, local)
- **Type Hints**: Required for public APIs
- **Docstrings**: Google style

### Code Structure

**File Organization:**
```
src/monitorx/
├── api/           # REST API endpoints
├── sdk/           # Python SDK client
├── services/      # Core business logic
├── middleware/    # FastAPI middleware
├── config/        # Configuration
├── types/         # Data types
└── dashboard/     # Streamlit dashboard
```

**Import Order:**
```python
# Standard library
import os
from typing import Optional

# Third-party
import httpx
from fastapi import FastAPI

# Local
from monitorx.types import InferenceMetric
from monitorx.services import MetricsCollector
```

### Type Hints

Always use type hints for public APIs:

```python
from typing import Optional, List, Dict, Any

async def collect_metric(
    model_id: str,
    latency: float,
    tags: Optional[Dict[str, str]] = None
) -> bool:
    """Collect inference metric.

    Args:
        model_id: Unique model identifier
        latency: Request latency in milliseconds
        tags: Optional metadata tags

    Returns:
        True if successful, False otherwise
    """
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_average(values: List[float]) -> float:
    """Calculate the average of a list of values.

    This function computes the arithmetic mean of the input values.
    Empty lists will raise a ValueError.

    Args:
        values: List of numeric values to average

    Returns:
        The arithmetic mean of the values

    Raises:
        ValueError: If the input list is empty

    Examples:
        >>> calculate_average([1.0, 2.0, 3.0])
        2.0
    """
    if not values:
        raise ValueError("Cannot calculate average of empty list")
    return sum(values) / len(values)
```

### Error Handling

Be explicit about error handling:

```python
from loguru import logger

try:
    result = await api_call()
except httpx.HTTPError as e:
    logger.error(f"API call failed: {e}")
    raise
except Exception as e:
    logger.exception("Unexpected error occurred")
    raise
```

### Async/Await

MonitorX uses async/await extensively:

```python
# Good: Proper async context manager
async with MonitorXClient(base_url=url) as client:
    await client.collect_metric(...)

# Good: Concurrent operations
results = await asyncio.gather(
    client.get_metrics(),
    client.get_alerts(),
    return_exceptions=True
)

# Avoid: Blocking calls in async functions
async def bad_example():
    time.sleep(1)  # ❌ Blocks event loop

async def good_example():
    await asyncio.sleep(1)  # ✅ Non-blocking
```

---

## 🧪 Testing Guidelines

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api.py -v

# Run with coverage
pytest tests/ --cov=monitorx --cov-report=html

# Run specific test
pytest tests/test_api.py::test_register_model -v
```

### Writing Tests

**Test Structure:**
```python
import pytest
from monitorx.sdk import MonitorXClient

class TestMetricsCollection:
    """Tests for metric collection functionality."""

    @pytest.mark.asyncio
    async def test_collect_inference_metric_success(self):
        """Test successful inference metric collection."""
        # Arrange
        client = MonitorXClient(base_url="http://test")

        # Act
        result = await client.collect_inference_metric(
            model_id="test-model",
            model_type="llm",
            latency=100.0
        )

        # Assert
        assert result is True
```

**Test Categories:**
- **Unit Tests**: Test individual functions/classes
- **Integration Tests**: Test component interactions
- **API Tests**: Test REST endpoints
- **End-to-End Tests**: Test complete workflows

**Test Naming:**
- `test_<function>_<scenario>_<expected_result>`
- Example: `test_collect_metric_with_invalid_model_id_raises_error`

**Fixtures:**
```python
@pytest.fixture
async def client():
    """Provide test client instance."""
    client = MonitorXClient(base_url="http://test")
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_something(client):
    result = await client.do_something()
    assert result
```

**Mocking:**
```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_api_call_with_mock():
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value.json.return_value = {"status": "ok"}

        client = MonitorXClient()
        result = await client.collect_metric(...)

        assert result is True
        mock_post.assert_called_once()
```

### Test Coverage

We aim for high test coverage:
- **Minimum**: 80% coverage for new code
- **Target**: 90%+ coverage
- **Critical paths**: 100% coverage

```bash
# Generate coverage report
pytest tests/ --cov=monitorx --cov-report=html

# Open report
open htmlcov/index.html
```

---

## 🚀 Submitting Changes

### Commit Messages

Write clear, descriptive commit messages:

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(sdk): add batch metric collection

Implement batch collection method that processes multiple metrics
in parallel using asyncio.gather() for 10x performance improvement.

Closes #123
```

```
fix(api): handle missing model_id in metrics endpoint

Add validation to ensure model_id is present before processing.
Return 400 Bad Request with clear error message if missing.

Fixes #456
```

### Pull Request Process

1. **Update Documentation**
   - Update README if needed
   - Update API docs for API changes
   - Add docstrings to new code

2. **Add Tests**
   - Write tests for new features
   - Update existing tests if needed
   - Ensure all tests pass

3. **Run Quality Checks**
   ```bash
   # Format code
   black src/ tests/
   isort src/ tests/

   # Type check
   mypy src/

   # Run tests
   pytest tests/ -v
   ```

4. **Create Pull Request**
   - Use a descriptive title
   - Reference related issues
   - Describe changes in detail
   - Add screenshots if relevant

**PR Template:**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Closes #123

## Testing
- [ ] All existing tests pass
- [ ] Added tests for new functionality
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass
```

5. **Code Review**
   - Respond to feedback promptly
   - Make requested changes
   - Keep discussion focused and professional

6. **Merge**
   - Maintainers will merge when approved
   - Delete your branch after merge

---

## 📄 License

By contributing to MonitorX, you agree that your contributions will be licensed under the **Apache License 2.0**.

All contributions are subject to the [Apache License 2.0](LICENSE) terms:

```
Copyright 2025 MonitorX Team

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

### Contribution Terms

Per Apache License 2.0 Section 5:

> Unless You explicitly state otherwise, any Contribution intentionally
> submitted for inclusion in the Work by You to the Licensor shall be
> under the terms and conditions of this License, without any additional
> terms or conditions.

This means:
- ✅ No CLA required
- ✅ Contributors grant patent license
- ✅ Contributors retain copyright
- ✅ Clear contribution terms

---

## 🎯 What to Contribute

### Good First Issues

Look for issues labeled `good-first-issue`:
- Documentation improvements
- Simple bug fixes
- Test additions
- Example code

### High Priority

Areas where we especially need help:
- 📚 **Documentation**: Tutorials, examples, guides
- 🧪 **Tests**: Increase coverage, add edge cases
- 🐛 **Bug Fixes**: Known issues in GitHub
- ✨ **Features**: Items from the roadmap

### Ideas for Contributions

**Features:**
- Additional alerting channels (PagerDuty, Discord)
- Advanced visualization components
- Performance optimizations
- Custom metric types
- Grafana integration
- Prometheus exporter

**Documentation:**
- Video tutorials
- Blog posts
- Case studies
- Architecture deep-dives

**Infrastructure:**
- CI/CD improvements
- Docker optimizations
- Kubernetes manifests
- Terraform modules

---

## 💬 Getting Help

**Resources:**
- 📖 **Documentation**: [docs/](docs/)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/your-org/monitorx/discussions)
- 🐛 **Issues**: [GitHub Issues](https://github.com/your-org/monitorx/issues)

**Questions:**
- Check the [FAQ](docs/FAQ.md)
- Search existing discussions
- Ask in GitHub Discussions (don't file an issue)

**Communication:**
- Be patient and respectful
- Provide context and details
- Share code examples when relevant

---

## 🙏 Recognition

Contributors will be recognized in:
- README contributors section
- Release notes
- Project documentation

Thank you for contributing to MonitorX! 🎉

---

**Happy Contributing!** ❤️
