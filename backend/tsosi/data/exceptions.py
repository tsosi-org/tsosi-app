from tsosi.exceptions import TsosiException, ValidationError


class DataException(TsosiException):
    pass


class DataValidationError(ValidationError):
    pass
