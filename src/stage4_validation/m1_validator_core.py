import math
from typing import List, Dict, Tuple, Optional, Any

class MathematicalValidator:
    """
    Stage 4 Mathematical Validator.
    Blames layout errors based on local residuals to prevent false cascades.
    """

    def __init__(self, padding: float = 0.0, margin: float = 0.0):
        self.padding = padding
        self.margin = margin

    def compute_local_frame(self, node_rect: Dict[str, float], parent_rect: Dict[str, float]) -> Tuple[float, float]:
        """
        Computes the dx, dy relative to the parent's top-left.
        node_rect and parent_rect expected to have 'x', 'y', 'width', 'height'.
        """
        dx = node_rect['x'] - parent_rect['x']
        dy = node_rect['y'] - parent_rect['y']
        return dx, dy

    def compute_local_residual(
        self,
        node_id: str,
        observed_rect: Dict[str, float],
        expected_sizing_mode: str,
        parent_rect: Dict[str, float],
        children_rects: List[Dict[str, float]]
    ) -> Dict[str, float]:
        """
        Calculates the local residual based on the expected sizing mode.
        """
        residuals = {"width": 0.0, "height": 0.0}

        if expected_sizing_mode == "hug":
            # Expected size is the bounding box union of children plus padding
            if not children_rects:
                expected_w = self.padding * 2
                expected_h = self.padding * 2
            else:
                min_x = min(c['x'] for c in children_rects)
                max_x = max(c['x'] + c['width'] for c in children_rects)
                min_y = min(c['y'] for c in children_rects)
                max_y = max(c['y'] + c['height'] for c in children_rects)

                expected_w = (max_x - min_x) + (self.padding * 2)
                expected_h = (max_y - min_y) + (self.padding * 2)

            residuals["width"] = abs(observed_rect['width'] - expected_w)
            residuals["height"] = abs(observed_rect['height'] - expected_h)

        elif expected_sizing_mode == "fill":
            # Expected width is derived from parent width minus margins
            expected_w = parent_rect['width'] - (self.margin * 2)
            # Height for fill is often context-dependent, but we apply similar logic
            expected_h = parent_rect['height'] - (self.margin * 2)

            residuals["width"] = abs(observed_rect['width'] - expected_w)
            residuals["height"] = abs(observed_rect['height'] - expected_h)

        return residuals

    def blame_node(
        self,
        node_id: str,
        observed_rect: Dict[str, float],
        expected_sizing_mode: str,
        parent_rect: Dict[str, float],
        children_rects: List[Dict[str, float]]
    ) -> Optional[str]:
        """
        Flags the node as the 'blamed' node if the local residual exceeds
         the calculated tolerance epsilon.
        """
        residuals = self.compute_local_residual(
            node_id, observed_rect, expected_sizing_mode, parent_rect, children_rects
        )

        # Tolerance formula: epsilon = 0.5 + (0.005 * dimension)
        def check_tolerance(observed_dim: float, residual: float) -> bool:
            epsilon = 0.5 + (0.005 * observed_dim)
            return residual > epsilon

        width_blamed = check_tolerance(observed_rect['width'], residuals["width"])
        height_blamed = check_tolerance(observed_rect['height'], residuals["height"])

        if width_blamed or height_blamed:
            return node_id

        return None
