import asyncio
import os
from pathlib import Path
from src.stage1_extraction.m0_probe_harness import HermeticProbeService
from src.stage4_validation.m1_validator_core import MathematicalValidator

async def run_integration_test():
    # Initialize services
    probe = HermeticProbeService()
    validator = MathematicalValidator(padding=0, margin=0) # Simplified for the test

    await probe.start()
    context = await probe.create_pinned_context()
    page = await context.new_page()

    # Path to one of the generated fixtures
    fixture_path = Path("corpus/m0_synthetic/tc2_hug_vs_fill/index.html").absolute()

    print(f"Testing fixture: {fixture_path}")
    await page.goto(f"file://{fixture_path}")

    # 1. Use HermeticProbeService to extract geometry
    # We'll use discover_breakpoints but focus on one viewport for the validation step
    await page.set_viewport_size({"width": 1200, "height": 1080})

    # Label elements
    await page.evaluate("""
        () => {
            const elements = document.body.getElementsByTagName('*');
            for (let i = 0; i < elements.length; i++) {
                elements[i].setAttribute('data-probe-id', i.toString());
            }
        }
    """)

    # Inject FastPass
    await page.evaluate("""
        () => {
            window.__IR_PROBE__ = {
                collectFastPass: () => {
                    const elements = document.querySelectorAll('[data-probe-id]');
                    const data = [];
                    elements.forEach((el) => {
                        const rect = el.getBoundingClientRect();
                        data.push({
                            id: el.getAttribute('data-probe-id'),
                            rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                        });
                    });
                    return data;
                }
            };
        }
    """)

    observed_elements = await page.evaluate("window.__IR_PROBE__.collectFastPass()")

    # 2. Use MathematicalValidator to assert geometry
    # For tc2 (Hug vs Fill), at 1200px, the button should be in 'hug' mode
    # We'll treat the container as parent and button as child

    # Simplification: Map observed elements to a dict
    rects = {el['id']: el['rect'] for el in observed_elements}

    # In tc2:
    # index 0 is <div class="container">
    # index 1 is <button class="btn">
    parent_rect = rects.get('0')
    node_rect = rects.get('1')

    if parent_rect and node_rect:
        print(f"Parent (Container): {parent_rect}")
        print(f"Node (Button): {node_rect}")

        # Check local frame
        dx, dy = validator.compute_local_frame(node_rect, parent_rect)
        print(f"Local Frame: dx={dx}, dy={dy}")

        # Validate 'hug' mode
        # Button has no children, so hug size = padding * 2 (which is 0 in our validator init)
        # However, a button has internal text. For this test, we assume
        # the observed size is the ground truth and we check for blame.

        # We'll simulate the 'expected_sizing_mode' based on the fixture's expected_ir
        # At 1200px, btn is 'hug'
        blame = validator.blame_node(
            node_id='1',
            observed_rect=node_rect,
            expected_sizing_mode='hug',
            parent_rect=parent_rect,
            children_rects=[] # Button text isn't a DOM element in this simple probe
        )

        if blame:
            print(f"❌ Node {blame} was blamed for layout error!")
        else:
            print(f"✅ Node 1 passed validation (no significant local residual).")
    else:
        print("Could not find expected elements in the probe output.")

    await probe.stop()

if __name__ == "__main__":
    asyncio.run(run_integration_test())
