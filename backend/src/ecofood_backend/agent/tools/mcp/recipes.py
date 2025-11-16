from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import Recipe


def recipes_search(
  query: str,
  diet: Optional[str] = None,
  cuisine: Optional[str] = None,
  max_prep_minutes: Optional[int] = None,
  limit: int = 5,
) -> Dict[str, Any]:
  """
  Search for recipes matching a textual query and optional filters.

  This implementation uses a small, static catalogue so it is fully
  self-contained and deterministic for now. Later it can be wired to
  a real recipe API and/or the EcoFood database.
  """

  catalogue: List[Recipe] = [
    Recipe(
      id="salmon-bowl",
      title="Herb-Roasted Salmon Grain Bowl",
      summary="Roasted salmon over quinoa with crunchy vegetables and a citrus-herb dressing.",
      cuisine="Mediterranean",
      diet_tags=["high-protein", "omega-3", "gluten-free"],
      prep_minutes=15,
      cook_minutes=20,
      calories_per_person=520,
      ingredients=[
        {"name": "Salmon fillet", "quantity": "2", "unit": "150 g portions", "notes": "skin-on"},
        {"name": "Quinoa", "quantity": "1", "unit": "cup", "notes": "rinsed"},
        {"name": "Cherry tomatoes", "quantity": "1", "unit": "cup", "notes": "halved"},
        {"name": "Baby spinach", "quantity": "2", "unit": "cups"},
        {"name": "Olive oil", "quantity": "2", "unit": "tbsp"},
        {"name": "Citrus-herb dressing", "quantity": "1/3", "unit": "cup", "notes": "homemade or store bought"},
      ],
      steps=[
        "Preheat oven to 200°C (400°F) and line a large pan with parchment.",
        "Toss salmon with 1 tbsp olive oil, salt, pepper, and herbs; roast skin-side down for 12–14 minutes.",
        "Cook quinoa in a medium pan with 2 cups water until fluffy, about 15 minutes.",
        "Combine spinach, tomatoes, and remaining olive oil in a bowl; season lightly.",
        "Assemble bowls with quinoa base, vegetables, salmon flakes, and drizzle with dressing.",
      ],
      required_tools=["Large pan", "Medium pan", "Mixing bowl"],
    ),
    Recipe(
      id="veg-bento",
      title="Rainbow Veggie Bento",
      summary="Colorful lunchbox with marinated tofu, rice, and crisp vegetables.",
      cuisine="Japanese-inspired",
      diet_tags=["vegetarian", "high-fiber"],
      prep_minutes=20,
      cook_minutes=15,
      calories_per_person=480,
      ingredients=[
        {"name": "Firm tofu", "quantity": "300", "unit": "g", "notes": "pressed"},
        {"name": "Cooked rice", "quantity": "2", "unit": "cups"},
        {"name": "Edamame", "quantity": "1", "unit": "cup", "notes": "shelled"},
        {"name": "Carrot", "quantity": "1", "unit": "large", "notes": "julienned"},
        {"name": "Cucumber", "quantity": "0.5", "unit": "large", "notes": "sliced"},
        {"name": "Soy-ginger dressing", "quantity": "1/4", "unit": "cup"},
        {"name": "Toasted sesame seeds", "quantity": "1", "unit": "tbsp"},
      ],
      steps=[
        "Cut tofu into batons and marinate with soy-ginger dressing for at least 10 minutes.",
        "Pan-sear tofu in a medium pan with a drizzle of oil until golden on all sides.",
        "Steam edamame for 3–4 minutes until bright green; season with salt.",
        "Arrange rice, tofu, edamame, carrot, and cucumber in bento-style sections.",
        "Finish with remaining dressing and a sprinkle of sesame seeds.",
      ],
      required_tools=["Medium pan", "Small pan"],
    ),
    Recipe(
      id="oats-berries",
      title="Overnight Oats with Berries",
      summary="Creamy oats soaked overnight, topped with mixed berries and seeds.",
      cuisine="Global",
      diet_tags=["vegetarian", "quick", "breakfast"],
      prep_minutes=10,
      cook_minutes=0,
      calories_per_person=360,
      ingredients=[
        {"name": "Rolled oats", "quantity": "1", "unit": "cup"},
        {"name": "Milk or plant milk", "quantity": "1.5", "unit": "cups"},
        {"name": "Greek yogurt", "quantity": "0.5", "unit": "cup"},
        {"name": "Chia seeds", "quantity": "1", "unit": "tbsp"},
        {"name": "Mixed berries", "quantity": "1", "unit": "cup", "notes": "fresh or frozen"},
        {"name": "Honey or maple syrup", "quantity": "1", "unit": "tbsp"},
      ],
      steps=[
        "Combine oats, milk, yogurt, chia seeds, and sweetener in a mixing bowl.",
        "Stir until evenly hydrated, then portion into jars.",
        "Chill overnight; top with berries and extra seeds before serving.",
      ],
      required_tools=["Mixing bowl"],
    ),
    Recipe(
      id="veggie-chili",
      title="Smoky Three-Bean Chili",
      summary="Hearty bean chili with tomatoes, peppers, and warm spices.",
      cuisine="Tex-Mex",
      diet_tags=["vegan", "high-fiber", "batch-cooking"],
      prep_minutes=20,
      cook_minutes=40,
      calories_per_person=430,
      ingredients=[
        {"name": "Onion", "quantity": "1", "unit": "large", "notes": "diced"},
        {"name": "Bell peppers", "quantity": "2", "unit": "medium", "notes": "diced"},
        {"name": "Mixed beans", "quantity": "3", "unit": "cups", "notes": "rinsed"},
        {"name": "Crushed tomatoes", "quantity": "800", "unit": "g"},
        {"name": "Vegetable broth", "quantity": "2", "unit": "cups"},
        {"name": "Chili powder", "quantity": "1.5", "unit": "tbsp"},
        {"name": "Smoked paprika", "quantity": "1", "unit": "tsp"},
      ],
      steps=[
        "Heat oil in a large casserole and sauté onion and peppers until softened.",
        "Stir in spices and cook 1 minute until fragrant.",
        "Add beans, tomatoes, and broth; bring to a simmer.",
        "Cook uncovered for 30–35 minutes until thickened, stirring occasionally.",
        "Adjust seasoning and rest 5 minutes before serving.",
      ],
      required_tools=["Large casserole"],
    ),
    Recipe(
      id="chickpea-sheet-pan",
      title="Crispy Chickpea Sheet-Pan Dinner",
      summary="Roasted chickpeas, cauliflower, and greens with lemon tahini drizzle.",
      cuisine="Middle Eastern",
      diet_tags=["vegan", "sheet-pan", "high-fiber"],
      prep_minutes=15,
      cook_minutes=25,
      calories_per_person=410,
      ingredients=[
        {"name": "Cooked chickpeas", "quantity": "2", "unit": "cups", "notes": "patted dry"},
        {"name": "Cauliflower florets", "quantity": "4", "unit": "cups"},
        {"name": "Kale leaves", "quantity": "2", "unit": "cups", "notes": "torn"},
        {"name": "Olive oil", "quantity": "3", "unit": "tbsp"},
        {"name": "Smoked paprika", "quantity": "1", "unit": "tsp"},
        {"name": "Tahini", "quantity": "3", "unit": "tbsp"},
        {"name": "Lemon juice", "quantity": "2", "unit": "tbsp"},
      ],
      steps=[
        "Heat oven to 205°C (400°F). Toss chickpeas and cauliflower with oil, paprika, salt, and pepper.",
        "Roast on a large pan for 20 minutes, shaking halfway through.",
        "Add kale, roast 5 more minutes until crisp edges form.",
        "Whisk tahini, lemon juice, water, and pinch of salt for a pourable sauce.",
        "Serve roasted mix with generous drizzle of the sauce.",
      ],
      required_tools=["Large pan"],
    ),
    Recipe(
      id="soba-stirfry",
      title="Greens & Ginger Soba Stir-Fry",
      summary="Quick soba noodles tossed with ginger, greens, and miso-peanut sauce.",
      cuisine="Pan-Asian",
      diet_tags=["vegetarian", "quick"],
      prep_minutes=15,
      cook_minutes=10,
      calories_per_person=390,
      ingredients=[
        {"name": "Soba noodles", "quantity": "250", "unit": "g"},
        {"name": "Snow peas", "quantity": "1", "unit": "cup", "notes": "trimmed"},
        {"name": "Baby bok choy", "quantity": "2", "unit": "heads", "notes": "sliced"},
        {"name": "Ginger", "quantity": "1", "unit": "tbsp", "notes": "grated"},
        {"name": "Garlic cloves", "quantity": "2", "unit": "pieces", "notes": "minced"},
        {"name": "Miso-peanut sauce", "quantity": "1/3", "unit": "cup"},
        {"name": "Toasted peanuts", "quantity": "2", "unit": "tbsp", "notes": "chopped"},
      ],
      steps=[
        "Cook soba according to package directions; rinse under cold water and drain.",
        "Stir-fry ginger, garlic, and vegetables in a large pan over medium-high heat for 3 minutes.",
        "Add noodles and sauce, tossing to coat and heat through.",
        "Finish with peanuts and a squeeze of lime if available.",
      ],
      required_tools=["Large pan", "Medium pan"],
    ),
  ]

  q = query.lower().strip()
  diet_filter = diet.lower().strip() if diet else None
  cuisine_filter = cuisine.lower().strip() if cuisine else None

  def matches(recipe: Recipe) -> bool:
    text_blob = " ".join(
      [
        recipe.title.lower(),
        recipe.summary.lower(),
        recipe.cuisine.lower(),
        " ".join(tag.lower() for tag in recipe.diet_tags),
      ]
    )
    if q and q not in text_blob:
      return False
    if diet_filter and not any(diet_filter in tag.lower() for tag in recipe.diet_tags):
      return False
    if cuisine_filter and cuisine_filter not in recipe.cuisine.lower():
      return False
    if max_prep_minutes is not None and recipe.prep_minutes > max_prep_minutes:
      return False
    return True

  results = [r.to_dict() for r in catalogue if matches(r)]
  return {"recipes": results[: max(limit, 1)]}


TOOLS: Dict[str, Any] = {
  "recipes.search": recipes_search,
}
