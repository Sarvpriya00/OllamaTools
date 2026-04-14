# file3.py
def check_day_type(day_index):
    # Assuming 0=Monday, 6=Sunday
    if day_index == 0:
        print("It's Monday.")
    elif day_index == 5:
        print("It's Saturday.")
    elif day_index == 6:
        print("It's Sunday.")
    elif day_index >= 1 and day_index <= 4:
        print("It's a weekday.")
    else:
        print("Invalid day index.")

# Example usage:
check_day_type(2)
check_day_type(6)
check_day_type(0)
check_day_type(8)