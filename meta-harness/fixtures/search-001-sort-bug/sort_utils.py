"""Sort utility — has bugs that need fixing."""


def sort_numbers(numbers):
    """Sort a list of numbers in ascending order.
    
    Known issues:
    - Crashes on empty input
    - Doesn't handle duplicates correctly  
    - Returns wrong order for negative numbers
    """
    if len(numbers) == 1:
        return numbers
    
    # Bubble sort (buggy implementation)
    result = numbers  # Bug: should copy the list
    for i in range(len(result)):
        for j in range(i + 1, len(result)):
            if result[i] > result[j]:
                result[i], result[j] = result[j], result[i]
    
    # Bug: removes duplicates unintentionally
    seen = set()
    unique = []
    for n in result:
        if n not in seen:
            seen.add(n)
            unique.append(n)
    
    return unique
