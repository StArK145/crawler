import asyncio
from typing import Dict
from src.stage3_ast.m25_ast_schema import (
    PureExpr, ElementNode, TextNode, ComponentDefinition
)
from src.stage3_ast.m3_llm_schema import LLMRefactoringPlan, RenameComponent, RenameProp
from src.stage3_ast.m3_refactoring_engine import ASTRefactorer
from src.stage3_ast.m3_value_gate import ValueGate
from src.stage4_emission.react_emitter import ReactEmitter

async def test_end_to_end_refactor():
    # 1. Construct Mock "Hug vs Fill" AST with generic names
    # <div class="container"><button class="btn">{props.prop_1}</button></div>

    # Dynamic prop expression for the button text
    prop_expr = PureExpr(path="props.prop_1")
    btn_text = TextNode(kind="text", value=prop_expr, preserve_inline_space=False)

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

    # Generic Component Definition
    baseline_ast = ComponentDefinition(
        name="Component_0",
        props_schema={"prop_1": "string"},
        root=container_node
    )

    # Registry for the refactorer
    registry = {"Component_0": baseline_ast}

    # 2. Mock LLM Output (Refactoring Plan)
    plan = LLMRefactoringPlan(operations=[
        RenameComponent(old_name="Component_0", new_name="HeroCTA"),
        RenameProp(component_name="Component_0", old_prop_name="prop_1", new_prop_name="ctaText")
    ])

    print("--- Starting Refactoring Process ---")

    # 3. Apply Refactoring
    refactorer = ASTRefactorer(registry)
    try:
        refactored_ast = refactorer.apply_plan(baseline_ast, plan)
        print("✅ Refactoring plan applied successfully.")
    except Exception as e:
        print(f"❌ Refactoring failed: {e}")
        return

    # 4. Verify Integrity (Value Gate)
    integrity_passed = ValueGate.verify_ast_integrity(baseline_ast, refactored_ast)
    print(f"Integrity Check: {'PASSED' if integrity_passed else 'FAILED'}")

    # 5. Emit final JSX
    # Mock tailwind map for final emission
    ir_tailwind_map = {
        "cont_001": "flex flex-col p-4 bg-gray-100",
        "btn_001": "px-4 py-2 bg-blue-500 text-white rounded"
    }
    cva_map = {} # No CVA for this simple check

    emitter = ReactEmitter()
    final_jsx = emitter.emit_component(refactored_ast, ir_tailwind_map, cva_map)

    print("\n--- Final Compiled JSX Output ---")
    print(final_jsx)
    print("---------------------------------")

    if integrity_passed:
        print("\nVerification: ir_node_id mappings were successfully preserved.")

if __name__ == "__main__":
    asyncio.run(test_end_to_end_refactor())
