from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root_dir: Path
    data_dir: Path
    db_path: Path
    use_mock_tianyan: bool = True


def default_settings(testing: bool = False) -> Settings:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / ("work" if testing else "data")
    data_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        root_dir=root,
        data_dir=data_dir,
        db_path=data_dir / ("tiance_test.db" if testing else "tiance.db"),
        use_mock_tianyan=True,
    )
