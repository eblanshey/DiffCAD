# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for FreeCAD settings repository persistence model behavior.
"""Unit tests for FreeCAD settings repository behavior."""

from dataclasses import replace

from freecad.diff_wb.domain.config import (
    EXCLUDED_PROPERTIES,
    EXCLUDED_PROPERTIES_BY_TYPE,
    EXCLUDED_TYPES,
    FLOAT_PRECISION,
)
from freecad.diff_wb.domain.freecad_ports import FreeCadContext
from freecad.diff_wb.infrastructure.freecad.settings_repo import (
    MAX_FLOAT_PRECISION,
    MIN_FLOAT_PRECISION,
    FreeCADSettingsRepository,
)


class _FakeParamGet:
    def __init__(self) -> None:
        self._strings: dict[str, str] = {}
        self._bools: dict[str, bool] = {}
        self._ints: dict[str, int] = {}

    def GetString(self, key: str, default: str = "") -> str:
        return self._strings.get(key, default)

    def SetString(self, key: str, value: str) -> None:
        self._strings[key] = value

    def GetBool(self, key: str, default: bool = False) -> bool:
        return self._bools.get(key, default)

    def SetBool(self, key: str, value: bool) -> None:
        self._bools[key] = value

    def GetInt(self, key: str, default: int = 0) -> int:
        return self._ints.get(key, default)

    def SetInt(self, key: str, value: int) -> None:
        self._ints[key] = value

    def RemBool(self, key: str) -> None:
        self._bools.pop(key, None)

    def RemString(self, key: str) -> None:
        self._strings.pop(key, None)

    def RemInt(self, key: str) -> None:
        self._ints.pop(key, None)


class _FakeApp:
    def __init__(self, group: _FakeParamGet) -> None:
        self._group = group

    def ParamGet(self, path: str) -> _FakeParamGet:
        return self._group


class _FakeGui:
    def getDocument(self, doc_name: str) -> None:
        return None


def _make_repo() -> tuple[FreeCADSettingsRepository, _FakeParamGet]:
    group = _FakeParamGet()
    ctx = FreeCadContext(app=_FakeApp(group), gui=_FakeGui())  # type: ignore[arg-type]
    return FreeCADSettingsRepository(ctx), group


class TestFreeCADSettingsRepository:
    def test_default_mode_returns_config_defaults(self) -> None:
        repo, _ = _make_repo()

        settings = repo.get_settings()

        assert settings.excluded_types == EXCLUDED_TYPES
        assert settings.excluded_properties == EXCLUDED_PROPERTIES
        assert settings.excluded_properties_by_type == EXCLUDED_PROPERTIES_BY_TYPE
        assert settings.float_precision == FLOAT_PRECISION

    def test_custom_mode_returns_parsed_line_values(self) -> None:
        repo, group = _make_repo()

        group.SetBool("UseDefaultExcludedTypes", False)
        group.SetString("CustomExcludedTypes", "  App::Part\n\n App::Link  \n")

        group.SetBool("UseDefaultExcludedProperties", False)
        group.SetString("CustomExcludedProperties", "  Label2\n\n TimeStamp  \n")

        assert repo.get_excluded_types() == ["App::Part", "App::Link"]
        assert repo.get_excluded_properties() == ["Label2", "TimeStamp"]

    def test_custom_empty_list_preserved_without_default_fallback(self) -> None:
        repo, group = _make_repo()

        group.SetBool("UseDefaultExcludedTypes", False)
        group.SetString("CustomExcludedTypes", "")

        assert repo.get_excluded_types() == []
        assert repo.get_settings().excluded_types == []

    def test_default_excluded_types_are_isolated_from_mutation(self) -> None:
        repo, _ = _make_repo()

        first_read = repo.get_excluded_types()
        first_read.append("App::MutatedType")

        second_read = repo.get_excluded_types()
        assert second_read == EXCLUDED_TYPES
        assert "App::MutatedType" not in second_read

    def test_default_excluded_properties_are_isolated_from_mutation(self) -> None:
        repo, _ = _make_repo()

        first_read = repo.get_excluded_properties()
        first_read.append("MutatedProperty")

        second_read = repo.get_excluded_properties()
        assert second_read == EXCLUDED_PROPERTIES
        assert "MutatedProperty" not in second_read

    def test_default_excluded_properties_by_type_are_deep_copied(self) -> None:
        repo, _ = _make_repo()

        first_read = repo.get_excluded_properties_by_type()
        first_key = next(iter(first_read))
        first_read[first_key].append("MutatedInnerProperty")

        second_read = repo.get_excluded_properties_by_type()
        assert second_read == EXCLUDED_PROPERTIES_BY_TYPE
        assert "MutatedInnerProperty" not in second_read[first_key]

    def test_default_to_custom_prefill_marker_uses_initialized_flag(self) -> None:
        repo, _ = _make_repo()

        initial_state = repo.get_persistence_state()
        assert initial_state.excluded_types.use_default is True
        assert initial_state.excluded_types.custom_initialized is False

        switched_state = replace(
            initial_state,
            excluded_types=replace(initial_state.excluded_types, use_default=False),
        )
        repo.save_persistence_state(switched_state)

        after_first_switch = repo.get_persistence_state()
        assert after_first_switch.excluded_types.use_default is False
        assert after_first_switch.excluded_types.custom_initialized is False

        repo.save_persistence_state(
            replace(
                after_first_switch,
                excluded_types=replace(after_first_switch.excluded_types, custom_initialized=True),
            )
        )

        final_state = repo.get_persistence_state()
        assert final_state.excluded_types.custom_initialized is True

    def test_by_type_parse_and_serialization_round_trip(self) -> None:
        repo, group = _make_repo()

        initial_state = repo.get_persistence_state()
        custom_by_type = {
            "App::Part": ["Label", "Tip"],
            "Sketcher::SketchObject": ["Geometry"],
        }
        repo.save_persistence_state(
            replace(
                initial_state,
                excluded_properties_by_type=replace(
                    initial_state.excluded_properties_by_type,
                    use_default=False,
                    custom_initialized=True,
                    custom_values=custom_by_type,
                ),
            )
        )

        serialized = group.GetString("CustomExcludedPropertiesByType", "")
        assert "App::Part -> Label" in serialized
        assert "App::Part -> Tip" in serialized
        assert "Sketcher::SketchObject -> Geometry" in serialized

        reloaded_state = repo.get_persistence_state()
        assert reloaded_state.excluded_properties_by_type.custom_values == custom_by_type
        assert repo.get_excluded_properties_by_type() == custom_by_type

    def test_float_precision_read_write_and_bounds_handling(self) -> None:
        repo, group = _make_repo()

        initial_state = repo.get_persistence_state()
        repo.save_persistence_state(replace(initial_state, float_precision=5))
        assert repo.get_settings().float_precision == 5
        assert group.GetInt("FloatPrecision", -1) == 5

        repo.save_persistence_state(replace(repo.get_persistence_state(), float_precision=-8))
        assert repo.get_settings().float_precision == MIN_FLOAT_PRECISION
        assert group.GetInt("FloatPrecision", -1) == MIN_FLOAT_PRECISION

        # Save path still enforces bounds and refreshes cache.
        repo.save_persistence_state(replace(repo.get_persistence_state(), float_precision=MAX_FLOAT_PRECISION + 100))
        assert repo.get_settings().float_precision == MAX_FLOAT_PRECISION

    def test_get_settings_uses_cache_and_save_updates_cached_snapshot(self) -> None:
        repo, group = _make_repo()

        first = repo.get_settings()
        assert first.float_precision == FLOAT_PRECISION

        # External ParamGet writes do not alter cached read until save action path updates state.
        group.SetInt("FloatPrecision", 9)
        cached = repo.get_settings()
        assert cached is first
        assert cached.float_precision == FLOAT_PRECISION

        # Save path refreshes cache eagerly.
        state = repo.get_persistence_state()
        repo.save_persistence_state(replace(state, float_precision=7))
        refreshed = repo.get_settings()
        assert refreshed is not first
        assert refreshed.float_precision == 7
