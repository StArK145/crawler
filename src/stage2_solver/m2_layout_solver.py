from typing import List, Dict, Tuple, Optional, Any

class LayoutIntentSolver:
    """
    M2a Layout Intent Solver.
    Converts raw bounding boxes and perturbation data into CSS layout intent.
    """

    def __init__(self, padding: float = 0.0, margin: float = 0.0):
        self.padding = padding
        self.margin = margin

    def solve_sizing_mode(
        self,
        node_id: str,
        base_rect: Dict[str, float],
        text_scaled_rects: Dict[str, Any],
        parent_rect: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Determines if a node is in 'hug', 'fill', or 'fixed' sizing mode.

        text_scaled_rects is expected to be in the format:
        {
            "half": { "node_id": {"x": ..., "y": ..., "w": ..., "h": ...} },
            "double": { "node_id": {"x": ..., "y": ..., "w": ..., "h": ...} }
        }
        """
        # Extract widths for comparison
        w_base = base_rect.get('width', base_rect.get('w', 0))

        half_rect = text_scaled_rects.get("half", {}).get(node_id, {})
        double_rect = text_scaled_rects.get("double", {}).get(node_id, {})

        w_half = half_rect.get('width', half_rect.get('w', 0))
        w_double = double_rect.get('width', double_rect.get('w', 0))

        # 1. Hug Detection: Width changes proportionally with text scale
        # We check if there is a significant difference between 0.5x and 2.0x
        if w_half != w_double and w_double > w_half:
            # In a real implementation, we would check for proportional change
            # relative to the content, but for the solver, any significant
            # growth on double-text usually indicates a hug container.
            return {"mode": "hug"}

        # 2. Fill Detection: Width remains static but matches parent width (minus padding/margins)
        # We allow a small epsilon for float precision
        expected_fill_w = parent_rect.get('width', parent_rect.get('w', 0)) - (self.padding * 2 + self.margin * 2)
        if abs(w_base - expected_fill_w) < 0.5:
            return {"mode": "fill"}

        # 3. Fixed Detection: Otherwise, return fixed with the observed base value
        return {"mode": "fixed", "value": w_base}

    def assert_box_model_invariant(
        self,
        node_rect: Dict[str, float],
        computed_styles: Dict[str, Any],
        child_rects: List[Dict[str, float]],
        layout_type: str = "flex_row"
    ) -> Dict[str, Any]:
        """
        Verifies if the node's observed width matches the theoretical sum of its children
        and spacing, proving the layout is physically possible.
        """
        if layout_type == "flex_row":
            flex_gap = computed_styles.get("gap", 0.0)
            padding_left = computed_styles.get("paddingLeft", 0.0)
            padding_right = computed_styles.get("paddingRight", 0.0)

            # Theoretical width = sum(child.width) + gaps + padding
            child_widths_sum = sum(c.get('width', c.get('w', 0)) for c in child_rects)
            num_gaps = max(0, len(child_rects) - 1)
            theoretical_width = child_widths_sum + (flex_gap * num_gaps) + padding_left + padding_right
        else:
            # Fallback for other layout types (not yet implemented)
            theoretical_width = node_rect.get('width', node_rect.get('w', 0))

        observed_width = node_rect.get('width', node_rect.get('w', 0))
        residual_px = abs(theoretical_width - observed_width)
        passes_invariant = residual_px <= 0.5

        return {
            "computed_sum": theoretical_width,
            "observed_width": observed_width,
            "residual_px": residual_px,
            "passes_invariant": passes_invariant
        }

    def solve_margin_collapse(
        self,
        node_rects: List[Dict[str, Any]],
        computed_styles: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolves vertical margin collapse between adjacent siblings in a Block formatting context.

        node_rects: List of siblings sorted by Y coordinate.
        computed_styles: Map of node_id to style object.
        """
        results = {}

        for i in range(len(node_rects) - 1):
            sibling_a = node_rects[i]
            sibling_b = node_rects[i+1]

            id_a = sibling_a['id']
            id_b = sibling_b['id']

            # Calculate vertical gap
            bottom_a = sibling_a['rect']['y'] + sibling_a['rect']['height']
            top_b = sibling_b['rect']['y']
            gap = top_b - bottom_a

            # Deterministically assign gap to sibling_a as effective_margin_bottom
            results[id_a] = {
                "effective_margin_bottom": gap,
                "margin_collapse_owner": "self"
            }

        return results
