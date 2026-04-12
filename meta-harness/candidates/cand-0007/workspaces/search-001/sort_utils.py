"""Sort utility — fixed version."""


def sort_numbers(numbers):
    """Sort a list of numbers in ascending order.
    
    Handles empty input, duplicates, and negative numbers correctly.
    """
    if not numbers:
        return []
    
    # Copy to avoid mutating the input
    result = list(numbers)
    
    # Bubble sort (correct implementation preserving duplicates)
    n = len(result)
    for i in range(n):
        for j in range(i + 1, n):
            if result[i] > result[j]:
                result[i], result[j] = result[j], result[i]
    
    return result
