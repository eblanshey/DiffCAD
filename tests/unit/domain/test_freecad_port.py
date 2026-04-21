# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for FreeCadPort protocol and adapter implementation.
# These tests verify that the FreeCadPort interface correctly exposes document operations
# and that the adapter properly wraps FreeCAD's runtime API.
"""Unit tests for FreeCAD port protocol and adapter."""

from freecad.diff_wb.domain.freecad_ports import FreeCadPort
from tests.fakes.fake_freecad_port import FakeFreeCadPort


class TestFreeCadPortProtocol:
    """Tests for the FreeCadPort protocol definition."""

    def test_protocol_has_get_all_open_documents_method(self) -> None:
        """Test that FreeCadPort protocol includes get_all_open_documents method."""
        # Verify the method exists in the protocol
        assert hasattr(FreeCadPort, "get_all_open_documents")

    def test_get_all_open_documents_returns_list_of_document_like(self) -> None:
        """Test that get_all_open_documents returns list[DocumentLike]."""
        # This is a protocol check - we verify through the fake implementation
        fake_port = FakeFreeCadPort()
        result = fake_port.get_all_open_documents()

        assert isinstance(result, list)

    def test_protocol_has_save_document_method(self) -> None:
        """Test that FreeCadPort protocol includes save_document method."""
        assert hasattr(FreeCadPort, "save_document")


class TestFreeCadPortGetAllOpenDocuments:
    """Tests for FreeCadPort.get_all_open_documents() method."""

    def test_returns_empty_list_when_no_documents_open(self) -> None:
        """Test that get_all_open_documents returns empty list when no documents are open."""
        fake_port = FakeFreeCadPort()

        result = fake_port.get_all_open_documents()

        assert result == []
        assert len(result) == 0

    def test_returns_list_of_document_like(self) -> None:
        """Test that get_all_open_documents returns list of DocumentLike objects."""
        # Create mock documents with FileName and Objects attributes
        mock_doc1 = type(
            "MockDoc",
            (),
            {
                "FileName": "/path/to/doc1.FCStd",
                "Objects": ["obj1", "obj2"],
                "getObject": lambda self, name: None,
                "recompute": lambda self: None,
            },
        )()

        mock_doc2 = type(
            "MockDoc",
            (),
            {
                "FileName": "/path/to/doc2.FCStd",
                "Objects": ["obj3"],
                "getObject": lambda self, name: None,
                "recompute": lambda self: None,
            },
        )()

        fake_port = FakeFreeCadPort(open_documents=[mock_doc1, mock_doc2])

        result = fake_port.get_all_open_documents()

        assert len(result) == 2
        assert isinstance(result, list)

    def test_each_document_has_filename_attribute(self) -> None:
        """Test that each returned document has FileName attribute."""
        mock_doc1 = type(
            "MockDoc",
            (),
            {
                "FileName": "/path/to/doc1.FCStd",
                "Objects": [],
                "getObject": lambda self, name: None,
                "recompute": lambda self: None,
            },
        )()

        mock_doc2 = type(
            "MockDoc",
            (),
            {
                "FileName": "/path/to/doc2.FCStd",
                "Objects": [],
                "getObject": lambda self, name: None,
                "recompute": lambda self: None,
            },
        )()

        fake_port = FakeFreeCadPort(open_documents=[mock_doc1, mock_doc2])
        result = fake_port.get_all_open_documents()

        for doc in result:
            assert hasattr(doc, "FileName")
            assert isinstance(doc.FileName, str)

    def test_each_document_has_objects_attribute(self) -> None:
        """Test that each returned document has Objects attribute."""
        mock_doc1 = type(
            "MockDoc",
            (),
            {
                "FileName": "/path/to/doc1.FCStd",
                "Objects": ["obj1", "obj2"],
                "getObject": lambda self, name: None,
                "recompute": lambda self: None,
            },
        )()

        mock_doc2 = type(
            "MockDoc",
            (),
            {
                "FileName": "/path/to/doc2.FCStd",
                "Objects": ["obj3"],
                "getObject": lambda self, name: None,
                "recompute": lambda self: None,
            },
        )()

        fake_port = FakeFreeCadPort(open_documents=[mock_doc1, mock_doc2])
        result = fake_port.get_all_open_documents()

        for doc in result:
            assert hasattr(doc, "Objects")
            assert isinstance(doc.Objects, list)

    def test_returns_correct_documents(self) -> None:
        """Test that get_all_open_documents returns the correct documents."""
        mock_doc1 = type(
            "MockDoc",
            (),
            {
                "FileName": "/path/to/doc1.FCStd",
                "Objects": ["obj1"],
                "getObject": lambda self, name: None,
                "recompute": lambda self: None,
            },
        )()

        mock_doc2 = type(
            "MockDoc",
            (),
            {
                "FileName": "/path/to/doc2.FCStd",
                "Objects": ["obj2"],
                "getObject": lambda self, name: None,
                "recompute": lambda self: None,
            },
        )()

        expected_docs = [mock_doc1, mock_doc2]
        fake_port = FakeFreeCadPort(open_documents=expected_docs)

        result = fake_port.get_all_open_documents()

        assert result == expected_docs


class TestFakeFreeCadPortGetAllOpenDocuments:
    """Tests for the FakeFreeCadPort implementation of get_all_open_documents."""

    def test_fake_returns_configured_documents(self) -> None:
        """Test that FakeFreeCadPort returns the documents configured at initialization."""
        mock_doc = type(
            "MockDoc",
            (),
            {
                "FileName": "/path/to/doc.FCStd",
                "Objects": [],
                "getObject": lambda self, name: None,
                "recompute": lambda self: None,
            },
        )()

        fake_port = FakeFreeCadPort(open_documents=[mock_doc])
        result = fake_port.get_all_open_documents()

        assert len(result) == 1
        assert result[0] == mock_doc

    def test_fake_defaults_to_empty_list(self) -> None:
        """Test that FakeFreeCadPort defaults to empty list when no documents provided."""
        fake_port = FakeFreeCadPort()
        result = fake_port.get_all_open_documents()

        assert result == []

    def test_fake_with_active_document_only(self) -> None:
        """Test that FakeFreeCadPort with only active document returns empty list for all docs."""
        mock_doc = type(
            "MockDoc",
            (),
            {
                "FileName": "/path/to/doc.FCStd",
                "Objects": [],
                "getObject": lambda self, name: None,
                "recompute": lambda self: None,
            },
        )()

        fake_port = FakeFreeCadPort(active_document=mock_doc)
        result = fake_port.get_all_open_documents()

        # Active document is separate from open documents list
        assert result == []
