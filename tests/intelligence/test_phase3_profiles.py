import json

from knowledge_service.intelligence.config import load_profiles, save_profiles
from knowledge_service.intelligence.models import IntelligenceProfile, PodcastSource, WatchListEntry


def test_profiles_import_export_json_and_yaml_compatible(tmp_path):
    profile = IntelligenceProfile(
        name="AI",
        description="AI intelligence profile",
        color="#00aaff",
        interests=["AI", "Datacenters"],
        watch_list=[WatchListEntry(display_name="Sam Altman", aliases=["sama"], organization="OpenAI", source_handles={"x": "sama"})],
        required_podcasts=[PodcastSource(name="Dwarkesh Podcast", url="https://podscripts.co/podcasts/dwarkesh-podcast", priority=9)],
    )

    json_path = tmp_path / "profiles.json"
    yaml_path = tmp_path / "profiles.yaml"
    save_profiles(json_path, [profile])
    save_profiles(yaml_path, [profile])

    json_profiles = load_profiles(json_path)
    yaml_profiles = load_profiles(yaml_path)

    assert json_profiles[0].name == "AI"
    assert json_profiles[0].watch_list[0].source_handles["x"] == "sama"
    assert yaml_profiles[0].required_podcasts[0].polling_interval_seconds == 3600
    assert json.loads(json_path.read_text())["profiles"][0]["podcasts"]["required"][0]["name"] == "Dwarkesh Podcast"


def test_profile_optional_podcasts_exclude_ignored_sources():
    profile = IntelligenceProfile(
        name="Investing",
        optional_podcasts=[
            PodcastSource(name="All-In Podcast", url="https://example.com/all-in"),
            PodcastSource(name="Ignored", url="https://example.com/ignored"),
        ],
        ignore_podcasts=[PodcastSource(name="Ignored", url="https://example.com/ignored")],
    )

    enabled = profile.enabled_podcasts()

    assert [podcast.name for podcast in enabled] == ["All-In Podcast"]
