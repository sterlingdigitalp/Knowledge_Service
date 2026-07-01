# Watch Universe v1

Production intelligence watch universe for Knowledge_Service.

## Scope

- **Profiles:** AI, Investing, Founders, Longevity
- **Per profile:** exactly 10 watched people, 10–12 recurring sources
- **Philosophy:** person-centric monitoring; podcasts are acquisition routes
- **Configuration:** `config/profiles.json`, `data/source_routes.json`

## Universe Summary

| Profile | Watched People | Sources | Required Podcasts | Optional Podcasts | Non-Podcast Sources |
|---------|----------------|---------|-------------------|-------------------|---------------------|
| AI | 10 | 12 | 3 | 3 | 6 |
| Investing | 10 | 12 | 3 | 2 | 7 |
| Founders | 10 | 12 | 3 | 3 | 6 |
| Longevity | 10 | 12 | 3 | 3 | 6 |

## Cross-Profile People

Shared people are deduplicated at the identity level but may belong to multiple profiles:

- **Marc Andreessen:** Investing, Founders
- **Patrick O'Shaughnessy:** Investing, Founders
- **Sam Altman:** AI, Investing, Founders
- **Satya Nadella:** AI, Founders

**Unique watched people across universe:** 35

## Source Route Registry

**Total registered sources:** 44

| Source ID | Canonical Name | Preferred Route | Certification |
|-----------|------------------|-----------------|---------------|
| `a16z_blog` | a16z Blog | `published_transcript` | pending |
| `a4m` | A4M World Congress | `youtube_transcript_api` | pending |
| `acquired` | Acquired | `published_transcript` | pending |
| `all_in` | All-In Podcast | `published_transcript` | certified |
| `anthropic_news` | Anthropic News | `published_transcript` | pending |
| `ark_research` | ARK Invest Research | `published_transcript` | pending |
| `berkshire_letters` | Berkshire Hathaway Shareholder Letters | `published_transcript` | pending |
| `bg2_pod` | BG2 Pod | `published_transcript` | pending |
| `colossus` | Colossus | `published_transcript` | pending |
| `doctors_farmacy` | The Doctor's Farmacy with Mark Hyman | `published_transcript` | pending |
| `dwarkesh` | Dwarkesh Podcast | `published_transcript` | certified |
| `examine` | Examine.com | `published_transcript` | pending |
| `first_round_review` | First Round Review | `published_transcript` | pending |
| `founders` | Founders | `published_transcript` | certified |
| `foundmyfitness` | FoundMyFitness | `published_transcript` | pending |
| `grants_pub` | Grant's Interest Rate Observer | `published_transcript` | pending |
| `hard_fork` | Hard Fork | `published_transcript` | pending |
| `how_i_built_this` | How I Built This | `published_transcript` | pending |
| `howard_marks_memos` | Howard Marks Memos | `published_transcript` | pending |
| `huberman_lab` | Huberman Lab | `published_transcript` | pending |
| `insidetracker_blog` | InsideTracker Blog | `published_transcript` | pending |
| `invest_like_best` | Invest Like the Best | `published_transcript` | pending |
| `latent_space` | Latent Space | `published_transcript` | pending |
| `lenny_podcast` | Lenny's Podcast | `published_transcript` | pending |
| `lex_fridman` | Lex Fridman Podcast | `official_transcript` | certified |
| `lifespan_sinclair` | Lifespan with Dr. David Sinclair | `published_transcript` | pending |
| `longevity_technology` | Longevity.Technology | `published_transcript` | pending |
| `masters_of_scale` | Masters of Scale | `published_transcript` | pending |
| `microsoft_build` | Microsoft Build | `youtube_transcript_api` | pending |
| `neurips` | NeurIPS | `published_transcript` | pending |
| `nia_news` | National Institute on Aging News | `published_transcript` | pending |
| `no_priors` | No Priors | `published_transcript` | pending |
| `nvidia_ai_podcast` | The AI Podcast (NVIDIA) | `published_transcript` | pending |
| `nvidia_gtc` | NVIDIA GTC | `youtube_transcript_api` | pending |
| `odd_lots` | Odd Lots | `published_transcript` | pending |
| `openai_blog` | OpenAI Blog | `published_transcript` | pending |
| `pershing_letters` | Pershing Square Holdings Letters | `published_transcript` | pending |
| `peter_attia` | The Peter Attia Drive | `published_transcript` | certified |
| `peter_attia_site` | Peter Attia MD | `published_transcript` | pending |
| `proof_simon_hill` | The Proof with Simon Hill | `published_transcript` | pending |
| `saastr_annual` | SaaStr Annual | `youtube_transcript_api` | pending |
| `stratechery` | Stratechery | `published_transcript` | pending |
| `stripe_sessions` | Stripe Sessions | `youtube_transcript_api` | pending |
| `ycombinator_blog` | Y Combinator Blog | `published_transcript` | pending |

## Inclusion Principles

1. **People over venues** — watch lists drive discovery; sources exist to acquire evidence when watched people appear.
2. **Active, primary sources** — CEOs, practicing investors, active researchers, and currently publishing clinicians.
3. **Podcasts as acquisition routes** — required podcasts are high-signal interview venues; optional podcasts broaden coverage.
4. **Non-podcast recurrence** — blogs, letters, research portals, and conferences provide structured non-interview signal.
5. **No placeholders** — every person and source is real, named, and URL-verified at configuration time.

## Profile Rationale Summaries

### AI

AI systems, coding, datacenters, inference, agents, and enterprise AI.

**Interests:** AI, Coding, Datacenters, Inference, Agents, Enterprise AI, AGI, ML systems

### Investing

Markets, capital allocation, technology investing, and macro debates.

**Interests:** investing, markets, AI, China, macro, venture capital, public equities

### Founders

Company building, founder biographies, and operating lessons.

**Interests:** founders, company building, biography, business, operations, culture

### Longevity

Healthspan, performance, metabolic health, and translational medicine.

**Interests:** longevity, muscle, GLP-1, metabolic, healthspan, cardiovascular, sleep, nutrition

## Files

| File | Purpose |
|------|---------|
| `config/profiles.json` | Production Intelligence Profiles |
| `config/profiles.yaml` | YAML export of profiles |
| `data/source_routes.json` | Acquisition route registry |
| `data/source_routes.yaml` | YAML export of route registry |
| `docs/PROFILE_WATCHLISTS.md` | Per-profile people and source rationales |

## Rebuild

```bash
.venv/bin/python3 config/build_watch_universe.py
```
