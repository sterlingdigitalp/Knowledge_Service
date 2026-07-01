#!/usr/bin/env python3
"""One-shot builder for production watch universe v1 configuration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knowledge_service.intelligence.config import load_profiles, save_profiles
from knowledge_service.intelligence.models import IntelligenceProfile, PodcastListKind, PodcastSource, WatchListEntry


def _person(
    name: str,
    *,
    aliases: list[str] | None = None,
    organization: str | None = None,
    handles: dict[str, str] | None = None,
    priority: int = 7,
    rationale: str = "",
) -> WatchListEntry:
    return WatchListEntry(
        display_name=name,
        aliases=aliases or [],
        organization=organization,
        source_handles=handles or {},
        priority=priority,
        metadata={"inclusion_rationale": rationale},
    )


def _podcast(
    name: str,
    url: str,
    *,
    priority: int = 7,
    polling: int = 3600,
    max_episodes: int = 3,
    rationale: str = "",
    source_type: str = "podcast",
    required: bool = True,
) -> PodcastSource:
    return PodcastSource(
        name=name,
        url=url,
        kind=PodcastListKind.REQUIRED if required else PodcastListKind.OPTIONAL,
        priority=priority,
        polling_interval_seconds=polling,
        max_episodes=max_episodes,
        discovery_mode="podscripts",
        transcript_source="published",
        metadata={
            "inclusion_rationale": rationale,
            "source_type": source_type,
            "role": "acquisition_route",
        },
    )


def _recurring(
    source_id: str,
    name: str,
    url: str,
    source_type: str,
    *,
    priority: int = 6,
    rationale: str = "",
) -> dict:
    return {
        "source_id": source_id,
        "name": name,
        "url": url,
        "source_type": source_type,
        "priority": priority,
        "enabled": True,
        "inclusion_rationale": rationale,
    }


def production_profiles() -> list[IntelligenceProfile]:
    return [
        IntelligenceProfile(
            name="AI",
            description="AI systems, coding, datacenters, inference, agents, and enterprise AI.",
            icon="brain",
            color="#3b82f6",
            interests=["AI", "Coding", "Datacenters", "Inference", "Agents", "Enterprise AI", "AGI", "ML systems"],
            watch_list=[
                _person("Sam Altman", aliases=["sama"], organization="OpenAI", handles={"x": "sama"}, priority=10, rationale="OpenAI CEO; primary public voice on frontier model deployment, product strategy, and industry direction."),
                _person("Satya Nadella", organization="Microsoft", priority=9, rationale="Microsoft CEO; highest-signal enterprise AI adoption narrative across Azure, Copilot, and OpenAI partnership."),
                _person("Dario Amodei", organization="Anthropic", priority=9, rationale="Anthropic CEO; leading voice on scaling laws, constitutional AI, and competitive frontier lab strategy."),
                _person("Andrej Karpathy", aliases=["karpathy"], handles={"x": "karpathy"}, priority=9, rationale="Practitioner-educator bridging research and production ML systems; high signal on agents, data, and training stacks."),
                _person("Fei-Fei Li", organization="Stanford HAI", priority=8, rationale="Stanford HAI co-director; policy, human-centered AI, and institutional research leadership."),
                _person("Jensen Huang", organization="NVIDIA", priority=9, rationale="NVIDIA CEO; definitive source on AI compute, networking, and infrastructure buildout."),
                _person("Demis Hassabis", organization="Google DeepMind", priority=8, rationale="DeepMind CEO; AGI research direction, AlphaFold-era science, and Google AI integration."),
                _person("Yann LeCun", organization="Meta", handles={"x": "ylecun"}, priority=8, rationale="Meta Chief AI Scientist; open research, world models, and public debate on AI architecture."),
                _person("Ilya Sutskever", organization="Safe Superintelligence", priority=9, rationale="SSI co-founder; foundational model research lineage and post-OpenAI superintelligence focus."),
                _person("Grant Sanderson", aliases=["3Blue1Brown"], priority=7, rationale="3Blue1Brown creator; unusually clear explanations at the math–ML boundary for technical audiences."),
            ],
            required_podcasts=[
                _podcast("Dwarkesh Podcast", "https://podscripts.co/podcasts/dwarkesh-podcast", priority=10, polling=1800, rationale="Highest-density long-form interviews with AI researchers, executives, and economists.", required=True),
                _podcast("Lex Fridman Podcast", "https://podscripts.co/podcasts/lex-fridman-podcast", priority=9, polling=3600, rationale="Canonical long-form venue for frontier AI leaders and scientists.", required=True),
                _podcast("Latent Space", "https://podscripts.co/podcasts/latent-space", priority=9, polling=3600, rationale="AI engineering and applied research community; strong operator and researcher guest mix.", required=True),
            ],
            optional_podcasts=[
                _podcast("No Priors", "https://podscripts.co/podcasts/no-priors", priority=8, polling=3600, rationale="a16z AI podcast; founder and investor lens on model companies and applications.", required=False),
                _podcast("Hard Fork", "https://podscripts.co/podcasts/hard-fork", priority=7, polling=3600, rationale="NYT technology desk; timely synthesis of consumer and policy AI news.", required=False),
                _podcast("The AI Podcast (NVIDIA)", "https://podscripts.co/podcasts/the-ai-podcast-nvidia", priority=7, polling=7200, rationale="Infrastructure and applied AI deployments across industry verticals.", required=False),
            ],
            metadata={
                "watch_universe_version": "v1",
                "recurring_sources": [
                    _recurring("openai_blog", "OpenAI Blog", "https://openai.com/blog", "company_blog", priority=9, rationale="Primary product, safety, and research announcements from OpenAI."),
                    _recurring("anthropic_news", "Anthropic News", "https://www.anthropic.com/news", "company_blog", priority=9, rationale="Model releases, safety research, and enterprise positioning from Anthropic."),
                    _recurring("nvidia_gtc", "NVIDIA GTC", "https://www.nvidia.com/gtc/", "conference", priority=8, rationale="Annual keynotes and sessions defining AI hardware/software roadmaps."),
                    _recurring("neurips", "NeurIPS", "https://neurips.cc/", "conference", priority=8, rationale="Flagship ML research conference; papers and invited talks set field direction."),
                    _recurring("microsoft_build", "Microsoft Build", "https://build.microsoft.com/", "conference", priority=8, rationale="Enterprise developer conference for Copilot, Azure AI, and Windows AI integrations."),
                    _recurring("ycombinator_blog", "Y Combinator Blog", "https://www.ycombinator.com/blog", "company_blog", priority=7, rationale="Startup AI adoption patterns, batch trends, and operator essays from YC."),
                ],
            },
        ),
        IntelligenceProfile(
            name="Investing",
            description="Markets, capital allocation, technology investing, and macro debates.",
            icon="chart",
            color="#22c55e",
            interests=["investing", "markets", "AI", "China", "macro", "venture capital", "public equities"],
            watch_list=[
                _person("Bill Ackman", organization="Pershing Square", priority=9, rationale="Activist investor with detailed public macro and corporate governance theses."),
                _person("Warren Buffett", organization="Berkshire Hathaway", priority=10, rationale="Definitive long-term capital allocation framework via annual letters and Berkshire meetings."),
                _person("Patrick O'Shaughnessy", aliases=["Patrick O’Shaughnessy"], handles={"x": "patrick_oshag"}, priority=9, rationale="Colossus founder; high-quality investor and operator interviews across public and private markets."),
                _person("Marc Andreessen", organization="a16z", handles={"x": "pmarca"}, priority=9, rationale="a16z co-founder; technology cycle framing and venture-scale company building."),
                _person("Chamath Palihapitiya", organization="Social Capital", handles={"x": "chamath"}, priority=8, rationale="All-In co-host; macro, rates, and technology investing debates with high reach."),
                _person("David Einhorn", organization="Greenlight Capital", priority=8, rationale="Contrarian value investor; detailed forensic equity and macro commentary."),
                _person("Stanley Druckenmiller", priority=9, rationale="Legendary macro trader; regime-change and liquidity signals from rare public appearances."),
                _person("Howard Marks", organization="Oaktree Capital", priority=9, rationale="Credit cycle and risk memos that anchor institutional investing psychology."),
                _person("Cathie Wood", organization="ARK Invest", handles={"x": "CathieDWood"}, priority=7, rationale="Disruptive innovation research with explicit AI and genomics theses."),
                _person("Sam Altman", aliases=["sama"], organization="OpenAI", handles={"x": "sama"}, priority=8, rationale="Technology investor-operator lens on AI capex, startups, and platform shifts."),
            ],
            required_podcasts=[
                _podcast("All-In Podcast", "https://podscripts.co/podcasts/all-in-with-chamath-jason-sacks-friedberg", priority=10, polling=1800, rationale="Weekly macro, policy, and technology investing debate among active operators.", required=True),
                _podcast("Invest Like the Best", "https://podscripts.co/podcasts/invest-like-the-best", priority=9, polling=3600, rationale="Deep investor and founder interviews from Patrick O'Shaughnessy's network.", required=True),
                _podcast("Acquired", "https://podscripts.co/podcasts/acquired", priority=9, polling=3600, rationale="Canonical company deep dives for quality-of-business and moat analysis.", required=True),
            ],
            optional_podcasts=[
                _podcast("Odd Lots", "https://podscripts.co/podcasts/odd-lots", priority=8, polling=3600, rationale="Bloomberg markets desk; macro plumbing, Fed policy, and market structure.", required=False),
                _podcast("BG2 Pod", "https://podscripts.co/podcasts/bg2-pod-with-brad-gerstner-and-bill-gurley", priority=8, polling=3600, rationale="Brad Gerstner and Bill Gurley on venture cycles, AI, and public tech.", required=False),
            ],
            metadata={
                "watch_universe_version": "v1",
                "recurring_sources": [
                    _recurring("howard_marks_memos", "Howard Marks Memos", "https://www.oaktreecapital.com/insights/memos", "newsletter", priority=10, rationale="Institutional risk framework and cycle positioning from Oaktree."),
                    _recurring("berkshire_letters", "Berkshire Hathaway Shareholder Letters", "https://www.berkshirehathaway.com/letters/letters.html", "company_letters", priority=10, rationale="Primary Buffett/Munger capital allocation doctrine, annually updated."),
                    _recurring("a16z_blog", "a16z Blog", "https://a16z.com/", "company_blog", priority=8, rationale="Venture firm research on AI, fintech, and market maps."),
                    _recurring("colossus", "Colossus", "https://joincolossus.com/", "media", priority=8, rationale="Investor letters, founder profiles, and archival business biographies."),
                    _recurring("grants_pub", "Grant's Interest Rate Observer", "https://www.grantspub.com/", "newsletter", priority=8, rationale="Independent macro and credit analysis respected by institutional investors."),
                    _recurring("ark_research", "ARK Invest Research", "https://ark-invest.com/articles/", "research", priority=7, rationale="Disruptive innovation models with explicit AI and automation forecasts."),
                    _recurring("pershing_letters", "Pershing Square Holdings Letters", "https://www.pershingsquareholdings.com/letters", "company_letters", priority=8, rationale="Bill Ackman's detailed activist theses and portfolio commentary."),
                ],
            },
        ),
        IntelligenceProfile(
            name="Founders",
            description="Company building, founder biographies, and operating lessons.",
            icon="spark",
            color="#f59e0b",
            interests=["founders", "company building", "biography", "business", "operations", "culture"],
            watch_list=[
                _person("Steve Jobs", organization="Apple", priority=9, rationale="Reference founder for product taste, distribution, and category creation."),
                _person("Patrick O'Shaughnessy", aliases=["Patrick O’Shaughnessy"], handles={"x": "patrick_oshag"}, priority=8, rationale="Investor who systematically studies great operators and capital allocators."),
                _person("Sam Altman", aliases=["sama"], organization="OpenAI", handles={"x": "sama"}, priority=9, rationale="YC-era operator playbook applied to frontier AI company building."),
                _person("Satya Nadella", organization="Microsoft", priority=8, rationale="Enterprise transformation case study: cloud pivot, culture reset, AI platform."),
                _person("Marc Andreessen", organization="a16z", handles={"x": "pmarca"}, priority=8, rationale="Software-eats-the-world thesis and venture-scale company formation."),
                _person("Reid Hoffman", organization="Greylock", handles={"x": "reidhoffman"}, priority=8, rationale="Blitzscaling and network-effects operator; Masters of Scale host."),
                _person("Jeff Bezos", organization="Amazon", priority=9, rationale="Customer obsession, flywheel economics, and annual shareholder letter doctrine."),
                _person("Brian Chesky", organization="Airbnb", handles={"x": "bchesky"}, priority=8, rationale="Live operator updates on product, management systems, and travel platform strategy."),
                _person("Soichiro Honda", organization="Honda", priority=7, rationale="Manufacturing founder archetype studied via Founders podcast canon."),
                _person("Elon Musk", organization="Tesla", handles={"x": "elonmusk"}, priority=8, rationale="Multi-company operator with high-signal product and manufacturing announcements."),
            ],
            required_podcasts=[
                _podcast("Founders", "https://podscripts.co/podcasts/founders", priority=10, polling=86400, rationale="David Senra's biography-driven operating lessons from history's greatest builders.", required=True),
                _podcast("Invest Like the Best", "https://podscripts.co/podcasts/invest-like-the-best", priority=8, polling=3600, rationale="Operator and founder interviews with implementation detail.", required=True),
                _podcast("Acquired", "https://podscripts.co/podcasts/acquired", priority=9, polling=3600, rationale="Company creation stories with strategic and financial depth.", required=True),
            ],
            optional_podcasts=[
                _podcast("Lenny's Podcast", "https://podscripts.co/podcasts/lennys-podcast", priority=8, polling=3600, rationale="Product and growth operators sharing playbooks for scaling teams.", required=False),
                _podcast("Masters of Scale", "https://podscripts.co/podcasts/masters-of-scale", priority=7, polling=3600, rationale="Reid Hoffman's venue for scaling tactics from iconic founders.", required=False),
                _podcast("How I Built This", "https://podscripts.co/podcasts/how-i-built-this", priority=7, polling=7200, rationale="NPR founder narratives with early-stage struggle and pivot detail.", required=False),
            ],
            metadata={
                "watch_universe_version": "v1",
                "recurring_sources": [
                    _recurring("ycombinator_blog", "Y Combinator Blog", "https://www.ycombinator.com/blog", "company_blog", priority=8, rationale="Startup formation patterns, batch trends, and founder advice."),
                    _recurring("first_round_review", "First Round Review", "https://review.firstround.com/", "company_blog", priority=8, rationale="Tactical essays on hiring, product, and early go-to-market."),
                    _recurring("a16z_blog", "a16z Blog", "https://a16z.com/", "company_blog", priority=7, rationale="Builder-focused market maps and operating frameworks."),
                    _recurring("stratechery", "Stratechery", "https://stratechery.com/", "newsletter", priority=9, rationale="Ben Thompson's aggregation theory and platform strategy analysis."),
                    _recurring("stripe_sessions", "Stripe Sessions", "https://stripe.com/sessions", "conference", priority=7, rationale="Operator keynotes on internet economy infrastructure and scaling."),
                    _recurring("saastr_annual", "SaaStr Annual", "https://www.saastrannual.com/", "conference", priority=7, rationale="B2B SaaS operator conference for GTM and leadership lessons."),
                ],
            },
        ),
        IntelligenceProfile(
            name="Longevity",
            description="Healthspan, performance, metabolic health, and translational medicine.",
            icon="pulse",
            color="#ef4444",
            interests=["longevity", "muscle", "GLP-1", "metabolic", "healthspan", "cardiovascular", "sleep", "nutrition"],
            watch_list=[
                _person("Peter Attia", handles={"x": "PeterAttiaMD"}, priority=10, rationale="Clinician-researcher anchor for longevity protocols and risk stratification."),
                _person("Tom Dayspring", priority=8, rationale="Lipidology specialist; high-signal collaborator on cardiovascular prevention."),
                _person("Andrew Huberman", organization="Stanford", handles={"x": "hubermanlab"}, priority=9, rationale="Neuroscience protocols for sleep, performance, and behavioral interventions."),
                _person("Rhonda Patrick", organization="FoundMyFitness", handles={"x": "foundmyfitness"}, priority=9, rationale="Translational nutrition and aging research communicator with primary literature depth."),
                _person("David Sinclair", organization="Harvard Medical School", priority=8, rationale="Aging biology researcher; NAD+ and epigenetic reprogramming discourse."),
                _person("Mark Hyman", organization="Cleveland Clinic Center for Functional Medicine", priority=7, rationale="Functional medicine lens on metabolic health and policy-access debates."),
                _person("Valter Longo", organization="USC Longevity Institute", priority=8, rationale="Fasting-mimicking diet and longevity nutrition clinical research."),
                _person("Steven Austad", organization="University of Alabama at Birmingham", priority=7, rationale="Geroscience researcher on comparative aging and intervention realism."),
                _person("George Church", organization="Harvard", priority=8, rationale="Genomics pioneer; gene therapy and multiplex editing for aging targets."),
                _person("Bryan Johnson", organization="Blueprint", handles={"x": "bryan_johnson"}, priority=7, rationale="N-of-1 longevity experimentation with open biomarker tracking."),
            ],
            required_podcasts=[
                _podcast("The Peter Attia Drive", "https://podscripts.co/podcasts/the-peter-attia-drive", priority=10, polling=86400, rationale="Primary clinical longevity venue with deep expert interviews.", required=True),
                _podcast("Huberman Lab", "https://podscripts.co/podcasts/huberman-lab", priority=9, polling=3600, rationale="Neuroscience-based performance and healthspan protocols.", required=True),
                _podcast("FoundMyFitness", "https://podscripts.co/podcasts/foundmyfitness", priority=9, polling=3600, rationale="Rhonda Patrick's venue for nutrition, aging, and mechanistic studies.", required=True),
            ],
            optional_podcasts=[
                _podcast("The Proof with Simon Hill", "https://podscripts.co/podcasts/the-proof-with-simon-hill", priority=7, polling=7200, rationale="Evidence-based nutrition debates relevant to metabolic health.", required=False),
                _podcast("Lifespan with Dr. David Sinclair", "https://podscripts.co/podcasts/lifespan-with-dr-david-sinclair", priority=7, polling=7200, rationale="Aging biology explanations and intervention updates from Sinclair.", required=False),
                _podcast("The Doctor's Farmacy with Mark Hyman", "https://podscripts.co/podcasts/the-doctors-farmacy-with-mark-hyman", priority=6, polling=7200, rationale="Functional medicine interviews on metabolic and policy topics.", required=False),
            ],
            metadata={
                "watch_universe_version": "v1",
                "recurring_sources": [
                    _recurring("examine", "Examine.com", "https://examine.com/", "research", priority=9, rationale="Independent supplement and nutrition evidence summaries."),
                    _recurring("peter_attia_site", "Peter Attia MD", "https://peterattiamd.com/", "company_blog", priority=9, rationale="Newsletter, show notes, and clinical frameworks from Attia's practice."),
                    _recurring("longevity_technology", "Longevity.Technology", "https://longevity.technology/", "media", priority=7, rationale="Industry news on aging therapeutics, clinics, and trials."),
                    _recurring("nia_news", "National Institute on Aging News", "https://www.nia.nih.gov/news", "research", priority=8, rationale="NIH aging research funding, trials, and public guidance."),
                    _recurring("insidetracker_blog", "InsideTracker Blog", "https://www.insidetracker.com/blog", "company_blog", priority=6, rationale="Blood biomarker interpretation for performance and healthspan."),
                    _recurring("a4m", "A4M World Congress", "https://www.a4m.com/", "conference", priority=6, rationale="Large longevity medicine conference for clinical practice trends."),
                ],
            },
        ),
    ]


def production_source_routes() -> dict:
    podcast_routes = {
        "dwarkesh": {
            "canonical_name": "Dwarkesh Podcast",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts pages are complete and timestamped", "consistently available"],
            "url_patterns": ["dwarkesh-podcast", "dwarkesh\\.com"],
            "name_aliases": ["dwarkesh podcast"],
            "monitoring_reason": "Deep technical AI interviews; acquisition route for AI profile watched people.",
            "certification": {"status": "certified", "evidence": ["published_transcript certified on podscripts dwarkesh episodes"]},
        },
        "lex_fridman": {
            "canonical_name": "Lex Fridman Podcast",
            "preferred_route": "official_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["official transcript highest quality", "excellent speaker formatting"],
            "url_patterns": ["lexfridman\\.com", "lex-fridman"],
            "name_aliases": ["lex fridman"],
            "monitoring_reason": "Long-form AI leader interviews; acquisition route for AI profile.",
            "certification": {"status": "certified", "evidence": ["official_transcript path certified on lexfridman.com transcripts"]},
        },
        "latent_space": {
            "canonical_name": "Latent Space",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "AI engineering guest density"],
            "url_patterns": ["latent-space"],
            "name_aliases": ["latent space podcast"],
            "monitoring_reason": "Applied AI and engineering community podcast for AI profile.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
        "no_priors": {
            "canonical_name": "No Priors",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "a16z AI founder/investor guests"],
            "url_patterns": ["no-priors"],
            "name_aliases": ["no priors podcast"],
            "monitoring_reason": "a16z AI podcast acquisition route.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
        "hard_fork": {
            "canonical_name": "Hard Fork",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "NYT technology news synthesis"],
            "url_patterns": ["hard-fork"],
            "name_aliases": ["hard fork"],
            "monitoring_reason": "Consumer and policy AI news acquisition route.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
        "nvidia_ai_podcast": {
            "canonical_name": "The AI Podcast (NVIDIA)",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "infrastructure and applied AI focus"],
            "url_patterns": ["the-ai-podcast-nvidia"],
            "name_aliases": ["nvidia ai podcast"],
            "monitoring_reason": "NVIDIA applied AI and infrastructure acquisition route.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
        "all_in": {
            "canonical_name": "All-In Podcast",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts discovery URLs are complete and timestamped"],
            "url_patterns": ["all-in-with-chamath", "allin\\.com"],
            "name_aliases": ["all in podcast", "all-in"],
            "monitoring_reason": "Macro and technology investing debate; Investing and Founders acquisition route.",
            "certification": {"status": "certified", "evidence": ["published_transcript succeeded on podscripts All-In episodes during runtime certification"]},
        },
        "invest_like_best": {
            "canonical_name": "Invest Like the Best",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "investor and founder interview depth"],
            "url_patterns": ["invest-like-the-best"],
            "name_aliases": ["invest like the best", "iltb"],
            "monitoring_reason": "Patrick O'Shaughnessy investor interviews; Investing and Founders acquisition route.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
        "acquired": {
            "canonical_name": "Acquired",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "company deep-dive transcripts"],
            "url_patterns": ["podcasts/acquired"],
            "name_aliases": ["acquired podcast"],
            "monitoring_reason": "Company deep dives; Investing and Founders acquisition route.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
        "odd_lots": {
            "canonical_name": "Odd Lots",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "Bloomberg markets coverage"],
            "url_patterns": ["odd-lots"],
            "name_aliases": ["odd lots"],
            "monitoring_reason": "Macro and market structure acquisition route for Investing profile.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
        "bg2_pod": {
            "canonical_name": "BG2 Pod",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "Gerstner/Gurley venture and public tech lens"],
            "url_patterns": ["bg2-pod"],
            "name_aliases": ["bg2 pod", "bg2"],
            "monitoring_reason": "Venture and public tech cycle acquisition route.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
        "founders": {
            "canonical_name": "Founders",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete"],
            "url_patterns": ["podcasts/founders"],
            "monitoring_reason": "Founder biography podcast; Founders profile acquisition route.",
            "certification": {"status": "certified"},
        },
        "lenny_podcast": {
            "canonical_name": "Lenny's Podcast",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "product and growth operator interviews"],
            "url_patterns": ["lennys-podcast"],
            "name_aliases": ["lenny's podcast", "lenny podcast"],
            "monitoring_reason": "Product operator acquisition route for Founders profile.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
        "masters_of_scale": {
            "canonical_name": "Masters of Scale",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "Reid Hoffman scaling interviews"],
            "url_patterns": ["masters-of-scale"],
            "name_aliases": ["masters of scale"],
            "monitoring_reason": "Scaling tactics acquisition route for Founders profile.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
        "how_i_built_this": {
            "canonical_name": "How I Built This",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "NPR founder narratives"],
            "url_patterns": ["how-i-built-this"],
            "name_aliases": ["how i built this"],
            "monitoring_reason": "Founder narrative acquisition route for Founders profile.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
        "peter_attia": {
            "canonical_name": "The Peter Attia Drive",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts provides full episode transcripts"],
            "url_patterns": ["the-peter-attia-drive", "peterattiamd\\.com"],
            "name_aliases": ["peter attia drive"],
            "monitoring_reason": "Primary longevity clinical podcast acquisition route.",
            "certification": {"status": "certified"},
        },
        "huberman_lab": {
            "canonical_name": "Huberman Lab",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "neuroscience protocol depth"],
            "url_patterns": ["huberman-lab"],
            "name_aliases": ["huberman lab"],
            "monitoring_reason": "Neuroscience and performance acquisition route for Longevity profile.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
        "foundmyfitness": {
            "canonical_name": "FoundMyFitness",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "nutrition and aging research"],
            "url_patterns": ["foundmyfitness"],
            "name_aliases": ["found my fitness"],
            "monitoring_reason": "Rhonda Patrick nutrition and aging acquisition route.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
        "proof_simon_hill": {
            "canonical_name": "The Proof with Simon Hill",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "evidence-based nutrition debates"],
            "url_patterns": ["the-proof-with-simon-hill"],
            "name_aliases": ["the proof", "simon hill"],
            "monitoring_reason": "Nutrition evidence acquisition route for Longevity profile.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
        "lifespan_sinclair": {
            "canonical_name": "Lifespan with Dr. David Sinclair",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "aging biology explanations"],
            "url_patterns": ["lifespan-with-dr-david-sinclair"],
            "name_aliases": ["lifespan podcast", "david sinclair podcast"],
            "monitoring_reason": "Aging biology acquisition route for Longevity profile.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
        "doctors_farmacy": {
            "canonical_name": "The Doctor's Farmacy with Mark Hyman",
            "preferred_route": "published_transcript",
            "fallbacks": ["youtube_transcript_api", "yt_dlp_whisper"],
            "reason": ["podscripts mirror complete", "functional medicine interviews"],
            "url_patterns": ["the-doctors-farmacy-with-mark-hyman"],
            "name_aliases": ["doctor's farmacy", "mark hyman podcast"],
            "monitoring_reason": "Functional medicine acquisition route for Longevity profile.",
            "certification": {"status": "pending", "evidence": ["podscripts index verified HTTP 200 at configuration time"]},
        },
    }
    non_podcast_routes = {
        "openai_blog": {"canonical_name": "OpenAI Blog", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["company research and product announcements"], "url_patterns": ["openai\\.com/blog"], "monitoring_reason": "OpenAI product and safety announcements.", "certification": {"status": "pending"}},
        "anthropic_news": {"canonical_name": "Anthropic News", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["frontier lab news and research posts"], "url_patterns": ["anthropic\\.com/news"], "monitoring_reason": "Anthropic model and safety releases.", "certification": {"status": "pending"}},
        "nvidia_gtc": {"canonical_name": "NVIDIA GTC", "preferred_route": "youtube_transcript_api", "fallbacks": ["yt_dlp_whisper"], "reason": ["keynote video transcripts"], "url_patterns": ["nvidia\\.com/gtc"], "monitoring_reason": "AI hardware and platform roadmap keynotes.", "certification": {"status": "pending"}},
        "neurips": {"canonical_name": "NeurIPS", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["conference papers and invited talks"], "url_patterns": ["neurips\\.cc"], "monitoring_reason": "Flagship ML research conference.", "certification": {"status": "pending"}},
        "microsoft_build": {"canonical_name": "Microsoft Build", "preferred_route": "youtube_transcript_api", "fallbacks": ["yt_dlp_whisper"], "reason": ["developer conference keynotes"], "url_patterns": ["build\\.microsoft\\.com"], "monitoring_reason": "Enterprise AI developer announcements.", "certification": {"status": "pending"}},
        "ycombinator_blog": {"canonical_name": "Y Combinator Blog", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["startup operator essays"], "url_patterns": ["ycombinator\\.com/blog"], "monitoring_reason": "Startup AI adoption and operator writing.", "certification": {"status": "pending"}},
        "howard_marks_memos": {"canonical_name": "Howard Marks Memos", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["investor memos with full text"], "url_patterns": ["oaktreecapital\\.com/insights/memos"], "monitoring_reason": "Institutional risk and cycle commentary.", "certification": {"status": "pending"}},
        "berkshire_letters": {"canonical_name": "Berkshire Hathaway Shareholder Letters", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["annual shareholder letters"], "url_patterns": ["berkshirehathaway\\.com/letters"], "monitoring_reason": "Buffett capital allocation doctrine.", "certification": {"status": "pending"}},
        "a16z_blog": {"canonical_name": "a16z Blog", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["venture research articles"], "url_patterns": ["a16z\\.com"], "monitoring_reason": "Technology investing and market maps.", "certification": {"status": "pending"}},
        "colossus": {"canonical_name": "Colossus", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["investor letters and founder media"], "url_patterns": ["joincolossus\\.com"], "monitoring_reason": "Investor and founder archival media.", "certification": {"status": "pending"}},
        "grants_pub": {"canonical_name": "Grant's Interest Rate Observer", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["macro newsletter archive"], "url_patterns": ["grantspub\\.com"], "monitoring_reason": "Independent macro and credit analysis.", "certification": {"status": "pending"}},
        "ark_research": {"canonical_name": "ARK Invest Research", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["disruptive innovation research articles"], "url_patterns": ["ark-invest\\.com/articles"], "monitoring_reason": "AI and innovation equity research.", "certification": {"status": "pending"}},
        "pershing_letters": {"canonical_name": "Pershing Square Holdings Letters", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["activist investor letters"], "url_patterns": ["pershingsquareholdings\\.com/letters"], "monitoring_reason": "Bill Ackman portfolio and activist theses.", "certification": {"status": "pending"}},
        "first_round_review": {"canonical_name": "First Round Review", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["operator essays"], "url_patterns": ["review\\.firstround\\.com"], "monitoring_reason": "Early-stage operating playbooks.", "certification": {"status": "pending"}},
        "stratechery": {"canonical_name": "Stratechery", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["Ben Thompson strategy essays"], "url_patterns": ["stratechery\\.com"], "monitoring_reason": "Platform strategy and aggregation theory.", "certification": {"status": "pending"}},
        "stripe_sessions": {"canonical_name": "Stripe Sessions", "preferred_route": "youtube_transcript_api", "fallbacks": ["yt_dlp_whisper"], "reason": ["operator conference talks"], "url_patterns": ["stripe\\.com/sessions"], "monitoring_reason": "Internet economy operator keynotes.", "certification": {"status": "pending"}},
        "saastr_annual": {"canonical_name": "SaaStr Annual", "preferred_route": "youtube_transcript_api", "fallbacks": ["yt_dlp_whisper"], "reason": ["B2B SaaS conference sessions"], "url_patterns": ["saastrannual\\.com"], "monitoring_reason": "SaaS leadership and GTM conference.", "certification": {"status": "pending"}},
        "examine": {"canonical_name": "Examine.com", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["nutrition and supplement research summaries"], "url_patterns": ["examine\\.com"], "monitoring_reason": "Evidence-based nutrition reference.", "certification": {"status": "pending"}},
        "peter_attia_site": {"canonical_name": "Peter Attia MD", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["clinical newsletter and show notes"], "url_patterns": ["peterattiamd\\.com"], "monitoring_reason": "Attia clinical frameworks and newsletter.", "certification": {"status": "pending"}},
        "longevity_technology": {"canonical_name": "Longevity.Technology", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["longevity industry news"], "url_patterns": ["longevity\\.technology"], "monitoring_reason": "Aging therapeutics industry coverage.", "certification": {"status": "pending"}},
        "nia_news": {"canonical_name": "National Institute on Aging News", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["NIH aging research announcements"], "url_patterns": ["nia\\.nih\\.gov/news"], "monitoring_reason": "Federal aging research and trials.", "certification": {"status": "pending"}},
        "insidetracker_blog": {"canonical_name": "InsideTracker Blog", "preferred_route": "published_transcript", "fallbacks": ["transcript_mirror"], "reason": ["biomarker and performance articles"], "url_patterns": ["insidetracker\\.com/blog"], "monitoring_reason": "Blood biomarker interpretation for healthspan.", "certification": {"status": "pending"}},
        "a4m": {"canonical_name": "A4M World Congress", "preferred_route": "youtube_transcript_api", "fallbacks": ["yt_dlp_whisper"], "reason": ["longevity medicine conference sessions"], "url_patterns": ["a4m\\.com"], "monitoring_reason": "Clinical longevity medicine conference.", "certification": {"status": "pending"}},
    }
    sources = {}
    for source_id, payload in {**podcast_routes, **non_podcast_routes}.items():
        sources[source_id] = payload
    return {"sources": sources}


def _write_source_routes_yaml(path: Path, routes: dict) -> None:
    try:
        import yaml  # type: ignore
    except Exception:
        path.write_text(json.dumps(routes, indent=2, sort_keys=True), encoding="utf-8")
        return
    path.write_text(yaml.safe_dump(routes, sort_keys=False), encoding="utf-8")


def generate_watch_universe_doc(profiles: list[IntelligenceProfile], routes: dict) -> str:
    from collections import defaultdict

    people_map: dict[str, list[str]] = defaultdict(list)
    for profile in profiles:
        for entry in profile.watch_list:
            people_map[entry.display_name].append(profile.name)

    lines = [
        "# Watch Universe v1",
        "",
        "Production intelligence watch universe for Knowledge_Service.",
        "",
        "## Scope",
        "",
        "- **Profiles:** AI, Investing, Founders, Longevity",
        "- **Per profile:** exactly 10 watched people, 10–12 recurring sources",
        "- **Philosophy:** person-centric monitoring; podcasts are acquisition routes",
        "- **Configuration:** `config/profiles.json`, `data/source_routes.json`",
        "",
        "## Universe Summary",
        "",
        "| Profile | Watched People | Sources | Required Podcasts | Optional Podcasts | Non-Podcast Sources |",
        "|---------|----------------|---------|-------------------|-------------------|---------------------|",
    ]
    for profile in profiles:
        recurring = profile.metadata.get("recurring_sources", [])
        lines.append(
            f"| {profile.name} | 10 | {len(profile.required_podcasts) + len(profile.optional_podcasts) + len(recurring)} | "
            f"{len(profile.required_podcasts)} | {len(profile.optional_podcasts)} | {len(recurring)} |"
        )

    lines.extend([
        "",
        "## Cross-Profile People",
        "",
        "Shared people are deduplicated at the identity level but may belong to multiple profiles:",
        "",
    ])
    for name, profile_names in sorted(people_map.items()):
        if len(profile_names) > 1:
            lines.append(f"- **{name}:** {', '.join(profile_names)}")

    unique_people = len(people_map)
    lines.extend([
        "",
        f"**Unique watched people across universe:** {unique_people}",
        "",
        "## Source Route Registry",
        "",
        f"**Total registered sources:** {len(routes['sources'])}",
        "",
        "| Source ID | Canonical Name | Preferred Route | Certification |",
        "|-----------|------------------|-----------------|---------------|",
    ])
    for source_id, entry in sorted(routes["sources"].items()):
        cert = entry.get("certification", {}).get("status", "pending")
        lines.append(f"| `{source_id}` | {entry['canonical_name']} | `{entry['preferred_route']}` | {cert} |")

    lines.extend([
        "",
        "## Inclusion Principles",
        "",
        "1. **People over venues** — watch lists drive discovery; sources exist to acquire evidence when watched people appear.",
        "2. **Active, primary sources** — CEOs, practicing investors, active researchers, and currently publishing clinicians.",
        "3. **Podcasts as acquisition routes** — required podcasts are high-signal interview venues; optional podcasts broaden coverage.",
        "4. **Non-podcast recurrence** — blogs, letters, research portals, and conferences provide structured non-interview signal.",
        "5. **No placeholders** — every person and source is real, named, and URL-verified at configuration time.",
        "",
        "## Profile Rationale Summaries",
        "",
    ])
    for profile in profiles:
        lines.extend([f"### {profile.name}", "", profile.description, ""])
        lines.append(f"**Interests:** {', '.join(profile.interests)}")
        lines.append("")

    lines.extend([
        "## Files",
        "",
        "| File | Purpose |",
        "|------|---------|",
        "| `config/profiles.json` | Production Intelligence Profiles |",
        "| `config/profiles.yaml` | YAML export of profiles |",
        "| `data/source_routes.json` | Acquisition route registry |",
        "| `data/source_routes.yaml` | YAML export of route registry |",
        "| `docs/PROFILE_WATCHLISTS.md` | Per-profile people and source rationales |",
        "",
        "## Rebuild",
        "",
        "```bash",
        ".venv/bin/python3 config/build_watch_universe.py",
        "```",
        "",
    ])
    return "\n".join(lines)


def generate_profile_watchlists_doc(profiles: list[IntelligenceProfile]) -> str:
    lines = [
        "# Profile Watchlists v1",
        "",
        "Inclusion rationale for every watched person and recurring source in the production watch universe.",
        "",
    ]
    for profile in profiles:
        lines.extend([
            f"## {profile.name}",
            "",
            profile.description,
            "",
            f"**Profile ID:** `{profile.profile_id}`  ",
            f"**Interests:** {', '.join(profile.interests)}",
            "",
            "### Watched People (10)",
            "",
            "| Person | Organization | Priority | Profiles | Rationale |",
            "|--------|--------------|----------|----------|-----------|",
        ])
        for entry in profile.watch_list:
            org = entry.organization or "—"
            rationale = entry.metadata.get("inclusion_rationale", "")
            lines.append(f"| {entry.display_name} | {org} | {entry.priority} | {profile.name} | {rationale} |")

        lines.extend(["", "### Recurring Sources (12)", "", "#### Required Podcasts (acquisition routes)", ""])
        for podcast in profile.required_podcasts:
            rationale = podcast.metadata.get("inclusion_rationale", "")
            lines.append(f"- **{podcast.name}** — `{podcast.url}`  ")
            lines.append(f"  - Priority {podcast.priority}; polling {podcast.polling_interval_seconds}s  ")
            lines.append(f"  - *Rationale:* {rationale}")
            lines.append("")

        lines.append("#### Optional Podcasts (acquisition routes)")
        lines.append("")
        for podcast in profile.optional_podcasts:
            rationale = podcast.metadata.get("inclusion_rationale", "")
            lines.append(f"- **{podcast.name}** — `{podcast.url}`  ")
            lines.append(f"  - Priority {podcast.priority}; polling {podcast.polling_interval_seconds}s  ")
            lines.append(f"  - *Rationale:* {rationale}")
            lines.append("")

        lines.extend(["#### Non-Podcast Recurring Sources", ""])
        for source in profile.metadata.get("recurring_sources", []):
            lines.append(f"- **{source['name']}** (`{source['source_id']}`) — `{source['url']}`  ")
            lines.append(f"  - Type: {source['source_type']}; priority {source['priority']}  ")
            lines.append(f"  - *Rationale:* {source['inclusion_rationale']}")
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.extend([
        "## Cross-Profile Membership",
        "",
        "| Person | Profiles |",
        "|--------|----------|",
    ])
    from collections import defaultdict

    people_map: dict[str, list[str]] = defaultdict(list)
    for profile in profiles:
        for entry in profile.watch_list:
            people_map[entry.display_name].append(profile.name)
    for name, profile_names in sorted(people_map.items()):
        marker = " *(multi-profile)*" if len(profile_names) > 1 else ""
        lines.append(f"| {name} | {', '.join(profile_names)}{marker} |")

    return "\n".join(lines)


def validate_profiles(profiles: list[IntelligenceProfile]) -> list[str]:
    errors: list[str] = []
    if len(profiles) != 4:
        errors.append(f"expected 4 profiles, got {len(profiles)}")
    for profile in profiles:
        if len(profile.watch_list) != 10:
            errors.append(f"{profile.name}: expected 10 watched people, got {len(profile.watch_list)}")
        recurring = profile.metadata.get("recurring_sources", [])
        podcast_count = len(profile.required_podcasts) + len(profile.optional_podcasts)
        total_sources = podcast_count + len(recurring)
        if total_sources < 10 or total_sources > 12:
            errors.append(f"{profile.name}: expected 10-12 sources, got {total_sources} (podcasts={podcast_count}, recurring={len(recurring)})")
        names = [entry.display_name for entry in profile.watch_list]
        if len(names) != len(set(names)):
            errors.append(f"{profile.name}: duplicate people within profile")
    return errors


def main() -> int:
    profiles = production_profiles()
    errors = validate_profiles(profiles)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    config_dir = ROOT / "config"
    data_dir = ROOT / "data"
    config_dir.mkdir(parents=True, exist_ok=True)

    save_profiles(config_dir / "profiles.json", profiles)
    save_profiles(config_dir / "profiles.yaml", profiles)

    routes = production_source_routes()
    (data_dir / "source_routes.json").write_text(json.dumps(routes, indent=2, sort_keys=True), encoding="utf-8")
    _write_source_routes_yaml(data_dir / "source_routes.yaml", routes)

    docs_dir = ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "WATCH_UNIVERSE_V1.md").write_text(generate_watch_universe_doc(profiles, routes), encoding="utf-8")
    (docs_dir / "PROFILE_WATCHLISTS.md").write_text(generate_profile_watchlists_doc(profiles), encoding="utf-8")

    loaded = load_profiles(config_dir / "profiles.json")
    assert len(loaded) == 4

    print(f"Wrote {config_dir / 'profiles.json'}")
    print(f"Wrote {config_dir / 'profiles.yaml'}")
    print(f"Wrote {data_dir / 'source_routes.json'} ({len(routes['sources'])} sources)")
    print(f"Wrote {docs_dir / 'WATCH_UNIVERSE_V1.md'}")
    print(f"Wrote {docs_dir / 'PROFILE_WATCHLISTS.md'}")
    print("Validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())