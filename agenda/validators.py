from django.core.exceptions import ValidationError


class PasswordRequirementsValidator:
    def validate(self, password, user=None):
        errors = []

        if len(password) < 8:
            errors.append('La contraseña debe tener al menos 8 caracteres.')
        if not any(character.isupper() for character in password):
            errors.append('La contraseña debe incluir al menos una mayúscula.')
        if not any(character.isdigit() for character in password):
            errors.append('La contraseña debe incluir al menos un número.')
        if not any(
            not character.isalnum() and not character.isspace()
            for character in password
        ):
            errors.append(
                'La contraseña debe incluir al menos un carácter especial.'
            )

        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return (
            'Debe tener al menos 8 caracteres, una mayúscula, '
            'un número y un carácter especial.'
        )
