import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Any

# Ensure project root is on sys.path so `src.*` imports work when running this file directly
_CURRENT_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _CURRENT_FILE.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_all_reports(json_file_path: str, force_compliance: bool = True) -> Dict[str, Dict[str, Any]]:
    """Generate Executive, Technical, and Compliance reports together.

    Returns a dict mapping report types to their result dicts. Any report that fails returns None.
    """
    results: Dict[str, Any] = {"executive": None, "technical": None, "compliance": None}

    # Executive
    try:
        from src.executive_report import Cloud202ExecutiveReportGenerator
        exec_gen = Cloud202ExecutiveReportGenerator()
        results["executive"] = exec_gen.generate_report(json_file_path)
    except Exception as e:
        logger.error(f"Executive report failed: {e}")

    # Technical
    try:
        from src.technical_report import Cloud202TechnicalDeepDiveGenerator
        tech_gen = Cloud202TechnicalDeepDiveGenerator()
        results["technical"] = tech_gen.generate_report(json_file_path)
    except Exception as e:
        logger.error(f"Technical report failed: {e}")

    # Compliance (forced if configured)
    try:
        from src.compliance_report import ComplianceReportGenerator
        comp_gen = ComplianceReportGenerator()
        results["compliance"] = comp_gen.generate_report(json_file_path, force=force_compliance)
    except Exception as e:
        logger.error(f"Compliance report failed: {e}")

    return results


def main():
    """CLI Orchestrator for generating all three reports"""
    print("\n" + "="*60)
    print("🚀 Cloud202 Report Orchestrator")
    print("="*60)

    parser = argparse.ArgumentParser(description="Cloud202 - Generate Executive, Technical, and Compliance reports")
    parser.add_argument("--json", dest="json_path", help="Path to assessment JSON file", default=None)
    args = parser.parse_args()

    # If a JSON path is provided via CLI, use it directly; otherwise, pick from current directory
    if args.json_path:
        json_file = args.json_path.strip().strip("\"'")
    else:
        json_files = list(Path(".").glob("*.json"))
        if Path("test_json_comprehensive.json").exists():
            json_files = [Path("test_json_comprehensive.json")] + [p for p in json_files if p.name != "test_json_comprehensive.json"]

    if args.json_path is None and json_files:
        print(f"\n📂 Found {len(json_files)} JSON file(s):")
        for i, file in enumerate(json_files, 1):
            try:
                size_kb = (file.stat().st_size / 1024)
                size_str = f"{size_kb:.1f} KB"
            except Exception:
                size_str = "unknown size"
            print(f"   {i}. {file.name} ({size_str})")

        print(f"\n   {len(json_files) + 1}. Enter custom file path")
        print("   0. Exit")

        while True:
            try:
                choice = input(f"\nSelect option (0-{len(json_files) + 1}): ").strip()
                if choice == "0":
                    print("👋 Exiting...")
                    return 0
                elif choice == str(len(json_files) + 1):
                    json_file = input("\n📄 Enter JSON file path: ").strip().strip("\"'")
                    break
                elif 1 <= int(choice) <= len(json_files):
                    json_file = str(json_files[int(choice) - 1])
                    print(f"✅ Selected: {json_file}")
                    break
                else:
                    print("❌ Invalid selection.")
            except (ValueError, IndexError):
                print("❌ Invalid input.")
    elif args.json_path is None:
        json_file = input("\n📄 Enter JSON file path: ").strip().strip("\"'")

    if not os.path.exists(json_file):
        print(f"❌ File not found: {json_file}")
        return 1

    try:
        print("\n⚙️ Generating all reports (Executive, Technical, Compliance)...")
        combined = generate_all_reports(json_file, force_compliance=True)

        print("\n" + "="*60)
        print("✅ REPORT GENERATION RESULTS")
        print("="*60)
        print(f"📂 Input file: {json_file}")

        for rtype in ["executive", "technical", "compliance"]:
            res = combined.get(rtype)
            if res and isinstance(res, dict) and res.get('pdf_path'):
                print(f"📄 {rtype.title()} Report: {res['pdf_path']}")
            else:
                print(f"❌ {rtype.title()} Report: generation failed")

        return 0

    except Exception as e:
        logger.error(f"Report orchestration failed: {e}")
        print(f"\n❌ Error: {e}")
        print("📋 Please ensure:")
        print("   - Your AWS credentials are configured")
        print("   - Your JSON file is valid")
        print("   - Required packages are installed: reportlab, strands")
        return 1


if __name__ == "__main__":
    exit(main())