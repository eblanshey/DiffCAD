"""File responsibility: Unit tests for Result class.

This module contains unit tests for the generic Result dataclass used across
all actions in the application layer. Tests cover factory methods, constructor
usage, and edge cases for both success and failure scenarios.
"""

from freecad.diff_wb.application.actions.result_models import Result


class TestResultSuccess:
    """Tests for successful Result creation and access."""

    def test_success_factory_method_returns_success_result(self) -> None:
        """Test that success() factory method creates a success result."""
        data = {"key": "value"}
        result = Result.success(data)

        assert result.is_success is True
        assert result.data == data
        assert result.message is None

    def test_success_with_string_data(self) -> None:
        """Test success factory with string data."""
        result = Result.success("some string")

        assert result.is_success is True
        assert result.data == "some string"
        assert result.message is None

    def test_success_with_none_data(self) -> None:
        """Test success factory with None data."""
        result = Result.success(None)

        assert result.is_success is True
        assert result.data is None
        assert result.message is None

    def test_success_with_integer_data(self) -> None:
        """Test success factory with integer data."""
        result = Result.success(42)

        assert result.is_success is True
        assert result.data == 42
        assert result.message is None

    def test_success_with_list_data(self) -> None:
        """Test success factory with list data."""
        data = [1, 2, 3]
        result = Result.success(data)

        assert result.is_success is True
        assert result.data == data
        assert result.message is None


class TestResultFailure:
    """Tests for failed Result creation and access."""

    def test_failure_factory_method_returns_failure_result(self) -> None:
        """Test that failure() factory method creates a failure result."""
        error_message = "Something went wrong"
        result = Result.failure(error_message)

        assert result.is_success is False
        assert result.data is None
        assert result.message == error_message

    def test_failure_with_empty_message(self) -> None:
        """Test failure factory with empty message."""
        result = Result.failure("")

        assert result.is_success is False
        assert result.data is None
        assert result.message == ""

    def test_failure_with_long_error_message(self) -> None:
        """Test failure factory with long error message."""
        message = "This is a very detailed error message explaining what went wrong and why."
        result = Result.failure(message)

        assert result.is_success is False
        assert result.data is None
        assert result.message == message


class TestResultDirectConstruction:
    """Tests for direct Result construction using constructor."""

    def test_direct_construction_success(self) -> None:
        """Test creating Result directly with success parameters."""
        result = Result(is_success=True, data={"key": "value"}, message=None)

        assert result.is_success is True
        assert result.data == {"key": "value"}
        assert result.message is None

    def test_direct_construction_failure(self) -> None:
        """Test creating Result directly with failure parameters."""
        result = Result(is_success=False, data=None, message="Error occurred")

        assert result.is_success is False
        assert result.data is None
        assert result.message == "Error occurred"

    def test_direct_construction_with_default_values(self) -> None:
        """Test creating Result with default values for optional parameters."""
        # Test with only required parameter
        result = Result(is_success=True)

        assert result.is_success is True
        assert result.data is None
        assert result.message is None


class TestResultDefaultValues:
    """Tests for Result default values."""

    def test_default_data_is_none(self) -> None:
        """Test that default data value is None."""
        result = Result(is_success=True)

        assert result.data is None

    def test_default_message_is_none(self) -> None:
        """Test that default message value is None."""
        result = Result(is_success=True)

        assert result.message is None


class TestResultDataAccess:
    """Tests for accessing data on success and failure results."""

    def test_access_data_on_success_result(self) -> None:
        """Test that data can be accessed on success result."""
        expected_data = {"nested": {"key": "value"}}
        result = Result.success(expected_data)

        assert result.data == expected_data
        assert result.data["nested"]["key"] == "value"

    def test_access_data_on_failure_result_returns_none(self) -> None:
        """Test that data access on failure returns None."""
        result = Result.failure("Error")

        assert result.data is None

    def test_message_is_none_on_success(self) -> None:
        """Test that message is None on success result."""
        result = Result.success("data")

        assert result.message is None


class TestResultImmutability:
    """Tests for Result attribute modification."""

    def test_can_modify_is_success(self) -> None:
        """Test that is_success can be modified (dataclass is mutable by default)."""
        result = Result.success("data")
        assert result.is_success is True

        result.is_success = False
        assert result.is_success is False

    def test_can_modify_data(self) -> None:
        """Test that data can be modified."""
        result = Result.success("original")
        assert result.data == "original"

        result.data = "modified"
        assert result.data == "modified"
