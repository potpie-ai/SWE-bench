import argparse
import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, cast

from agent import PotpieAgentExecutor

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "evals_resolved"
DEFAULT_ENV_FILE = Path(".env")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Potpie agent evaluations sequentially."
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Path to a JSON/JSONL file containing evaluation instances. "
        "Can also be provided via environment variables.",
    )
    parser.add_argument(
        "--base-url",
        help="Base URL for the Potpie agent service. "
        "Overrides any value from environment variables.",
    )
    parser.add_argument(
        "--secret",
        help="API secret token for the Potpie agent service. "
        "Overrides any value from environment variables.",
    )
    parser.add_argument(
        "--user-id",
        help="User ID to use when communicating with the Potpie agent. "
        "Overrides any value from environment variables.",
    )
    parser.add_argument(
        "--agent-id",
        help="Agent ID to use when creating conversations. "
        "Overrides any value from environment variables.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="Timeout (minutes) for agent responses. "
        "Defaults to 25 if not provided via CLI or environment.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to write evaluation outputs. Defaults to ./evals.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional limit on number of instances to evaluate.",
    )
    parser.add_argument(
        "--instance-ids",
        nargs="+",
        help="Optional list of instance IDs to evaluate. Only instances matching these IDs will be processed.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help="Path to a .env file with configuration values. Defaults to ./.env.",
    )
    return parser.parse_args()


def load_env_file(path: Optional[Path]) -> None:
    if path is None:
        return
    path = path.expanduser()
    if not path.exists() or not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def env_get(keys: Iterable[str]) -> Optional[str]:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


def resolve_required_string(
    current: Optional[str], keys: Iterable[str], description: str
) -> str:
    value = current or env_get(keys)
    if not value:
        key_hint = ", ".join(keys)
        raise ValueError(
            f"{description} missing. Provide via CLI flag or environment variable "
            f"(one of: {key_hint})."
        )
    return value


def resolve_optional_int(
    current: Optional[int], keys: Iterable[str], default: Optional[int] = None
) -> Optional[int]:
    if current is not None:
        return current
    env_value = env_get(keys)
    if env_value is None:
        return default
    try:
        return int(env_value)
    except ValueError as exc:
        raise ValueError(
            f"Expected integer for environment variables {keys}, got {env_value!r}"
        ) from exc


def resolve_path(
    current: Optional[Path], keys: Iterable[str], default: Optional[Path] = None
) -> Optional[Path]:
    if current is not None:
        return current
    env_value = env_get(keys)
    if env_value:
        return Path(env_value).expanduser()
    return default


def resolve_instance_ids(
    current: Optional[List[str]], keys: Iterable[str]
) -> Optional[List[str]]:
    if current is not None:
        return current
    env_value = env_get(keys)
    if env_value is None:
        return None
    # Support both comma-separated and space-separated lists
    instance_ids = [id.strip() for id in re.split(r"[,\s]+", env_value) if id.strip()]
    return instance_ids if instance_ids else None


def load_swebench_lite_instances(split: str = "test") -> List[Dict[str, Any]]:
    try:
        from datasets import load_dataset  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "Missing optional dependency 'datasets'. Install it with "
            "`pip install datasets` to load SWE-bench Lite instances."
        ) from exc

    logger.info("Loading SWE-bench Lite (%s split) from Hugging Face", split)
    dataset = load_dataset("princeton-nlp/SWE-bench_Lite", split=split)
    records = cast(Iterable[Dict[Any, Any]], dataset)
    return [{str(key): value for key, value in record.items()} for record in records]


def load_instances(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Input file {path} does not exist.")

    if path.suffix.lower() in {".jsonl", ".jsonlines"}:
        instances: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as stream:
            for line in stream:
                trimmed = line.strip()
                if not trimmed:
                    continue
                instances.append(json.loads(trimmed))
        return instances

    if path.suffix.lower() in {".json"}:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return list(data)
        if isinstance(data, dict):
            return [data]
        raise ValueError("JSON input must be a list or dict of instances.")

    raise ValueError(
        f"Unsupported input format {path.suffix}. Use a .json or .jsonl file."
    )


def coalesce(instance: Dict[str, Any], keys: Iterable[str]) -> Optional[str]:
    for key in keys:
        value = instance.get(key)
        if value:
            return str(value)
    return None


def resolve_repo_name(instance: Dict[str, Any]) -> str:
    repo_name = coalesce(
        instance,
        (
            "repo",
            "repo_name",
            "repo_full_name",
            "repository",
            "repository_name",
            "repo_owner",
        ),
    )
    if repo_name:
        return repo_name

    head = instance.get("head") or {}
    repo_from_head = coalesce(head, ("repo", "full_name", "name"))
    if repo_from_head:
        return repo_from_head

    raise KeyError("Instance is missing a repository identifier.")


def resolve_commit_id(instance: Dict[str, Any]) -> str:
    commit_id = coalesce(
        instance,
        (
            "base_commit",
            "base_commit_sha",
            "base_commit_id",
            "commit",
            "commit_id",
            "sha",
        ),
    )
    if commit_id:
        return commit_id

    base = instance.get("base") or {}
    base_sha = coalesce(base, ("sha", "commit", "commit_id"))
    if base_sha:
        return base_sha

    raise KeyError("Instance is missing a commit identifier.")


def resolve_query(instance: Dict[str, Any], instance_id: str) -> str:
    query = coalesce(
        instance,
        (
            "problem_statement",
            "prompt",
            "issue",
            "body",
            "description",
            "summary",
            "title",
        ),
    )
    if query:
        return f"Instance ID: {instance_id}\n\n{query}"
    raise KeyError("Instance is missing a prompt/problem description for the agent.")


def resolve_instance_id(index: int, instance: Dict[str, Any]) -> str:
    instance_id = coalesce(
        instance,
        (
            "instance_id",
            "id",
            "instance",
            "slug",
            "issue_url",
            "html_url",
        ),
    )
    if instance_id:
        return instance_id
    return f"instance_{index:05d}"


def safe_filename(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name)


def extract_diff_from_response(response_text: str) -> Tuple[str, str]:
    """
    Extract the diff from the agent response.

    The diff is expected to be between markers:
    --generated diff--
    <diff content>
    --generated diff--

    Returns:
        tuple: (reasoning, model_patch) where:
            - reasoning: The complete response text
            - model_patch: The extracted diff, or empty string if not found
    """
    reasoning = response_text

    # Pattern to match content between --generated diff-- markers
    pattern = r"--generated diff--\s*(.*?)\s*--generated diff--"
    matches = re.findall(pattern, response_text, re.DOTALL)

    if matches:
        model_patch = matches[-1].strip()
        # Remove the code block markers if present (``` at start/end)
        model_patch = re.sub(r"^```[\w]*\n?", "", model_patch, flags=re.MULTILINE)
        model_patch = re.sub(r"\n?```$", "", model_patch, flags=re.MULTILINE)
        model_patch = model_patch.strip()
    else:
        model_patch = ""

    return reasoning, model_patch


async def evaluate_instance(
    executor: PotpieAgentExecutor,
    user_id: str,
    agent_id: str,
    instance_id: str,
    repo_name: str,
    commit_id: str,
    query: str,
) -> Dict[str, Any]:
    logger.info("Evaluating %s", instance_id)
    response = await executor.run_agent(
        user_id=user_id,
        repo_name=repo_name,
        commit_id=commit_id,
        agent_id=agent_id,
        query=query,
    )

    # Extract reasoning and model_patch from response
    reasoning, model_patch = extract_diff_from_response(response.text)

    return {
        "instance_id": instance_id,
        "repo_name": repo_name,
        "commit_id": commit_id,
        "query": query,
        "response_text": response.text,
        "reasoning": reasoning,
        "model_patch": model_patch,
        "conversation_id": response.conversation_id,
    }


async def process_instances(args: argparse.Namespace) -> None:
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.input:
        instances = load_instances(args.input)
    else:
        instances = load_swebench_lite_instances()

    args.instance_ids = [
        "astropy__astropy-12907",
    ]

    # Filter by instance_ids if provided
    if args.instance_ids:
        instance_id_set = set(args.instance_ids)
        filtered_instances = []
        for index, instance in enumerate(instances):
            instance_id = resolve_instance_id(index, instance)
            if instance_id in instance_id_set:
                filtered_instances.append(instance)
        instances = filtered_instances
        if instances:
            logger.info(
                "Filtered to %d instance(s) matching provided instance_ids",
                len(instances),
            )
        else:
            logger.warning(
                "No instances matched the provided instance_ids: %s",
                args.instance_ids,
            )

    if args.limit is not None:
        instances = instances[: args.limit]

    executor = PotpieAgentExecutor(
        base_url=args.base_url,
        secret=args.secret,
        timeout=args.timeout,
    )

    summary_path = output_dir / "summary.jsonl"
    processed = 0

    with summary_path.open("w", encoding="utf-8") as summary_file:
        for index, instance in enumerate(instances):
            instance_id = resolve_instance_id(index, instance)
            repo_name = resolve_repo_name(instance)
            commit_id = resolve_commit_id(instance)
            query = resolve_query(instance, instance_id)

            result_path = output_dir / f"{safe_filename(instance_id)}.json"

            try:
                result = await evaluate_instance(
                    executor=executor,
                    user_id=args.user_id,
                    agent_id=args.agent_id,
                    instance_id=instance_id,
                    repo_name=repo_name,
                    commit_id=commit_id,
                    query=query,
                )
                result["status"] = "success"
                logger.info("Completed %s", instance_id)
            except Exception as exc:
                logger.exception("Evaluation failed for %s", instance_id)
                result = {
                    "instance_id": instance_id,
                    "repo_name": repo_name,
                    "commit_id": commit_id,
                    "query": query,
                    "status": "error",
                    "error": str(exc),
                }

            result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            summary_file.write(json.dumps(result) + "\n")
            processed += 1

    logger.info(
        "Finished processing %d instance(s). Results in %s", processed, output_dir
    )


def main() -> None:
    args = parse_args()
    load_env_file(args.env_file)
    args.input = resolve_path(
        args.input,
        ("RUN_EVAL_INPUT", "RUN_EVAL_INSTANCES", "EVAL_INPUT"),
    )

    args.base_url = resolve_required_string(
        args.base_url,
        ("POTPIE_BASE_URL",),
        "Base URL",
    )
    args.secret = resolve_required_string(
        args.secret,
        ("RUN_EVAL_SECRET", "POTPIE_SECRET", "AGENT_SECRET", "SECRET", "TOKEN"),
        "API secret token",
    )
    args.user_id = resolve_required_string(
        args.user_id,
        ("RUN_EVAL_USER_ID", "POTPIE_USER_ID", "USER_ID"),
        "User ID",
    )
    args.agent_id = resolve_required_string(
        args.agent_id,
        ("RUN_EVAL_AGENT_ID", "POTPIE_AGENT_ID", "AGENT_ID"),
        "Agent ID",
    )
    args.timeout = resolve_optional_int(
        args.timeout,
        ("RUN_EVAL_TIMEOUT", "POTPIE_TIMEOUT", "TIMEOUT"),
        default=25,
    )
    args.output_dir = resolve_path(
        args.output_dir,
        ("RUN_EVAL_OUTPUT_DIR", "EVAL_OUTPUT_DIR"),
        default=DEFAULT_OUTPUT_DIR,
    )
    args.limit = resolve_optional_int(
        args.limit,
        ("RUN_EVAL_LIMIT", "EVAL_LIMIT"),
    )
    args.instance_ids = resolve_instance_ids(
        args.instance_ids,
        ("RUN_EVAL_INSTANCE_IDS", "EVAL_INSTANCE_IDS", "INSTANCE_IDS"),
    )

    asyncio.run(process_instances(args))


if __name__ == "__main__":
    main()
