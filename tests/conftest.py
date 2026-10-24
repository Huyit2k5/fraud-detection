import os
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture(scope="session")
def spark():
    from java_env import spark_env

    os.environ.update(spark_env())
    from spark_etl import get_spark_session

    session = get_spark_session("tests")
    yield session
    session.stop()
