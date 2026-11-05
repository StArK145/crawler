import asyncio
from playwright.async_api import async_playwright, BrowserContext, Page

class HermeticProbeService:
    """
    A headless Chromium harness designed for 100% deterministic layout rendering
    and fast in-page geometry sweeps.
    """

    def __init__(self):
        self.playwright = None
        self.browser = None

    async def start(self):
        """Initializes the Playwright engine and launches the browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--font-render-hinting=none",
                "--disable-font-subpixel-positioning",
                "--disable-lcd-text",
                "--enable-features=OverlayScrollbars",
                "--hide-scrollbars",
            ],
        )

    async def create_pinned_context(self) -> BrowserContext:
        """
        Creates a browser context with injected scripts to freeze time
        and seed randomness for perfect determinism.
        """
        context = await self.browser.new_context()

        # Determinism Injection Script
        # 1. Mulberry32 PRNG for Math.random
        # 2. Freeze Date.now() and performance.now()
        init_script = """
        (function() {
            const seed = 12345;
            function mulberry32(a) {
                return function() {
                    let t = a += 0x6D2B79F5;
                    t = Math.imul(t ^ t >>> 15, t | 1);
                    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
                    return ((t ^ t >>> 14) >>> 0) / 4294967296;
                }
            }
            const rand = mulberry32(seed);
            Math.random = rand;

            const FIXED_TIME = 1735689600000;
            Date.now = () => FIXED_TIME;
            performance.now = () => 0;

            // Freeze the prototypes to prevent overrides
            Object.defineProperty(Date, 'now', { value: () => FIXED_TIME, writable: false });
            Object.defineProperty(performance, 'now', { value: () => 0, writable: false });
        })();
        """
        await context.add_init_script(init_script)
        return context

    async def discover_breakpoints(self, page: Page):
        """
        Labels elements, injects the FastPass collector, and sweeps
        across multiple viewports to identify topology shifts.
        """
        # 1. Assign sequential data-probe-id to all elements in the body
        await page.evaluate("""
            () => {
                const elements = document.body.getElementsByTagName('*');
                for (let i = 0; i < elements.length; i++) {
                    elements[i].setAttribute('data-probe-id', i.toString());
                }
            }
        """)

        # 2. Inject __IR_PROBE__.collectFastPass
        await page.evaluate("""
            () => {
                window.__IR_PROBE__ = {
                    collectFastPass: () => {
                        const elements = document.querySelectorAll('[data-probe-id]');
                        const rects = new Float32Array(elements.length * 4);
                        let topology = "";

                        elements.forEach((el, i) => {
                            const rect = el.getBoundingClientRect();
                            rects[i * 4] = rect.x;
                            rects[i * 4 + 1] = rect.y;
                            rects[i * 4 + 2] = rect.width;
                            rects[i * 4 + 3] = rect.height;

                            const style = window.getComputedStyle(el);
                            topology += style.display + style.flexDirection + "|";
                        });

                        return {
                            rects: Array.from(rects), // Playwright cannot return Float32Array directly
                            topologyHash: topology
                        };
                    }
                };
            }
        """)

        # 3. Sweep through 15 standard viewport widths
        viewport_widths = [
            320, 360, 375, 390, 414, 480, 576, 768, 800, 992, 1024, 1200, 1280, 1366, 1440, 1920
        ][:15]

        results = []
        for width in viewport_widths:
            await page.set_viewport_size({"width": width, "height": 1080})
            # Give layout a moment to settle
            await asyncio.sleep(0.1)

            data = await page.evaluate("window.__IR_PROBE__.collectFastPass()")
            results.append({
                "width": width,
                "topology": data["topologyHash"]
            })

        return results

    async def run_text_scale_pass(self, page: Page):
        """
        Performs differential perturbation by scaling text content.
        Helps distinguish hug containers from fixed/fill containers.
        """
        return await page.evaluate("""
            () => {
                const probe = window.__IR_PROBE__;
                if (!probe || !probe.collectFastPass) {
                    throw new Error("window.__IR_PROBE__.collectFastPass is not initialized");
                }

                // 1. Find leaf elements containing text
                const textNodes = [];
                const walk = (node) => {
                    if (node.nodeType === Node.TEXT_NODE) {
                        if (node.textContent.trim().length > 0) {
                            textNodes.push(node);
                        }
                    } else if (node.nodeType === Node.ELEMENT_NODE) {
                        for (let child of node.childNodes) {
                            walk(child);
                        }
                    }
                };
                walk(document.body);

                // 2. Save original text
                const originalTexts = textNodes.map(node => node.textContent);

                const capture = () => {
                    const data = probe.collectFastPass();
                    // We need to map rects back to probe-ids
                    const elements = document.querySelectorAll('[data-probe-id]');
                    const map = {};
                    elements.forEach((el, i) => {
                        const id = el.getAttribute('data-probe-id');
                        const rect = {
                            x: data.rects[i * 4],
                            y: data.rects[i * 4 + 1],
                            w: data.rects[i * 4 + 2],
                            h: data.rects[i * 4 + 3]
                        };
                        map[id] = rect;
                    });
                    return map;
                };

                // 3. 0.5x Text Length Pass
                textNodes.forEach((node, i) => {
                    node.textContent = originalTexts[i].slice(0, Math.floor(originalTexts[i].length / 2));
                });
                const pass05 = capture();

                // 4. 2.0x Text Length Pass
                textNodes.forEach((node, i) => {
                    node.textContent = originalTexts[i] + originalTexts[i];
                });
                const pass20 = capture();

                // 5. Restore original text
                textNodes.forEach((node, i) => {
                    node.textContent = originalTexts[i];
                });

                return {
                    half: pass05,
                    double: pass20
                };
            }
        """)

    async def stop(self):
        """Cleans up browser and playwright resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
