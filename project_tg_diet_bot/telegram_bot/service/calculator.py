""" Application that provides functionality for the Telegram bot. """
import logging.config

from omegaconf import OmegaConf


# Load logging configuration with OmegaConf
logging_config = OmegaConf.to_container(OmegaConf.load("./telegram_bot/conf/logging_config.yaml"), resolve=True)

# Apply the logging configuration
logging.config.dictConfig(logging_config)

# Configure logging
logger = logging.getLogger(__name__)

class Calculator:
    """Class that provides functionality for calculating BMR, TDEE, and macros."""
    def bmr(self, weight: float, height: float, gender: int, age: float) -> float:
        if gender == 0:  # Female
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        else:  # Male
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        return bmr


    def tdee(self, weight: float, height: float, age: float, activity_level: int, gender: int) -> float:
        bmr = self.bmr(weight, height, gender, age)
        if activity_level == 0:  # Sedentary lifestyle
            tdee = bmr * 1.2
        elif activity_level == 1:  # Low activity
            tdee = bmr * 1.375
        elif activity_level == 2:  # Moderate activity
            tdee = bmr * 1.55
        else:  # High activity
            tdee = bmr * 1.725
        return tdee

    def tdee_with_goal(self, tdee: float, goal: int) -> float:
        if goal == 0:
            tdee_goal = tdee + 500
        elif goal == 1:
            tdee_goal = tdee - 500
        else:
            tdee_goal = tdee
        return tdee_goal

    def macros(self, tdee: float) -> dict[str, float]:
        proteins = tdee * 0.30 / 4  # 1 gram of protein = 4 kcal
        fats = tdee * 0.25 / 9  # 1 gram of fat = 9 kcal
        carbs = tdee * 0.45 / 4  # 1 gram of carbohydrate = 4 kcal

        return {"proteins": proteins, "fats": fats, "carbs": carbs}
