import random
import logging

logger = logging.getLogger(__name__)

def generate_reward() -> float:
    """
    Generate random ad reward (3-5 Rs)
    Matches user expectation: "Earn 3-5 Rs each"
    """
    values = [3.0, 3.2, 3.5, 3.8, 4.0, 4.2, 4.5, 4.8, 5.0]
    reward = random.choice(values)
    logger.debug(f"Generated ad reward: {reward} Rs")
    return reward
