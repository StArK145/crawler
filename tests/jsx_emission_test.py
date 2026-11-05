import asyncio
from src.stage3_ast.m25_ast_schema import (
    PureExpr, ElementNode, TextNode, ComponentDefinition
)
from src.stage4_emission.react_emitter import ReactEmitter

async def test_jsx_emission():
    # 1. Construct Mock AST for the "Hug vs Fill" button
    # Structure: <div class="container"><button class="btn">Click Me</button></div>

    # Inner Text: "Click Me"
    text_expr = PureExpr(value="Click Me")
    btn_text = TextNode(
        kind="text",
        value=text_expr,
        preserve_inline_space=False
    )

    # Button: <button class="btn">
    btn_node = ElementNode(
        kind="element",
        ir_node_id="btn_001",
        tag="button",
        dom_attrs={},
        children=[btn_text]
    )

    # Container: <div class="container">
    container_node = ElementNode(
        kind="element",
        ir_node_id="cont_001",
        tag="div",
        dom_attrs={},
        children=[btn_node]
    )

    # Full Component Definition
    comp_def = ComponentDefinition(
        name="HugFillButton",
        props_schema={"label": "string"},
        root=container_node
    )

    # 2. Setup Emission Data
    # Mock the ir_tailwind_map
    ir_tailwind_map = {
        "cont_001": "flex flex-col p-4 bg-gray-100",
        "btn_001": "px-4 py-2 bg-blue-500 text-white rounded"
    }

    # Mock a CVA map to show variant emission for the button
    cva_map = {
        "ButtonVariant": {
            "base_classes": "px-4 py-2 rounded",
            "variants": ["bg-blue-500", "bg-red-500"],
            "affected_node_ids": ["btn_001"]
        }
    }

    # 3. Emit JSX
    emitter = ReactEmitter()
    jsx_output = emitter.emit_component(comp_def, ir_tailwind_map, cva_map)

    print("--- Compiled JSX Output ---")
    print(jsx_output)
    print("--------------------------")

if __name__ == "__main__":
    asyncio.run(test_jsx_emission())
