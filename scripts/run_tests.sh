#!/bin/bash
# ============================================
# Docker Test Runner - Executes test suite in isolated container
# ============================================

set -e  # Exit on error

echo "=========================================="
echo "  eCommerce Intelligence - Test Suite"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
PROFILE="test"
SERVICE="test-runner"
RUN_MODE="run"  # 'run' for one-off, 'up' for persistent

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            echo "Running UNIT tests only..."
            TEST_CMD="python -m pytest tests/unit -v --tb=short"
            shift
            ;;
        --integration)
            echo "Running INTEGRATION tests only..."
            TEST_CMD="python -m pytest tests/integration -v --tb=short -m integration"
            shift
            ;;
        --coverage)
            echo "Running with COVERAGE report..."
            TEST_CMD="python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term"
            shift
            ;;
        --up)
            RUN_MODE="up"
            shift
            ;;
        --logs)
            echo "Tailing test runner logs..."
            docker compose --profile $PROFILE logs -f $SERVICE
            exit 0
            ;;
        --clean)
            echo "Cleaning test artifacts..."
            rm -rf htmlcov .coverage coverage-report/
            exit 0
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --unit         Run unit tests only"
            echo "  --integration  Run integration tests only"
            echo "  --coverage     Generate HTML coverage report"
            echo "  --up           Start persistent test runner container"
            echo "  --logs         Follow test runner logs"
            echo "  --clean        Remove coverage artifacts"
            echo "  -h, --help     Show this help"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run all tests (one-off)"
            echo "  $0 --unit --coverage  # Unit tests with coverage"
            echo "  $0 --up --logs        # Start test runner & follow logs"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use -h or --help for usage"
            exit 1
            ;;
    esac
done

# Set default test command if not set
if [ -z "$TEST_CMD" ]; then
    TEST_CMD="python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing --cov-fail-under=70"
fi

echo -e "${YELLOW}Test command:${NC} $TEST_CMD"
echo ""

if [ "$RUN_MODE" = "run" ]; then
    # One-off execution (container removed after)
    echo "Starting one-off test runner container..."
    docker compose --profile $PROFILE run --rm $SERVICE bash -c "$TEST_CMD"
    EXIT_CODE=$?
else
    # Persistent service (for debugging)
    echo "Starting persistent test runner service..."
    docker compose --profile $PROFILE up -d $SERVICE
    echo -e "${GREEN}Test runner started. Use 'docker compose --profile $PROFILE logs -f $SERVICE' to view logs${NC}"
    echo "To execute tests manually:"
    echo "  docker compose exec $SERVICE $TEST_CMD"
    exit 0
fi

# Check exit code
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}✗ Tests failed with exit code $EXIT_CODE${NC}"
    exit $EXIT_CODE
fi
