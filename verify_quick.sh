#!/bin/bash

# MonitorX Quick Verification Script
# This script verifies that MonitorX is Working As Intended (WAI)

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         MonitorX - Quick Verification Script              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print test result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

echo "Running verification tests..."
echo ""

# Test 1: Check Python version
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 1: Python Environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python --version
print_result $? "Python installed and accessible"
echo ""

# Test 2: Check required files
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 2: Project Structure"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check critical files
files=("README.md" "pyproject.toml" "requirements.txt" "docker-compose.yml" ".env.example")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        print_result 0 "File exists: $file"
    else
        print_result 1 "File missing: $file"
    fi
done
echo ""

# Test 3: Check directories
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 3: Directory Structure"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

dirs=("src/monitorx" "tests" "docs" "examples")
for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        print_result 0 "Directory exists: $dir"
    else
        print_result 1 "Directory missing: $dir"
    fi
done
echo ""

# Test 4: Check Python modules
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 4: Python Module Imports"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python -c "import monitorx" 2>/dev/null
print_result $? "Can import monitorx module"

python -c "from monitorx import MonitorXClient" 2>/dev/null
print_result $? "Can import MonitorXClient"

python -c "from monitorx.types import InferenceMetric, DriftMetric" 2>/dev/null
print_result $? "Can import types"

python -c "from monitorx.services import MetricsCollector" 2>/dev/null
print_result $? "Can import services"
echo ""

# Test 5: Run pytest
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 5: Test Suite (119 tests)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python -m pytest tests/ -q --tb=no 2>&1 | tail -1
PYTEST_RESULT=${PIPESTATUS[0]}
print_result $PYTEST_RESULT "All tests passed"
echo ""

# Test 6: Check documentation
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 6: Documentation Files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

docs=("docs/API.md" "docs/SDK_ADVANCED.md" "docs/SECURITY.md" "docs/DEPLOYMENT.md" "docs/ARCHITECTURE.md" "docs/ALERTING.md")
for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        lines=$(wc -l < "$doc")
        print_result 0 "$doc ($lines lines)"
    else
        print_result 1 "$doc not found"
    fi
done
echo ""

# Test 7: Example files
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 7: Example Files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

examples=("examples/alerting_setup.py" "examples/sdk_advanced_features.py")
for example in "${examples[@]}"; do
    if [ -f "$example" ]; then
        print_result 0 "Example exists: $example"
    else
        print_result 1 "Example missing: $example"
    fi
done
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    VERIFICATION SUMMARY                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║          ✅ MonitorX is Working As Intended (WAI)         ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Next steps:"
    echo "  1. Start services:    docker-compose up -d"
    echo "  2. Open dashboard:    http://localhost:8501"
    echo "  3. Open API docs:     http://localhost:8000/docs"
    echo "  4. Check health:      curl http://localhost:8000/api/v1/health"
    echo ""
    echo "For full verification, see: VERIFICATION_GUIDE.md"
    echo ""
    exit 0
else
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║            ❌ Some verification tests failed              ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Please check the failed tests above and fix any issues."
    echo "See VERIFICATION_GUIDE.md for detailed troubleshooting."
    echo ""
    exit 1
fi
