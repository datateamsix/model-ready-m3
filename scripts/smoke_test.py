"""Local scaffold smoke test with no cloud writes."""

from app.config import settings
from app.core.state import RunStage


def main() -> None:
    print(f"project={settings.project_id}")
    print(f"location={settings.location}")
    print(f"agent={settings.agent_name}")
    print(f"target_terminal_state={RunStage.MODEL_READY}")


if __name__ == "__main__":
    main()
