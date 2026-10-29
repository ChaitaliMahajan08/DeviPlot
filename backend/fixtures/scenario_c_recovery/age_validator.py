def is_valid_age(age: int) -> bool:
    """
    Returns True if person is of legal adult age (18 or older).
    """
    if age < 0 or age > 130:
        return False
    # Defect: strictly greater than 18 excludes legal age of 18
    return age > 18
