from auto_pilot import __version__


def test_version():
    """Test that the package has a version."""
    assert __version__ == "0.1.0"


def test_example():
    """Example test."""
    assert 1 + 1 == 2
