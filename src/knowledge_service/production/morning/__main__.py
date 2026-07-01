"""CLI entry: python -m knowledge_service.production.morning"""

from .daily_runner import main

raise SystemExit(main())