import subprocess

from watchfiles import run_process


def start_bot() -> None:
    subprocess.run(["python", "-m", "src.main"], check=False)


if __name__ == "__main__":
    run_process(
    "src",
    "prompts",
    ".env",
    target=start_bot,
)