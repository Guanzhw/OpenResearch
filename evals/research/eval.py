#!/usr/bin/env python3
"""Prepare a small, blind report review without calling a model."""

import argparse
import hashlib
import json
import re
import secrets
import shutil
from pathlib import Path
from urllib.parse import unquote, urlsplit


HERE = Path(__file__).resolve().parent
CASES = HERE / "cases.json"
SHA = re.compile(r"^[0-9a-f]{40,64}$")
INLINE_LINK = re.compile(r"!?\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)")
REFERENCE_LINK = re.compile(r"^\s*\[[^\]]+\]:\s*(<[^>]+>|\S+)", re.MULTILINE)
HTML_LINK = re.compile(r"\b(?:src|href)=[\"']([^\"']+)[\"']", re.IGNORECASE)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cases(path=CASES):
    suite = json.loads(path.read_text(encoding="utf-8"))
    suite_version = suite.get("suite_version")
    if suite.get("schema_version") != 1 or not isinstance(suite_version, str) or not suite_version or not isinstance(suite.get("cases"), list):
        raise ValueError("cases.json must contain schema_version 1 and cases")
    version_match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", suite_version)
    if not version_match:
        raise ValueError("suite_version must use three numeric components")
    require_grading = tuple(int(part) for part in version_match.groups()) >= (0, 3, 0)
    ids = set()
    grading_ids = set()
    for case in suite["cases"]:
        case_id = case.get("id", "")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", case_id) or case_id in ids:
            raise ValueError(f"invalid or duplicate case id: {case_id!r}")
        if case.get("split") not in {"development", "confirmation"}:
            raise ValueError(f"invalid split for {case_id}")
        if case.get("kind") not in {"field-report", "source-check"}:
            raise ValueError(f"invalid kind for {case_id}")
        if not case.get("prompt") or not case.get("review_focus"):
            raise ValueError(f"missing prompt or review focus for {case_id}")
        if case["kind"] == "source-check" and not case.get("primary_source"):
            raise ValueError(f"missing primary source for {case_id}")
        if case["kind"] == "source-check" and require_grading:
            grading = case.get("grading")
            if not isinstance(grading, dict) or set(grading) != {"required_facts", "critical_errors"}:
                raise ValueError(f"{case_id}.grading must contain required_facts and critical_errors")
            for collection, text_key in (("required_facts", "fact"), ("critical_errors", "false_claim")):
                entries = grading.get(collection)
                if not isinstance(entries, list) or not entries:
                    raise ValueError(f"{case_id}.grading.{collection} must be a nonempty list")
                expected_keys = {"id", text_key}
                if collection == "required_facts":
                    expected_keys |= {"source_url", "source_section"}
                for entry in entries:
                    if not isinstance(entry, dict) or set(entry) != expected_keys:
                        raise ValueError(f"invalid {case_id}.grading.{collection} entry shape")
                    rubric_id = entry.get("id")
                    if not isinstance(rubric_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", rubric_id) or rubric_id in grading_ids:
                        raise ValueError(f"invalid or duplicate grading id for {case_id}: {rubric_id!r}")
                    if not isinstance(entry.get(text_key), str) or not entry[text_key].strip():
                        raise ValueError(f"missing {case_id}.grading.{collection}.{text_key}")
                    if collection == "required_facts":
                        if not isinstance(entry["source_url"], str) or not isinstance(entry["source_section"], str):
                            raise ValueError(f"invalid source URL or section for {case_id} grading id {rubric_id}")
                        source = urlsplit(entry["source_url"])
                        if source.scheme != "https" or not source.netloc or not entry["source_section"].strip():
                            raise ValueError(f"invalid source URL or section for {case_id} grading id {rubric_id}")
                    grading_ids.add(rubric_id)
        ids.add(case_id)
    return {case["id"]: case for case in suite["cases"]}


def resolve(base, value, label, required=True):
    if not value:
        if required:
            raise ValueError(f"missing {label}")
        return None
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {path}")
    if required and path.stat().st_size == 0:
        raise ValueError(f"{label} is empty: {path}")
    return path


def check_manifest(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("comparison") != "workflow-ablation":
        raise ValueError("manifest must be schema_version 1, workflow-ablation")
    casebook = resolve(path.parent, data.get("casebook_file"), "casebook_file")
    if data.get("casebook_sha256") != digest(casebook):
        raise ValueError("casebook snapshot hash differs from manifest")
    cases = load_cases(casebook)
    case_id = data.get("case_id")
    if case_id not in cases:
        raise ValueError(f"unknown case: {case_id}")
    if data.get("prompt") != cases[case_id]["prompt"]:
        raise ValueError("manifest prompt differs from frozen case")
    shared = data.get("shared", {})
    for key in ("harness", "model", "reasoning_effort", "source_access"):
        if not isinstance(shared.get(key), str) or not shared[key].strip():
            raise ValueError(f"missing shared.{key}")
    if not isinstance(shared.get("enabled_tools"), list):
        raise ValueError("shared.enabled_tools must be a list")
    for key in ("max_wall_seconds", "max_tool_calls", "max_total_tokens"):
        if not isinstance(shared.get(key), int) or shared[key] <= 0:
            raise ValueError(f"shared.{key} must be a positive integer")
    if shared.get("fresh_session") is not True:
        raise ValueError("shared.fresh_session must be true")
    arms = data.get("arms", {})
    if set(arms) != {"control", "treatment"}:
        raise ValueError("manifest needs exactly control and treatment arms")
    files = {}
    for name, arm in arms.items():
        if not SHA.fullmatch(arm.get("build_commit", "")):
            raise ValueError(f"{name}.build_commit must be a full commit or snapshot hash")
        status = arm.get("status")
        if status not in {"complete", "failed", "timeout"}:
            raise ValueError(f"{name}.status must be complete, failed, or timeout")
        if not isinstance(arm.get("workflow_files"), list) or not arm["workflow_files"]:
            raise ValueError(f"{name}.workflow_files must list loaded instruction snapshots")
        files[name] = {
            "effective_prompt": resolve(path.parent, arm.get("effective_prompt_file"), f"{name}.effective_prompt_file"),
            "workflow": [resolve(path.parent, item, f"{name}.workflow_files") for item in arm["workflow_files"]],
            "trace": resolve(path.parent, arm.get("trace_file"), f"{name}.trace_file", required=False),
            "report": resolve(path.parent, arm.get("report_file"), f"{name}.report_file", required=status == "complete"),
        }
        if status != "complete" and not arm.get("failure_reason"):
            raise ValueError(f"{name}.failure_reason is required for {status}")
        if files[name]["trace"] is None and not arm.get("missing_trace_reason"):
            raise ValueError(f"{name} needs a trace or missing_trace_reason")
        for key in ("elapsed_seconds", "tool_calls"):
            if not isinstance(arm.get(key), (int, float)) or arm[key] < 0:
                raise ValueError(f"{name}.{key} must be nonnegative")
        usage = arm.get("cumulative_tokens", {})
        for key in ("input", "cached_input", "output"):
            value = usage.get(key)
            if value is not None and (not isinstance(value, int) or value < 0):
                raise ValueError(f"{name}.cumulative_tokens.{key} must be nonnegative or null")
        if any(usage.get(key) is None for key in ("input", "cached_input", "output")) and not arm.get("missing_usage_reason"):
            raise ValueError(f"{name} needs cumulative usage or missing_usage_reason")
    if files["control"]["report"] and files["control"]["report"] == files["treatment"]["report"]:
        raise ValueError("both arms point to the same report")
    return data, files


def init_manifest(args, cases):
    case = cases[args.case]
    arm = {
        "build_commit": "",
        "workflow_files": [],
        "effective_prompt_file": "",
        "trace_file": "",
        "report_file": "",
        "status": "pending",
        "failure_reason": "",
        "missing_trace_reason": "",
        "elapsed_seconds": None,
        "tool_calls": None,
        "cumulative_tokens": {"input": None, "cached_input": None, "output": None},
        "missing_usage_reason": "",
    }
    manifest = {
        "schema_version": 1,
        "comparison": "workflow-ablation",
        "casebook_file": Path(args.output).name + ".cases.json",
        "casebook_sha256": digest(CASES),
        "case_id": case["id"],
        "prompt": case["prompt"],
        "shared": {
            "harness": "",
            "model": "",
            "reasoning_effort": "",
            "enabled_tools": [],
            "source_access": "",
            "max_wall_seconds": None,
            "max_tool_calls": None,
            "max_total_tokens": None,
            "fresh_session": True,
        },
        "arms": {"control": dict(arm), "treatment": dict(arm)},
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshot = output.with_name(manifest["casebook_file"])
    if output.exists() or snapshot.exists():
        raise ValueError("manifest or casebook snapshot already exists")
    with snapshot.open("xb") as handle:
        handle.write(CASES.read_bytes())
    with output.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(output.resolve())


def local_assets(report):
    content = report.read_text(encoding="utf-8")
    targets = [match.group(1) for regex in (INLINE_LINK, REFERENCE_LINK, HTML_LINK) for match in regex.finditer(content)]
    assets = set()
    for target in targets:
        target = target.strip("<>")
        if target.startswith("#"):
            continue
        parsed = urlsplit(target)
        if parsed.scheme in {"http", "https", "mailto", "data"}:
            continue
        if parsed.scheme or parsed.netloc:
            raise ValueError(f"unsupported report link in {report}: {target}")
        relative = Path(unquote(parsed.path).replace("\\", "/"))
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ValueError(f"report asset must stay beside report: {target}")
        source = (report.parent / relative).resolve()
        if not source.is_file() or not source.is_relative_to(report.parent.resolve()):
            raise ValueError(f"report asset missing or outside report directory: {target}")
        assets.add(relative)
    return sorted(assets)


def copy_report(report, target):
    target.mkdir(parents=True)
    assets = []
    if report:
        for relative in local_assets(report):
            source = report.parent / relative
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            assets.append({"file": str(relative), "sha256": digest(source)})
        shutil.copy2(report, target / "report.md")
    else:
        (target / "report.md").write_text(
            "本次运行未生成报告。评审时请将缺失视为该次尝试的结果。\n", encoding="utf-8"
        )
    return assets


def make_packet(args):
    manifest_path = Path(args.manifest).resolve()
    manifest, files = check_manifest(manifest_path)
    casebook = resolve(manifest_path.parent, manifest.get("casebook_file"), "casebook_file")
    case = load_cases(casebook)[manifest["case_id"]]
    review_dir = Path(args.review_dir).resolve()
    key_file = Path(args.key_file).resolve()
    if review_dir == key_file.parent or review_dir in key_file.parents:
        raise ValueError("the identity key must be outside the review directory")
    if review_dir.exists() or key_file.exists():
        raise ValueError("review directory and identity key must not already exist")
    for arm in files.values():
        if arm["report"]:
            local_assets(arm["report"])
    order = ["control", "treatment"]
    if secrets.randbelow(2):
        order.reverse()
    review_dir.mkdir(parents=True)
    labels = {}
    for label, name in zip("AB", order):
        report = files[name]["report"]
        assets = copy_report(report, review_dir / label)
        labels[label] = {
            "arm": name,
            "status": manifest["arms"][name]["status"],
            "report_sha256": digest(report) if report else None,
            "assets_sha256": assets,
            "trace_sha256": digest(files[name]["trace"]) if files[name]["trace"] else None,
            "effective_prompt_sha256": digest(files[name]["effective_prompt"]),
            "workflow_sha256": [{"file": str(p), "sha256": digest(p)} for p in files[name]["workflow"]],
        }
    if case["kind"] == "source-check":
        grading = case.get("grading")
        if grading:
            fact_rows = "\n".join(
                f"| `{item['id']}` | {item['fact']} | [{item['source_section']}]({item['source_url']}) | | |"
                for item in grading["required_facts"]
            )
            error_rows = "\n".join(
                f"| `{item['id']}` | {item['false_claim']} | | |"
                for item in grading["critical_errors"]
            )
            grading_section = f"""## Frozen factual rubric

For each fact, mark A and B as `supported`, `missing`, or `wrong`. `Missing` means the report omits it; `wrong` means it contradicts or misstates the source. Record citation traceability separately. Mark whether each critical error appears in either report. A report passes when every required fact is supported and no critical error appears. A missing report cannot pass.

| ID | Required fact | Frozen source | A status | B status |
|---|---|---|---|---|
{fact_rows}

| ID | Critical error (false claim) | A present? | B present? |
|---|---|---|---|
{error_rows}
"""
            result_rows = """| First impression | | | | |
| Factual verdict for A | | | | |
| Factual verdict for B | | | | |
| User preference (separate) | | | | |"""
            outcome_note = "The primary outcome is the frozen factual pass/fail result for each report. Record A/B preference, style, and holistic usefulness separately."
            final_instruction = "Record both factual verdicts and any user preference separately before opening the identity key."
        else:
            grading_section = "## Source audit\n\nThis frozen casebook predates structured factual grading. Use the source anchors in `source-audit.md` and record a qualitative source-audit result; do not label it a standardized factual pass."
            result_rows = """| First impression | | | | |
| Source-audit result | | | | |
| User preference (separate) | | | | |"""
            outcome_note = "Record factual source findings first and any A/B preference separately."
            final_instruction = "Record the source-audit result and any user preference separately before opening the identity key."
        case_guidance = f"""{grading_section}

Check consequential claims outside the frozen rubric against primary sources and record them too. Keep style and holistic usefulness separate from factual correctness.

{outcome_note}
"""
    else:
        case_guidance = "The user's final blind preference is the primary outcome; record source findings, style, and holistic usefulness separately."
        result_rows = """| First impression | | | | |
| After source audit (final preference) | | | | |"""
        final_instruction = "Record the user's final blind preference before opening the identity key. A missing report counts as an outcome."
    brief = f"""# Blind report review: {manifest['case_id']}

## User task

{manifest['prompt']}

Read `A/report.md` and `B/report.md` before looking at run metadata or source-audit anchors.
This is label-blinded only: first check the reports and linked assets for identifying text or paths.
If an arm is identifiable, record the review as unblinded.
Record a first impression: **A**, **B**, **tie**, or **cannot judge**, with a reason.
Then audit pivotal factual claims while the labels stay blind. Record exact claims and sources.
{case_guidance}
{final_instruction}

| Stage | Choice or verdict | Reason | Confidence | Factual issues with exact claim and source |
|---|---|---|---|---|
{result_rows}
"""
    (review_dir / "review.md").write_text(brief, encoding="utf-8")
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key = {
        "case_id": manifest["case_id"],
        "casebook_sha256": manifest["casebook_sha256"],
        "manifest_sha256": digest(manifest_path),
        "labels": labels,
    }
    with key_file.open("x", encoding="utf-8") as handle:
        json.dump(key, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"review packet: {review_dir}")
    print(f"identity key: {key_file}")


def preview(args, cases):
    """Package older reports for UI review without inventing run provenance."""
    review_dir = Path(args.review_dir).resolve()
    key_file = Path(args.key_file).resolve()
    if review_dir == key_file.parent or review_dir in key_file.parents:
        raise ValueError("the identity key must be outside the review directory")
    if review_dir.exists() or key_file.exists():
        raise ValueError("review directory and identity key must not already exist")
    reports = [resolve(Path.cwd(), item, "report") for item in args.reports]
    if reports[0] == reports[1]:
        raise ValueError("preview needs two distinct reports")
    for report in reports:
        local_assets(report)
    if secrets.randbelow(2):
        reports.reverse()
    review_dir.mkdir(parents=True)
    key = {"case_id": args.case, "casebook_sha256": digest(CASES), "mode": "archive-preview", "labels": {}}
    for label, report in zip("AB", reports):
        assets = copy_report(report, review_dir / label)
        key["labels"][label] = {"source": str(report), "sha256": digest(report), "assets_sha256": assets}
    (review_dir / "review.md").write_text(
        f"# Archived report preview: {args.case}\n\n"
        f"Reference task: {cases[args.case]['prompt']}\n\n"
        "Read `A/report.md` and `B/report.md`, then record A, B, tie, or cannot judge, with a reason.\n\n"
        "This is label-blinded only. Check for identifying text or paths before calling it a blind review.\n\n"
        "These older files have no verified paired-run manifest or exact-prompt record. "
        "This packet tests the review surface only; "
        "it cannot establish a workflow effect.\n",
        encoding="utf-8",
    )
    key_file.parent.mkdir(parents=True, exist_ok=True)
    with key_file.open("x", encoding="utf-8") as handle:
        json.dump(key, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"archive preview: {review_dir}")
    print(f"identity key: {key_file}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="check the frozen cases and an optional run manifest")
    validate.add_argument("--manifest")
    init = commands.add_parser("init", help="create a manifest template before running agents")
    init.add_argument("case")
    init.add_argument("output")
    packet = commands.add_parser("packet", help="make an anonymous A/B review packet")
    packet.add_argument("manifest")
    packet.add_argument("review_dir")
    packet.add_argument("key_file")
    older = commands.add_parser("preview", help="blind older reports without claiming run comparability")
    older.add_argument("case")
    older.add_argument("report_1")
    older.add_argument("report_2")
    older.add_argument("review_dir")
    older.add_argument("key_file")
    args = parser.parse_args()
    try:
        cases = load_cases()
        if args.command == "validate":
            if args.manifest:
                check_manifest(Path(args.manifest).resolve())
            print(f"validated {len(cases)} cases" + (" and run manifest" if args.manifest else ""))
        elif args.command == "init":
            if args.case not in cases:
                raise ValueError(f"unknown case: {args.case}")
            init_manifest(args, cases)
        elif args.command == "packet":
            make_packet(args)
        else:
            if args.case not in cases:
                raise ValueError(f"unknown case: {args.case}")
            args.reports = [args.report_1, args.report_2]
            preview(args, cases)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
