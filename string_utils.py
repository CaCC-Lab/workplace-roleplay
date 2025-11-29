def reverse_string(s):
    """
    Reverses a given string.
    
    Args:
        s (str): The string to reverse
        
    Returns:
        str: The reversed string
    """
    return s[::-1]


# Example usage and tests
if __name__ == "__main__":
    # Test cases
    test_cases = [
        "hello",
        "world",
        "Python",
        "12345",
        "",
        "a",
        "Hello, World!"
    ]
    
    print("Testing reverse_string function:")
    for test in test_cases:
        result = reverse_string(test)
        print(f"Input: '{test}' -> Output: '{result}'")