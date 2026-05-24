"""Module responsibility: Dependency injection container for application layer.

This module wires actions and domain services together.
It's the composition root for the application layer.
"""

from .container import ApplicationContainer, create_application_container


__all__ = ["ApplicationContainer", "create_application_container"]
