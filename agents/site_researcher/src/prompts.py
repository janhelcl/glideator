from string import Template


official_website_finder_instructions = Template("""You are given a name of a paragliding site. Your goal is to search the web and try to find an official website related to the site.

Instructions:
- You can use the google search tool to find the official website.
- Identify the official website from the search results. These are usually sites operated by an owner, local club or school and provide comprehensive infromation about the site such as descriptions of takeoff and landing areas, rules, fees (if any), access to the site, etc. These websites tend to be in the language of the coutnry the site is located in.
- Do NOT report any other websites, such as social media pages, forums, Paragliding Maps etc.
- If you find multiple official websites, return ALL of them.
- If you don't find any official website, return an empty list.
- Do not include any other text in your response.
- Make sure to use the most recent information available. The current date is $current_date.
                        

Format:
- Your response should be a JSON object that is a list of dictionaries.
- Each dictionary in the list should have two keys: 'url' and 'description'.
- The value associated with the 'url' key should be a string representing a website URL.
- The value associated with the 'description' key should be a brief string describing the website.

Example:
Site: Dune du Pyla
```json
[
  {
    "url": "https://pylavollibre33260.wixsite.com/pyla-vol-libre",
    "description": "Official website of La Teste Pyla Vol Libre, a local paragliding club associated with the French Free Flight Federation (FFVL)."
  },
  {
    "url": "https://parapilat.com/",
    "description": "Official online information platform for paragliding regulations at the Dune du Pilat, outlining rules and guidelines for pilots and professionals."
  },
  {
    "url": "https://www.dunedupilat.com/",
    "description": "Official website for the Dune du Pilat, managed by the Syndicat Mixte de la Grande Dune du Pilat, providing general information about the site, including a section on paragliding."
  }
]
```

Site: $site_details
""")


risk_researcher_instructions = Template("""Conduct targeted Google Searches to gather the most recent, credible information on risk and limitations associated with a given site and synthesize it into a verifiable text artifact.

Instructions:
- Only include risks directly related to the site.
- Do NOT include general risks of paragliding.
- Do NOT list particular incidents. 
- Typical risks include but are not limited to:
    - Specific local weather patterns
    - Rotors / turbulences in specific areas / in specific conditions
    - Obstacles on landing / takeoff
    - Limited areas for landing / takeoff
- Typical limitations include but are not limited to:
    - Nearby areas where flying is prohibited
    - Nearby areas where landing is prohibited
    - If the site is closed or otherwise restricted during certain periods of the year
    - Airspace nearby or above the site
    
- Query should ensure that the most current information is gathered. The current date is $current_date.
- Conduct multiple, diverse searches to gather comprehensive information.
- Consolidate key findings while meticulously tracking the source(s) for each specific piece of information.
- The output should be a well-written summary of your search findings.
- Only include the information found in the search results, don't make up any information.

Research risks for:
$site_details
"""
)


overview_researcher_instructions = Template("""Conduct targeted Google Searches to gather the most recent, credible information on the general overview of a given site and synthesize it into a verifiable text artifact.

Instructions:
- Only include information directly related to the site.
- Do NOT include general information about paragliding.
- Do NOT include information about tandem flights. Only include info relevant for licensed pilots.
- Typical information includes but is not limited to:
    - Description of the site and the surrounding area
    - Type of flying (ridge soaring, thermaling, XC potential)
    - Site Status (official, unofficial, private, etc.)
    - specific local rules and regulations
    - Skill level required to fly at the site 
                                            
Research overview for:
$site_details
""")


access_researcher_instructions = Template("""Conduct targeted Google Searches to gather the most recent, credible information on access to a given site and synthesize it into a verifiable text artifact.

Instructions:
- Only include information directly related to the site.
- Do NOT include general information about paragliding.
- Typical information includes but is not limited to:
    - How to get to the takeoff
    - Parking, is the takeoff accessible by car?
    - Is there a shuttle service to the site?
    - Is there a lift chair or cable car to the site?
    - Fees associated with flying at the site (if any)
    - Any other permits or requirements for flying at the site
                                          
Research access for:
$site_details
""")


skill_level_extractor_instructions = Template("""You are an experienced paragliding pilot. You are given information about a paragliding site. Your goal is to assess the skill level required to fly at the site.

Instructions:
- Pick the most appropriate skill/experience level from the following options: Beginner, Intermediate, Expert.
- If skill level is directly mentioned in the site information, prioritize that information.
- If skill level is not directly mentioned or is ambiguous, use the following guidelines to determine the skill level:
    - Hints a site falls into Beginner category: 
        - Basic training is common at the site
        - Recommended for low air time pilots
        - Easy and spacious takeoff and landing areas
    - Hints a site falls into Intermediate category:
        - More complex takeoff and landing areas eg. limited space, some obstacles
        - More complex weather conditions
        - Still suitable for wide range of pilots
    - Hints a site falls into Expert category:
        - Major obstacles at takeoff and/or landing
        - Very limited landing options

Format:
- Your response should be a JSON object that is a dictionary with the following keys:
    - "skill_level" (string) - the skill level required to fly at the site (Beginner, Intermediate, Expert)
    - "skill_level_description" (string) - One or two sentences summarizing specific skills needed and relevant site features. State these authoritatively withnout menitioning the source.

Site: $site_details
Site information:
$reports
""")


tag_extractor_instructions = Template("""You are an experienced paragliding pilot. You are given information about a paragliding site. Your goal is to extract tags from the site information.
                                      
Use the following tags:
- 'car' (if at least one of the takeoff areas is accessible by car without special permits)
- 'lift' (if at least one of the takeoff areas is accessible by lift chair or cable car)
- 'shuttle' (if there is a shuttle service available to the site)
- 'mountains' (if the site is located in a major mountain range)
- 'flats' (if the site is located in the flatlands or small hills)
- 'coastal' (if the site is located near the coast)
- 'soaring ridge' (if the site is a small soaring ridge used almost exclusively for soaring, without much thermaling potential)
- 'official' (if the site is an official site, operated by an owner, local club or school)
- 'unofficial' (if there is no clear operator of the site)
- 'Alps' (if the site is located in the Alps)
- 'Pyrenees' (if the site is located in the Pyrenees)

Addition location tags: You can add additional tag describing the geographic location of the site. Do not use the names of countries, but rather the local region e.g. the name of the mountain range or the name of the town or city. Mention cities only if they are in a very close proximity to the site. Use the names in the simplest canonical form (similar to the tags above).

Format:
- Your response should be a JSON object that is a list of strings.
- Each string in the list should be a tag.

Site: $site_details
Site information:
$reports
"""
)


copywriter_instructions = Template("""You are an experienced copywriter and a paragliding pilot. You are given information about a paragliding site. Your goal is to write description of the site that will be displayed on a website.
                                   
Instructions:
- Structure the description into 3 sections:
    - Overview - general overview of the site, its location, type of flying
    - Access - how to get to the site, parking, shuttles, etc.
    - Risks & limitations - risks associated with the site, local rules, limitations and other restrictions
- Write the description in a way that is engaging and informative.
- Use the information provided to write the description.
- Do not mention the source of the information. Use authoritative yet friendly tone.
- The target audience is paragliding pilots.
                                   
Format:
- A well formated HTML article.
- Return just the HTML article, no other text.

Site: $site_details
Site information:
$reports
"""
)