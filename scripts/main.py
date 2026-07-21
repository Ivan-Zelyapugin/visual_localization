import logging
from pathlib import Path
from pprint import pprint
import argparse

from svl.keypoint_pipeline.detection_and_description import SuperPointAlgorithm
from svl.keypoint_pipeline.matcher import SuperGlueMatcher
from svl.keypoint_pipeline.typing import SuperGlueConfig, SuperPointConfig
from svl.localization.drone_streamer import DroneImageStreamer
from svl.localization.map_reader import SatelliteMapReader
from svl.localization.pipeline import Pipeline, PipelineConfig
from svl.localization.preprocessing import QueryProcessor
from svl.tms.data_structures import CameraModel
from svl.yolo_detector import YOLODetector

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Drone Visual Localization with YOLO")
    parser.add_argument(
        "--yolo-model",
        type=str,
        default=None,
        help="Path to trained YOLO model file (.pt)",
    )
    parser.add_argument(
        "--yolo-device",
        type=str,
        default="cpu",
        help="Device to run YOLO on (cpu, cuda, etc.)",
    )
    parser.add_argument(
        "--yolo-conf",
        type=float,
        default=0.5,
        help="Confidence threshold for YOLO detections",
    )
    args = parser.parse_args()

    # logging.basicConfig(level=logging.INFO)
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    # set to debug for more information

    # Initialize YOLO detector (if model path provided)
    yolo_detector = None
    if args.yolo_model is not None:
        yolo_logger = logging.getLogger("%s.YOLODetector" % __name__)
        yolo_detector = YOLODetector(
            model_path=args.yolo_model,
            device=args.yolo_device,
            conf_threshold=args.yolo_conf,
            logger=yolo_logger,
        )

    # Initialize the keypoint detector (Оптимизировано для плотного поиска точек)
    superpoint_config = SuperPointConfig(
        device="cpu",              # ИСПРАВЛЕНО: Включаем видеокарту NVIDIA вместо "cpu"
        nms_radius=3,              # ИСПРАВЛЕНО: Слегка уменьшили, чтобы точки ложились плотнее на углах
        keypoint_threshold=0.001,  # ИСПРАВЛЕНО: Снизили порог, чтобы находить слабоконтрастные фичи
        max_keypoints=2048,        # ИСПРАВЛЕНО: Вместо -1 явно задаем лимит (2048 идеальный баланс)
    )
    superpoint_algorithm = SuperPointAlgorithm(superpoint_config)

    # Initialize the keypoint matcher (Оптимизировано для сложных ракурсов)
    superglue_config = SuperGlueConfig(
        device="cpu",              # ИСПРАВЛЕНО: Включаем видеокарту NVIDIA для матчера
        weights="outdoor",
        sinkhorn_iterations=50,    # ИСПРАВЛЕНО: Подняли до 50 (дает нейросети больше попыток сопоставить граф)
        match_threshold=0.3,       # ИСПРАВЛЕНО: Снизили до 0.3, чтобы не терять сложные геометрические пары
    )
    superglue_matcher = SuperGlueMatcher(superglue_config)

    # Initialize the map reader
    map_reader = SatelliteMapReader(
        db_path="data/map/",
        resize_size=(800,),
        logger=logging.getLogger("%s.SatelliteMapReader" % __name__),  # noqa
    )
    map_reader.initialize_db()
    map_reader.setup_db()
    map_reader.resize_db_images()
    map_reader.describe_db_images(superpoint_algorithm)

    # Initialize the drone image streamer
    streamer = DroneImageStreamer(
        image_folder="data/query/",
        has_gt=True,
        logger=logging.getLogger("%s.DroneImageStreamer" % __name__),  # noqa
    )
    print(len(streamer))

    # Initialize the query processor
    camera_model = CameraModel(
        focal_length=4.5 / 1000,  # 4.5mm
        resolution_height=4056,
        resolution_width=3040,
        hfov_deg=82.9,
    )
    query_processor = QueryProcessor(
        processings=["resize"],
        camera_model=camera_model,
        satellite_resolution=None,
        size=(800,),
    )

    # Initialize the pipeline
    logger = logging.getLogger("%s.Pipeline" % __name__)  # noqa
    logger.setLevel(logging.DEBUG)
    pipeline = Pipeline(
        map_reader=map_reader,
        drone_streamer=streamer,
        detector=superpoint_algorithm,
        matcher=superglue_matcher,
        query_processor=query_processor,
        config=PipelineConfig(),
        yolo_detector=yolo_detector,
        # logger=logging.getLogger("%s.Pipeline" % __name__),  # noqa
        logger=logger,
    )
    output_path = "data/output"
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    preds = pipeline.run(
        output_path=output_path,
    )
    metrics = pipeline.compute_metrics(preds)
    pprint(metrics)
