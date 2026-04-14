# file1.py
def check_number(num):
    if num > 10:
        print("Number is large.")
    elif num > 5:
        print("Number is medium.")
    elif num > 0:
        print("Number is small positive.")
    else:
        print("Number is zero or negative.")

# Example usage:
check_number(15)
check_number(7)
check_number(3)
check_number(-2)