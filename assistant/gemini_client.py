import google.generativeai as genai
import config
import json
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Configure Gemini client
genai.configure(api_key=config.GEMINI_API_KEY)

# Model for intent detection
model_intent = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest",
    generation_config={"temperature": 0.1},
    safety_settings=config.GEMINI_SAFETY_SETTINGS,
    system_instruction=config.INTENT_DETECTION_SYSTEM_PROMPT
)

# Model for general conversation
model_chat = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest",
    generation_config=config.GEMINI_GENERATION_CONFIG,
    safety_settings=config.GEMINI_SAFETY_SETTINGS,
    system_instruction=config.CAREER_ADVISOR_SYSTEM_PROMPT
)

# Model instance for suggestion generation (JSON focus)
model_suggestion = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest",
    generation_config=config.GEMINI_SUGGESTION_CONFIG,
    safety_settings=config.GEMINI_SAFETY_SETTINGS,
    # No system instruction needed here as it's provided in the prompt template
)


def generate_conversational_response(prompt: str, chat_history: list = None):
    """
    Generates the main conversational response using the main model and history.
    Returns the raw response text and the history entry part for the model.
    """
    try:
        formatted_history = []
        if chat_history:
            for entry in chat_history:
                parts_content = entry.get('parts', [])
                if isinstance(parts_content, list) and all(isinstance(p, str) for p in parts_content):
                     formatted_history.append({'role': entry.get('role'), 'parts': parts_content})
                else: print(f"Warning: Skipping potentially malformed history entry: {entry}")

        chat = model_chat.start_chat(history=formatted_history or [])
        response = chat.send_message(prompt)

        raw_response_text = response.text
        # Ensure history part is always a list of strings
        new_history_entry_model = {'role': 'model', 'parts': [str(raw_response_text)]}
        return raw_response_text, new_history_entry_model

    except Exception as e:
        print(f"Error generating Gemini response: {e}")
        error_message = "I'm sorry, I encountered an error trying to process that. Could you try rephrasing? 🤔"
        # Add more specific error checking if needed (e.g., for safety blocks)
        if hasattr(e, 'response') and hasattr(e.response, 'prompt_feedback'):
             error_message = "I apologize, but I can't provide a response due to safety guidelines. Could we focus on another aspect? 🙏"
        elif "response.prompt_feedback" in str(e).lower():
             error_message = "I apologize, but I can't provide a response due to safety guidelines. Could we focus on another aspect? 🙏"

        return error_message, {'role': 'model', 'parts': [error_message]}


# --- Function to Generate Suggestions Only ---
def generate_suggestions_only(user_query: str, bot_response: str) -> list:
    """
    Makes a separate call to Gemini specifically to generate suggestions based on context.
    Returns a list of suggestion strings, or empty list on failure.
    """
    suggestions = []
    try:
        # Format the specific prompt for suggestion generation
        prompt = config.SUGGESTION_GENERATION_PROMPT_TEMPLATE.format(
            user_query=user_query,
            bot_response=bot_response
        )
        print(f"--- Generating Suggestions with Prompt ---\n{prompt}\n--------------------------------------")

        # Call the suggestion model (might use model_intent or model_suggestion)
        response = model_suggestion.generate_content(
            prompt,
            # Ensure safety settings are applied to suggestion generation too
            safety_settings=config.GEMINI_SAFETY_SETTINGS
        )

        # Attempt to clean and parse JSON list directly
        json_str = response.text.strip()
        if json_str.startswith("```json"): json_str = json_str[7:]
        if json_str.endswith("```"): json_str = json_str[:-3]
        json_str = json_str.strip()

        if not json_str:
             print("Suggestion generation returned empty string.")
             return []

        parsed_suggestions = json.loads(json_str)

        if isinstance(parsed_suggestions, list):
            # Filter out empty strings and ensure all are strings
            suggestions = [str(s) for s in parsed_suggestions if isinstance(s, str) and s.strip()]
            print(f"Successfully parsed suggestions: {suggestions}")
        else:
            print(f"Warning: Suggestion response was not a JSON list. Response: {json_str}")

    except json.JSONDecodeError as json_e:
        print(f"Error decoding suggestions JSON: {json_e}. Raw suggestion response: '{response.text if 'response' in locals() else 'N/A'}'")
    except Exception as e:
        print(f"Error generating suggestions: {e}")
        # Check for specific API errors if possible (e.g., safety blocks on suggestion prompt)
        if hasattr(e, 'response') and hasattr(e.response, 'prompt_feedback'):
             print("Suggestion generation blocked by safety settings.")
        elif "response.prompt_feedback" in str(e).lower():
             print("Suggestion generation blocked by safety settings.")

    # Limit number of suggestions
    return suggestions[:4] # Return max 4 suggestions


def detect_intent_and_extract_keywords(prompt: str):
    """Uses Gemini to classify intent and extract job search keywords (stateless)."""
    # (This function remains the same as before)
    try:
        response = model_intent.generate_content(prompt)
        json_str = response.text.strip()
        if json_str.startswith("```json"): json_str = json_str[7:]
        if json_str.endswith("```"): json_str = json_str[:-3]
        json_str = json_str.strip()
        intent_data = json.loads(json_str)
        if "intent" not in intent_data: raise ValueError("Missing 'intent' key")
        if "parameters" not in intent_data: intent_data["parameters"] = {}
        return intent_data
    except (json.JSONDecodeError, ValueError) as e:
         print(f"Error decoding/validating JSON from intent detection: {e}\nRaw Response: {response.text}")
         return {"intent": "get_advice", "parameters": {}}
    except Exception as e:
        print(f"Error detecting intent with Gemini: {e}")
        return {"intent": "get_advice", "parameters": {}}

