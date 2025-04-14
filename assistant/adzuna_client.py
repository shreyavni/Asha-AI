# assistant/adzuna_client.py
import requests
import config

# WARNING: In-memory counter resets on app restart. Use persistent storage in production.
adzuna_call_count = 0
ADZUNA_DAILY_LIMIT = 250

def search_adzuna_jobs(role: str | None = None, location: str | None = None, max_results: int = 5):
    """Searches Adzuna API for jobs/internships."""
    # Check if Adzuna is configured
    if not config.ADZUNA_BASE_URL:
        print("Adzuna client disabled: API keys not configured.")
        return {"error": "Job search functionality is currently unavailable."}

    global adzuna_call_count
    if adzuna_call_count >= ADZUNA_DAILY_LIMIT:
        print("WARNING: Adzuna daily limit potentially reached.")
        return {"error": "The job search limit has been reached for today. Please try again tomorrow."}

    params = {
        'app_id': config.ADZUNA_APP_ID,
        'app_key': config.ADZUNA_API_KEY,
        'results_per_page': max_results,
        'content-type': 'application/json'
    }
    if role: params['what'] = role
    if location: params['where'] = location
    # Simple check if keywords suggest internship
    if role and 'internship' in role.lower():
         params['what_or'] = 'internship trainee graduate' # Broaden search slightly

    print(f"Querying Adzuna with: {params}") # Debugging

    try:
        response = requests.get(config.ADZUNA_BASE_URL, params=params)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        adzuna_call_count += 1
        print(f"Adzuna API call count: {adzuna_call_count}/{ADZUNA_DAILY_LIMIT}")

        data = response.json()
        results = data.get('results', [])

        if not results:
            # Changed message to be more neutral
            return {"message": f"I checked for '{role or 'opportunities'}' {('in '+location) if location else ''} but couldn't find specific listings on Adzuna right now.", "results": []}

        # Format results for presentation
        formatted_results = []
        for job in results:
            formatted_results.append({
                "title": job.get('title'),
                "company": job.get('company', {}).get('display_name', 'N/A'),
                "location": job.get('location', {}).get('display_name', 'N/A'),
                "url": job.get('redirect_url')
            })
        return {"results": formatted_results}

    except requests.exceptions.RequestException as e:
        print(f"Error querying Adzuna API: {e}")
        # Improved error message
        return {"error": "Sorry, I couldn't connect to the job search service right now. Please try again later or ask for general advice."}
    except Exception as e:
        print(f"An unexpected error occurred during Adzuna search: {e}")
        return {"error": "An unexpected error occurred while searching for jobs. Could you try rephrasing your search?"}