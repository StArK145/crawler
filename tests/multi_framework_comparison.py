import asyncio
from src.stage3_ast.m25_ast_schema import (
    PureExpr, ElementNode, TextNode, ComponentDefinition
)
from src.stage4_emission.react_emitter import ReactEmitter
from src.stage4_emission.nextjs_emitter import NextJsEmitter, emit_route_shell
from src.stage4_emission.vue_emitter import VueEmitter
from src.stage4_emission.angular_emitter import AngularEmitter

async def run_multi_framework_comparison():
    # 1. Construct a representative "Hug vs Fill" AST
    # <div class="container"><button class="btn">{props.label}</button></div>

    label_expr = PureExpr(path="props.label")
    btn_text = TextNode(kind="text", value=label_expr, preserve_inline_space=False)

    btn_node = ElementNode(
        kind="element",
        ir_node_id="btn_001",
        tag="button",
        dom_attrs={},
        children=[btn_text]
    )

    container_node = ElementNode(
        kind="element",
        ir_node_id="cont_001",
        tag="div",
        dom_attrs={},
        children=[btn_node]
    )

    comp_def = ComponentDefinition(
        name="ActionButton",
        props_schema={"label": "string"},
        root=container_node
    )

    # 2. Setup Common Data
    ir_tailwind_map = {
        "cont_001": "flex flex-col p-4 bg-gray-100",
        "btn_001": "px-4 py-2 bg-blue-500 text-white rounded"
    }
    cva_map = {
        "ButtonVariant": {
            "base_classes": "px-4 py-2 rounded",
            "variants": ["bg-blue-500", "bg-red-500"],
            "affected_node_ids": ["btn_001"]
        }
    }

    print("=== MULTI-FRAMEWORK EMISSION COMPARISON ===\n")

    # --- React ---
    react_emitter = ReactEmitter()
    react_jsx = react_emitter.emit_component(comp_def, ir_tailwind_map, cva_map)
    print("--- [REACT] ---")
    print(react_jsx)
    print("\n")

    # --- Next.js ---
    next_emitter = NextJsEmitter()
    next_jsx = next_emitter.emit_component(comp_def, ir_tailwind_map, cva_map)
    next_shell = emit_route_shell(comp_def, ir_tailwind_map, cva_map)
    print("--- [NEXT.JS] ---")
    print(f"Component:\n{next_jsx}")
    print(f"\nPage Shell:\n{next_shell['app/page.tsx']}")
    print(f"\nLayout Shell:\n{next_shell['app/layout.tsx']}")
    print("\n")

    # --- Vue 3 ---
    vue_emitter = VueEmitter()
    vue_sfc = vue_emitter.emit_sfc(comp_def, ir_tailwind_map, cva_map)
    print("--- [VUE 3] ---")
    print(vue_sfc)
    print("\n")

    # --- Angular 19 ---
    angular_emitter = AngularEmitter()
    angular_ts = angular_emitter.emit_component(comp_def, ir_tailwind_map, cva_map)
    print("--- [ANGULAR 19] ---")
    print(angular_ts)
    print("\n===========================================")

if __name__ == "__main__":
    asyncio.run(run_multi_framework_comparison())
