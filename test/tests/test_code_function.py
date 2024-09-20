from aiproxy.functions.code import run_code
from aiproxy.streaming import StreamWriter

def run(streamer:StreamWriter):
    data = {
        "PIZZA_RECIPES": [
            {
                "name": "Margherita",
                "ingredients": ["tomato", "mozzarella", "basil"]
            },
            {
                "name": "Pepperoni",
                "ingredients": ["tomato", "mozzarella", "pepperoni"]
            },
            {
                "name": "Hawaiian",
                "ingredients": ["tomato", "mozzarella", "ham", "pineapple"]
            }
        ]
    }
    ## Note: The code below has a spelling mistake in the lambda function, this should cause an error which is picked up and fixed by the function
    x = run_code("def find_recipe_with_most_ingredients(data):\n    recipes = data.get('PIZZA_RECIPES')\n    max_ingredients_recipe = max(recipes, key=lambda recipe: len(recip['ingredients']))\n    return max_ingredients_recipe", "find_recipe_with_most_ingredients", vars=data)
    print(x)
