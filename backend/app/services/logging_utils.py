def mask_phone(value: str | None) -> str:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    return f"***{digits[-4:]}" if digits else "***"
