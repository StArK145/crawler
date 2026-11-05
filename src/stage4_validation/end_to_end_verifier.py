import asyncio
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from playwright.async_api import async_playwright, Page

@dataclass
class VerificationReport:
    """
    Detailed report of the visual verification pass.
    """
    passed: bool
    typecheck_passed: bool
    layout_failures: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class EndToEndVerifier:
    """
    Identity-Preserving Visual Verifier.
    Proves that the generated DOM matches the original source snapshot
    by comparing observed geometry against the original IR map.
    """

    def __init__(self, tolerance_base: float = 0.5, tolerance_factor: float = 0.005):
        self.tolerance_base = tolerance_base
        self.tolerance_factor = tolerance_factor

    def calculate_local_residual(self, observed: Dict[str, float], expected: Dict[str, float]) -> Tuple[float, float]:
        """
        Calculates the absolute delta for width and height.
        """
        res_w = abs(observed.get('width', 0) - expected.get('width', 0))
        res_h = abs(observed.get('height', 0) - expected.get('height', 0))
        return res_w, res_h

    def is_within_tolerance(self, observed_dim: float, residual: float) -> bool:
        """
        Check if residual exceeds epsilon = base + (factor * dimension).
        """
        epsilon = self.tolerance_base + (self.tolerance_factor * observed_dim)
        return residual <= epsilon

    async def verify_render(
        self,
        local_url: str,
        original_ir_map: Dict[str, Any],
        typecheck_passed: bool = True
    ) -> VerificationReport:
        """
        Launches Playwright, extracts live geometry, and compares it against the regime rects.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Set viewport to match the regime we are verifying
            # Assuming original_ir_map contains a 'viewport' key
            viewport = original_ir_map.get('viewport', {'width': 1280, 'height': 800})
            await page.set_viewport_size(viewport)

            await page.goto(local_url)

            # Extract bounding boxes and styles for all elements with data-ir-id
            # We execute a script to return a map of { id: {x, y, width, height} }
            observed_geometry = await page.evaluate("""
                () => {
                    const results = {};
                    const elements = document.querySelectorAll('[data-ir-id]');
                    elements.forEach(el => {
                        const rect = el.getBoundingClientRect();
                        results[el.getAttribute('data-ir-id')] = {
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height
                        };
                    });
                    return results;
                }
            """)

            layout_failures = []
            # The original_ir_map is expected to have 'regime_rects_local'
            regime_rects = original_ir_map.get('regime_rects_local', {})

            for node_id, observed_rect in observed_geometry.items():
                if node_id not in regime_rects:
                    # Node exists in rendered output but not in the original snapshot
                    layout_failures.append({
                        "node_id": node_id,
                        "error": "hallucinated_node",
                        "delta": 0.0
                    })
                    continue

                expected_rect = regime_rects[node_id]
                res_w, res_h = self.calculate_local_residual(observed_rect, expected_rect)

                # Check width tolerance
                if not self.is_within_tolerance(observed_rect['width'], res_w):
                    layout_failures.append({
                        "node_id": node_id,
                        "error": "width_residual_exceeded",
                        "delta": res_w,
                        "observed": observed_rect['width'],
                        "expected": expected_rect['width']
                    })

                # Check height tolerance
                if not self.is_within_tolerance(observed_rect['height'], res_h):
                    layout_failures.append({
                        "node_id": node_id,
                        "error": "height_residual_exceeded",
                        "delta": res_h,
                        "observed": observed_rect['height'],
                        "expected": expected_rect['height']
                    })

            await browser.close()

            passed = (len(layout_failures) == 0) and typecheck_passed

            return VerificationReport(
                passed=passed,
                typecheck_passed=typecheck_passed,
                layout_failures=layout_failures,
                metadata={
                    "observed_node_count": len(observed_geometry),
                    "expected_node_count": len(regime_rects),
                    "viewport": viewport
                }
            )
