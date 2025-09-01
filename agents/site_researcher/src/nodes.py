import os
import json
from typing import List

from pydantic import TypeAdapter
from dotenv import load_dotenv
from google.genai import Client


from . import prompts
from . import utils
from . import schemas


load_dotenv()


genai_client = Client(api_key=os.getenv("GOOGLE_API_KEY"))


class EmptyResponseError(Exception):
    """Exception raised when a response is empty."""


def official_website_finder(state):
    """LangGraph node that finds links to official websites of the paragliding site.
    """
    prompt = prompts.official_website_finder_instructions.safe_substitute(
        site_details=state["site_details"],
        current_date=utils.get_current_date()
    )
    response = genai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "tools": [{"google_search": {}}],
            "temperature": 0,
            "response_schema": list[schemas.SiteURL]
        }
    )
    json_text = response.text
    cleaned_json_text = json_text.strip().replace("```json", "").replace("```", "")
    json_obj = json.loads(cleaned_json_text)
    _ = TypeAdapter(List[schemas.SiteURL]).validate_python(json_obj)
    return {"official_websites": json_obj}


def risk_researcher(state):
    """LangGraph node that researches risks for a given site."""
    prompt = prompts.risk_researcher_instructions.safe_substitute(
        site_details=state["site_details"],
        current_date=utils.get_current_date()
    )
    response = genai_client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config={
            "tools": [{"google_search": {}}],
            "temperature": 0,
        }
    )
    if not response.text:
        raise EmptyResponseError("Response is empty")
    return {"risk_report": response.text}


def overview_researcher(state):
    """LangGraph node that researches an overview of a given site."""
    prompt = prompts.overview_researcher_instructions.safe_substitute(
        site_details=state["site_details"],
        current_date=utils.get_current_date()
    )
    response = genai_client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config={
            "tools": [{"google_search": {}}],
            "temperature": 0,
        }
    )
    if not response.text:
        raise EmptyResponseError("Response is empty")
    return {"overview_report": response.text}


def concatenate_reports(state):
    """LangGraph node that concatenates the reports of the site."""
    return {"full_report": "\n---\n\n".join([state["overview_report"], state["access_report"], state["risk_report"]])}


def access_researcher(state):
    """LangGraph node that researches access to a given site."""
    prompt = prompts.access_researcher_instructions.safe_substitute(
        site_details=state["site_details"],
        current_date=utils.get_current_date()
    )
    response = genai_client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config={
            "tools": [{"google_search": {}}],
            "temperature": 0,
        }
    )
    if not response.text:
        raise EmptyResponseError("Response is empty")
    return {"access_report": response.text}


def skill_level_extractor(state):
    """LangGraph node that extracts the skill level required to fly at a given site.
    """
    prompt = prompts.skill_level_extractor_instructions.safe_substitute(
        site_details=state["site_details"],
        reports=state["full_report"]
    )
    response = genai_client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config={
            "temperature": 0,
            "response_schema": schemas.SkillLevel
        }
    )
    json_text = response.text
    cleaned_json_text = json_text.strip().replace("```json", "").replace("```", "")
    json_obj = json.loads(cleaned_json_text)
    _ = schemas.SkillLevel.model_validate(json_obj)
    return json_obj


def tag_extractor(state):
    """LangGraph node that extracts tags from the site information.
    """
    prompt = prompts.tag_extractor_instructions.safe_substitute(
        site_details=state["site_details"],
        reports=state["full_report"]
    )
    response = genai_client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config={
            "temperature": 0,
            "response_schema": schemas.Tags
        }
    )
    json_text = response.text
    cleaned_json_text = json_text.strip().replace("```json", "").replace("```", "")
    json_obj = json.loads(cleaned_json_text)
    return {"tags": json_obj}


def copywriter(state):
    """LangGraph node that generates a description of the site."""
    prompt = prompts.copywriter_instructions.safe_substitute(
        site_details=state["site_details"],
        current_date=utils.get_current_date(),
        reports=state["full_report"]
    )
    response = genai_client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config={
            "temperature": 0,
        }
    )
    return {"description": response.text.replace("```html", "").replace("```", "")}
