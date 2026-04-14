# file4.py
def check_temperature(temp):
    if temp > 30:
        print("It's very hot. Stay hydrated.")
    elif temp >= 20:
        print("It's pleasant weather.")
    elif temp >= 10:
        print("It's cool. A light jacket is recommended.")
    else:
        print("It's cold. Dress warmly.")

# Example usage:
check_temperature(32)
check_temperature(22)
check_temperature(15)
check_temperature(5)