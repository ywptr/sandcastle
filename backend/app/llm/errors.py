class ProviderFailed(ValueError):
    """Only sanitized fixed messages cross the provider boundary."""


class SettingsInvalid(Exception):
    pass


class SettingsStorageError(Exception):
    pass


def reject_credential_output(text: str, api_key: str):
    if api_key in text:
        raise ProviderFailed("Provider output was rejected for containing credential material.")
