from langgraph.graph import START, END
from langgraph.graph import StateGraph
from langgraph.pregel import RetryPolicy

from . import schemas
from . import nodes

# TODO: split into two graphs:
#  - one for acquiring information about the site
#  - one for extracting information about the site
#  - add reflection loops
builder = StateGraph(schemas.OverallState)

# SET UP NODES
# acquire information about the site
builder.add_node("overview_researcher", nodes.overview_researcher, retry_policy=RetryPolicy())
builder.add_node("access_researcher", nodes.access_researcher, retry_policy=RetryPolicy())
builder.add_node("risk_researcher", nodes.risk_researcher, retry_policy=RetryPolicy())
builder.add_node("concatenate_reports", nodes.concatenate_reports)

# extract information about the site
builder.add_node("tag_extractor", nodes.tag_extractor)
builder.add_node("skill_level_extractor", nodes.skill_level_extractor)
builder.add_node("official_website_finder", nodes.official_website_finder, retry_policy=RetryPolicy())
builder.add_node("copywriter", nodes.copywriter)

# SET UP EDGES
builder.add_edge(START, "overview_researcher")
builder.add_edge(START, "access_researcher")
builder.add_edge(START, "risk_researcher")
builder.add_edge("overview_researcher", "concatenate_reports")
builder.add_edge("access_researcher", "concatenate_reports")
builder.add_edge("risk_researcher", "concatenate_reports")
builder.add_edge("concatenate_reports", "tag_extractor")
builder.add_edge("concatenate_reports", "skill_level_extractor")
builder.add_edge("concatenate_reports", "official_website_finder")
builder.add_edge("concatenate_reports", "copywriter")
builder.add_edge("tag_extractor", END)
builder.add_edge("skill_level_extractor", END)
builder.add_edge("official_website_finder", END)
builder.add_edge("copywriter", END)


site_researcher_graph = builder.compile()
