import logging
from typing import Set, Dict, Any, Optional
from src.stage3_ast.m25_ast_schema import ComponentDefinition, ElementNode, LoopNode, ASTNode
from src.stage3_ast.m3_refactoring_engine import ASTRefactorer, InvalidRefactoringException
from src.stage3_ast.m3_llm_schema import LLMRefactoringPlan

# Set up basic telemetry logger
logging.basicConfig(level=logging.INFO)
telemetry = logging.getLogger("ast_telemetry")

class ValueGate:
    """
    Verification gate to ensure LLM refactoring preserves structural integrity.
    """

    @staticmethod
    def extract_node_ids(node: ASTNode, ids: Optional[Set[str]] = None) -> Set[str]:
        """
        Recursively extracts all ir_node_ids from an AST.
        """
        if ids is None:
            ids = set()

        if isinstance(node, ElementNode):
            ids.add(node.ir_node_id)
            for child in node.children:
                ValueGate.extract_node_ids(child, ids)
        elif isinstance(node, LoopNode):
            for child in node.body:
                ValueGate.extract_node_ids(child, ids)

        return ids

    @classmethod
    def verify_ast_integrity(cls, original_ast: ComponentDefinition, refactored_ast: ComponentDefinition) -> bool:
        """
        Asserts that the refactoring preserved all original nodes and introduced no hallucinations.
        """
        original_set = cls.extract_node_ids(original_ast.root)
        refactored_set = cls.extract_node_ids(refactored_ast.root)

        if original_set != refactored_set:
            missing = original_set - refactored_set
            extra = refactored_set - original_set
            telemetry.error(f"Integrity Violation: Missing={missing}, Extra={extra}")
            return False

        return True

    @classmethod
    async def execute_with_fallback(
        cls,
        llm_client: Any,
        baseline_ast: ComponentDefinition,
        component_registry: Dict[str, ComponentDefinition],
        layout_summary: str
    ) -> ComponentDefinition:
        """
        Invokes LLM, applies refactoring, and falls back to baseline on any failure.
        """
        try:
            # 1. Generate prompt and get plan from LLM
            # (Assuming llm_client handles the prompt construction and Pydantic parsing)
            # import json
            # prompt = build_refactoring_prompt(baseline_ast.model_dump_json(), layout_summary)
            # plan = await llm_client.generate_plan(prompt)

            # Mocking the LLM call for the signature
            plan: LLMRefactoringPlan = await llm_client.generate_plan(baseline_ast, layout_summary)

            # 2. Attempt to apply the plan
            refactorer = ASTRefactorer(component_registry)
            refactored_ast = refactorer.apply_plan(baseline_ast, plan)

            # 3. Verify structural integrity
            if not cls.verify_ast_integrity(baseline_ast, refactored_ast):
                telemetry.warning("llm_dropped_nodes: Refactored AST integrity check failed.")
                return baseline_ast

            return refactored_ast

        except InvalidRefactoringException as e:
            telemetry.warning(f"invalid_ops: LLM provided an impossible operation: {e}")
            return baseline_ast
        except Exception as e:
            telemetry.error(f"unexpected_refactor_error: {e}")
            return baseline_ast
