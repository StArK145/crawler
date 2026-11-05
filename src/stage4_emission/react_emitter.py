from typing import List, Dict, Any, Optional
from src.stage3_ast.m25_ast_schema import PureExpr, ElementNode, TextNode, LoopNode, ComponentCall, ComponentDefinition

class ReactEmitter:
    """
    Structural compiler that translates the Canonical Component AST into React/JSX code.
    """

    def emit_expression(self, expr: PureExpr) -> str:
        """
        Converts PureExpr into JS string equivalents.
        """
        if expr.value is not None:
            if isinstance(expr.value, str):
                return f"'{expr.value}'"
            return str(expr.value)

        if expr.path:
            return expr.path # e.g., 'props.title'

        if expr.eq_left and expr.eq_right:
            left = self.emit_expression(expr.eq_left)
            right = self.emit_expression(expr.eq_right)
            return f"({left} === {right})"

        return "null"

    def emit_node(self, node: Any, ir_tailwind_map: Dict[str, str], cva_map: Dict[str, Any]) -> str:
        """
        Recursively emits JSX for an AST node.
        """
        if isinstance(node, ElementNode):
            tag = node.tag
            # Determine class name emission
            classes = ir_tailwind_map.get(node.ir_node_id, "")

            # Check if this node is part of a CVA variant
            cva_variant_name = None
            for var_name, config in cva_map.items():
                if node.ir_node_id in config.get('affected_node_ids', []):
                    cva_variant_name = var_name
                    break

            # Build attributes
            attrs = []
            for attr_name, expr in node.dom_attrs.items():
                val = self.emit_expression(expr)
                attrs.append(f'{attr_name}={{ {val} }}')

            # Handle className
            if cva_variant_name:
                # We assume the CVA function is named after the variant (e.g., ButtonVariant -> buttonVariants)
                # and we default to a 'default' variant for the emission
                func_name = cva_variant_name[0].lower() + cva_variant_name[1:]
                # We strip 'Variant' to make it cleaner: ButtonVariant -> buttonVariants
                func_name = func_name.replace("Variant", "Variants")
                class_attr = f'className={{{func_name}({{ variant: \'default\' }})}}'
            elif classes:
                class_attr = f'className="{classes}"'
            else:
                class_attr = ""

            if class_attr:
                attrs.append(class_attr)

            # Recursively emit children
            children_jsx = "".join([self.emit_node(child, ir_tailwind_map, cva_map) for child in node.children])

            # Self-closing if no children
            if not children_jsx and not attrs:
                return f"<{tag} />"

            attr_str = " " + " ".join(attrs) if attrs else ""
            return f"<{tag}{attr_str}>{children_jsx}</{tag}>"

        elif isinstance(node, TextNode):
            expr_val = self.emit_expression(node.value)
            text = "{" + expr_val + "}"
            if node.preserve_inline_space:
                return '{" "} ' + text
            return text

        elif isinstance(node, LoopNode):
            iterable = self.emit_expression(node.iterable)
            item_var = node.item_var
            index_var = node.index_var
            key_expr = self.emit_expression(node.key_expr)

            # Recursively emit the body of the loop
            body_jsx = "".join([self.emit_node(child, ir_tailwind_map, cva_map) for child in node.body])

            return f"{{{iterable}.map(({item_var}, {index_var}) => <React.Fragment key={{{key_expr}}}>{body_jsx}</React.Fragment>)}}"

        elif isinstance(node, ComponentCall):
            tag = node.component_name
            props_attrs = []
            for prop_name, expr in node.props.items():
                val = self.emit_expression(expr)
                props_attrs.append(f'{prop_name}={{ {val} }}')

            attr_str = " " + " ".join(props_attrs) if props_attrs else ""
            return f"<{tag}{attr_str} />"

        return ""

    def emit_component(self, component_def: ComponentDefinition, ir_tailwind_map: Dict[str, str], cva_map: Dict[str, Any]) -> str:
        """
        Wraps the root node in a React functional component definition.
        """
        # Generate the function signature dynamically from the current props_schema
        props_list = []
        for prop_name, prop_type in component_def.props_schema.items():
            props_list.append(f"{prop_name}: {prop_type}")

        props_sig = "{" + ", ".join(props_list) + "}" if props_list else "{}"

        # Emit the root node
        root_jsx = self.emit_node(component_def.root, ir_tailwind_map, cva_map)

        # Wrap in functional component
        component_name = component_def.name
        return f"const {component_name} = ({props_sig}) => {{\n  return (\n    {root_jsx}\n  );\n}};"
