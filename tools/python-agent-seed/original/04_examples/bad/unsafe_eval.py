"""Bad example: evaluating untrusted input."""


def calculate(expression: str):
    return eval(expression)


# Problem:
# eval can execute arbitrary code. Use a real parser, safe expression evaluator, or explicit operation mapping.
