from typing import List

from pydantic import BaseModel, Field


class SiteURL(BaseModel):
    url: str
    description: str


class CandidateWebsiteEvidence(BaseModel):
    takeoff_landing_areas: bool = Field(
        description="Whether the website provides information about takeoff and landing areas"
    )
    rules: bool = Field(
        description="Whether the website provides information about specific local rules and regulations"
    )
    fees: bool = Field(description="Whether the website provides information about fees")
    access: bool = Field(description="Whether the website provides information about access to the site")
    meteostation: bool = Field(
        description="Whether the website provides information about local meteostation"
    )
    webcams: bool = Field(description="Whether the website provides information about webcams")


class CandidateWebsite(BaseModel):
    name: str = Field(description="Name of the entity operating the website")
    url: str = Field(description="Website URL")
    evidence: CandidateWebsiteEvidence = Field(description="Evidence for the relevance of the website")


class RetrievalResult(BaseModel):
    candidate_websites: List[CandidateWebsite] = Field(
        description="List of candidate websites that are relevant to the research site"
    )


class WebcamExtractionResult(BaseModel):
    found: bool = Field(description="Whether the webcam was found")
    webcam_url: str = Field(description="URL of the webcam (empty if not found)", default="")


class MeteostationExtractionResult(BaseModel):
    found: bool = Field(description="Whether the meteostation was found")
    meteostation_url: str = Field(description="URL of the meteostation (empty if not found)", default="")