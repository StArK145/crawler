import os
import json
from pathlib import Path

def generate_fixtures():
    base_dir = Path("corpus/m0_synthetic")

    test_cases = [
        {
            "id": "tc1_margin_collapse",
            "name": "Margin Collapse Trap",
            "html": """<!DOCTYPE html>
<html>
<head>
    <style>
        .box-a { margin-bottom: 32px; background: red; height: 50px; }
        .box-b { margin-top: 24px; background: blue; height: 50px; }
    </style>
</head>
<body>
    <div class="box-a">Box A</div>
    <div class="box-b">Box B</div>
</body>
</html>""",
            "expected_ir": {
                "elements": [
                    {
                        "id": "box_a",
                        "margin_collapse_owner": "next_sibling",
                        "computed_margin_bottom": "32px"
                    },
                    {
                        "id": "box_b",
                        "computed_margin_top": "0px"
                    }
                ],
                "layout_assertions": {
                    "vertical_gap_between_a_b": "32px"
                }
            }
        },
        {
            "id": "tc2_hug_vs_fill",
            "name": "Hug vs Fill (Flexbox)",
            "html": """<!DOCTYPE html>
<html>
<head>
    <style>
        .container { display: flex; flex-direction: column; }
        .btn { padding: 10px 20px; }
        @media (min-width: 900px) {
            .container { flex-direction: row; }
            .btn { width: auto; }
        }
    </style>
</head>
<body>
    <div class="container">
        <button class="btn">Click Me</button>
    </div>
</body>
</html>""",
            "expected_ir": {
                "breakpoints": [
                    {
                        "width": 900,
                        "changes": {
                            "container": {"flex-direction": "row"},
                            "btn": {"width_mode": "hug"}
                        }
                    }
                ],
                "mobile_state": {
                    "btn": {"width_mode": "fill"}
                },
                "desktop_state": {
                    "btn": {"width_mode": "hug"}
                }
            }
        },
        {
            "id": "tc3_100vw_trap",
            "name": "100vw Scrollbar Trap",
            "html": """<!DOCTYPE html>
<html>
<head>
    <style>
        body { overflow-x: clip; }
        .wrapper { max-width: 600px; margin: 0 auto; }
        .child {
            width: 100vw;
            position: relative;
            left: 50%;
            transform: translateX(-50%);
        }
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="child">100vw Content</div>
    </div>
</body>
</html>""",
            "expected_ir": {
                "assertions": {
                    "uses_100vw": True,
                    "root_requires_overflow_x_clip": True
                }
            }
        }
    ]

    for tc in test_cases:
        tc_dir = base_dir / tc["id"]
        tc_dir.mkdir(parents=True, exist_ok=True)

        with open(tc_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(tc["html"])

        with open(tc_dir / "expected_ir.json", "w", encoding="utf-8") as f:
            json.dump(tc["expected_ir"], f, indent=4)

    print(f"Successfully generated {len(test_cases)} synthetic fixtures in {base_dir}")

if __name__ == "__main__":
    generate_fixtures()
