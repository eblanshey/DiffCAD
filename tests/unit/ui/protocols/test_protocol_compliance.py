"""File responsibility: Protocol compliance tests for DiffView and SnapshotView.

These tests use runtime validation to ensure that view implementations
properly conform to their protocol contracts. Since mypy's structural typing
doesn't enforce exact signature matching, these runtime checks provide
the necessary validation at test time.

The tests verify:
1. All required methods exist
2. Method signatures are compatible with protocols
3. Views can be instantiated and used as protocol types
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from freecad.diff_wb.ui.protocols.diff_view import DiffView
from freecad.diff_wb.ui.protocols.snapshot_view import SnapshotView
from tests.unit.ui.protocols.protocol_validation import (
    assert_protocol_compliance,
    validate_protocol_compliance,
)


class TestDiffViewProtocolCompliance:
    """Tests verifying DiffView protocol compliance."""

    def test_diff_panel_view_implements_diff_view(self) -> None:
        """DiffPanelView must implement all DiffView protocol methods."""
        from freecad.diff_wb.ui.views.diff_panel_view import DiffPanelView

        # This will raise AssertionError if there are violations
        assert_protocol_compliance(DiffPanelView, DiffView)

    def test_diff_view_required_methods_exist(self) -> None:
        """Verify all DiffView methods exist in implementation."""
        from freecad.diff_wb.ui.views.diff_panel_view import DiffPanelView
        from tests.unit.ui.protocols.protocol_validation import get_protocol_methods

        protocol_methods = get_protocol_methods(DiffView)

        for method_name in protocol_methods:
            assert hasattr(DiffPanelView, method_name), f"Missing method: {method_name}"
            assert callable(getattr(DiffPanelView, method_name)), f"Method not callable: {method_name}"

    def test_show_loading_signature_compatibility(self) -> None:
        """show_loading should accept at least no arguments (protocol contract)."""
        import inspect

        from freecad.diff_wb.ui.views.diff_panel_view import DiffPanelView

        sig = inspect.signature(DiffPanelView.show_loading)
        params = list(sig.parameters.values())

        # Remove 'self' if present
        if params and params[0].name == "self":
            params = params[1:]

        # All regular parameters must have defaults (protocol allows calling with no args)
        # VAR_KEYWORD (**kwargs) and VAR_POSITIONAL (*args) don't have defaults but are flexible
        for param in params:
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue  # These are inherently optional
            assert param.default != inspect.Parameter.empty, (
                f"show_loading parameter '{param.name}' has no default, but protocol allows calling with no arguments"
            )

    def test_show_diff_tree_accepts_list(self) -> None:
        """show_diff_tree must accept list parameter."""
        import inspect

        from freecad.diff_wb.ui.views.diff_panel_view import DiffPanelView

        sig = inspect.signature(DiffPanelView.show_diff_tree)
        params = list(sig.parameters.values())

        # Remove 'self' if present
        if params and params[0].name == "self":
            params = params[1:]

        assert len(params) >= 1, "show_diff_tree missing 'nodes' parameter"
        assert params[0].name == "nodes", f"Expected 'nodes' parameter, got '{params[0].name}'"

    def test_show_summary_accepts_three_integers(self) -> None:
        """show_summary must accept added, deleted, modified integers."""
        import inspect

        from freecad.diff_wb.ui.views.diff_panel_view import DiffPanelView

        sig = inspect.signature(DiffPanelView.show_summary)
        params = list(sig.parameters.values())

        # Remove 'self' if present
        if params and params[0].name == "self":
            params = params[1:]

        param_names = [p.name for p in params]
        expected = ["added", "deleted", "modified"]

        for name in expected:
            assert name in param_names, f"show_summary missing '{name}' parameter"


class TestSnapshotViewProtocolCompliance:
    """Tests verifying SnapshotView protocol compliance."""

    def test_diff_panel_view_implements_snapshot_view(self) -> None:
        """DiffPanelView must implement all SnapshotView protocol methods."""
        from freecad.diff_wb.ui.views.diff_panel_view import DiffPanelView

        # This will raise AssertionError if there are violations
        assert_protocol_compliance(DiffPanelView, SnapshotView)

    def test_snapshot_view_required_methods_exist(self) -> None:
        """Verify all SnapshotView methods exist in implementation."""
        from freecad.diff_wb.ui.views.diff_panel_view import DiffPanelView
        from tests.unit.ui.protocols.protocol_validation import get_protocol_methods

        protocol_methods = get_protocol_methods(SnapshotView)

        for method_name in protocol_methods:
            assert hasattr(DiffPanelView, method_name), f"Missing method: {method_name}"
            assert callable(getattr(DiffPanelView, method_name)), f"Method not callable: {method_name}"

    def test_show_success_signature(self) -> None:
        """show_success must accept snapshot_name string."""
        import inspect

        from freecad.diff_wb.ui.views.diff_panel_view import DiffPanelView

        sig = inspect.signature(DiffPanelView.show_success)
        params = list(sig.parameters.values())

        # Remove 'self' if present
        if params and params[0].name == "self":
            params = params[1:]

        assert len(params) >= 1, "show_success missing 'snapshot_name' parameter"
        assert params[0].name == "snapshot_name", f"Expected 'snapshot_name' parameter, got '{params[0].name}'"

    def test_show_snapshots_accepts_list(self) -> None:
        """show_snapshots must accept list of SnapshotSummary."""
        import inspect

        from freecad.diff_wb.ui.views.diff_panel_view import DiffPanelView

        sig = inspect.signature(DiffPanelView.show_snapshots)
        params = list(sig.parameters.values())

        # Remove 'self' if present
        if params and params[0].name == "self":
            params = params[1:]

        assert len(params) >= 1, "show_snapshots missing 'snapshots' parameter"
        assert params[0].name == "snapshots", f"Expected 'snapshots' parameter, got '{params[0].name}'"


class TestProtocolValidationUtility:
    """Tests for the protocol validation utility itself."""

    def test_validation_catches_missing_method(self) -> None:
        """Validator should detect missing protocol methods."""

        class IncompleteView:
            def show_loading(self) -> None:
                pass

            # Missing other required methods

        violations = validate_protocol_compliance(IncompleteView, DiffView, raise_on_error=False)

        assert len(violations) > 0, "Should detect missing methods"
        assert any("Missing method" in v for v in violations), "Should report missing methods"

    def test_validation_passes_for_compliant_class(self) -> None:
        """Validator should pass for a fully compliant implementation."""

        class CompliantView:
            def show_loading(self) -> None:
                pass

            def show_diff_tree(self, nodes: list[Any], git_path: str = "") -> None:
                pass

            def show_diff_trees(self, diffs: list[Any]) -> None:
                pass

            def show_summary(self, added: int, deleted: int, modified: int) -> None:
                pass

            def show_error(self, message: str) -> None:
                pass

            def show_properties(self, properties: list[Any]) -> None:
                pass

            def show_repository(self, repo: object | None) -> None:
                pass

            def set_refresh_callback(self, callback: Callable[[], None]) -> None:
                pass

            def set_history_selection_callback(self, callback: Callable[[object], None]) -> None:
                pass

            def set_add_button_callback(self, callback: Callable[[str], None]) -> None:
                pass

        violations = validate_protocol_compliance(CompliantView, DiffView, raise_on_error=False)
        assert violations == [], f"Should have no violations, got: {violations}"
