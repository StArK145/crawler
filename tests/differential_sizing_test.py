import asyncio
from pathlib import Path
from src.stage1_extraction.m0_probe_harness import HermeticProbeService
from src.stage2_solver.m2_layout_solver import LayoutIntentSolver

async def run_differential_test():
    # Initialize services
    probe = HermeticProbeService()
    solver = LayoutIntentSolver()

    await probe.start()
    context = await probe.create_pinned_context()
    page = await context.new_page()

    # Path to the "Hug vs Fill" fixture
    fixture_path = Path("corpus/m0_synthetic/tc2_hug_vs_fill/index.html").absolute()
    print(f"Testing differential sizing on: {fixture_path}")
    await page.goto(f"file://{fixture_path}")

    # Initial setup for probe
    await page.set_viewport_size({"width": 1200, "height": 1080})
    await page.evaluate("""
        () => {
            const elements = document.body.getElementsByTagName('*');
            for (let i = 0; i < elements.length; i++) {
                elements[i].setAttribute('data-probe-id', i.toString());
            }
        }
    """)
    # Inject the collector required by run_text_scale_pass
    await page.evaluate("""
        () => {
            window.__IR_PROBE__ = {
                collectFastPass: () => {
                    const elements = document.querySelectorAll('[data-probe-id]');
                    const rects = new Float32Array(elements.length * 4);
                    elements.forEach((el, i) => {
                        const rect = el.getBoundingClientRect();
                        rects[i * 4] = rect.x;
                        rects[i * 4 + 1] = rect.y;
                        rects[i * 4 + 2] = rect.width;
                        rects[i * 4 + 3] = rect.height;
                    });
                    return { rects: Array.from(rects) };
                }
            };
        }
    """)

    # 1. Run Differential Perturbation Pass
    print("Running text scale pass...")
    scaled_data = await probe.run_text_scale_pass(page)

    # 2. Get base rect for the button (node_id '1')
    # We can just take the 'half' rect or a fresh one
    base_rect = scaled_data['half'].get('1', {})
    parent_rect = scaled_data['half'].get('0', {})

    print(f"Base Rect (Button): {base_rect}")
    print(f"Parent Rect (Container): {parent_rect}")

    # 3. Solve Sizing Mode
    # The solver uses the diff between 'half' and 'double' to classify
    result = solver.solve_sizing_mode(
        node_id='1',
        base_rect=base_rect,
        text_scaled_rects=scaled_data,
        parent_rect=parent_rect
    )

    print(f"\nSizing Mode Result: {result}")

    await probe.stop()

if __name__ == "__main__":
    asyncio.run(run_differential_test())
