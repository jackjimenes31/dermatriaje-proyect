import pytest


@pytest.fixture(autouse=True)
def _media_root_temporal(settings, tmp_path):
    """Las imágenes subidas durante los tests no deben ensuciar media/ real."""
    settings.MEDIA_ROOT = tmp_path
