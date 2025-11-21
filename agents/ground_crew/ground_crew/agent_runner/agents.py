from typing import Any, Dict

from browser_use import Agent, ChatBrowserUse, Browser, ChatGoogle

from . import prompts, schemas, utils


class BrowserUseBaseAgent:
    """Base class for BrowserUse agents."""

    n_tries = 3

    async def run(self) -> Dict[str, Any]:
        """Run the agent."""
        for _ in range(getattr(self, "n_tries", 1)):
            history = await self._run_single_try()
            if history.is_successful():
                return self._parse_history(history)
            else:
                continue
        return self._parse_history(history)

    async def _run_single_try(self) -> Dict[str, Any]:
        """Run the agent for a single try."""
        agent = Agent(
            task=self.task,
            browser=Browser(headless=False),
            llm=ChatGoogle(model="gemini-2.5-flash-preview-09-2025"),
            output_model_schema=self.output_model_schema,
            calculate_cost=True,
        )
        return await agent.run()

    @classmethod
    def _parse_history(cls, history) -> Dict[str, Any]:
        """Parse the result from the history."""
        if not history.structured_output:
            structured_output = None
        else:
            structured_output = history.structured_output.model_dump()
        usage_stats = history.usage.model_dump()
        return {
            "structured_output": structured_output,
            "usage_stats": usage_stats,
            "is_successful": history.is_successful(),
            "duration_seconds": history.total_duration_seconds(),
        }


class CandidateRetrievalAgent(BrowserUseBaseAgent):
    """Agent for retrieving candidate websites."""

    output_model_schema = schemas.RetrievalResult
    task_prompt = prompts.retrieval_instructions

    def set_task(self, site_details: str):
        self.task = self.task_prompt.safe_substitute(
            site_details=site_details,
            current_date=utils.get_current_date(),
        )


