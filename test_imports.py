
import sys
from pathlib import Path
sys.path.insert(0, str(Path("src").absolute()))

print("Testing imports...")

from svl.yolo_detector import YOLODetector
print("✓ YOLODetector imported")

from svl.localization.pipeline import Pipeline, PipelineConfig
print("✓ Pipeline imported")

print("All imports okay!")

# Test YOLO detector
yolo_path = Path("best_2.pt")
if yolo_path.exists():
    print(f"\nTesting YOLO with {yolo_path}...")
    detector = YOLODetector(yolo_path, device="cuda")
    print("✓ YOLO detector initialized")
else:
    print(f"\nWarning: {yolo_path} not found")
