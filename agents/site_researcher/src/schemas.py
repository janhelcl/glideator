from typing import Literal, Dict, TypedDict

from pydantic import BaseModel


class SiteURL(BaseModel):
    url: str
    description: str


class SkillLevel(BaseModel):
    skill_level: Literal["Beginner", "Intermediate", "Expert"]
    skill_level_description: str


class Tags(BaseModel):
    tags: list[str]


class OverallState(TypedDict):
    site_name: str
    site_details: str
    risk_report: str
    overview_report: str
    access_report: str
    full_report: str
    final_answer: str
    skill_level: str
    skill_level_description: str
    tags: list[str]
    official_websites: list[SiteURL]
    description: Dict[str, str]



