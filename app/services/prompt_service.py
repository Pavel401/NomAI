import base64


class PromptService:
    """
    Service class for handling prompt generation for nutrition analysis.
    """

    @staticmethod
    def get_dietary_context(
        selectedGoal: list = None,
        selectedDiet: list = None,
        selectedAllergy: list = None,
    ) -> str:
        """Generate dietary context string based on user preferences."""
        dietary_context = ""
        if selectedDiet:
            dietary_context += f"The user follows these dietary preferences: {', '.join(selectedDiet)}. "
        if selectedAllergy:
            dietary_context += (
                f"The user has allergies to: {', '.join(selectedAllergy)}. "
            )
        if selectedGoal:
            dietary_context += (
                f"The user has the following health goals: {', '.join(selectedGoal)}. "
            )
        return dietary_context

    @staticmethod
    def get_user_message_instruction(user_message: str = None) -> str:
        """Generate user message instruction for the prompt."""
        return (
            f"The user states: '{user_message}'. Only consider what is visible in the image and what the user explicitly mentions. "
            "Do not assume any additional ingredients like sausages unless clearly visible. "
            if user_message
            else "Only include ingredients that are clearly visible in the image. Do not guess hidden components such as meats or sauces unless clearly identifiable."
        )

    @staticmethod
    def get_nutrition_analysis_prompt_for_image(
        user_message: str = None,
        selectedGoal: list = None,
        selectedDiet: list = None,
        selectedAllergy: list = None,
        imageUrl: str = None,
    ) -> str:
        """Generate the complete nutrition analysis prompt."""
        dietary_context = PromptService.get_dietary_context(
            selectedGoal, selectedDiet, selectedAllergy
        )
        user_message_instruction = PromptService.get_user_message_instruction(
            user_message
        )

        return f"""
Analyze the food product, product name and its nutrition label. Provide response in this strict JSON format:

Some dietary context is provided to you.

{dietary_context}

ANALYSIS FRAMEWORK:

STEP 1 - QUANTITY IDENTIFICATION:
- Extract EXACT quantity from user description
- Identify specific brand if mentioned
- Note any size specifications (mini, regular, king-size, etc.)

STEP 2 - DATABASE LOOKUP:
- Find authoritative nutritional data for the specific food/brand
- Use per-unit values (per cookie, per chip, per slice)
- Verify data accuracy across multiple sources

STEP 3 - MATHEMATICAL CALCULATION:
- Multiply per-unit values by exact quantity mentioned
- Calculate total calories: (per-unit calories) × (quantity)
- Calculate total macros: (per-unit macro) × (quantity)
- Ensure macro calories sum correctly

STEP 4 - CONTEXTUAL ANALYSIS:
- Consider dietary preferences and restrictions
- Assess health impact relative to user's goals
- Provide evidence-based recommendations

OUTPUT REQUIREMENTS:
1. foodName: Use EXACT food name from user description
2. Nutritional values: Must reflect TOTAL amount described, not per-unit
3. Portion size: Convert to appropriate unit (gram weight preferred for accuracy)
4. Health assessment: Evidence-based, considering user's dietary context

MANDATORY JSON STRUCTURE:
1. The main food name (foodName)
   - If the user mentioned a specific food name in their message, use that exact name
   - If not a food image, return an error message stating "No food detected in image"

2. A detailed list of all identified ingredients with these properties for each:
   - name: Precise ingredient name
   - calories: Estimated calories (integer)
   - protein: Protein content in grams (integer)
   - carbs: Carbohydrate content in grams (integer)
   - fiber: Fiber content in grams (integer)
   - fat: Fat content in grams (integer)
   - healthScore: Rating from 0-10 where 10 is healthiest (integer)
   - healthComments: Brief assessment of nutritional value. Include guidance to "enjoy" or "eat in moderation" as appropriate.

3. Portion information:
   - portion: Unit type (must be one of: "cup", "gram",  "slices", "piece",)
   - portionSize: Numeric amount (can be decimal like 0.5) 
   - Portion size should be based on the most common serving size for the food item
   - If the portion size is not clear, use a reasonable estimate based on the image

4. Primary nutritional concerns for this food:
   - issue: Brief name of the nutritional concern (e.g. "High sodium", "Low protein", "Excessive sugar")
   - explanation: Clear explanation of the health impact of this concern
   - recommendations: List of complementary foods to add, with:
     * food: Name of food to add
     * quantity: Recommended amount
     * reasoning: How this food addresses the nutritional concern

5. Suggest 2-3 healthier alternative ingredients when applicable with same nutritional property structure

6. confidenceScore: A score from 0-10 indicating the confidence in the analysis (integer)

7. ImageURL should be based on the prompt user provides , if no image is provided return empty string

The final JSON should exactly follow this structure:
{{
  "status": "SUCCESS",
  "message": string,
  "foodName": string,
  "portion": string (one of: "cup", "gram", "slices", "piece"),
  "portionSize": number,
  "imageUrl": string {imageUrl if imageUrl else ""},
  "ingredients": [
    {{
      "name": string,
      "calories": integer,
      "protein": integer,
      "carbs": integer,
      "fiber": integer,
      "fat": integer,
      "sugar": integer (optional),
      "sodium": integer (optional),
      "healthScore": integer (0-10),
      "healthComments": string
    }}
  ],
  "primaryConcerns": [
    {{
      "issue": string,
      "explanation": string,
      "recommendations": [
        {{
          "food": string,
          "quantity": string,
          "reasoning": string
        }}
      ]
    }}
  ],
  "suggestAlternatives": [
    {{same structure as ingredients}}
  ],
  "overallHealthScore": integer (0-10),
  "overallHealthComments": string
}}

If the image does not contain food, return:
{{
  "status": "ERROR",
  "message": "No food detected in image",
  "foodName": "Error: No food detected",
  "portion": "cup",
  "portionSize": 0,
  "ingredients": [],
  "primaryConcerns": [],
  "suggestAlternatives": [],
  "overallHealthScore": 0,
  "overallHealthComments": "No food detected in image"
}}

If the user has provided specific information about the food name, portion size, or nutritional content in their message, prioritize that information in your analysis.

Ensure all nutrition values are reasonable estimates for the visible portions and that the JSON is valid and properly formatted according to the schema.

{user_message_instruction}

User message: {user_message}
        """

    @staticmethod
    def get_nutrition_analysis_prompt_from_description(
        user_message: str = None,
        selectedGoal: list = None,
        selectedDiet: list = None,
        selectedAllergy: list = None,
    ) -> str:
        """Generate the complete nutrition analysis prompt from a description."""
        dietary_context = PromptService.get_dietary_context(
            selectedGoal, selectedDiet, selectedAllergy
        )
        user_message_instruction = PromptService.get_user_message_instruction(
            user_message
        )

        return f"""
NUTRITION ANALYSIS TASK:
You are a nutrition expert. Analyze the food description and return ONLY valid JSON.

USER INPUT: "{user_message}"
DIETARY CONTEXT: {dietary_context}

If it's not a  food  return:
{{
  "message": "No food detected in image",
  "foodName": "Error: No food detected",
  "portion": "cup",
  "portionSize": 0,
  "ingredients": [],
  "primaryConcerns": [],
  "suggestAlternatives": [],
  "overallHealthScore": 0,
  "overallHealthComments": "No food detected in image"
}}

INSTRUCTIONS:
1. Extract EXACT quantity from description (e.g., "2 Oreo cookies" = analyze 2 cookies total)
2. Use official nutrition data (USDA/manufacturer labels)
3. Calculate TOTAL nutrition for the exact quantity mentioned
4. Keep all comments under word limits
5. Use integers for all numeric values (no decimals)
6. Use third person ("This food is..." not "You...")
7. overall health score from 0-10, with 10 being healthiest
8. Provide evidence-based recommendations
9. overallComments: MAX 40 words , explain if the food is healthy or not and why 
10. confidenceScore: Score from 0-10 indicating confidence in analysis
11. Suggest 3 alternative foods with better nutritional properties




CRITICAL ANALYSIS REQUIREMENTS:
1. EXACT QUANTITY MATCHING: Parse the EXACT quantity mentioned in the user's description. If they say "2 Oreo cookies", analyze specifically for 2 cookies, not 1 or a generic serving.

2. PRECISE NUTRITIONAL LOOKUP: Use authoritative nutrition data:
   - USDA FoodData Central as primary source
   - Official manufacturer nutrition labels (Nabisco for Oreos, etc.)
   - Peer-reviewed nutritional databases
   - Cross-reference multiple sources for accuracy

3. MATHEMATICAL PRECISION: 
   - Calculate totals by multiplying per-unit values by exact quantity
   - Example: If 1 Oreo = 53 calories, then 2 Oreos = 106 calories
   - Round to nearest whole number for calories, maintain precision for macros

4. BRAND-SPECIFIC DATA: When brand names are mentioned (Oreo, Lay's, etc.), use that specific brand's nutritional profile, not generic equivalents.

5. VERIFICATION CROSS-CHECK: Before finalizing values, verify that:
   - Total calories match sum of macros (protein×4 + carbs×4 + fat×9)
   - Values are realistic for the food type and quantity
   - Portion size reflects the actual amount described



QUALITY ASSURANCE CHECKLIST:
✓ Calories match the exact quantity described
✓ Macro totals are mathematically consistent  
✓ Brand-specific data used when applicable
✓ Portion size reflects actual amount consumed
✓ Health scores are evidence-based
✓ Recommendations are specific and actionable

CRITICAL RULES:
- Return ONLY valid JSON, no extra text
- All numbers must be integers (no decimals)
- Comments must be under word limits
- Use third person ("This food is..." not "You...")
- Calculate for EXACT quantity mentioned
        """


@staticmethod
def get_nutrition_analysis_prompt_from_description(
    user_message: str = None,
    selectedGoal: list = None,
    selectedDiet: list = None,
    selectedAllergy: list = None,
):
    """Generate the complete nutrition analysis prompt from a description."""
    dietary_context = PromptService.get_dietary_context(
        selectedGoal, selectedDiet, selectedAllergy
    )
    user_message_instruction = PromptService.get_user_message_instruction(user_message)

    return f"""
NUTRITION ANALYSIS TASK"""
