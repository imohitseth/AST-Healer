def add_numbers(a: int, b: int) -> int:
    
    return a + b

def multiply_numbers(a: int, b: int) -> int:
    return a * b

def get_first_element(lst: list) -> any:

    return lst[0]

def divide_numbers(a: int, b: int) -> float:
    if b == 0:
        return 0.0
    return a / b

#make some errors in the function before running and the agent will auto detect it upon running the task and rectify it.
'''
Examples of the errors:
i) a*b can be re-written as a.multiply(b)
ii) lst[0] can be re-written as lst[1] (index out of bound error)
iii) the if condition (if b==0) can be removed from the division function (zero division error)
'''
