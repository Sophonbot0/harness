def solve(items):
    if items is None:
        raise TypeError('items must not be None')
    return sorted(set(items))
