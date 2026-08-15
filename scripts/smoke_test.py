"""Local scaffold smoke test with no cloud writes."""

from app.config import settings
from app.core.state import RunStage


def main() -> None:
    print(f"project={settings.project_id}")
    print(f"vertex_location={settings.vertex_location}")
    print(f"cloud_region={settings.cloud_region}")
    print(f"agent={settings.agent_name}")
    print(f"success_milestone={RunStage.MODEL_READY}")
    print("terminal_stages=FAILED,COMPLETE")


if __name__ == "__main__":
    main()
