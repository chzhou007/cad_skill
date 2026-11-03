from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASE = SKILL_ROOT / "assets" / "alignment" / "sh16-current"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild and validate the bundled SH16 CAD topology alignment case."
    )
    parser.add_argument("--case", type=Path, default=DEFAULT_CASE)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Keep generated outputs here; otherwise use a temporary directory.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--visualization-output', type=Path, help='New viewer directory; default is <output-dir>-viewer.')
    group.add_argument('--without-visualization', action='store_true', help='Explicitly omit the default viewer for a retained run.')
    args = parser.parse_args()
    if args.visualization_output is not None and args.output_dir is None:
        parser.error('--visualization-output requires --output-dir')
    return args


def run(case_dir: Path, output_dir: Path, visualization_dir: Path | None = None) -> None:
    builder = case_dir / "implementation" / "src" / "build_edges.py"
    drawing = case_dir / "inputs" / "dxf" / "sh16-native-isometric_updated.fixed.dxf"
    legend = case_dir / "inputs" / "dxf" / "sh16-native-table.fixed.dxf"
    validator = SKILL_ROOT / "scripts" / "validate_alignment.py"
    subprocess.run(
        [
            sys.executable,
            str(builder),
            "--dxf",
            str(drawing),
            "--table-dxf",
            str(legend),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
    )

    subprocess.run(
        [
            sys.executable,
            str(validator),
            "--case",
            str(case_dir),
            "--actual",
            str(output_dir),
        ],
        check=True,
    )


    if visualization_dir is not None:
        companion = SKILL_ROOT.parent / 'visualize-cad-pipe-topology'
        subprocess.run([
            sys.executable, str(companion / 'scripts' / 'build_visualization.py'),
            '--graph', str(output_dir / 'graph_with_edges.json'),
            '--devices', str(output_dir / 'edge_device_instances.csv'),
            '--ports', str(output_dir / 'virtual_equipment_ports.csv'),
            '--dxf', str(drawing), '--legend-dxf', str(legend),
            '--config', str(companion / 'references' / 'sh16-profile.json'),
            '--output', str(visualization_dir),
        ], check=True)


def main() -> None:
    args = parse_args()
    case_dir = args.case.resolve()
    if args.output_dir is not None:
        output_dir = args.output_dir.resolve()
        visualization_dir = None
        if not args.without_visualization:
            visualization_dir = (args.visualization_output.resolve() if args.visualization_output
                                 else output_dir.with_name(output_dir.name + '-viewer'))
            companion = SKILL_ROOT.parent / 'visualize-cad-pipe-topology'
            if not (companion / 'scripts' / 'build_visualization.py').is_file():
                raise SystemExit('Install visualize-cad-pipe-topology, or explicitly pass --without-visualization for tables-only output.')
            if visualization_dir.exists() or visualization_dir.with_name(visualization_dir.name + '.zip').exists():
                raise SystemExit('Viewer output already exists. Choose a new --output-dir or --visualization-output.')
        output_dir.mkdir(parents=True, exist_ok=True)
        run(case_dir, output_dir, visualization_dir)
        return
    with tempfile.TemporaryDirectory(prefix="cad-topology-alignment-") as temporary:
        run(case_dir, Path(temporary) / "edges")


if __name__ == "__main__":
    main()
