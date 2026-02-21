from config import Settings


def test_settings_defaults() -> None:
    settings = Settings(
        _env_file=None,
    )
    assert settings.app_name == "AI Data Factory"
    assert settings.database_url.endswith("factory.db")
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.log_level == "INFO"


def test_settings_scraping_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.scraping_max_concurrent == 3
    assert settings.scraping_rate_limit == 2.0
    assert settings.scraping_respect_robots_txt is True


def test_settings_generation_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.generation_model == "gpt-4o-mini"
    assert settings.generation_max_concurrent == 5
    assert settings.quality_min_score == 0.7
