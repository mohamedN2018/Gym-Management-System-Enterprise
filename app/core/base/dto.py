"""Base Data Transfer Object.

DTOs are the only types allowed to cross layer boundaries (Part 2: *never expose ORM models
directly*). Built on Pydantic v2 for declarative validation and (de)serialization.

``from_attributes=True`` lets a DTO be built straight from an ORM entity
(``MemberDTO.model_validate(member_entity)``) without the entity leaking past the service.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BaseDTO(BaseModel):
    """Common configuration for all DTOs.

    - ``from_attributes`` — construct from ORM/attribute objects.
    - ``extra="forbid"``  — reject unknown fields (defensive: *never trust input*).
    - ``str_strip_whitespace`` — trim incoming strings.
    - ``validate_assignment`` — re-validate on mutation so DTOs can't drift into invalid state.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )
