# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for Vector, Rotation, and Placement classes including
# creation, equality, string representation, and identity methods.
"""Unit tests for Vector, Rotation, and Placement classes."""

from freecad.diff_wb.domain import Placement, Rotation, Vector


class TestVector:
    """Tests for the Vector class."""

    def test_creation(self):
        """Test vector creation."""
        v = Vector(x=1.0, y=2.0, z=3.0)
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0

    def test_string_representation(self):
        """Test string representation."""
        v = Vector(x=1.0, y=2.0, z=3.0)
        assert str(v) == "(1.0, 2.0, 3.0)"

    def test_equality_exact(self):
        """Test exact equality."""
        v1 = Vector(1.0, 2.0, 3.0)
        v2 = Vector(1.0, 2.0, 3.0)
        assert v1 == v2

    def test_equality_approximate(self):
        """Test approximate equality for floats."""
        v1 = Vector(1.0, 2.0, 3.0)
        v2 = Vector(1.0 + 1e-10, 2.0 - 1e-10, 3.0)
        assert v1 == v2

    def test_inequality(self):
        """Test inequality."""
        v1 = Vector(1.0, 2.0, 3.0)
        v2 = Vector(1.0, 2.0, 4.0)
        assert v1 != v2


class TestRotation:
    """Tests for the Rotation class."""

    def test_creation(self):
        """Test rotation creation."""
        r = Rotation(axis_x=0.0, axis_y=0.0, axis_z=1.0, angle_degrees=45.0)
        assert r.axis_x == 0.0
        assert r.axis_y == 0.0
        assert r.axis_z == 1.0
        assert r.angle_degrees == 45.0

    def test_identity(self):
        """Test identity rotation."""
        r = Rotation.identity()
        assert r.axis_x == 0.0
        assert r.axis_y == 0.0
        assert r.axis_z == 1.0
        assert r.angle_degrees == 0.0

    def test_string_representation(self):
        """Test string representation."""
        r = Rotation(0.0, 0.0, 1.0, 90.0)
        assert "Angle=90" in str(r)

    def test_equality(self):
        """Test rotation equality."""
        r1 = Rotation(0.0, 0.0, 1.0, 45.0)
        r2 = Rotation(0.0, 0.0, 1.0, 45.0)
        assert r1 == r2


class TestPlacement:
    """Tests for the Placement class."""

    def test_creation(self):
        """Test placement creation."""
        pos = Vector(1.0, 2.0, 3.0)
        rot = Rotation(0.0, 0.0, 1.0, 45.0)
        p = Placement(position=pos, rotation=rot)
        assert p.position == pos
        assert p.rotation == rot

    def test_identity(self):
        """Test identity placement."""
        p = Placement.identity()
        assert p.position == Vector(0.0, 0.0, 0.0)
        assert p.rotation == Rotation.identity()

    def test_equality(self):
        """Test placement equality."""
        p1 = Placement(Vector(1.0, 2.0, 3.0), Rotation(0.0, 0.0, 1.0, 45.0))
        p2 = Placement(Vector(1.0, 2.0, 3.0), Rotation(0.0, 0.0, 1.0, 45.0))
        assert p1 == p2
