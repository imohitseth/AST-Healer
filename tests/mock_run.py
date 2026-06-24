from tests.mock_code import get_first_element, divide_numbers, multiply_numbers

def run_calculation():
    print("Running buggy multiply_numbers...")
    result = multiply_numbers(5, 5)
    print(f"5 * 5 = {result}")

    
    print("Running buggy get_first_element...")
    result = get_first_element(["hello"])
    print(f"First element: {result}")
    
    
    print("Running buggy division...")
    result = divide_numbers(5, 0)
    print(f"5 / 0 = {result}")

if __name__ == "__main__":
    run_calculation()
