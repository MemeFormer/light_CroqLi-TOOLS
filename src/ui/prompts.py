# src/ui/prompts.py

def get_user_input():
    return input("Enter your input: ")

def get_choice(choices):
    return input(f"Choose from {choices}: ")

def get_confirmation():
    return input("Are you sure? (y/n): ").lower() == 'y'

def get_multiple_choices(choices):
    return input(f"Choose multiple from {choices} (comma-separated): ").split(',')

def get_form_input(fields):
    return {field: input(f"Enter {field}: ") for field in fields}