import pytest
from tests.mock_code import add_numbers, multiply_numbers, get_first_element, divide_numbers

def test_add_numbers():
    assert add_numbers(2, 3) == 5
    assert add_numbers(-1, 1) == 0

def test_multiply_numbers():
    assert multiply_numbers(2, 3) == 6
    assert multiply_numbers(5, 5) == 25

def test_get_first_element():
    assert get_first_element([10, 20]) == 10
    assert get_first_element(["hello"]) == "hello"

def test_divide_numbers_normal():
    assert divide_numbers(10, 2) == 5.0

def test_divide_numbers_zero():
    assert divide_numbers(5, 0) == 0.0
