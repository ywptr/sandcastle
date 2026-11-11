class ProviderFailed(ValueError):
    """Only sanitized fixed messages cross the provider boundary."""


class ProviderIncomplete(ProviderFailed):
    """The provider did not return completed text."""


class ProviderOutputInvalid(ProviderFailed):
    """The provider output is unusable or contains credential material."""


class SettingsInvalid(Exception):
    pass


class SettingsStorageError(Exception):
    pass


def reject_credential_output(text: str, api_key: str):
    if api_key in text:
        raise ProviderOutputInvalid("Provider output was rejected for containing credential material.")
