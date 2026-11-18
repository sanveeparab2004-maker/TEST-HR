import os
import pytest

# Ensure all tests run strictly against an isolated test database, never touching the real assess_local.db
os.environ["DATABASE_URL"] = "sqlite:///./test_suite.db"

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    # Clean up test database file after test suite runs
    if os.path.exists("test_suite.db"):
        try:
            os.remove("test_suite.db")
        except Exception:
            pass
