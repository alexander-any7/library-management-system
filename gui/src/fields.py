from urllib.parse import urlparse

from flet import TextField as FLetTextField


class TextField(FLetTextField):
    URL = "url"
    TEXT = "text"

    def __init__(self, *args, id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id
        self.on_change = self.clear_errors

    def clear_errors(self, e):
        """Clears the error text of a `TextField`
        if an `on_change` event occurs"""
        if e.control.error_text:
            e.control.error_text = None
            e.control.update()

    def validate_has_text(self):
        """validate that the field has a text"""
        if not self.value:
            self.error_text = "This field cannot be blank"
            self.update()
            return False
        return True

    def validate_is_url(self):
        """Validate that the field has a
        value and the value is a valid url"""
        if self.validate_has_text():
            result = urlparse(self.value)

            if not result.scheme and not result.netloc:
                self.error_text = "This is not a valid URL"
                self.update()
                return False

            return True

    def __get_validator_func(self, value):
        """returns a validator function from the list of available functions"""
        validators = {
            self.TEXT: self.validate_has_text,
            self.URL: self.validate_is_url,
        }
        validator_func = validators.get(value)
        if not validator_func:
            raise ValueError("Validator function not found")
        return validator_func

    def validate_and_get_value(self, type=TEXT):
        """validate the user input with a given validator function.
        default validator is `validate_has_text`
        """
        validator_func = self.__get_validator_func(type)
        return self.value if validator_func() else None
