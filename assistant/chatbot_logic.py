    # assistant/chatbot_logic.py
from . import gemini_client
# --- Main Processing Function ---
def process_message(user_input: str, chat_history: list):
    """
    Processes user input, manages history, detects intent.
    Makes TWO calls to Gemini: one for response, one for suggestions.
    Returns the bot's response text, suggestions list, and updated history.
    """
    print(f"Processing user input: {user_input}")
    print(f"Incoming history length: {len(chat_history)}")

    current_history_user = {'role': 'user', 'parts': [user_input]}
    current_session_history = list(chat_history)
    current_session_history.append(current_history_user)

    intent_data = gemini_client.detect_intent_and_extract_keywords(user_input)
    intent = intent_data.get("intent", "get_advice")
    parameters = intent_data.get("parameters", {})
    # Store original query for suggestion context
    parameters['query'] = user_input
    print(f"Detected Intent: {intent}, Parameters: {parameters}")

    bot_response_text_final = "" # Final text response for user
    new_history_entry_model = None
    suggestions = [] # Initialize empty list

    try:
        # --- Step 1: Generate the main bot response using Gemini ---
        prompt_for_main_response = user_input # Default prompt is user input

        if intent in ["find_jobs", "find_internships"]:
            # Construct the specific guidance prompt for job searches
            role = parameters.get("role")
            location = parameters.get("location")
            seniority = parameters.get("seniority")
            type_ = parameters.get("type", "job")
            search_term = role if role else "opportunities"
            full_search_desc = search_term
            if type_ == 'internship' and 'internship' not in search_term.lower(): full_search_desc += " internship"
            if seniority and not any(s in search_term.lower() for s in ['beginner', 'fresher', 'entry level']): full_search_desc += f" for {seniority}"

            guidance_prompt = f"""
            The user is looking for '{full_search_desc}' {('in or near ' + location) if location else 'in their area (assume India context)'}.
            Okay, let's find those opportunities! ✨ While I can't pull live job listings, I can definitely guide you on the best ways to search. Please provide helpful advice including:
            1. **🎯 Key Platforms:** Recommend 2-3 specific, relevant job boards/platforms popular in India (e.g., Naukri.com, LinkedIn, Internshala, etc.). Briefly say why.
            2. **🔑 Smart Keywords:** Suggest 3-5 effective keywords or alternative job titles related to '{search_term}'.
            3. **🔗 Search Links:** Generate direct, clickable Markdown links `[Platform Name Search](URL)` to the search results pages of the recommended platforms. Construct URLs accurately.
            4. **💡 Extra Tips:** Add 1-2 brief, actionable tips.
            5. **Tone & Follow-up:** Remember to be friendly, motivational, use emojis, and end with an engaging question!
            """
            prompt_for_main_response = guidance_prompt # Override the prompt
            print(f"Routing to Gemini for job/internship guidance: {full_search_desc}")

        elif intent == "get_advice":
            print("Routing to Gemini for conversational advice using history.")
            prompt_to_send = user_input
            if "roadmap" in user_input.lower() or "steps" in user_input.lower() or "plan" in user_input.lower():
                 prompt_to_send += "\nPlease format the steps or plan clearly. Use a Markdown table or list. If creating a visual plan, use **Mermaid syntax** in a ```mermaid code block. Remember to ask a relevant follow-up question."
            elif "compare" in user_input.lower() or "difference" in user_input.lower():
                prompt_to_send += "\nLet's break down the comparison! Please use a Markdown table if that helps clarify things. 🤔 Remember to ask a relevant follow-up question."
            else:
                 prompt_to_send += "\n(Remember to be friendly, use emojis, and ask an engaging follow-up question if appropriate.)"
            prompt_for_main_response = prompt_to_send # Override the prompt

        elif intent == "off_topic":
            print("Handling off-topic request using Gemini.")
            # Prompt remains user_input, Gemini will decline based on system prompt
            prompt_for_main_response = user_input

        else: # Default fallback
            print(f"Unknown intent '{intent}', defaulting to Gemini general response.")
            prompt_for_main_response = user_input

        # --- Actually make the FIRST Gemini call ---
        bot_response_text_final, new_history_entry_model = gemini_client.generate_conversational_response(
            prompt_for_main_response, current_session_history
        )

        # --- Step 2: Generate Suggestions using SECOND Gemini call (if response is not an error) ---
        # Check if the main response is not an error message before trying to generate suggestions
        is_error_response = "sorry" in bot_response_text_final.lower() and ("error" in bot_response_text_final.lower() or "hiccup" in bot_response_text_final.lower() or "apologize" in bot_response_text_final.lower())

        if not is_error_response and intent != "off_topic": # Don't suggest after declining off-topic
            print("--- Attempting to generate suggestions ---")
            suggestions = gemini_client.generate_suggestions_only(
                user_query=user_input, # Pass original user query
                bot_response=bot_response_text_final # Pass the response just generated
            )
            print(f"Generated suggestions via second call: {suggestions}")
        else:
            print("--- Skipping suggestion generation due to error or off-topic ---")
            suggestions = []


    # --- General Exception Handling (Catches errors in the logic above, e.g., during prompt construction) ---
    except Exception as e:
         print(f"!!! Unexpected Error in process_message logic: {e}")
         # Use the error message generated by the generate_conversational_response call if it exists
         if not bot_response_text_final:
              bot_response_text_final = "Oh dear! 😅 It seems I've encountered an unexpected technical hiccup processing your request. Could you please try rephrasing?"
         # Ensure history entry is created even if error happened before suggestion generation
         if not new_history_entry_model:
              new_history_entry_model = {'role': 'model', 'parts': [bot_response_text_final]}
         suggestions = [] # No suggestions on error


    # --- Update history with the final text (already done in generate_conversational_response) ---
    # Ensure the history entry is valid before appending
    if not new_history_entry_model or 'parts' not in new_history_entry_model or not isinstance(new_history_entry_model['parts'], list):
         print("Error: Invalid history entry model generated. Using fallback.")
         new_history_entry_model = {'role': 'model', 'parts': [str(bot_response_text_final) or "Sorry, I couldn't process that."]}
    elif not new_history_entry_model['parts']: # Ensure parts list is not empty
         new_history_entry_model['parts'] = [str(bot_response_text_final) or "Sorry, I couldn't process that."]

    # --- Construct Final Updated History ---
    final_updated_history = current_session_history
    final_updated_history.append(new_history_entry_model)

    # Limit history size
    MAX_HISTORY_TURNS = 10
    if len(final_updated_history) > MAX_HISTORY_TURNS * 2:
         final_updated_history = final_updated_history[-(MAX_HISTORY_TURNS * 2):]
         print(f"History truncated to: {len(final_updated_history)}")

    # Return final text, A.I.-GENERATED suggestions, and updated history
    return bot_response_text_final, suggestions, final_updated_history
