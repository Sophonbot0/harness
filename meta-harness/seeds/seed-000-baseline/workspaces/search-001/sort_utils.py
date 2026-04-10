"""Sort utility — has bugs that need fixing."""


def sort_numbers(numbers):
    """Sort a list of numbers in ascending order.
    
    Known issues:
    - Crashes on empty input
    - Doesn't handle duplicates correctly  
    - Returns wrong order for negative numbers
    """
    if len(numbers) == 0:
        return []
    if len(numbers) == 1:
        return list(numbers)
    
    # Bubble sort (fixed)
    result = list(numbers)  # copy to avoid mutating input
    for i in range(len(result)):
        for j in range(i + 1, len(result)):
            if result[i] > result[j]:
                result[i], result[j] = result[j], result[i]
    
    return result
