from knowledge_service.production.benchmark_llm import LLMQualityBenchmark


def test_llm_benchmark_detects_title_improvement():
    benchmark = LLMQualityBenchmark()
    report = benchmark.compare_runs(
        heuristic_items=[
            {"item_id": "a", "title": "AI Compute Memory", "executive_summary": "What changed. Why it matters."},
        ],
        xai_items=[
            {"item_id": "a", "title": "Inference Economics", "executive_summary": "What changed across sources. Why it matters now. Watch corroboration."},
        ],
        heuristic_brief={"reading_time_seconds": 55, "quality_score": 0.45},
        xai_brief={"reading_time_seconds": 54, "quality_score": 0.62},
    )

    assert report["theme_titles"]["improved"] is True
    assert report["quality_evaluation"]["human_noticeable_improvement"] is True