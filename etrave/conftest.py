"""Réglages communs des tests d'Étrave."""
import pytest


@pytest.fixture(autouse=True)
def exports_hors_du_bureau(tmp_path, monkeypatch):
    """Les exports vont sur le Bureau (demande de l'utilisateur du 27/11/2026) : aucun test n'écrit sur le vrai Bureau. Ils vont dans
    le sous-dossier `exports` du dossier jetable du test, l'ancien emplacement."""
    monkeypatch.setenv("ETRAVE_EXPORTS", str(tmp_path / "exports"))
