"""Explicit registry for frozen PlanSpace action-domain versions."""

from __future__ import annotations

from types import ModuleType


_KNOWN = {
    "planspace_generic_household_v0.1-candidate": "planspace.generic_domain_v0_1",
    "planspace_generic_household_v0.4-candidate": "planspace.generic_domain",
}


def get_generic_domain(version: str) -> ModuleType:
    """Return the implementation whose version exactly matches ``version``."""

    try:
        module_name = _KNOWN[version]
    except KeyError as error:
        known = ", ".join(sorted(_KNOWN))
        raise ValueError(f"unknown generic action-domain version {version!r}; known: {known}") from error
    if module_name.endswith("generic_domain_v0_1"):
        from . import generic_domain_v0_1 as domain
    else:
        from . import generic_domain as domain
    if domain.GENERIC_DOMAIN_VERSION != version:
        raise RuntimeError(f"domain registry resolved {domain.GENERIC_DOMAIN_VERSION}, expected {version}")
    return domain
