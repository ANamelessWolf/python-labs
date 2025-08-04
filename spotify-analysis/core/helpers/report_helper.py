import os
import json
from dataclasses import asdict
from core.models.listening_report import ListeningReport

def dump_listening_report(report: ListeningReport, filename: str = "listening_report.json") -> str:
    """
    Saves the given listening report as a JSON file under 'reports/' directory.

    Args:
        report (ListeningReport): The report dataclass to serialize.
        filename (str): Output filename (with .json extension).

    Returns:
        str: The full path to the saved file.
    """
    try:
        # Ensure reports/ directory exists
        report_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
        report_dir = os.path.abspath(report_dir)
        os.makedirs(report_dir, exist_ok=True)

        # Full path to output file
        report_path = os.path.join(report_dir, filename)

        # Serialize and write
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=4, ensure_ascii=False)

        return report_path
    except Exception as e:
        raise RuntimeError(f"Failed to write report: {str(e)}") from e
