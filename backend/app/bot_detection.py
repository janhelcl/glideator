from typing import Optional, Sequence, Tuple


# Canonical bot name -> identifying User-Agent fragments. Keep the most specific
# signatures before broader vendor signatures so the stored bot name remains useful.
BOT_SIGNATURES: Sequence[Tuple[str, Tuple[str, ...]]] = (
    ("OAI-SearchBot", ("oai-searchbot",)),
    ("ChatGPT-User", ("chatgpt-user",)),
    ("GPTBot", ("gptbot",)),
    ("Claude-SearchBot", ("claude-searchbot",)),
    ("Claude-User", ("claude-user",)),
    ("ClaudeBot", ("claudebot",)),
    ("Perplexity-User", ("perplexity-user",)),
    ("PerplexityBot", ("perplexitybot",)),
    ("Google-InspectionTool", ("google-inspectiontool",)),
    ("GoogleOther", ("googleother",)),
    ("Google-Agent", ("google-agent",)),
    ("Googlebot", ("googlebot",)),
    ("BingPreview", ("bingpreview",)),
    ("Bingbot", ("bingbot",)),
    ("DuckDuckBot", ("duckduckbot",)),
    ("Applebot", ("applebot",)),
    ("YandexBot", ("yandexbot",)),
    ("Baiduspider", ("baiduspider",)),
    ("PetalBot", ("petalbot",)),
    ("Bytespider", ("bytespider",)),
    ("Amazonbot", ("amazonbot",)),
    ("YouBot", ("youbot",)),
    ("CCBot", ("ccbot",)),
    ("FacebookBot", ("facebookexternalhit", "facebookcatalog", "meta-externalagent", "meta-externalfetcher")),
    ("Twitterbot", ("twitterbot",)),
    ("LinkedInBot", ("linkedinbot",)),
    ("Slackbot", ("slackbot",)),
    ("Discordbot", ("discordbot",)),
    ("TelegramBot", ("telegrambot",)),
    ("AhrefsBot", ("ahrefsbot",)),
    ("SemrushBot", ("semrushbot",)),
    ("MJ12bot", ("mj12bot",)),
    ("DotBot", ("dotbot",)),
    ("DataForSeoBot", ("dataforseobot",)),
    ("BLEXBot", ("blexbot",)),
)


def detect_known_bot(user_agent: Optional[str]) -> Optional[str]:
    """Return a canonical bot name for a known User-Agent, otherwise None.

    The raw User-Agent is intentionally used only in-memory for classification and
    is never persisted by the analytics pipeline.
    """
    if not user_agent:
        return None

    normalized = user_agent.lower()
    for bot_name, signatures in BOT_SIGNATURES:
        if any(signature in normalized for signature in signatures):
            return bot_name
    return None
