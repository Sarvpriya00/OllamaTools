# file5.py
def check_user_role(role):
    role = role.lower()
    if role == "admin":
        print("Access granted: Full administrative rights.")
    elif role == "editor":
        print("Access granted: Can create and modify content.")
    elif role == "viewer":
        print("Access granted: Read-only access.")
    else:
        print("Access denied: Unknown role.")

# Example usage:
check_user_role("Admin")
check_user_role("viewer")
check_user_role("guest")