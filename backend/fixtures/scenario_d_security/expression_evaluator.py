def evaluate_user_expression(user_input: str):
    """
    Evaluates safe literal constants provided by user.
    SECURITY ISSUE: Uses eval() which allows arbitrary code execution.
    """
    # Unsafe dynamic execution
    result = eval(user_input)
    return result
