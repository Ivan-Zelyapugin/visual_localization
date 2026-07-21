import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from ultralytics import YOLO


class YOLODetector:
    """YOLO object detector for detecting objects in images.

    Parameters
    ----------
    model_path : Union[str, Path]
        Path to the trained YOLO model (.pt file)
    device : str
        Device to run the model on ("cpu", "cuda", etc.)
    conf_threshold : float
        Confidence threshold for detections
    logger : Optional[logging.Logger]
        Logger to use for logging
    """

    def __init__(
        self,
        model_path: Union[str, Path],
        device: str = "cpu",
        conf_threshold: float = 0.5,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.device = device
        self.conf_threshold = conf_threshold
        self.logger = logger or logging.getLogger(__name__)

        # Load the YOLO model
        self.logger.info(f"Loading YOLO model from {self.model_path}")
        self.model = YOLO(self.model_path)
        self.model.to(self.device)

    def detect(
        self, image: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Detect objects in an image.

        Parameters
        ----------
        image : np.ndarray
            Input image (numpy array in BGR or RGB format)

        Returns
        -------
        List[Dict[str, Any]]
            List of detected objects, each with:
                - bbox: [x1, y1, x2, y2]
                - confidence: float
                - class_id: int
                - class_name: str
        """
        # Run detection
        results = self.model(image, conf=self.conf_threshold, device=self.device)
        
        detections = []
        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = box.conf[0].cpu().numpy()
                    cls_id = int(box.cls[0].cpu().numpy())
                    cls_name = self.model.names[cls_id] if self.model.names else str(cls_id)
                    
                    detections.append({
                        "bbox": [float(x1), float(y1), float(x2), float(y2)],
                        "confidence": float(conf),
                        "class_id": cls_id,
                        "class_name": cls_name,
                    })
        
        self.logger.debug(f"Detected {len(detections)} objects")
        return detections

    def draw_detections(
        self,
        image: np.ndarray,
        detections: List[Dict[str, Any]],
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> np.ndarray:
        """Draw detections on an image.

        Parameters
        ----------
        image : np.ndarray
            Input image to draw on
        detections : List[Dict[str, Any]]
            List of detections from detect() method
        color : Tuple[int, int, int]
            Color for bounding boxes (BGR format)
        thickness : int
            Thickness of bounding box lines

        Returns
        -------
        np.ndarray
            Image with detections drawn
        """
        img_copy = image.copy()
        
        for det in detections:
            x1, y1, x2, y2 = map(int, det["bbox"])
            label = f"{det['class_name']} {det['confidence']:.2f}"
            
            # Draw bounding box
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), color, thickness)
            
            # Draw label
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            y1_label = max(y1, label_size[1] + 10)
            cv2.rectangle(
                img_copy,
                (x1, y1_label - label_size[1] - 10),
                (x1 + label_size[0], y1_label),
                color,
                -1,
            )
            cv2.putText(
                img_copy,
                label,
                (x1, y1_label - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
            )
        
        return img_copy
