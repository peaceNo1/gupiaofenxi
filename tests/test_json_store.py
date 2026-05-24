from pathlib import Path

from gupiaofenxi.domain.models import ManualOverride, Position
from gupiaofenxi.storage.json_store import JsonStore


def test_json_store_persists_manual_overrides(tmp_path: Path):
    store = JsonStore(tmp_path)
    store.save_manual_overrides(
        [
            ManualOverride(symbol="002001", excluded=True, note="不做"),
            ManualOverride(symbol="300001", focus=True, note="明天复查"),
        ]
    )

    loaded = store.load_manual_overrides()

    assert loaded["002001"].excluded is True
    assert loaded["300001"].focus is True


def test_json_store_can_toggle_focus_symbol(tmp_path: Path):
    store = JsonStore(tmp_path)

    store.set_focus("000001", True)
    assert store.load_manual_overrides()["000001"].focus is True

    store.set_focus("000001", False)
    assert store.load_manual_overrides()["000001"].focus is False


def test_json_store_persists_positions(tmp_path: Path):
    store = JsonStore(tmp_path)

    store.upsert_position(Position(symbol="000001", name="平安银行", cost_price=10.0, quantity=1000))
    store.upsert_position(Position(symbol="600909", name="华安证券", cost_price=6.5, quantity=2000))
    loaded = store.load_positions()

    assert loaded["000001"].quantity == 1000
    assert loaded["600909"].cost_price == 6.5

    store.delete_position("000001")
    assert "000001" not in store.load_positions()
