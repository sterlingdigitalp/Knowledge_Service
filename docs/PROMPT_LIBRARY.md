# Prompt Library

Dedicated analyst prompts live in `src/knowledge_service/production/llm/prompts.py`.

## System Persona

All prompts share a senior research analyst persona. The model must not reference transcripts, claims, clustering, or LLM mechanics.

## Theme Naming

**Objective:** Equity-research section titles (2–5 words).

Examples:
- `AI Compute Memory` → `Inference Economics`
- `Healthcare Drug` → `GLP-1 Competitive Landscape`

## Executive Summary

**Structure:** What changed → Why it matters → Why now → What to watch next.

Target: 80–140 words of flowing analyst prose. No bullet lists or transcript quotes.

## Deep Dive

**Objective:** Research analyst briefing with historical context, competing views, corroboration, contradictions, and watch points.

Uses evidence excerpts and conversation history. Supports multi-turn continuity via xAI `previous_response_id`.

## Follow-up Questions

**Objective:** Four principal-style questions, one per line, no numbering.

## Morning Brief Wording

Prompt template available for item-level readability polish while preserving facts.