import os
import json
import pytest

# Fixture to provide test configuration loaded from paper_config.json
@pytest.fixture
def test_config():
    """
    Load and return the test configuration from the paper_config.json file.
    Assumes the file is located one directory level above this tests directory.
    """
    base_dir = os.path.join(os.path.dirname(__file__), '..')
    config_file = os.path.join(base_dir, 'paper_config.json')
    with open(config_file, 'r') as f:
        return json.load(f)