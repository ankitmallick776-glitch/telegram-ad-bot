import random

def generate_reward() -> float:
    values = [3.0, 3.2, 3.5, 3.8, 4.0, 4.2, 4.5, 4.8, 5.0]
    return random.choice(values)
