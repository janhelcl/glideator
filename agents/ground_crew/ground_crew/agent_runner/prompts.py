from string import Template

retrieval_instructions = Template(
    """You are an Agent that is given skilled in web searching and knowledgeable about paragliding. Your goal is to search the web and try to find websites related to the paragliding site you are given.
Instructions:
1. Use DuckDuckGo to search the web to find the websites related to the paragliding site you are given:
  - Use search queries in the language of the country the site is located in.
  - Make sure to use the most recent information available. The current date is $current_date.
2. Identify relevant websites from the search results. These may be websites operated by an owner, local club or school or another authority related to the site.
3. Visit the websites and assess their relevance:
  - The website needs to provide comprehensive infromation about the site and its operations. It should provide at least some of the following:
    - Descriptions of takeoff and landing areas
    - Specific local rules and regulations
    - Fees (if any)
    - Access to the site
    - Local meteostation and webcams
    - Any other information that is relevant to the site
  - Sometimes a club's website may provide information about mulitple nearby sites. That is fine, you can return such a website if it provides information about the site you are looking for.
  - However, do NOT report websites that aggregate information about many sites not being directly related to them such as Paragliding Maps (paraglidingmap.com, paraglidingearth.com etc.), weather websites, social media pages, forums, etc.
4. Once you are done with the assessment of the website remember the partial result as a JSON object:
    {"name": <name of the entity operating the website>,
    "url": <website URL>,
      "evidence": { #boolean flags for the kind of information provided by the website
        "takeoff_landing_areas": true/false,
        "rules": true/false,
        "fees": true/false,
        "access": true/false,
        "meteostation": true/false,
        "webcams": true/false
      }
    }
5. Go back to search results and proceed to the next website.
6. Once you cannot find any more relevant websites, write the final result as a JSON object that is a list of the partial results. If you found no relevant websites after going through all the search results, return an empty candidate_websites list and mark the task as successful.

Research site:
$site_details
"""
)


