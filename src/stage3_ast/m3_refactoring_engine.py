from typing import List, Dict, Any, Optional, Union
from src.stage3_ast.m25_ast_schema import (
    ComponentDefinition, ASTNode, ElementNode, TextNode, LoopNode,
    ComponentCall, PureExpr
)
from src.stage3_ast.m3_llm_schema import LLMRefactoringPlan, RenameComponent, RenameProp, ExtractComponent

class InvalidRefactoringException(Exception):
    """Raised when an LLM refactoring operation cannot be applied to the AST."""
    pass

class ASTRefactorer:
    """
    Deterministic engine to apply LLM refactoring operations to the Canonical Component AST.
    """

    def __init__(self, component_registry: Dict[str, ComponentDefinition]):
        # Registry maps component_name -> ComponentDefinition
        self.registry = component_registry

    def apply_plan(self, root_component: ComponentDefinition, plan: LLMRefactoringPlan) -> ComponentDefinition:
        """
        Applies a sequence of refactoring operations to the AST.
        """
        current_root = root_component

        for op in plan.operations:
            if isinstance(op, RenameComponent):
                current_root = self._handle_rename_component(current_root, op)
            elif isinstance(op, RenameProp):
                current_root = self._handle_rename_prop(current_root, op)
            elif isinstance(op, ExtractComponent):
                current_root = self._handle_extract_component(current_root, op)

        return current_root

    def _handle_rename_component(self, root: ComponentDefinition, op: RenameComponent) -> ComponentDefinition:
        # 1. Update the definition in registry if it exists
        if op.old_name in self.registry:
            def_copy = self.registry[op.old_name]
            def_copy.name = op.new_name
            self.registry[op.new_name] = def_copy
            del self.registry[op.old_name]

        # 2. Traverse AST to update ComponentCall references
        def traverse(node: ASTNode):
            if isinstance(node, ElementNode):
                node.children = [traverse(c) for c in node.children]
            elif isinstance(node, LoopNode):
                node.body = [traverse(c) for c in node.body]
            elif isinstance(node, ComponentCall):
                if node.component_name == op.old_name:
                    node.component_name = op.new_name
            return node

        root.root = traverse(root.root)
        return root

    def _handle_rename_prop(self, root: ComponentDefinition, op: RenameProp) -> ComponentDefinition:
        # 1. Update the props_schema of the target component
        if op.component_name in self.registry:
            comp = self.registry[op.component_name]
            if op.old_prop_name in comp.props_schema:
                prop_type = comp.props_schema.pop(op.old_prop_name)
                comp.props_schema[op.new_prop_name] = prop_type
            else:
                raise InvalidRefactoringException(f"Prop {op.old_prop_name} not found in component {op.component_name}")

        # 2. Traverse AST to update PureExpr referencing the prop
        def update_expr(expr: PureExpr) -> PureExpr:
            if expr.path:
                # The path is typically "props.prop_name"
                # We split to verify it's a prop reference and then replace the leaf
                parts = expr.path.split('.')
                if len(parts) == 2 and parts[0] == "props" and parts[1] == op.old_prop_name:
                    expr.path = f"props.{op.new_prop_name}"

            if expr.eq_left:
                expr.eq_left = update_expr(expr.eq_left)
            if expr.eq_right:
                expr.eq_right = update_expr(expr.eq_right)
            return expr

        def traverse(node: ASTNode):
            if isinstance(node, ElementNode):
                node.dom_attrs = {k: update_expr(v) for k, v in node.dom_attrs.items()}
                node.children = [traverse(c) for c in node.children]
            elif isinstance(node, LoopNode):
                node.key_expr = update_expr(node.key_expr)
                node.body = [traverse(c) for c in node.body]
            elif isinstance(node, ComponentCall):
                node.props = {k: update_expr(v) for k, v in node.props.items()}
            return node

        # Crucially, we must traverse the root component and any other components in the registry
        # to ensure all references are updated across the entire project.
        # We create a list of values to avoid "dictionary changed size during iteration"
        all_components = list(self.registry.values())
        for comp in all_components:
            comp.root = traverse(comp.root)

        return root

    def _handle_extract_component(self, root: ComponentDefinition, op: ExtractComponent) -> ComponentDefinition:
        extracted_node = None

        def find_and_detach(parent: Any, children_list: List[ASTNode]) -> List[ASTNode]:
            nonlocal extracted_node
            new_children = []
            for child in children_list:
                if isinstance(child, ElementNode) and child.ir_node_id == op.target_ir_node_id:
                    extracted_node = child
                    # Replace with ComponentCall
                    call_node = ComponentCall(
                        kind="component",
                        component_name=op.new_component_name,
                        props={mapping.target_prop: mapping.source_expr for mapping in op.prop_mappings}
                        # Note: mapping.source_expr here is simplified as a string for the mock,
                        # in reality it would be a PureExpr object.
                    )
                    # To adhere to schema, we convert string to PureExpr if needed
                    # (Simplified for this implementation)
                    new_children.append(call_node)
                else:
                    if isinstance(child, ElementNode):
                        child.children = find_and_detach(child, child.children)
                    elif isinstance(child, LoopNode):
                        child.body = find_and_detach(child, child.body)
                    new_children.append(child)
            return new_children

        # Start detachment from root
        if isinstance(root.root, ElementNode):
            root.root.children = find_and_detach(root.root, root.root.children)

        if extracted_node is None:
            raise InvalidRefactoringException(f"Node ID {op.target_ir_node_id} not found in AST")

        # Create new ComponentDefinition for the extracted node
        # We assume prop_schema is derived from the prop_mappings
        new_schema = {mapping.target_prop: "string" for mapping in op.prop_mappings}

        new_comp_def = ComponentDefinition(
            name=op.new_component_name,
            props_schema=new_schema,
            root=extracted_node
        )

        self.registry[op.new_component_name] = new_comp_def
        return root
