#!/usr/bin/env python
"""
System Validation Script - Checks that all components are properly configured.
"""

import importlib
import os
import sys
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def check_file(path, description):
    """Check if a file exists."""
    exists = Path(path).exists()
    status = f"{Colors.GREEN}✓{Colors.RESET}" if exists else f"{Colors.RED}✗{Colors.RESET}"
    print(f"  {status} {description}: {path}")
    return exists

def check_import(module_name, description):
    """Check if a Python module can be imported."""
    try:
        importlib.import_module(module_name)
        print(f"  {Colors.GREEN}✓{Colors.RESET} {description}: {module_name}")
        return True
    except ImportError as e:
        print(f"  {Colors.RED}✗{Colors.RESET} {description}: {module_name} - {e}")
        return False

def check_env_vars(vars_list):
    """Check if environment variables are set."""
    missing = []
    for var in vars_list:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"  {Colors.YELLOW}⚠{Colors.RESET} Missing env vars: {', '.join(missing)}")
        return False
    else:
        print(f"  {Colors.GREEN}✓{Colors.RESET} All required env vars set")
        return True

def main():
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}  eCommerce Intelligence - System Validation{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")

    all_ok = True

    # 1. Check project structure
    print(f"{Colors.BOLD}1. Project Structure{Colors.RESET}")
    all_ok &= check_file("src/__main__.py", "Main orchestrator")
    all_ok &= check_file("src/dashboard/app.py", "Dashboard")
    all_ok &= check_file("config/config.yaml", "Configuration")
    all_ok &= check_file("requirements.txt", "Dependencies")
    all_ok &= check_file("Dockerfile", "Docker configuration")
    all_ok &= check_file("docker-compose.yml", "Docker Compose")
    all_ok &= check_file("tests/test_agents.py", "Agent tests")
    print()

    # 2. Check Kubeflow pipelines
    print(f"{Colors.BOLD}2. Kubeflow Pipelines{Colors.RESET}")
    all_ok &= check_file("src/pipelines/kubeflow/pipeline.py", "Pipeline definition")
    all_ok &= check_file("src/pipelines/kubeflow/run_pipeline.py", "Pipeline runner")
    all_ok &= check_file("src/pipelines/kubeflow/pipeline.yaml", "Compiled pipeline YAML")
    all_ok &= check_file("src/pipelines/kubeflow/components/scraping_component.py", "Scraping component")
    all_ok &= check_file("src/pipelines/kubeflow/components/preprocessing_component.py", "Preprocessing component")
    all_ok &= check_file("src/pipelines/kubeflow/README.md", "Pipeline documentation")
    print()

    # 3. Check new modules
    print(f"{Colors.BOLD}3. New Modules{Colors.RESET}")
    all_ok &= check_file("src/scheduler/main.py", "Scheduler")
    all_ok &= check_file("src/monitoring/prometheus_exporter.py", "Metrics exporter")
    all_ok &= check_file("src/scraping/agents/main.py", "Agent launcher")
    all_ok &= check_file("scripts/launch_agents.py", "Launch script (Linux)")
    all_ok &= check_file("scripts/launch_agents.ps1", "Launch script (Windows)")
    all_ok &= check_file("scripts/run_tests.sh", "Test runner script (Linux)")
    all_ok &= check_file("scripts/run_tests.ps1", "Test runner script (Windows)")
    all_ok &= check_file("docker-compose.test.yml", "Test docker compose")
    print()

    # 4. Check Python imports
    print(f"{Colors.BOLD}4. Core Dependencies{Colors.RESET}")
    imports = [
        ("asyncio", "AsyncIO"),
        ("pandas", "Pandas"),
        ("numpy", "NumPy"),
        ("sklearn", "Scikit-learn"),
        ("xgboost", "XGBoost"),
        ("plotly", "Plotly"),
        ("streamlit", "Streamlit"),
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("sqlalchemy", "SQLAlchemy"),
        ("asyncpg", "asyncpg"),
        ("redis", "Redis-py"),
        ("yaml", "PyYAML"),
        ("pydantic", "Pydantic"),
        ("openai", "OpenAI SDK"),
        ("anthropic", "Anthropic SDK"),
        ("prometheus_client", "Prometheus client"),
    ]
    for module, desc in imports:
        check_import(module, desc)
    print()

    # 5. Check Kubeflow imports
    print(f"{Colors.BOLD}5. Kubeflow Dependencies{Colors.RESET}")
    kfp_imports = [
        ("kfp", "Kubeflow Pipelines SDK"),
        ("kfp.dsl", "KFP DSL"),
    ]
    for module, desc in kfp_imports:
        check_import(module, desc)
    print()

    # 6. Check environment configuration
    print(f"{Colors.BOLD}6. Environment Variables{Colors.RESET}")
    required_env = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "REDIS_PASSWORD",
    ]
    check_env_vars(required_env)
    print()

    # 7. Docker services status
    print(f"{Colors.BOLD}7. Docker Services{Colors.RESET}")
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            services_found = []
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        status = parts[1].strip()
                        services_found.append(name)
                        mark = f"{Colors.GREEN}✓{Colors.RESET}" if "Up" in status else f"{Colors.YELLOW}⚠{Colors.RESET}"
                        print(f"  {mark} {name}: {status}")
            
            expected_services = ["postgres", "redis"]
            for svc in expected_services:
                if not any(svc in name for name in services_found):
                    print(f"  {Colors.RED}✗{Colors.RESET} {svc}: NOT RUNNING")
                    all_ok = False
        else:
            print(f"  {Colors.YELLOW}⚠{Colors.RESET} Docker not accessible or no containers")
    except Exception as e:
        print(f"  {Colors.YELLOW}⚠{Colors.RESET} Could not check Docker status: {e}")
    print()

    # Summary
    print(f"{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    if all_ok:
        print(f"{Colors.GREEN}{Colors.BOLD}  ✓ ALL CHECKS PASSED{Colors.RESET}")
        print(f"\n  Next steps:")
        print(f"    - Run tests: make test-docker")
        print(f"    - Compile pipeline: make pipeline")
        print(f"    - Start agents: make agents-start")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}  ✗ SOME CHECKS FAILED{Colors.RESET}")
        print(f"\n  Please fix the issues above before continuing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
