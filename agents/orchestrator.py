import os
from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.custom_tools import AmazonScraperTool
from dotenv import load_dotenv

load_dotenv(override=True)
# Un-hook LiteLLM from Vertex overrides permanently
os.environ.pop("GOOGLE_PROJECT_ID", None)
if "GOOGLE_API_KEY" in os.environ and "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

# CrewAI natively uses LiteLLM, so we dynamically load the model connection string.
# Defaults to gemini-1.5-pro, but can be swapped to vertex_ai/... if using GCP
llm_string = os.getenv("CREWAI_LLM_MODEL", "gemini/gemini-1.5-pro")

def build_content_crew(asin: str):
    """
    Constructs the Phase 1 CrewAI orchestrated pipeline for a specific ASIN.
    Uses Python 3.11 for Native compatibility.
    """
    scraper_tool = AmazonScraperTool()

    # ==========================
    # AGENT A: Forensic Researcher
    # ==========================
    forensic_researcher = Agent(
        role="Forensic Researcher",
        goal="Extract 'The Hidden Truth' about an Amazon product by analyzing raw data.",
        backstory=(
            "You are an expert consumer advocate and researcher. You do not settle for marketing fluff. "
            "You analyze descriptions and contrast 'Top Positive' versus 'Top Critical' reviews to find true Friction Points."
        ),
        verbose=True,
        allow_delegation=False,
        tools=[scraper_tool],
        llm=llm_string
    )

    # ==========================
    # AGENT B: Narrative Architect
    # ==========================
    narrative_architect = Agent(
        role="Narrative Architect",
        goal="Write a high-retention, FTC compliant video script targeting social media short-form video.",
        backstory=(
            "You are an elite short-form video scriptwriter. You specialize in the 'Hook-Problem-Truth-CTA' format. "
            "You never hallucinate logos or non-existent features. You are 100% compliant with FTC guidelines."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm_string
    )

    # ==========================
    # TASKS (Sequential)
    # ==========================
    research_task = Task(
        description=(
            f"Thoroughly analyze Amazon ASIN: {asin}. Use the scraper tool to pull data. "
            "Find the 'Hidden Truth' by identifying 1 major pain point or friction point from critical reviews compared to the positive ones."
        ),
        expected_output="A JSON structure detailing Target Audience, positive aspects, and the core Friction Point.",
        agent=forensic_researcher,
        output_file=f"tmp_{asin}_Research_Report.json" 
    )

    script_task = Task(
        description=(
            "Using the Forensic Researcher's output, craft a final short-form video script. "
            "MANDATORY: You MUST include the exact text 'AI-Enhanced Review | Independent Analysis' as a visual cue for compliance. "
            "Use the Hook-Problem-Truth-CTA format."
        ),
        expected_output="A JSON Object containing 'voiceover' and 'visuals'. DO NOT wrap the output in markdown.",
        agent=narrative_architect,
        output_file=f"tmp_{asin}_Platform_Script.json"
    )

    # ==========================
    # CREW ASSEMBLY
    # ==========================
    engine = Crew(
        agents=[forensic_researcher, narrative_architect],
        tasks=[research_task, script_task],
        process=Process.sequential,
        verbose=True
    )

    return engine

if __name__ == "__main__":
    # Quick Test Block
    test_asin = "B0CFN6GRTH"
    print(f"Starting Crew Generation for ASIN: {test_asin}")
    crew = build_content_crew(test_asin)
    result = crew.kickoff()
    print("FINISHED SCRIPTING. Final Result:")
    print(result)
