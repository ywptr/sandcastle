"""Shared domain lookup/intent errors, independent of orchestration and transport."""


class MediaDomainNotFound(ValueError):
    pass


class InvalidMediaIntent(ValueError):
    pass
