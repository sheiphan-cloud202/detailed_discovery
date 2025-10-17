
from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Callable, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure project root and src are importable for flexible module resolution
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
SRC_DIR = PROJECT_ROOT / "src"

for path_candidate in [SRC_DIR, PROJECT_ROOT]:
    try:
        if str(path_candidate) not in sys.path:
            sys.path.insert(0, str(path_candidate))
    except Exception:
        # Best-effort path setup; continue even if some insertions fail
        pass

DATA_DIR = (PROJECT_ROOT / "reports").resolve()

@dataclass
class ReportResult:
    name: str
    status: str
    output_path: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None

def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def _timeit(fn: Callable[[], Any]) -> Tuple[Any, float]:
    import time
    t0 = time.time()
    val = fn()
    return val, time.time() - t0

def _load_executive_generator():
    candidates = [
        ("report_labs_executive", "Cloud202ExecutiveReportGenerator"),
        ("src.executive_report", "Cloud202ExecutiveReportGenerator"),
        ("executive_report", "Cloud202ExecutiveReportGenerator"),
        ("report_labs_executive", None),
        ("executive_report", None),
    ]
    last_err = None
    for mod_name, cls_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
            if cls_name:
                cls = getattr(mod, cls_name, None)
                if cls is None:
                    raise AttributeError(f"{mod_name} has no class {cls_name}")
                inst = cls()
                if not hasattr(inst, "generate_report"):
                    raise AttributeError(f"{cls_name} missing generate_report")
                return inst, "generate_report"
            else:
                if hasattr(mod, "generate_report"):
                    return mod, "generate_report"
                if hasattr(mod, "main"):
                    def call_main(json_path: str):
                        return mod.main(["--json_path", json_path]) if callable(mod.main) else None
                    return type("MainWrapper", (), {"generate_report": staticmethod(call_main)})(), "generate_report"
        except Exception as e:
            last_err = e
            continue
    raise ImportError(f"Could not locate an Executive report generator. Last error: {last_err}")

def _load_technical_generator():
    candidates = [
        ("src.technical_report", "Cloud202TechnicalDeepDiveGenerator"),
        ("technical_report", "Cloud202TechnicalDeepDiveGenerator"),
    ]
    last_err = None
    for mod_name, cls_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name, None)
            if cls is None:
                raise AttributeError(f"{mod_name} has no class {cls_name}")
            inst = cls()
            if not hasattr(inst, "generate_report"):
                raise AttributeError("Technical generator missing generate_report")
            return inst
        except Exception as e:
            last_err = e
            continue
    raise ImportError(f"Could not locate Technical report generator. Last error: {last_err}")

def _load_compliance_generator():
    candidates = [
        ("src.compliance_report", "ComplianceReportGenerator"),
        ("compliance_report", "ComplianceReportGenerator"),
    ]
    last_err = None
    for mod_name, cls_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name, None)
            if cls is None:
                raise AttributeError(f"{mod_name} has no class {cls_name}")
            inst = cls()
            if not hasattr(inst, "generate_report"):
                raise AttributeError("Compliance generator missing generate_report")
            return inst
        except Exception as e:
            last_err = e
            continue
    raise ImportError(f"Could not locate Compliance report generator. Last error: {last_err}")

def run_executive(json_path: str) -> ReportResult:
    started = _timestamp()
    try:
        exec_inst, method_name = _load_executive_generator()
        def _do():
            return getattr(exec_inst, method_name)(json_path)
        result, dur = _timeit(_do)
        output_path = None
        if isinstance(result, dict):
            output_path = result.get("output_path") or result.get("pdf_path")
        if isinstance(result, str) and result.lower().endswith(".pdf"):
            output_path = result
        return ReportResult(name="executive", status="success", output_path=str(output_path) if output_path else None,
                            extra=result if isinstance(result, dict) else {"return": str(result)},
                            started_at=started, finished_at=_timestamp(), duration_seconds=dur)
    except Exception as e:
        logger.exception("Executive report failed")
        return ReportResult(name="executive", status="error", error=str(e),
                            started_at=started, finished_at=_timestamp())

def run_technical(json_path: str) -> ReportResult:
    started = _timestamp()
    try:
        tech = _load_technical_generator()
        def _do():
            return tech.generate_report(json_path)
        result, dur = _timeit(_do)
        output_path = None
        if isinstance(result, dict):
            output_path = result.get("output_path") or result.get("pdf_path")
        if isinstance(result, str) and result.lower().endswith(".pdf"):
            output_path = result
        return ReportResult(name="technical", status="success", output_path=str(output_path) if output_path else None,
                            extra=result if isinstance(result, dict) else {"return": str(result)},
                            started_at=started, finished_at=_timestamp(), duration_seconds=dur)
    except Exception as e:
        logger.exception("Technical report failed")
        return ReportResult(name="technical", status="error", error=str(e),
                            started_at=started, finished_at=_timestamp())

def run_compliance(json_path: str, force: bool = True) -> ReportResult:
    started = _timestamp()
    try:
        comp = _load_compliance_generator()
        def _do():
            return comp.generate_report(json_path, force=force)
        result, dur = _timeit(_do)
        output_path = None
        if isinstance(result, dict):
            output_path = result.get("output_path") or result.get("pdf_path")
        if isinstance(result, str) and result.lower().endswith(".pdf"):
            output_path = result
        return ReportResult(name="compliance", status="success", output_path=str(output_path) if output_path else None,
                            extra=result if isinstance(result, dict) else {"return": str(result)},
                            started_at=started, finished_at=_timestamp(), duration_seconds=dur)
    except Exception as e:
        logger.exception("Compliance report failed")
        return ReportResult(name="compliance", status="error", error=str(e),
                            started_at=started, finished_at=_timestamp())

def main(argv=None):
    parser = argparse.ArgumentParser(description="Run Executive, Technical, and Compliance reports in parallel.")
    parser.add_argument("--json", "--json_path", dest="json_path", required=True, help="Path to the assessment JSON file")
    parser.add_argument("--outdir", dest="outdir", default=str(DATA_DIR / "outputs"), help="Output directory for the manifest")
    parser.add_argument("--workdir", dest="workdir", default=None, help="Optional working directory to chdir into before running")
    parser.add_argument("--no-exec", dest="no_exec", action="store_true", help="Skip Executive report")
    parser.add_argument("--no-tech", dest="no_tech", action="store_true", help="Skip Technical report")
    parser.add_argument("--no-comp", dest="no_comp", action="store_true", help="Skip Compliance report")
    parser.add_argument("--threads", dest="threads", type=int, default=3, help="Max threads to use")
    args = parser.parse_args(argv)

    json_path = Path(args.json_path).expanduser().resolve()
    if not json_path.exists():
        raise SystemExit(f"JSON not found: {json_path}")

    if args.workdir:
        os.chdir(args.workdir)

    outdir = Path(args.outdir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    jobs = []
    if not args.no_exec:
        jobs.append(("executive", run_executive, str(json_path)))
    if not args.no_tech:
        jobs.append(("technical", run_technical, str(json_path)))
    if not args.no_comp:
        jobs.append(("compliance", lambda p: run_compliance(p, force=True), str(json_path)))

    if not jobs:
        raise SystemExit("No reports selected.")

    results: Dict[str, ReportResult] = {}
    with ThreadPoolExecutor(max_workers=min(args.threads, len(jobs))) as ex:
        future_map = {ex.submit(fn, param): (name, fn) for name, fn, param in jobs}
        for fut in as_completed(future_map):
            name, _fn = future_map[fut]
            try:
                res: ReportResult = fut.result()
            except Exception as e:
                logger.exception("Worker crashed")
                res = ReportResult(name=name, status="error", error=str(e))
            results[name] = res

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest = {
        "run_id": run_id,
        "json": str(json_path),
        "created_at": _timestamp(),
        "results": {k: asdict(v) for k, v in results.items()},
    }
    manifest_path = outdir / f"manifest_{run_id}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print("\\n===== Parallel Report Run Summary =====")
    for name in ("executive", "technical", "compliance"):
        if name in results:
            r = results[name]
            status = "✅" if r.status == "success" else "❌"
            line = f"{status} {name.capitalize():11s} -> {r.status}"
            if r.output_path:
                line += f"  |  output: {r.output_path}"
            if r.error:
                line += f"  |  error: {r.error}"
            print(line)
    print(f"\\n🗂  Manifest saved to: {manifest_path}")

    if all(r.status == "error" for r in results.values()):
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
