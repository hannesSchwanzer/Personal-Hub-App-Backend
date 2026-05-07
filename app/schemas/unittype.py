from enum import Enum

class UnitType(str, Enum):
    miligrams = "miligrams"
    grams = "grams"
    kilograms = "kilograms"
    ounces = "ounces"
    pounds = "pounds"
    milliliters = "milliliters"
    liters = "liters"
    fluidOunces = "fluidOunces"
    gallons = "gallons"
    pieces = "pieces"
    teaspoons = "teaspoons"
    tablespoons = "tablespoons"
    centimeters = "centimeters"
    pinches = "pinches"

    @staticmethod
    def from_string(unit_string: str) -> "UnitType":
        if not unit_string:
            return UnitType.pieces

        normalized = ''.join(filter(str.isalpha, unit_string)).strip().lower()

        UNIT_ABBREVIATIONS = {
            # grams
            "g": UnitType.grams,
            "gram": UnitType.grams,
            "gramm": UnitType.grams,

            # kilograms
            "kg": UnitType.kilograms,
            "kilogram": UnitType.kilograms,
            "kilogramm": UnitType.kilograms,

            # milligrams
            "mg": UnitType.miligrams,
            "milligram": UnitType.miligrams,
            "milligramm": UnitType.miligrams,

            # milliliters
            "ml": UnitType.milliliters,
            "milliliter": UnitType.milliliters,
            "cl": UnitType.milliliters,

            # liters
            "l": UnitType.liters,
            "liter": UnitType.liters,

            # tablespoons
            "el": UnitType.tablespoons,
            "tbsp": UnitType.tablespoons,
            "tablespoon": UnitType.tablespoons,
            "eßl": UnitType.tablespoons,

            # teaspoons
            "tl": UnitType.teaspoons,
            "tsp": UnitType.teaspoons,
            "teelöffel": UnitType.teaspoons,

            # ounces
            "oz": UnitType.ounces,
            "ounce": UnitType.ounces,

            # pounds
            "lb": UnitType.pounds,
            "pound": UnitType.pounds,

            # pieces
            "stück": UnitType.pieces,
            "stk": UnitType.pieces,
            "piece": UnitType.pieces,
            "pcs": UnitType.pieces,

            # pinches
            "prise": UnitType.pinches,
            "pinches": UnitType.pinches,
            "prisen": UnitType.pinches,

            # centimeters
            "cm": UnitType.centimeters,
            "zentimeter": UnitType.centimeters,
        }

        # Exact abbreviation match
        if normalized in UNIT_ABBREVIATIONS:
            return UNIT_ABBREVIATIONS[normalized]

        # Match enum names/values
        for unit in UnitType:
            if normalized == unit.value.lower():
                return unit

        # Partial match fallback
        for key, unit in UNIT_ABBREVIATIONS.items():
            if key in normalized:
                return unit

        return UnitType.pieces
