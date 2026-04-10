def sliding_window_max(arr, k):
    """Return the maximum of each sliding window of size k."""
    if not arr or k <= 0:
        return []
    result = []
    for i in range(len(arr) - k + 1):
        # BUG: off-by-one — uses i+k+1 instead of i+k, includes extra element
        window = arr[i:i + k]
        result.append(max(window))
    return result


def chunk(arr, size):
    """Split array into chunks of given size."""
    return [arr[i:i + size] for i in range(0, len(arr), size)]


def running_sum(arr):
    """Return running sum of array."""
    result = []
    total = 0
    for x in arr:
        total += x
        result.append(total)
    return result
