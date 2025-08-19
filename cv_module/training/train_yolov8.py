import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

import yaml
from ultralytics import YOLO


def resolve_default_paths() -> Dict[str, Path]:
	root_dir = Path(__file__).resolve().parents[2]
	data_yaml = root_dir / "cv_module" / "dataset" / "dataset" / "data.yaml"
	hyp_yaml = Path(__file__).resolve().parent / "hyp_yolov8.yaml"
	project_dir = root_dir / "cv_module" / "models"
	return {
		"data": data_yaml,
		"hyp": hyp_yaml,
		"project": project_dir,
	}


def parse_args(defaults: Dict[str, Path]) -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Train YOLOv8 on dataset")
	parser.add_argument(
		"--config",
		type=str,
		default=str(Path(__file__).resolve().parent / "configs" / "baseline.yaml"),
		help="Experiment config YAML (defaults to configs/baseline.yaml)",
	)
	return parser.parse_args()


def load_experiment_config(config_path: str, defaults: Dict[str, Path]) -> Dict[str, Any]:
	config_file = Path(config_path)
	if not config_file.exists():
		raise FileNotFoundError(f"Config file not found: {config_file}")
	with open(config_file, "r", encoding="utf-8") as f:
		cfg = yaml.safe_load(f)

	# Set reasonable defaults if missing
	cfg.setdefault("model", "yolov8s.pt")
	cfg.setdefault("data", str(defaults["data"]))
	cfg.setdefault("hyp", str(defaults["hyp"]))
	cfg.setdefault("imgsz", 640)
	cfg.setdefault("epochs", 100)
	cfg.setdefault("batch", 16)
	cfg.setdefault("workers", 2)
	cfg.setdefault("device", "0")
	cfg.setdefault("name", "yolov8s")
	cfg.setdefault("seed", 42)
	cfg.setdefault("project", str(defaults["project"]))
	return cfg


def build_overrides_from_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
	overrides: Dict[str, Any] = {
		"data": cfg["data"],
		"imgsz": cfg["imgsz"],
		"epochs": cfg["epochs"],
		"batch": cfg["batch"],
		"workers": cfg["workers"],
		"device": cfg["device"],
		"project": cfg["project"],
		"name": cfg["name"],
		"cfg": cfg["hyp"],
		"exist_ok": True,
		"seed": cfg["seed"],
	}

	# Pass through any additional keys present in the config (e.g., patience, optimizer, half, lr0, lrf, etc.)
	# excluding keys that are handled separately or renamed.
	for key, value in cfg.items():
		if key in {"model", "hyp"}:
			continue
		if key not in overrides:
			overrides[key] = value
	return overrides


def find_latest_best(project_dir: Path) -> Optional[Path]:
	weights = list(project_dir.glob("*/weights/best.pt"))
	if not weights:
		return None
	# pick the most recently modified best.pt
	weights.sort(key=lambda p: p.stat().st_mtime, reverse=True)
	return weights[0]


def resolve_model_path(cfg: Dict[str, Any], defaults: Dict[str, Path]) -> str:
	model_value = cfg.get("model", "yolov8s.pt")
	if isinstance(model_value, str) and model_value.strip().lower() == "auto_best":
		project_dir = Path(cfg.get("project", str(defaults["project"])))
		latest = find_latest_best(project_dir)
		if latest is None:
			raise FileNotFoundError(f"No best.pt found under {project_dir}. Complete a training run first or specify a model path.")
		return str(latest)
	return str(model_value)


def main() -> None:
	paths = resolve_default_paths()
	args = parse_args(paths)
	cfg = load_experiment_config(args.config, paths)
	model_path = resolve_model_path(cfg, paths)
	model = YOLO(model_path)
	overrides = build_overrides_from_config(cfg)

	# Ensure project dir exists
	Path(overrides["project"]).mkdir(parents=True, exist_ok=True)
	model.train(**overrides)

	# Validate best weights from this run
	results_dir = Path(overrides["project"]) / overrides["name"]
	best_weights = results_dir / "weights" / "best.pt"
	if best_weights.exists():
		model = YOLO(str(best_weights))
		half_flag = bool(cfg.get("half", False))
		model.val(data=overrides["data"], imgsz=overrides["imgsz"], device=overrides["device"], half=half_flag)

	# Persist the exact config and git commit for provenance
	try:
		used_cfg_path = results_dir / "config_used.yaml"
		with open(used_cfg_path, "w", encoding="utf-8") as f:
			yaml.safe_dump(cfg, f, sort_keys=False)
		commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(Path(__file__).resolve().parents[2])).decode().strip()
		with open(results_dir / "git_commit.txt", "w", encoding="utf-8") as f:
			f.write(commit + "\n")
	except Exception:
		# Non-fatal: git might be unavailable, or not a repo
		pass


if __name__ == "__main__":
	main()


