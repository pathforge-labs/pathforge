"""
Unit tests for the ONET data loader.

Covers all query functions, the bottleneck calculator,
and lru_cache behavior on load_onet_dataset.
"""

from __future__ import annotations

import pytest

from app.data.onet_loader import (
    BottleneckScores,
    compute_bottleneck_average,
    get_all_categories,
    get_occupation_by_soc,
    get_occupations_by_category,
    load_onet_dataset,
    search_occupations_by_title,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear lru_cache before and after each test for isolation."""
    load_onet_dataset.cache_clear()
    yield
    load_onet_dataset.cache_clear()


# ── load_onet_dataset ─────────────────────────────────────────────


class TestLoadOnetDataset:
    def test_returns_dataset_with_occupations(self) -> None:
        ds = load_onet_dataset()
        assert len(ds["occupations"]) > 0

    def test_by_soc_code_index_populated(self) -> None:
        ds = load_onet_dataset()
        assert len(ds["by_soc_code"]) == len(ds["occupations"])

    def test_by_category_groups_correctly(self) -> None:
        ds = load_onet_dataset()
        for category, entries in ds["by_category"].items():
            assert all(e["category"] == category for e in entries)

    def test_cached_second_call_returns_same_object(self) -> None:
        ds1 = load_onet_dataset()
        ds2 = load_onet_dataset()
        assert ds1 is ds2  # same object from lru_cache

    def test_occupation_entries_have_required_fields(self) -> None:
        ds = load_onet_dataset()
        entry = ds["occupations"][0]
        assert "soc_code" in entry
        assert "title" in entry
        assert "automation_probability" in entry
        assert "bottleneck_scores" in entry
        assert "category" in entry


# ── get_occupation_by_soc ─────────────────────────────────────────


class TestGetOccupationBySoc:
    def test_returns_entry_for_known_soc(self) -> None:
        ds = load_onet_dataset()
        # pick a real SOC code from the dataset
        soc = ds["occupations"][0]["soc_code"]
        entry = get_occupation_by_soc(soc)
        assert entry is not None
        assert entry["soc_code"] == soc

    def test_returns_none_for_unknown_soc(self) -> None:
        result = get_occupation_by_soc("99-9999.99")
        assert result is None

    def test_returns_correct_entry(self) -> None:
        ds = load_onet_dataset()
        first = ds["occupations"][0]
        result = get_occupation_by_soc(first["soc_code"])
        assert result is not None
        assert result["title"] == first["title"]


# ── search_occupations_by_title ───────────────────────────────────


class TestSearchOccupationsByTitle:
    def test_returns_list(self) -> None:
        results = search_occupations_by_title("engineer")
        assert isinstance(results, list)

    def test_matches_substring_case_insensitive(self) -> None:
        results = search_occupations_by_title("ENGINEER")
        results_lower = search_occupations_by_title("engineer")
        assert len(results) == len(results_lower)

    def test_no_match_returns_empty(self) -> None:
        results = search_occupations_by_title("zzznomatchzzz")
        assert results == []

    def test_respects_max_results(self) -> None:
        # "er" is common enough to yield many results in any dataset
        results = search_occupations_by_title("er", max_results=3)
        assert len(results) <= 3

    def test_sorted_by_automation_probability_descending(self) -> None:
        results = search_occupations_by_title("er", max_results=20)
        if len(results) >= 2:
            for i in range(len(results) - 1):
                assert results[i]["automation_probability"] >= results[i + 1]["automation_probability"]

    def test_default_max_results_is_ten(self) -> None:
        # There should be enough entries in the dataset for this
        results = search_occupations_by_title("er")
        assert len(results) <= 10


# ── get_occupations_by_category ──────────────────────────────────


class TestGetOccupationsByCategory:
    def test_returns_entries_for_known_category(self) -> None:
        ds = load_onet_dataset()
        category = ds["occupations"][0]["category"]
        results = get_occupations_by_category(category)
        assert len(results) > 0
        assert all(e["category"] == category for e in results)

    def test_returns_empty_for_unknown_category(self) -> None:
        results = get_occupations_by_category("nonexistent_category_xyz")
        assert results == []


# ── get_all_categories ────────────────────────────────────────────


class TestGetAllCategories:
    def test_returns_sorted_list(self) -> None:
        categories = get_all_categories()
        assert categories == sorted(categories)

    def test_returns_non_empty_list(self) -> None:
        categories = get_all_categories()
        assert len(categories) > 0

    def test_all_categories_have_occupations(self) -> None:
        categories = get_all_categories()
        for cat in categories:
            assert len(get_occupations_by_category(cat)) > 0


# ── compute_bottleneck_average ────────────────────────────────────


class TestComputeBottleneckAverage:
    def test_average_of_equal_values(self) -> None:
        scores: BottleneckScores = {
            "perception_manipulation": 0.5,
            "creative_intelligence": 0.5,
            "social_intelligence": 0.5,
        }
        assert compute_bottleneck_average(scores) == pytest.approx(0.5)

    def test_average_of_zeros(self) -> None:
        scores: BottleneckScores = {
            "perception_manipulation": 0.0,
            "creative_intelligence": 0.0,
            "social_intelligence": 0.0,
        }
        assert compute_bottleneck_average(scores) == pytest.approx(0.0)

    def test_average_of_ones(self) -> None:
        scores: BottleneckScores = {
            "perception_manipulation": 1.0,
            "creative_intelligence": 1.0,
            "social_intelligence": 1.0,
        }
        assert compute_bottleneck_average(scores) == pytest.approx(1.0)

    def test_average_of_mixed_values(self) -> None:
        scores: BottleneckScores = {
            "perception_manipulation": 0.2,
            "creative_intelligence": 0.85,
            "social_intelligence": 0.95,
        }
        expected = (0.2 + 0.85 + 0.95) / 3
        assert compute_bottleneck_average(scores) == pytest.approx(expected)

    def test_shield_threshold(self) -> None:
        # >= 0.60 → SHIELD classification
        scores: BottleneckScores = {
            "perception_manipulation": 0.6,
            "creative_intelligence": 0.6,
            "social_intelligence": 0.6,
        }
        assert compute_bottleneck_average(scores) >= 0.60

    def test_exposure_threshold(self) -> None:
        # <= 0.35 → EXPOSURE classification
        scores: BottleneckScores = {
            "perception_manipulation": 0.3,
            "creative_intelligence": 0.35,
            "social_intelligence": 0.4,
        }
        avg = compute_bottleneck_average(scores)
        assert avg == pytest.approx((0.3 + 0.35 + 0.4) / 3)
