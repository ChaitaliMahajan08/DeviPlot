def factorial(n: int) -> int:
    """Computes factorial of non-negative integer n."""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n in (0, 1):
        return 1
    res = 1
    for i in range(2, n + 1):
        res *= i
    return res

def is_prime(n: int) -> bool:
    """Returns True if n is prime, False otherwise."""
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True
