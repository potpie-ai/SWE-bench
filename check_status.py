import argparse
import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, cast

from agent import PotpieAgentExecutor

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "status_checks"
DEFAULT_ENV_FILE = Path(".env")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Potpie repository parsing status for evaluation instances."
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
        "--output",
        type=Path,
        help="Path to output JSON file for status results. Defaults to ./status_checks/status_results.json",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional limit on number of instances to check.",
    )
    parser.add_argument(
        "--instance-ids",
        nargs="+",
        help="Optional list of instance IDs to check. Only instances matching these IDs will be processed.",
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


def resolve_commit_id(instance: Dict[str, Any]) -> Optional[str]:
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

    return None


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


async def check_instance_status(
    executor: PotpieAgentExecutor,
    user_id: str,
    instance_id: str,
    repo_name: str,
    commit_id: Optional[str],
) -> Dict[str, Any]:
    """
    Check the status of a single instance repository in Potpie.

    Returns:
        Dict with status information
    """
    logger.info(
        "Checking status for %s (repo: %s, commit: %s)",
        instance_id,
        repo_name,
        commit_id or "N/A",
    )
    start_time = time.time()

    try:
        status = await executor.get_repo_status(
            user_id=user_id,
            repo_name=repo_name,
            commit_id=commit_id,
        )
        elapsed_seconds = time.time() - start_time

        result = {
            "instance_id": instance_id,
            "repo_name": repo_name,
            "commit_id": commit_id,
            "status": status,
            "elapsed_seconds": round(elapsed_seconds, 2),
            "error": None,
        }
    except Exception as exc:
        elapsed_seconds = time.time() - start_time
        logger.exception("Status check failed for %s", instance_id)
        result = {
            "instance_id": instance_id,
            "repo_name": repo_name,
            "commit_id": commit_id,
            "status": None,
            "elapsed_seconds": round(elapsed_seconds, 2),
            "error": str(exc),
        }

    return result


async def check_instances_status(args: argparse.Namespace) -> None:
    output_path: Path = args.output or (DEFAULT_OUTPUT_DIR / "status_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.input:
        instances = load_instances(args.input)
    else:
        instances = load_swebench_lite_instances()

    args.instance_ids = [
        "django__django-16400",
        "matplotlib__matplotlib-25079",
        "matplotlib__matplotlib-25498",
        "pydata__xarray-3364",
        "pytest-dev__pytest-5103",
        "sphinx-doc__sphinx-8474",
        "sphinx-doc__sphinx-8506",
        "sphinx-doc__sphinx-8595",
        "sphinx-doc__sphinx-8627",
        "sympy__sympy-11400",
        "sympy__sympy-11870",
        "sympy__sympy-11897",
        "sympy__sympy-12171",
        "sympy__sympy-12236",
        "sympy__sympy-12419",
        "sympy__sympy-12454",
        "sympy__sympy-13031",
        "sympy__sympy-13043",
        "sympy__sympy-13146",
        "sympy__sympy-15346",
        "sympy__sympy-17630",
        "sympy__sympy-18087",
        "sympy__sympy-18835",
        "sympy__sympy-20322",
        "sympy__sympy-21379",
        "sympy__sympy-24066",
        "sympy__sympy-24102",
        "sympy__sympy-24909",
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
        timeout=25,  # Status checks should be quick
    )

    results: List[Dict[str, Any]] = []
    processed = 0

    for index, instance in enumerate(instances):
        instance_id = resolve_instance_id(index, instance)
        repo_name = resolve_repo_name(instance)
        commit_id = resolve_commit_id(instance)

        result = await check_instance_status(
            executor=executor,
            user_id=args.user_id,
            instance_id=instance_id,
            repo_name=repo_name,
            commit_id=commit_id,
        )

        results.append(result)
        processed += 1

        # Log progress
        logger.info(
            "Checked %s: status=%s",
            instance_id,
            result.get("status", "ERROR"),
        )

    # Write results to file
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info(
        "Finished checking %d instance(s). Results written to %s",
        processed,
        output_path,
    )

    # Print summary
    status_counts: Dict[str, int] = {}
    error_count = 0
    for result in results:
        status = result.get("status")
        if status:
            status_counts[status] = status_counts.get(status, 0) + 1
        else:
            error_count += 1

    logger.info("Status summary:")
    for status, count in sorted(status_counts.items()):
        logger.info("  %s: %d", status, count)
    if error_count > 0:
        logger.info("  ERROR: %d", error_count)


def main() -> None:
    args = parse_args()
    load_env_file(args.env_file)
    args.input = resolve_path(
        args.input,
        ("RUN_EVAL_INPUT", "RUN_EVAL_INSTANCES", "EVAL_INPUT", "STATUS_CHECK_INPUT"),
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
    args.output = resolve_path(
        args.output,
        ("STATUS_CHECK_OUTPUT", "STATUS_OUTPUT"),
        default=DEFAULT_OUTPUT_DIR / "status_results.json",
    )
    args.instance_ids = resolve_instance_ids(
        args.instance_ids,
        (
            "RUN_EVAL_INSTANCE_IDS",
            "EVAL_INSTANCE_IDS",
            "INSTANCE_IDS",
            "STATUS_CHECK_INSTANCE_IDS",
        ),
    )

    asyncio.run(check_instances_status(args))


if __name__ == "__main__":
    main()
